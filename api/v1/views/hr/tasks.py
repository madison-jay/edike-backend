from flask import request, jsonify, g
from api.v1.views import app_views
from api.v1.auth import login_required, role_required
from uuid import UUID
from datetime import datetime
from pydantic import ValidationError
from flask_cors import cross_origin
from api.v1.services.hr.task_services import TaskCreateSchema, TaskUpdateSchema
from api.v1.services.hr.document_services import (
    TaskDocumentCreateSchema,
    TaskDocumentUpdateSchema
)

# --- helper function for UUID validation ---
def is_valid_uuid(uuid_string):
    try:
        UUID(uuid_string)
        return True
    except ValueError:
        return False


# Task Endpoints
@app_views.route('/tasks', methods=['GET'])
@login_required
@role_required(['super_admin', 'hr_manager', 'manager', 'user'])
def get_tasks():
    try:
        """Task """
        if g.user_role in ['super_admin', 'hr_manager', 'manager']:
            response = g.supabase_user_client.from_('tasks').select(
                "*, task_assignments(*, employees(id, first_name, last_name, email, avatar_url)), task_documents(*)"
            ).execute()
            if response.data:
                return jsonify(response.data), 200
            return jsonify({"message": "No tasks found"}), 204
        
        current_user = g.supabase_user_client.from_('employees').select('id').eq('user_id', g.current_user).is_('deleted_at', 'null').execute()
        if not current_user.data:
            return jsonify({"error": "Current user not found"}), 400
        employee_id = current_user.data[0]['id']
        print('employee id',employee_id)
        response = g.supabase_user_client.from_('tasks').select(
            "*, task_assignments!inner(*, employees(id, first_name, last_name, email, avatar_url)), task_documents(*)"
        ).eq('task_assignments.employee_id', str(employee_id)).execute()
        print(response)
        if response.data:
            return jsonify(response.data), 200

        return jsonify([]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app_views.route('/tasks/<uuid:task_id>', methods=['GET'])
@login_required
@role_required(['super_admin', 'hr_manager', 'manager', 'user'])
def get_task(task_id):
    if not is_valid_uuid(str(task_id)):
        return jsonify({"error": "Invalid task ID format"}), 400
    try:
        response = g.supabase_user_client.from_('tasks').select(
            '*, assigned_to:assigned_to(first_name, last_name, email, avatar_url), created_by:created_by(first_name, last_name, email, avatar_url)'
        ).neq('status', 'Cancelled').execute()

        if response.data:
            return jsonify(response.data[0]), 200
        return jsonify([]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app_views.route('/tasks', methods=['POST'])
@login_required
@role_required(['super_admin', 'hr_manager', 'manager', 'user'])
def create_task():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided, request body must be JSON"}), 400
    task_response = None
    try:
        task_data = TaskCreateSchema(**data)
    
        # Get creator's employee ID
        creator_response = g.supabase_user_client.from_('employees').select('id').eq('user_id', g.current_user).is_('deleted_at', 'null').execute()
        if not creator_response.data:
            return jsonify({"error": "Creator employee record not found"}), 403

        task_payload = {
            "title": task_data.title,
            "description": task_data.description,
            "start_date": task_data.start_date,
            "end_date": task_data.end_date,
            "created_by": creator_response.data[0]['id'],
            "status": task_data.status,
            "priority": task_data.priority
        }
        task_response = g.service_supabase_client.from_('tasks').insert(task_payload).execute()

        assigned_to = data.get('assigned_to', [])
        for each_employee in assigned_to:
            if not is_valid_uuid(each_employee):
                return jsonify({"error": f"Invalid assigned_to ID format: {each_employee}"}), 400
            check_assigned_to = g.supabase_user_client.from_('employees').select('id').eq('id', each_employee).is_('deleted_at', 'null').execute()
            if not check_assigned_to.data:
                return jsonify({"error": f"Assigned employee not found: {each_employee}"}), 400
            
            # Check for leave conflicts
            leave_check = g.supabase_user_client.from_('leave_requests').select('id').eq('employee_id', each_employee).eq('status', 'approved').gte('end_date', task_data.start_date).lte('start_date', task_data.end_date).execute()
            if leave_check.data:
                return jsonify({"error": "Task conflicts with approved leave"}), 400
            
            assignment_payload = {
                "task_id": task_response.data[0]['id'],
                "employee_id": each_employee,
                "date_assigned": datetime.now().isoformat()
            }

            response = g.supabase_user_client.from_('task_assignments').insert(assignment_payload).execute()
        
        task_documents = data.get('documents', [])
        for task_document in task_documents:
            validated_task_document = TaskDocumentCreateSchema(**task_document, task_id=task_response.data[0]['id'])
            validated_task_document.task_id = task_response.data[0]['id']
            validated_task_document.created_by = creator_response.data[0]['id']

            document_response = g.supabase_user_client.from_('task_documents').insert(validated_task_document.model_dump()).execute()
            if not document_response.data:
                return jsonify({"error": "Failed to create task document"}), 500
        return jsonify({"message": "Task created successfully", "task": task_response.data[0]}), 201

    except ValidationError as e:
        return jsonify({"error": "Validation failed", "details": e.errors()}), 400
    except Exception as e:
        if task_response:
            g.supabase_user_client.from_('tasks').delete().eq('id', task_response.data[0]['id']).execute()
        return jsonify({"error": str(e)}), 500


@app_views.route('/tasks/<uuid:task_id>', methods=['PUT'])
@login_required
@role_required(['super_admin', 'hr_manager', 'manager', 'user'])
def update_task(task_id):
    if not is_valid_uuid(str(task_id)):
        return jsonify({"error": "Invalid task ID format"}), 400
    try:
        data = request.get_json()
        update_data = TaskUpdateSchema(**data)
        update_payload = update_data.model_dump(exclude_unset=True)

        if any(key in update_payload for key in ['start_date', 'end_date']):
            existing_task = g.supabase_user_client.from_('tasks').select('start_date, end_date ').eq('id', str(task_id)).neq('status', 'Cancelled').execute()
            if not existing_task.data:
                return jsonify({"error": "Task not found or cancelled"}), 404
            start_date = update_payload.get('start_date', existing_task.data[0]['start_date'])
            end_date = update_payload.get('end_date', existing_task.data[0]['end_date'])
        
        if 'assigned_to' in data:
            return jsonify({"error": "Re-assigning employees is not allowed in this endpoint."}), 400
        response = g.service_supabase_client.from_('tasks').update(update_payload).eq('id', str(task_id)).neq('status', 'Cancelled').execute()
        if response.data:
            return jsonify(response.data[0]), 200
        return jsonify({"error": "Task not found or cancelled"}), 404
    except ValidationError as e:
        return jsonify({"error": "Validation failed", "details": e.errors()}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app_views.route('/tasks/<uuid:task_id>', methods=['DELETE'])
@login_required
@role_required(['super_admin', 'hr_manager', 'manager', 'user'])
def delete_task(task_id):
    if not is_valid_uuid(str(task_id)):
        return jsonify({"error": "Invalid task ID format"}), 400
    try:
        response = g.service_supabase_client.from_('tasks').delete().eq('id', str(task_id)).execute()
        if response.data:
            return jsonify({"message": f"Task {task_id} deleted successfully"}), 200
        return jsonify({"error": "Task not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

#add a new document to a task
@app_views.route('/tasks/<uuid:task_id>/documents', methods=['POST'])
@login_required
@role_required(['super_admin', 'hr_manager', 'manager', 'user'])
def add_task_document(task_id):
    if not is_valid_uuid(str(task_id)):
        return jsonify({"error": "Invalid task ID format"}), 400
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided, request body must be JSON"}), 400
        
        task_document_data = TaskDocumentCreateSchema(**data, task_id=str(task_id))

        # Validate creator
        creator_response = g.supabase_user_client.from_('employees').select('id').eq('user_id', g.current_user).is_('deleted_at', 'null').execute()
        task_assigned_to = g.supabase_user_client.from_('task_assignments').select('employees:employee_id(user_id)').eq('task_id', str(task_id)).execute()
        task_assigned_to_ids = [assignment['employees']['user_id'] for assignment in task_assigned_to.data] if task_assigned_to.data else []
        if not creator_response.data or g.current_user not in task_assigned_to_ids or g.user_role not in ['hr_manager', "super_admin"]:
            return jsonify({"error": "User is not assigned to this task"}), 403
        task_document_data.created_by = creator_response.data[0]['id']

       

        response = g.supabase_user_client.from_('task_documents').insert(task_document_data.model_dump()).execute()
        if response.data:
            return jsonify(response.data[0]), 201
        return jsonify({"error": "Failed to create task document"}), 500
    except ValidationError as e:
        return jsonify({"error": "Validation failed", "details": e.errors()}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

#edit a task document
@app_views.route('/tasks/<uuid:task_id>/documents/<uuid:document_id>', methods=['PUT'])
@login_required
@role_required(['super_admin', 'hr_manager', 'manager', 'user'])
def edit_task_document(task_id, document_id):
    if not is_valid_uuid(str(task_id)) or not is_valid_uuid(str(document_id)):
        return jsonify({"error": "Invalid task ID or document ID format"}), 400
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided, request body must be JSON"}), 400

        task_document_data = TaskDocumentUpdateSchema(**data)
        task_update_payload = task_document_data.model_dump(exclude_unset=True)

        # Validate updater
        updater_response = g.supabase_user_client.from_('employees').select('id').eq('user_id', g.current_user).is_('deleted_at', 'null').execute()
        if not updater_response.data:
            return jsonify({"error": "User is not a valid employee"}), 403
        
        task_assigned_to = g.supabase_user_client.from_('task_assignments').select('employees:employee_id(user_id)').eq('task_id', str(task_id)).execute()
        task_assigned_to_ids = [assignment['employees']['user_id'] for assignment in task_assigned_to.data] if task_assigned_to.data else []
       

        task = g.supabase_user_client.from_('tasks').select('id, created_by').eq('id', str(task_id)).execute()
        if not task.data:
            return jsonify({"error": "Task not found"}), 404

        if g.current_user not in task_assigned_to_ids and task.data[0]['created_by'] != updater_response.data[0]['id']:
            return jsonify({"error": "User is not the creator and not an assignee of this task"}), 403

        response = g.supabase_user_client.from_('task_documents').update(task_update_payload).eq('id', str(document_id)).execute()
        if response.data:
            return jsonify(response.data[0]), 200
        return jsonify({"error": "Task document not found"}), 404
    except ValidationError as e:
        return jsonify({"error": "Validation failed", "details": e.errors()}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

#delete task document
@app_views.route('/tasks/<uuid:task_id>/documents/<uuid:document_id>', methods=['DELETE'])
@login_required
@role_required(['super_admin', 'hr_manager', 'manager', 'user'])
def delete_task_document(task_id, document_id):
    if not is_valid_uuid(str(task_id)) or not is_valid_uuid(str(document_id)):
        return jsonify({"error": "Invalid task ID or document ID format"}), 400
    try:
        # Validate user permissions
        task_assigned_to = g.supabase_user_client.from_('task_assignments').select('employees:employee_id(user_id)').eq('task_id', str(task_id)).execute()
        task_assigned_to_ids = [assignment['employees']['user_id'] for assignment in task_assigned_to.data] if task_assigned_to.data else []

        created = g.supabase_user_client.from_('tasks').select('created_by').eq('id', str(task_id)).execute()
        if not created.data:
            return jsonify({"error": "Task not found"}), 404
        created_by = created.data[0]['created_by']

        employee = g.supabase_user_client.from_('employees').select('id').eq('user_id', g.current_user).is_('deleted_at', 'null').execute()
        if not employee.data:
            return jsonify({"error": "Employee record not found"}), 404
        employee_id = employee.data[0]['id']

        print(employee_id, created_by, task_assigned_to_ids)

        if g.current_user not in task_assigned_to_ids and created_by != employee_id:
            return jsonify({"error": "User is not assigned to this task"}), 403

        response = g.supabase_user_client.from_('task_documents').delete().eq('id', str(document_id)).execute()
        if response.data:
            return jsonify({"message": "Task document deleted successfully"}), 200
        return jsonify({"error": "Task document not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


#add new employee to a task
@app_views.route('/tasks/<uuid:task_id>/assignments', methods=['POST'])
@login_required
@role_required(['super_admin', 'hr_manager', 'manager', 'user'])
def add_employee_to_task(task_id):
    if not is_valid_uuid(str(task_id)):
        return jsonify({"error": "Invalid task ID format"}), 400
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided, request body must be JSON"}), 400

        employee_id = data.get("employee_id")
        if not employee_id or not is_valid_uuid(str(employee_id)):
            return jsonify({"error": "Invalid employee ID format"}), 400

        created_by = g.supabase_user_client.from_('employees').select('id').eq('user_id', g.current_user).is_('deleted_at', 'null').execute()
        if not created_by.data:
            return jsonify({"error": "Creator employee record not found"}), 403
        created_by_id = created_by.data[0]['id']

        task_response = g.supabase_user_client.from_('tasks').select('id, created_by').eq('id', str(task_id)).execute()
        if not task_response.data:
            return jsonify({"error": "Task not found"}), 404
        task = task_response.data[0]
        if task['created_by'] != created_by_id:
            return jsonify({"error": "User is not the creator of this task"}), 403

        response = g.supabase_user_client.from_('task_assignments').insert({"task_id": str(task_id), "employee_id": str(employee_id)}).execute()
        if response.data:
            return jsonify(response.data[0]), 201
        return jsonify({"error": "Failed to add employee to task"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

#remove employee from a task
@app_views.route('/tasks/<uuid:task_id>/assignments/<uuid:employee_id>', methods=['DELETE'])
@login_required
@role_required(['super_admin', 'hr_manager', 'manager', 'user'])
def remove_employee_from_task(task_id, employee_id):
    if not is_valid_uuid(str(task_id)) or not is_valid_uuid(str(employee_id)):
        return jsonify({"error": "Invalid task ID or employee ID format"}), 400
    try:
        # Validate user permissions
        created_by = g.supabase_user_client.from_('employees').select('id').eq('user_id', g.current_user).is_('deleted_at', 'null').execute()
        if not created_by.data:
            return jsonify({"error": "Creator employee record not found"}), 403
        created_by_id = created_by.data[0]['id']

        task_response = g.supabase_user_client.from_('tasks').select('id, created_by').eq('id', str(task_id)).execute()
        if not task_response.data:
            return jsonify({"error": "Task not found"}), 404
        task = task_response.data[0]
        if task['created_by'] != created_by_id:
            return jsonify({"error": "User is not the creator of this task"}), 403

        response = g.supabase_user_client.from_('task_assignments').delete().eq('task_id', str(task_id)).eq('employee_id', str(employee_id)).execute()
        print(response)
        if len(response.data) > 0:
            return jsonify({"message": "Employee removed from task successfully"}), 200
        return jsonify({"error": "Failed to remove employee from task"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
