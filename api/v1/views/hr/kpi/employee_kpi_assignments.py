from flask import request, jsonify, g, current_app
from api.v1.auth import login_required, role_required
from uuid import UUID
from api.v1.views import app_views
import traceback
from pydantic import ValidationError
from api.v1.services.hr.kpi_services import (
    EmployeeKPIAssignmentCreateSchema, EmployeeKPIAssignmentUpdateSchema
)


#get all employee kpi assignments
@app_views.route('/hr/kpi/employee-assignments/<uuid:employee_id>', methods=['GET'])
@login_required
@role_required(['hr_manager', 'super_admin', 'manager', 'user'])
def get_employee_kpi_assignments(employee_id):
    """Get all Employee KPI Assignments for a specific employee
    """
    try:
        response = g.supabase_user_client.from_('employee_kpi_assignments').select('*, kpi_id(title, description, weight, target_type, target_value, active, created_at)').eq('employee_id', str(employee_id)).eq('kpi_id.active', 'TRUE').execute()
        return jsonify({"assignments": response.data}), 200
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": str(e)}), 500

#create employee kpi assignment
@app_views.route('/hr/kpi/employee-assignments', methods=['POST'])
@login_required
@role_required(['hr_manager', 'super_admin'])
def create_employee_kpi_assignment():
    """Create a new Employee KPI Assignment
    """
    try:
        data = request.get_json()
        validated_data = EmployeeKPIAssignmentCreateSchema(**data)
        assignment_data = validated_data.model_dump()
        
        created_assignment = g.supabase_user_client.from_('employee_kpi_assignments').insert(assignment_data).execute()
        if not created_assignment.data:
            return jsonify({"error": "Failed to create Employee KPI Assignment"}), 500
        return jsonify(created_assignment.data[0]), 201
    except ValidationError as ve:
        current_app.logger.error(f"Validation error: {ve.errors()}")
        return jsonify({"error": ve.errors()}), 400
    
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": str(e)}), 500

#update employee kpi assignment
@app_views.route('/hr/kpi/employee-assignments/<uuid:assignment_id>', methods=['PUT'])
@login_required
@role_required(['hr_manager', 'super_admin', 'manager', 'user'])
def update_employee_kpi_assignment(assignment_id):
    """Update an existing Employee KPI Assignment
    """
    try:
        data = request.get_json()

        # limit user update to only these fields
        employee_allowed_fields = ['status', 'evidence_url', 'submitted_value', 'submitted_at']
        employee_assignment_data = data
        if g.user_role == 'user':
            employee_assignment_data = {k: v for k, v in data.items() if k in employee_allowed_fields}
            if len(employee_assignment_data) < len(data):
                raise ValueError(f'User is trying to access unauthorized fields. The only authorized fields are {employee_allowed_fields}')
        
        validated_data = EmployeeKPIAssignmentCreateSchema(**employee_assignment_data)
        assignment_data = validated_data.model_dump()        

        #check if status is present and set to 'Approved' or 'Rejected'
        if 'status' in assignment_data.keys() and assignment_data['status'] in ['Accepted', 'Rejected']:
            reviewed_by = g.supabase_user_client.from_('employees').select('id').eq('user_id', g.current_user).is_('deleted_at', 'null').execute()
            if not reviewed_by.data:
                return jsonify({'error': "Could not fetch Reviewer's data"}),  401
            reviewed_by_id = reviewed_by.data[0]['id']
            assignment_data['reviewed_by'] = reviewed_by_id


        updated_assignment = g.supabase_user_client.from_('employee_kpi_assignments').update(assignment_data).eq('id', str(assignment_id)).execute()
        if not updated_assignment.data:
            return jsonify({"error": "Failed to update Employee KPI Assignment"}), 500
        return jsonify(updated_assignment.data[0]), 200
    except ValidationError as ve:
        current_app.logger.error(f"Validation error: {ve.errors()}")
        return jsonify({"error": ve.errors()}), 400
    
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": str(e)}), 500
    

#delete employee kpi assignment
@app_views.route('/hr/kpi/employee-assignments/<uuid:assignment_id>', methods=['DELETE'])
@login_required
@role_required(['hr_manager', 'super_admin'])
def delete_employee_kpi_assignment(assignment_id):
    """Delete an Employee KPI Assignment
    """
    try:
        deleted_assignment = g.supabase_user_client.from_('employee_kpi_assignments').delete().eq('id', str(assignment_id)).execute()
        if not deleted_assignment.data:
            return jsonify({"error": "Employee KPI Assignment not found"}), 404
        return jsonify({"message": "Employee KPI Assignment deleted successfully"}), 200
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": str(e)}), 500