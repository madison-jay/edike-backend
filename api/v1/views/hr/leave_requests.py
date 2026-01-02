# api/v1/views/__init__.py
from flask import Blueprint, request, jsonify, g
from api.v1.auth import login_required, role_required, service_supabase_client
from uuid import UUID
from api.v1.views import app_views
from pydantic import ValidationError
from datetime import date
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


# Leave Request Endpoints
@app_views.route('/leave_requests', methods=['GET'])
@login_required
@role_required(['super_admin', 'hr_manager', 'manager', 'user'])
def get_leave_requests():
    """
    Get leave requests.
    - super_admin, hr_manager: All requests.
    - manager: Requests in their department.
    - user: Their own requests.
    """
    try:
        response = g.supabase_user_client.from_('leave_requests').select(
            '*, employee:employee_id(first_name, avatar_url, last_name, email), approver:approved_by(first_name, last_name, email)'
        ).execute()
        if response.data:
            return jsonify(response.data), 200
        return jsonify({"message": "No leave requests found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app_views.route('/leave_requests/<uuid:request_id>', methods=['GET'])
@login_required
@role_required(['super_admin', 'hr_manager', 'manager', 'user'])
def get_leave_request(request_id):
    """
    Get a single leave request by ID.
    """
    if not is_valid_uuid(str(request_id)):
        return jsonify({"error": "Invalid request ID format"}), 400
    try:
        response = g.supabase_user_client.from_('leave_requests').select(
            '*, employee:employee_id(first_name, last_name, avatar_url, email), approver:approved_by(first_name, last_name, email)'
        ).execute()
        if response.data:
            return jsonify(response.data[0]), 200
        return jsonify([]), 204
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app_views.route('/leave_requests', methods=['POST'])
@login_required
@role_required(['super_admin', 'hr_manager', 'user'])
def create_leave_request():
    """
    Create a leave request.
    - user: Creates for themselves.
    - super_admin, hr_manager: Can specify employee_id.
    """
    data = request.json
    if not data:
        return jsonify({"error": "No data provided, request body must be JSON"}), 400
    try:
        leave_data = LeaveRequestCreateSchema(**data)
        
        # Validate dates
        delta = (leave_data.end_date - leave_data.start_date).days + 1
        if delta <= 0:
            return jsonify({"error": "End date must be after start date"}), 400

        # Get employee_id
        if g.user_role == 'user':
            employee_response = g.supabase_user_client.from_('employees').select('id, leave_balance').eq('user_id', g.current_user).execute()
            if not employee_response.data:
                return jsonify({"error": "No employee record found for user"}), 403
            employee_id = employee_response.data[0]['id']
            current_balance = employee_response.data[0]['leave_balance']
        else:
            employee_id = data.get('employee_id')
            if not employee_id or not is_valid_uuid(employee_id):
                return jsonify({"error": "Valid employee_id required for admin creation"}), 400
            employee_response = g.supabase_user_client.from_('employees').select('leave_balance').eq('id', employee_id).execute()
            if not employee_response.data:
                return jsonify({"error": "Employee not found"}), 404
            current_balance = employee_response.data[0]['leave_balance']

        # Check leave balance
        if current_balance < delta:
            return jsonify({"error": "Insufficient leave balance", "current_balance": current_balance, "requested_days": delta}), 400

        # Create leave request
        leave_request = {
            "employee_id": employee_id,
            "leave_type": leave_data.leave_type,
            "start_date": leave_data.start_date.isoformat(),
            "end_date": leave_data.end_date.isoformat(),
            "reason": leave_data.reason
        }
        response = g.supabase_user_client.from_('leave_requests').insert(leave_request).execute()
        return jsonify(response.data[0]), 201
    except ValidationError as e:
        return jsonify({"error": "Validation failed", "details": e.errors()}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app_views.route('/leave_requests/<uuid:request_id>', methods=['PUT'])
@login_required
@role_required(['super_admin', 'hr_manager', 'manager', 'user'])
def update_leave_request(request_id):
    """
    Update a leave request (approve, reject, cancel).
    - user: Can only cancel.
    - manager: Can approve/reject in their department.
    - super_admin, hr_manager: Can update any request.
    """
    if not is_valid_uuid(str(request_id)):
        return jsonify({"error": "Invalid request ID format"}), 400
    try:
        update_data = LeaveRequestUpdateSchema(**request.json)
        update_payload = update_data.model_dump(exclude_unset=True)

        if g.user_role == 'user' and update_data.status and update_data.status != 'cancelled':
            return jsonify({"error": "Users can only cancel their own requests"}), 403

        if update_data.status in ['approved', 'rejected']:
            # Record approver
            print("Current user:", g.current_user)
            employee_response = g.supabase_user_client.from_('employees').select('id').eq('user_id', g.current_user).execute()
            if not employee_response.data:
                return jsonify({"error": "No employee record found for approver"}), 403
            update_payload['approved_by'] = employee_response.data[0]['id']

            # Update leave balance if approved
            if update_data.status == 'approved':
                request_response = g.supabase_user_client.from_('leave_requests').select('employee_id, start_date, end_date').eq('id', str(request_id)).execute()
                if not request_response.data:
                    return jsonify({"error": "Leave request not found"}), 404
                request_data = request_response.data[0]
                delta = (date.fromisoformat(request_data['end_date']) - date.fromisoformat(request_data['start_date'])).days + 1
                employee_response = g.supabase_user_client.from_('employees').select('leave_balance').eq('id', request_data['employee_id']).execute()
                if not employee_response.data or employee_response.data[0]['leave_balance'] < delta:
                    return jsonify({"error": "Insufficient leave balance"}), 400
                new_balance = {"leave_balance": employee_response.data[0]['leave_balance'] - delta}
                g.supabase_user_client.from_('employees').update(new_balance).eq('id', request_data['employee_id']).execute()

        response = g.supabase_user_client.from_('leave_requests').update(update_payload).eq('id', str(request_id)).execute()
        if response.data:
            return jsonify(response.data[0]), 200
        return jsonify({"error": "Failed to update leave request or not found"}), 404
    except ValidationError as e:
        return jsonify({"error": "Validation failed", "details": e.errors()}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app_views.route('/leave_requests/<uuid:request_id>', methods=['DELETE'])
@login_required
@role_required(['super_admin', 'hr_manager'])
def delete_leave_request(request_id):
    """
    Delete a leave request (admin only).
    """
    if not is_valid_uuid(str(request_id)):
        return jsonify({"error": "Invalid request ID format"}), 400
    try:
        response = g.supabase_user_client.from_('leave_requests').delete().eq('id', str(request_id)).execute()
        if response.data:
            return jsonify({"message": f"Leave request {request_id} deleted successfully"}), 200
        return jsonify({"error": "Leave request not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app_views.route('/employees/<uuid:employee_id>/leave_balance', methods=['PUT'])
@login_required
@role_required(['super_admin'])
def update_leave_balance(employee_id):
    """
    Update an employee's leave balance (super_admin only).
    """
    if not is_valid_uuid(str(employee_id)):
        return jsonify({"error": "Invalid employee ID format"}), 400
    try:
        update_data = LeaveBalanceUpdateSchema(**request.json)
        update_payload = update_data.model_dump()
        response = g.supabase_user_client.from_('employees').update(update_payload).eq('id', str(employee_id)).execute()
        if response.data:
            return jsonify(response.data[0]), 200
        return jsonify({"error": "Employee not found"}), 404
    except ValidationError as e:
        return jsonify({"error": "Validation failed", "details": e.errors()}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500