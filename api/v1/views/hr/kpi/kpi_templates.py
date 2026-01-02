from flask import request, jsonify, g, current_app
from api.v1.auth import login_required, role_required
from uuid import UUID
from api.v1.views import app_views
import traceback
from pydantic import ValidationError
from api.v1.services.hr.kpi_services import (

    KPIRoleAssignmentCreateSchema, KPIRoleAssignmentUpdateSchema,
    KPITemplateCreateSchema, KPITemplateUpdateSchema
)



#get all kpi templates
@app_views.route('/hr/kpi/templates', methods=['GET'])
@login_required
@role_required(['hr_manager', 'super_admin'])
def get_kpi_templates():
    """Get all KPI templates and the role assignments"""
    try:
        if g.user_role in ['hr_manager', 'super_admin']:
            templates = g.supabase_user_client.rpc('get_kpi_assignments_with_names').execute()
        else:
            templates = g.supabase_user_client.from_('kpi_templates').select('*').execute() 
        return jsonify({"templates": templates.data}), 200
    
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": str(e)}), 500

#get kpi template by id
@app_views.route('/hr/kpi/templates/<uuid:template_id>', methods=['GET'])
@login_required
@role_required(['hr_manager', 'super_admin', 'manager', 'user'])
def get_kpi_template(template_id):
    """Get a KPI template by ID
    """
    try:
        response = g.supabase_user_client.from_('kpi_templates').select('*').eq('kpi_id', str(template_id)).execute()
        if response.data:
            return jsonify(response.data[0]), 200
        return jsonify({"error": "KPI template not found"}), 404
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": str(e)}), 500

#Create a kpi template
@app_views.route('/hr/kpi/templates', methods=['POST'])
@login_required
@role_required(['hr_manager', 'super_admin'])
def create_kpi_template():
    """Create a new KPI template
    """
    try:
        data = request.get_json()
        validated_data = KPITemplateCreateSchema(**data)
        template_data = validated_data.model_dump()

        created_template = g.supabase_user_client.from_('kpi_templates').insert(template_data).execute()
        if not created_template.data:
            return jsonify({"error": "Failed to create KPI template"}), 500
        return jsonify(created_template.data[0]), 201
    except ValidationError as ve:
        current_app.logger.error(f"Validation error: {ve.errors()}")
        return jsonify({"error": ve.errors()}), 400
    
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": str(e)}), 500

#update kpi template
@app_views.route('/hr/kpi/templates/<uuid:template_id>', methods=['PUT'])
@login_required
@role_required(['hr_manager', 'super_admin'])
def update_kpi_template(template_id):
    """Update an existing KPI template
    """
    try:
        data = request.get_json()
        validated_data = KPITemplateUpdateSchema(**data)
        template_data = validated_data.model_dump()

        updated_template = g.supabase_user_client.from_('kpi_templates').update(template_data).eq('kpi_id', template_id).execute()
        if not updated_template.data:
            return jsonify({"error": "Failed to update KPI template"}), 500
        return jsonify(updated_template.data[0]), 200
    except ValidationError as ve:
        current_app.logger.error(f"Validation error: {ve.errors()}")
        return jsonify({"error": ve.errors()}), 400

    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": str(e)}), 500

#delete kpi template
@app_views.route('/hr/kpi/templates/<uuid:template_id>', methods=['DELETE'])
@login_required
@role_required(['hr_manager', 'super_admin'])
def delete_kpi_template(template_id):
    """Delete a KPI template
    """
    try:
        deleted_template = g.supabase_user_client.from_('kpi_templates').delete().eq('kpi_id', template_id).execute()
        if not deleted_template.data:
            return jsonify({"error": "Failed to delete KPI template"}), 500
        return jsonify({"message": "KPI template deleted successfully"}), 200
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app_views.route('/hr/kpi/role-assignments', methods=['GET'])
@login_required
@role_required(['hr_manager', 'super_admin'])
def get_kpi_role_assignments():
    """Get all KPI role and department assignments"""
    try:
        assignments = g.supabase_user_client.from_('kpi_role_assignments').select('*').execute()
        return jsonify(assignments.data), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching KPI assignments: {str(e)}")
        return jsonify({"error": str(e)}), 500

#create kpi role assignment
@app_views.route('/hr/kpi/role-assignments', methods=['POST'])
@login_required
@role_required(['hr_manager', 'super_admin'])
def create_kpi_role_assignment():
    """Create a new KPI role assignment
    """
    try:
        data = request.get_json()
        validated_data = KPIRoleAssignmentCreateSchema(**data)
        assignment_data = validated_data.model_dump()

        created_assignment = g.supabase_user_client.from_('kpi_role_assignments').insert(assignment_data).execute()
        if not created_assignment.data:
            return jsonify({"error": "Failed to create KPI role assignment"}), 500
        return jsonify(created_assignment.data[0]), 201
    except ValidationError as ve:
        current_app.logger.error(f"Validation error: {ve.errors()}")
        return jsonify({"error": ve.errors()}), 400
    
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": str(e)}), 500

#update kpi role assignment
@app_views.route('/hr/kpi/role-assignments/<uuid:assignment_id>', methods=['PUT'])
@login_required
@role_required(['hr_manager', 'super_admin'])
def update_kpi_role_assignment(assignment_id):
    """Update an existing KPI role assignment
    """
    try:
        data = request.get_json()
        validated_data = KPIRoleAssignmentUpdateSchema(**data)
        assignment_data = validated_data.model_dump()

        updated_assignment = g.supabase_user_client.from_('kpi_role_assignments').update(assignment_data).eq('assignment_id', assignment_id).execute()
        if not updated_assignment.data:
            return jsonify({"error": "Failed to update KPI role assignment"}), 500
        return jsonify(updated_assignment.data[0]), 200
    except ValidationError as ve:
        current_app.logger.error(f"Validation error: {ve.errors()}")
        return jsonify({"error": ve.errors()}), 400

    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": str(e)}), 500

#delete kpi role assignment
@app_views.route('/hr/kpi/role-assignments/<uuid:assignment_id>', methods=['DELETE'])
@login_required
@role_required(['hr_manager', 'super_admin'])
def delete_kpi_role_assignment(assignment_id):
    """Delete a KPI role assignment
    """
    try:
        deleted_assignment = g.supabase_user_client.from_('kpi_role_assignments').delete().eq('assignment_id', assignment_id).execute()
        if not deleted_assignment.data:
            return jsonify({"error": "Failed to delete KPI role assignment"}), 500
        return jsonify({"message": "KPI role assignment deleted successfully"}), 200
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": str(e)}), 500