from flask import request, jsonify, g
from api.v1.views import app_views
from api.v1.auth import login_required, role_required
from uuid import UUID
from datetime import datetime
from pydantic import ValidationError
from api.v1.services.hr.shift_services import (
    ShiftTypeCreateSchema,
    ShiftTypeUpdateSchema,
    ShiftScheduleCreateSchema,
    ShiftScheduleUpdateSchema
)

def is_valid_uuid(uuid_string):
    try:
        UUID(uuid_string)
        return True
    except ValueError:
        return False


# GET all shift types → return empty list instead of 404
@app_views.route('/shift_types', methods=['GET'])
@login_required
@role_required(['super_admin', 'hr_manager', 'manager', 'user'])
def get_shift_types():
    try:
        response = g.supabase_user_client.from_('shift_types').select('*').execute()
        return jsonify(response.data or []), 200  # Always 200, empty list if none
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# GET single shift type → 404 only if ID invalid or not found
@app_views.route('/shift_types/<uuid:shift_type_id>', methods=['GET'])
@login_required
@role_required(['super_admin', 'hr_manager', 'manager', 'user'])
def get_shift_type(shift_type_id):
    if not is_valid_uuid(str(shift_type_id)):
        return jsonify({"error": "Invalid shift type ID format"}), 400

    try:
        response = g.supabase_user_client.from_('shift_types').select('*').eq('id', str(shift_type_id)).execute()
        if response.data:
            return jsonify(response.data[0]), 200
        return jsonify({"message": "Shift type not found"}), 404  # OK to keep 404 here
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# GET all current shift schedules (today) → return empty list if none today
@app_views.route('/shift_schedules', methods=['GET'])
@login_required
@role_required(['super_admin', 'hr_manager', 'manager'])
def get_shift_schedules():
    try:
        today_date = datetime.now().date().isoformat()
        response = g.supabase_user_client.from_('shift_schedules').select(
            '*, employee:employee_id(avatar_url, first_name, last_name, id, email)'
        ).lte('start_date', today_date).gte('end_date', today_date).execute()

        return jsonify(response.data or []), 200  # Empty array if no one is on shift today
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# GET employee's shift schedule history → return empty list if none
@app_views.route('/shift_schedules/employees/<uuid:employee_id>', methods=['GET'])
@login_required
@role_required(['super_admin', 'hr_manager', 'manager', 'user'])
def get_employee_shift_schedule(employee_id):
    if not is_valid_uuid(str(employee_id)):
        return jsonify({"error": "Invalid employee ID format"}), 400

    try:
        response = g.supabase_user_client.from_('shift_schedules') \
            .select('*') \
            .eq('employee_id', str(employee_id)) \
            .execute()

        return jsonify(response.data or []), 200  # Always 200, even if no history
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# The rest remain mostly unchanged — they already handle not-found correctly with 404
# (which is acceptable for single resource operations)

@app_views.route('/shift_types', methods=['POST'])
@login_required
@role_required(['super_admin', 'hr_manager'])
def create_shift_type():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided, request body must be JSON"}), 400
    try:
        shift_type_data = ShiftTypeCreateSchema(**data)
        response = g.service_supabase_client.from_('shift_types').insert(shift_type_data.model_dump()).execute()
        return jsonify(response.data[0]), 201
    except ValidationError as e:
        return jsonify({"error": "Validation failed", "details": e.errors()}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app_views.route('/shift_types/<uuid:shift_type_id>', methods=['PUT'])
@login_required
@role_required(['super_admin', 'hr_manager'])
def update_shift_type(shift_type_id):
    if not is_valid_uuid(str(shift_type_id)):
        return jsonify({"error": "Invalid shift type ID format"}), 400
    try:
        update_data = ShiftTypeUpdateSchema(**request.get_json())
        update_payload = update_data.model_dump(exclude_unset=True)
        response = g.service_supabase_client.from_('shift_types') \
            .update(update_payload).eq('id', str(shift_type_id)).execute()
        if response.data:
            return jsonify(response.data[0]), 200
        return jsonify({"error": "Shift type not found"}), 404
    except ValidationError as e:
        return jsonify({"error": "Validation failed", "details": e.errors()}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app_views.route('/shift_types/<uuid:shift_type_id>', methods=['DELETE'])
@login_required
@role_required(['super_admin', 'hr_manager'])
def delete_shift_type(shift_type_id):
    if not is_valid_uuid(str(shift_type_id)):
        return jsonify({"error": "Invalid shift type ID format"}), 400
    try:
        response = g.service_supabase_client.from_('shift_types').delete().eq('id', str(shift_type_id)).execute()
        if response.data:
            return jsonify({"message": f"Shift type {shift_type_id} deleted successfully"}), 200
        return jsonify({"error": "Shift type not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app_views.route('/shift_schedules', methods=['POST'])
@login_required
@role_required(['super_admin', 'hr_manager'])
def create_shift_schedule():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided, request body must be JSON"}), 400
    try:
        schedule_data = ShiftScheduleCreateSchema(**data)
        # Check for overlap
        existing = g.supabase_user_client.from_('shift_schedules') \
            .select('id') \
            .eq('employee_id', schedule_data.employee_id) \
            .lte('start_date', schedule_data.end_date) \
            .gte('end_date', schedule_data.start_date) \
            .execute()

        if existing.data:
            return jsonify({"error": "Overlapping shift schedule exists for this employee"}), 400

        response = g.service_supabase_client.from_('shift_schedules') \
            .insert(schedule_data.model_dump()).execute()
        return jsonify(response.data[0]), 201
    except ValidationError as e:
        return jsonify({"error": "Validation failed", "details": e.errors()}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app_views.route('/shift_schedules/<uuid:schedule_id>', methods=['PUT'])
@login_required
@role_required(['super_admin', 'hr_manager'])
def update_shift_schedule(schedule_id):
    if not is_valid_uuid(str(schedule_id)):
        return jsonify({"error": "Invalid schedule ID format"}), 400
    try:
        update_data = ShiftScheduleUpdateSchema(**request.get_json())
        update_payload = update_data.model_dump(exclude_unset=True)
        response = g.service_supabase_client.from_('shift_schedules') \
            .update(update_payload).eq('id', str(schedule_id)).execute()
        if response.data:
            return jsonify(response.data[0]), 200
        return jsonify({"error": "Shift schedule not found"}), 404
    except ValidationError as e:
        return jsonify({"error": "Validation failed", "details": e.errors()}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app_views.route('/shift_schedules/<uuid:schedule_id>', methods=['DELETE'])
@login_required
@role_required(['super_admin', 'hr_manager'])
def delete_shift_schedule(schedule_id):
    if not is_valid_uuid(str(schedule_id)):
        return jsonify({"error": "Invalid schedule ID format"}), 400
    try:
        response = g.service_supabase_client.from_('shift_schedules') \
            .delete().eq('id', str(schedule_id)).execute()
        if response.data:
            return jsonify({"message": f"Shift schedule {schedule_id} deleted successfully"}), 200
        return jsonify({"error": "Shift schedule not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500