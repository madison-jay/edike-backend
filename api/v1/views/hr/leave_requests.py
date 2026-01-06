# api/v1/views/__init__.py (leave requests section)

from flask import request, jsonify, g
from api.v1.views import app_views
from api.v1.auth import login_required, role_required
from uuid import UUID
from datetime import date
from pydantic import ValidationError
from api.v1.services.hr.leave_services import (
    LeaveRequestCreateSchema,
    LeaveRequestUpdateSchema,
    LeaveBalanceUpdateSchema,
    ALLOWED_STATUSES
)


def is_valid_uuid(uuid_string):
    try:
        UUID(uuid_string)
        return True
    except ValueError:
        return False


# GET all leave requests (role-based filtering)
@app_views.route('/leave_requests', methods=['GET'])
@login_required
@role_required(['super_admin', 'hr_manager', 'manager', 'user'])
def get_leave_requests():
    """
    Get leave requests with role-based access:
    - super_admin, hr_manager: All requests
    - manager: Requests from employees in their department
    - user: Only their own requests
    """
    try:
        query = g.supabase_user_client.from_('leave_requests').select(
            '*, employee:employee_id(id, first_name, last_name, avatar_url, email), '
            'approver:approved_by(id, first_name, last_name, email)'
        )

        # Role-based filtering
        if g.user_role == 'user':
            # Find employee's ID from current user
            emp_res = g.supabase_user_client.from_('employees') \
                .select('id').eq('user_id', g.current_user).single().execute()
            if not emp_res.data:
                return jsonify({"error": "Employee profile not found"}), 404
            query = query.eq('employee_id', emp_res.data['id'])

        elif g.user_role == 'manager':
            # Find manager's employee record
            mgr_res = g.supabase_user_client.from_('employees') \
                .select('department_id').eq('user_id', g.current_user).single().execute()
            if not mgr_res.data or not mgr_res.data.get('department_id'):
                return jsonify({"error": "Manager has no department assigned"}), 403

            # Get employees in the same department
            dept_employees = g.supabase_user_client.from_('employees') \
                .select('id').eq('department_id', mgr_res.data['department_id']).execute()
            employee_ids = [emp['id'] for emp in dept_employees.data]
            if not employee_ids:
                return jsonify([]), 200
            query = query.in_('employee_id', employee_ids)

        # super_admin and hr_manager → see all (no filter)

        response = query.execute()
        return jsonify(response.data or []), 200  # Always 200, even if empty

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# GET single leave request by ID
@app_views.route('/leave_requests/<uuid:request_id>', methods=['GET'])
@login_required
@role_required(['super_admin', 'hr_manager', 'manager', 'user'])
def get_leave_request(request_id):
    if not is_valid_uuid(str(request_id)):
        return jsonify({"error": "Invalid request ID format"}), 400

    try:
        response = g.supabase_user_client.from_('leave_requests').select(
            '*, employee:employee_id(id, first_name, last_name, avatar_url, email), '
            'approver:approved_by(id, first_name, last_name, email)'
        ).eq('id', str(request_id)).single().execute()

        if response.data:
            return jsonify(response.data), 200
        return jsonify({"error": "Leave request not found"}), 404

    except Exception as e:
        # Handles case where no row found (Supabase raises error on .single() if empty)
        if "No rows returned" in str(e) or "empty" in str(e).lower():
            return jsonify({"error": "Leave request not found"}), 404
        return jsonify({"error": str(e)}), 500


