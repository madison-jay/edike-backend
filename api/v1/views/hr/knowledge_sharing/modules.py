from flask import Blueprint, request, jsonify, g, current_app
from api.v1.auth import login_required, role_required
from uuid import UUID
from api.v1.views import app_views
import traceback
from pydantic import ValidationError
from api.v1.services.hr.kss_services import (
    ModuleCreateSchema, ModuleUpdateSchema,
    AssignmentCreateSchema, AssignmentUpdateSchema,
    EmployeeLessonProgressCreateSchema, EmployeeLessonProgressUpdateSchema
)
import traceback

"""
endpoints for HR Manager to manage Knowledge Sharing System (KSS)
get create, update and delete module
get create, update and delete lesson
get create, update and delete assignment
get create, update and delete question
get create, update and delete employee lesson progress


The Idea
"""

@app_views.route('/kss/modules', methods=['GET'])
@login_required
@role_required(['hr_manager', 'super_admin', 'user', 'manager'])
def get_modules():
    """Get all modules"""
    try:
        if g.user_role in ['hr_manager', 'super_admin']:
            modules = g.supabase_user_client.from_('modules').select('*, lessons(*)').execute()
        elif g.user_role == 'manager':
            # Get modules assigned to manager's role or department
            employee = g.supabase_user_client.from_('employees').select('department:department_id(id, name)').eq('user_id', g.current_user).is_('deleted_at', 'null').execute()
            print('employee ===== ', employee)
            employee_department_id = employee.data[0]['department']['id']  # Adjusted to access nested department ID
            module_assignments = g.supabase_user_client.from_('module_assignments').select('module_id').or_(f"department_id.eq.{employee_department_id},role.eq.manager").execute()
            assigned_module_ids = [assignment['module_id'] for assignment in module_assignments.data]
            modules = g.supabase_user_client.from_('modules').select('*, lessons(*)').in_('id', assigned_module_ids).execute()
        else:
            # Employee case: Get modules assigned to employee's department or non-manager roles
            employee = g.supabase_user_client.from_('employees').select('department:department_id(name, id)').eq('user_id', g.current_user).is_('deleted_at', 'null').execute()
            employee_department_id = employee.data[0]['department']['id']  # Access nested department ID

            # Query module_assignments where either department_id matches or role matches (excluding manager role)
            module_assignments = g.supabase_user_client.from_('module_assignments').select('module_id').or_(
                f"department_id.eq.{employee_department_id},and(role.eq.{g.user_role},role.neq.manager)"
            ).execute()

            assigned_module_ids = [assignment['module_id'] for assignment in module_assignments.data]
            modules = g.supabase_user_client.from_('modules').select('*, lessons(*)').in_('id', assigned_module_ids).execute()
        
        return jsonify(modules.data), 200
    except Exception as e:
        traceback.print_exc()
        current_app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app_views.route('/kss/modules', methods=['POST'])
@login_required
@role_required(['hr_manager', 'super_admin'])
def create_module():
    """Create a new module
    Expects JSON body with:
    - title: str
    - description: Optional[str]
    - target_type: Literal['DEPARTMENT', 'ROLE', 'ALL']
    - target_value: str
    Returns the created module or error message
    """
    try:
        data = request.get_json()
        validated_data = ModuleCreateSchema(**data)
        module_data = validated_data.model_dump(exclude_unset=True)


        created_module = g.supabase_user_client.from_('modules').insert(module_data).execute()
        if not created_module.data:
            return jsonify({"error": "Failed to create module"}), 500
        return jsonify(created_module.data[0]), 201
    except ValidationError as ve:
        current_app.logger.error(f"Validation error: {ve.errors()}")
        return jsonify({"error": ve.errors()}), 400
    
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": str(e)}), 500
    

@app_views.route('/kss/modules/<uuid:module_id>', methods=['PUT'])
@login_required
@role_required(['hr_manager', 'super_admin'])
def update_module(module_id):
    try:
        data = request.get_json()
        print(data)
        validated_data = ModuleUpdateSchema(**data)
        update_data = validated_data.model_dump(exclude_unset=True)
        updated_module = g.supabase_user_client.from_('modules').update(update_data).eq('id', str(module_id)).execute()
        print('updated module ===== ', updated_module)
        if not updated_module.data:
            return jsonify({"error": "Module not found or no changes made"}), 404
        return jsonify(updated_module.data[0]), 200
    except ValidationError as ve:
        current_app.logger.error(f"Validation error: {ve.errors()}")
        return jsonify({"error": ve.errors()}), 400
    except Exception as e:
        traceback.print_exc()
        current_app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app_views.route('/kss/modules/<uuid:module_id>', methods=['DELETE'])
