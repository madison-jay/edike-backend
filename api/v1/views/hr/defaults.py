from flask import current_app, request, jsonify, g
from api.v1.auth import login_required, role_required, service_supabase_client
from api.v1.views import app_views
from api.v1.services.hr.payroll_services import (
    DeductionCreateSchema,
    DeductionUpdateSchema,
    DefaultChargeCreateSchema,
    DefaultChargeUpdateSchema,
)
from pydantic import ValidationError
import re
from uuid import UUID

@app_views.route('/default_charges', methods=['GET'])
@login_required
@role_required(['super_admin', 'hr_manager', 'manager', 'user'])
def get_default_charges():
    try:
        response = g.supabase_user_client.from_('default_charges').select('*').execute()
        if response.data:
            return jsonify(response.data), 200
        return jsonify({"message": "No default charges found"}), 204
    except Exception as e:
        current_app.logger.error(f"Error fetching default charges: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app_views.route('/default_charges/<uuid:default_charge_id>', methods=['GET'])
@login_required
@role_required(['super_admin', 'hr_manager', 'manager', 'user'])
def get_default_charge(default_charge_id):
    try:
        response = g.supabase_user_client.from_('default_charges').select('*').eq('id', default_charge_id).execute()
        if response.data:
            return jsonify(response.data), 200
        return jsonify({"message": "Default charge not found"}), 404
    except Exception as e:
        current_app.logger.error(f"Error fetching default charge {default_charge_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app_views.route('/default_charges', methods=['POST'])
@login_required
@role_required(['super_admin', 'hr_manager'])
def create_default_charge():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided, request body must be JSON"}), 400
    try:
        creator_response = g.supabase_user_client.from_('employees').select('id').eq('user_id', g.current_user).execute()
        if not creator_response.data:
            print(creator_response)
            return jsonify({"error": "Creator employee record not found"}), 404
        data['created_by'] = creator_response.data[0]['id']

        default_charge = DefaultChargeCreateSchema(**data)

        existing = g.supabase_user_client.from_('default_charges').select('id').eq('charge_name', default_charge.charge_name).execute()
        if existing.data:
            return jsonify({"error": "Default charge with this name already exists"}), 400
        response = g.supabase_user_client.from_('default_charges').insert(default_charge.model_dump()).execute()
        if response.data:
            return jsonify(response.data[0]), 201
        return jsonify({"error": "Failed to create default charge"}), 500
    except ValidationError as ve:
        current_app.logger.error(f"Validation error creating default charge: {str(ve)}")
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        current_app.logger.error(f"Error creating default charge: {str(e)}")
        return jsonify({"error": str(e)}), 500
    

@app_views.route('/default_charges/<uuid:default_charge_id>', methods=['PUT'])
@login_required
@role_required(['super_admin', 'hr_manager'])
def update_default_charge(default_charge_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided, request body must be JSON"}), 400
    try:
        update_data = DefaultChargeUpdateSchema(**data)
        update_payload = update_data.model_dump(exclude_unset=True)
        if 'charge_name' in update_payload:
            existing = g.supabase_user_client.from_('default_charges').select('id').eq('charge_name', update_payload['charge_name']).neq('id', default_charge_id).execute()
            if existing.data:
                return jsonify({"error": "Default charge with this name already exists"}), 400
        response = g.supabase_user_client.from_('default_charges').update(update_payload).eq('id', default_charge_id).execute()
        if response.data:
            return jsonify(response.data[0]), 200
        return jsonify({"error": "Default charge not found"}), 404
    except ValidationError as ve:
        current_app.logger.error(f"Validation error updating default charge {default_charge_id}: {str(ve)}")
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        current_app.logger.error(f"Error updating default charge {default_charge_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500
    
@app_views.route('/default_charges/<uuid:default_charge_id>', methods=['DELETE'])
@login_required
@role_required(['super_admin', 'hr_manager'])
def delete_default_charge(default_charge_id):
    try:
        deductions_check = g.supabase_user_client.from_('deductions').select('id').eq('default_charge_id', default_charge_id).is_('deleted_at', 'null').execute()
        if deductions_check.data:
            return jsonify({"error": "Default charge is in use and cannot be deleted"}), 400
        response = g.supabase_user_client.from_('default_charges').delete().eq('id', default_charge_id).execute()
        if response.data:
            return jsonify({"message": "Default charge deleted successfully"}), 200
        return jsonify({"error": "Default charge not found"}), 404
    except Exception as e:
        current_app.logger.error(f"Error deleting default charge {default_charge_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500