# CREATE leave request
@app_views.route('/leave_requests', methods=['POST'])
@login_required
@role_required(['super_admin', 'hr_manager', 'user'])
def create_leave_request():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided, request body must be JSON"}), 400

    try:
        leave_data = LeaveRequestCreateSchema(**data)

        # Validate date range
        delta = (leave_data.end_date - leave_data.start_date).days + 1
        if delta <= 0:
            return jsonify({"error": "End date must be after or same as start date"}), 400

        # Determine employee_id
        if g.user_role == 'user':
            emp_res = g.supabase_user_client.from_('employees') \
                .select('id, leave_balance').eq('user_id', g.current_user).single().execute()
            if not emp_res.data:
                return jsonify({"error": "No employee record found for current user"}), 403
            employee_id = emp_res.data['id']
            current_balance = emp_res.data['leave_balance']
        else:
            employee_id = data.get('employee_id')
            if not employee_id or not is_valid_uuid(employee_id):
                return jsonify({"error": "Valid employee_id is required"}), 400
            emp_res = g.supabase_user_client.from_('employees') \
                .select('leave_balance').eq('id', employee_id).single().execute()
            if not emp_res.data:
                return jsonify({"error": "Employee not found"}), 404
            current_balance = emp_res.data['leave_balance']

        # Check balance
        if current_balance < delta:
            return jsonify({
                "error": "Insufficient leave balance",
                "current_balance": current_balance,
                "requested_days": delta
            }), 400

        # Insert request
        payload = {
            "employee_id": employee_id,
            "leave_type": leave_data.leave_type,
            "start_date": leave_data.start_date.isoformat(),
            "end_date": leave_data.end_date.isoformat(),
            "reason": leave_data.reason,
            "status": "pending"  # default
        }

        response = g.supabase_user_client.from_('leave_requests').insert(payload).execute()
        return jsonify(response.data[0]), 201

    except ValidationError as e:
        return jsonify({"error": "Validation failed", "details": e.errors()}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# UPDATE leave request (approve/reject/cancel)
@app_views.route('/leave_requests/<uuid:request_id>', methods=['PUT'])
@login_required
@role_required(['super_admin', 'hr_manager', 'manager', 'user'])
def update_leave_request(request_id):
    if not is_valid_uuid(str(request_id)):
        return jsonify({"error": "Invalid request ID format"}), 400

    try:
        update_data = LeaveRequestUpdateSchema(**request.get_json())
        update_payload = update_data.model_dump(exclude_unset=True)

        if not update_payload:
            return jsonify({"error": "No update data provided"}), 400

        # Users can only cancel their own requests
        if g.user_role == 'user':
            if 'status' not in update_payload or update_payload['status'] != 'cancelled':
                return jsonify({"error": "Users can only cancel their own requests"}), 403

        # Fetch current request to validate permissions and balance
        req_res = g.supabase_user_client.from_('leave_requests') \
            .select('employee_id, start_date, end_date, status').eq('id', str(request_id)).single().execute()

        if not req_res.data:
            return jsonify({"error": "Leave request not found"}), 404

        current_status = req_res.data['status']

        # Prevent re-approval/rejection
        if current_status != 'pending' and 'status' in update_payload:
            return jsonify({"error": f"Cannot update request with status '{current_status}'"}), 400

        # Handle approval → deduct leave balance
        if 'status' in update_payload and update_payload['status'] == 'approved':
            delta = (date.fromisoformat(req_res.data['end_date']) - date.fromisoformat(req_res.data['start_date'])).days + 1
            emp_balance = g.supabase_user_client.from_('employees') \
                .select('leave_balance').eq('id', req_res.data['employee_id']).single().execute()
            if emp_balance.data['leave_balance'] < delta:
                return jsonify({"error": "Insufficient leave balance"}), 400

            g.supabase_user_client.from_('employees') \
                .update({"leave_balance": emp_balance.data['leave_balance'] - delta}) \
                .eq('id', req_res.data['employee_id']).execute()

            # Set approver
            approver_res = g.supabase_user_client.from_('employees') \
                .select('id').eq('user_id', g.current_user).single().execute()
            if approver_res.data:
                update_payload['approved_by'] = approver_res.data['id']

        # Execute update
        response = g.supabase_user_client.from_('leave_requests') \
            .update(update_payload).eq('id', str(request_id)).execute()

        if response.data:
            return jsonify(response.data[0]), 200
        return jsonify({"error": "Leave request not found or no changes applied"}), 404

    except ValidationError as e:
        return jsonify({"error": "Validation failed", "details": e.errors()}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# DELETE leave request (admin only)
@app_views.route('/leave_requests/<uuid:request_id>', methods=['DELETE'])
@login_required
@role_required(['super_admin', 'hr_manager'])
def delete_leave_request(request_id):
    if not is_valid_uuid(str(request_id)):
        return jsonify({"error": "Invalid request ID format"}), 400

    try:
        response = g.supabase_user_client.from_('leave_requests') \
            .delete().eq('id', str(request_id)).execute()

        if response.data:
            return jsonify({"message": f"Leave request {request_id} deleted successfully"}), 200
        return jsonify({"error": "Leave request not found"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# UPDATE employee leave balance (super_admin only)
@app_views.route('/employees/<uuid:employee_id>/leave_balance', methods=['PUT'])
@login_required
@role_required(['super_admin'])
def update_leave_balance(employee_id):
    if not is_valid_uuid(str(employee_id)):
        return jsonify({"error": "Invalid employee ID format"}), 400

    try:
        update_data = LeaveBalanceUpdateSchema(**request.get_json())
        update_payload = update_data.model_dump(exclude_unset=True)

        if 'leave_balance' not in update_payload:
            return jsonify({"error": "leave_balance field is required"}), 400

        response = g.supabase_user_client.from_('employees') \
            .update(update_payload).eq('id', str(employee_id)).execute()

        if response.data:
            return jsonify(response.data[0]), 200
        return jsonify({"error": "Employee not found"}), 404

    except ValidationError as e:
        return jsonify({"error": "Validation failed", "details": e.errors()}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500