@login_required
@role_required(['hr_manager', 'super_admin'])
def delete_module(module_id):
    try:
        deleted_module = g.supabase_user_client.from_('modules').delete().eq('id', str(module_id)).execute()
        if not deleted_module.data:
            return jsonify({"error": "Module not found"}), 404
        return jsonify({"message": "Module deleted successfully"}), 200
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app_views.route('/kss/modules/<uuid:module_id>/assignments', methods=['GET'])
@login_required
@role_required(['hr_manager', 'super_admin', 'user', 'employee', 'manager'])
def get_module_assignments(module_id):
    try:
        assignments = g.supabase_user_client.from_('module_assignments')\
            .select('*')\
            .eq('module_id', str(module_id))\
            .execute()
        return jsonify(assignments.data), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching assignments: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app_views.route('kss/modules/<uuid:module_id>/assignments', methods=['POST'])
@login_required
@role_required(['hr_manager', 'super_admin'])
def create_assignment(module_id):
    try:
        data = request.get_json()
        validated_data = AssignmentCreateSchema(**data)
        assignment_data = validated_data.model_dump(exclude_unset=True)
        assignment_data['module_id'] = str(module_id)

        created_assignment = g.supabase_user_client.from_('module_assignments').insert(assignment_data).execute()
        if not created_assignment.data:
            return jsonify({"error": "Failed to create assignment"}), 500
        
        return jsonify(created_assignment.data[0]), 201
    
    except ValidationError as ve:
        current_app.logger.error(f"Validation error: {ve.errors()}")
        return jsonify({"error": ve.errors()}), 400
    
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": str(e)}), 500

# delete assignment
@app_views.route('/kss/modules/assignments/<uuid:assignment_id>', methods=['DELETE'])
@login_required
@role_required(['hr_manager', 'super_admin'])
def delete_assignment(assignment_id):
    try:
        deleted_assignment = g.supabase_user_client.from_('module_assignments').delete().eq('id', str(assignment_id)).execute()
        if not deleted_assignment.data:
            return jsonify({"error": "Assignment not found"}), 404
        return jsonify({"message": "Assignment deleted successfully"}), 200
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": str(e)}), 500


# track lesson progress
@app_views.route('/kss/lessons/<uuid:lesson_id>/progress', methods=['POST'])
@login_required
@role_required(['user', 'manager'])
def track_lesson_progress(lesson_id):
    try:
        data = request.get_json()
        validated_data = EmployeeLessonProgressCreateSchema(**data)
        progress_data = validated_data.model_dump(exclude_unset=True)
        progress_data['lesson_id'] = str(lesson_id)

        created_progress = g.supabase_user_client.from_('employee_lesson_progress').insert(progress_data).execute()
        if not created_progress.data:
            return jsonify({"error": "Failed to track lesson progress"}), 500
        
        return jsonify(created_progress.data[0]), 201
    
    except ValidationError as ve:
        current_app.logger.error(f"Validation error: {ve.errors()}")
        return jsonify({"error": ve.errors()}), 400
    
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": str(e)}), 500

# check if all the lessons are completed for a module
@app_views.route('/kss/modules/<uuid:module_id>/completion', methods=['GET'])
@login_required
@role_required(['hr_manager', 'super_admin', 'user', 'employee', 'manager'])
def check_module_completion(module_id):
    try:
        employee_id = request.args.get('employee_id')
        if not employee_id:
            return jsonify({"error": "Missing employee_id"}), 400
        
        # Fetch all lessons for the module
        lessons_response = g.supabase_user_client.from_('lessons').select('id').eq('module_id', str(module_id)).execute()
        if not lessons_response.data:
            return jsonify({"error": "No lessons found for this module"}), 404
        lesson_ids = [lesson['id'] for lesson in lessons_response.data]

        # Fetch completed lessons for the employee
        progress_response = g.supabase_user_client.from_('employee_lesson_progress')\
            .select('lesson_id')\
            .eq('employee_id', employee_id)\
            .in_('lesson_id', lesson_ids)\
            .eq('is_completed', True)\
            .execute()
        
        completed_lesson_ids = {progress['lesson_id'] for progress in progress_response.data} if progress_response.data else set()

        all_completed = all(lesson_id in completed_lesson_ids for lesson_id in lesson_ids)

        return jsonify({
            "employee_id": employee_id,
            "module_id": str(module_id),
            "all_lessons_completed": all_completed,
            "total_lessons": len(lesson_ids),
            "completed_lessons": len(completed_lesson_ids)
        }), 200
    
    except ValidationError as ve:
        current_app.logger.error(f"Validation error: {ve.errors()}")
        return jsonify({"error": ve.errors()}), 400
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": str(e)}), 500