from flask import current_app, request, jsonify, g
from api.v1.auth import login_required, role_required, service_supabase_client
from uuid import UUID
from api.v1.views import app_views
from pydantic import ValidationError

from api.v1.services.hr.payroll_services import (
    DeductionCreateSchema,
    DeductionUpdateSchema,
    is_valid_uuid,
)


@app_views.route('employee/deductions/<uuid:employee_id>', methods=['GET'])
@login_required
@role_required(['super_admin', 'hr_manager', 'manager', 'user'])
def get_deductions(employee_id):
    try:
        if g.user_role not in ['super_admin', 'hr_manager']:
            user_employee_id = g.supabase_user_client.from_('employees').select('id').eq('user_id', g.current_user).execute()
            if not user_employee_id.data or user_employee_id.data[0]['id'] != employee_id:
                return jsonify({"error": "Unauthorized access to another employee's information"}), 403
        response = g.supabase_user_client.from_('deductions').select('id, employee:employee_id(first_name, last_name), pardoned_fee, status, reason, instances, default_charge:default_charge_id(id, charge_name, description, penalty_fee)').eq('employee_id', employee_id).execute()
        if response.data:
            return jsonify(response.data), 200
        return jsonify({"message": "No deductions found for this employee"}), 204
    except Exception as e:
        current_app.logger.error(f"Error fetching deductions for employee {employee_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app_views.route('deductions/', methods=['POST'])
@login_required
@role_required(['super_admin', 'hr_manager'])
def create_deduction():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided, request body must be JSON"}), 400
    try:
        creator_response = g.supabase_user_client.from_('employees').select('id').eq('user_id', g.current_user).execute()
        if not creator_response.data:
            return jsonify({"error": "Creator employee record not found"}), 404
        data['created_by'] = creator_response.data[0]['id']
        deduction_data = DeductionCreateSchema(**data)
        
        employee_check = g.supabase_user_client.from_('employees').select('id').eq('id', deduction_data.employee_id).execute()
        if not employee_check.data:
            return jsonify({"error": "Employee not found"}), 404
        
        # Check if the default charge exists
        default_charge_check = g.supabase_user_client.from_('default_charges').select('id, penalty_fee').eq('id', deduction_data.default_charge_id).execute()
        if not default_charge_check.data:
            return jsonify({"error": "Default charge not found"}), 404

        deduction_data.pardoned_fee = default_charge_check.data[0]['penalty_fee'] if deduction_data.pardoned_fee is None else deduction_data.pardoned_fee 
        
        instance_check = g.supabase_user_client.from_('deductions').select('id, instances').eq('employee_id', deduction_data.employee_id).eq('default_charge_id', deduction_data.default_charge_id).eq('status', 'pending').execute()
        if instance_check.data:
            return jsonify({"error": "An instance of this deduction already exists for this employee. Update the instances instead"}), 400

        deduction_response = g.supabase_user_client.from_('deductions').insert(deduction_data.model_dump()).execute()
        return jsonify(deduction_response.data[0]), 201
    except ValidationError as ve:
        current_app.logger.error(f"Validation error in create_deduction: {ve.errors()}")
        return jsonify({"error": "Validation failed", "details": ve.errors()}), 400
    except Exception as e:
        current_app.logger.error(f"Error creating deduction: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app_views.route('deductions/<uuid:deduction_id>', methods=['PUT'])
@login_required
@role_required(['super_admin', 'hr_manager'])
def update_deduction(deduction_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided, request body must be a JSON"})
    try:
        update_data = DeductionUpdateSchema(**data)
        update_payload = update_data.model_dump(exclude_unset=True)
        response = g.supabase_user_client.from_('deductions').update(update_payload).eq('id', deduction_id).execute()
        if response.data:
            return jsonify(response.data[0]), 200
        return jsonify({"message": "Deduction not found or no changes made"}), 404
    except ValidationError as ve:
        current_app.logger.error(f"Validation error in update_deduction: {ve.errors()}")
        return jsonify({"error": "Validation failed", "details": ve.errors()}), 400
    except Exception as e:
        current_app.logger.error(f"Error updating deduction {deduction_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

    