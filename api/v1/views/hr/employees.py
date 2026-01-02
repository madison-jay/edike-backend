from flask import Blueprint, request, jsonify, g
from api.v1.auth import login_required, role_required, service_supabase_client
from uuid import UUID
from api.v1.views import app_views
import traceback
from pydantic import ValidationError
import datetime
from api.v1.services.hr.document_services import (
    create_employee_document as employee_document_service,
    EmployeeDocumentUpdateSchema
)
from api.v1.services.hr.auth_services import (
    create_auth_user_and_employee,
    update_auth_user_role,
)
from api.v1.services.hr.employee_services import (
    EmployeeUpdateSchema,
    ALLOWED_ROLES,
)


# --- helper function for UUID validation ---
def is_valid_uuid(uuid_string):
    try:
        UUID(uuid_string)
        return True
    except ValueError:
        return False
    

@app_views.route('/employees', methods=['GET'])
@login_required
@role_required(['super_admin', 'hr_manager', 'manager', 'user'])
def get_employeee():
    """
    Get a list of employees.
    RLS policies in supabase will automaticallly filter results based on the user's role.
    - Super Admin, HR Manager: See all employees.
    - Manager: See employees in their department.
    - Employee (User): See only their own record.
    - Other users: See basic employee infor (if policy allows).
    """
    try:
        if g.user_role == 'user':
            response = g.supabase_user_client.from_('employees').select('*, departments(name), shift_types(name, start_time, end_time), employee_documents!employee_documents_employee_id_fkey(id, name, url, type, category, created_at)').eq('user_id', str(g.current_user)).is_('deleted_at', 'null').execute()
            if not response.data:
                return jsonify({"message": "No employee record found for current user."}), 404
            return jsonify(**response.data[0], role=g.user_role), 200
        else:
            response = g.supabase_user_client.from_('employees').select('*, departments(name), shift_types(name, start_time, end_time), employee_documents!employee_documents_employee_id_fkey(id, name, url, type, category, created_at)').is_('deleted_at', 'null').execute()
            if response.data:
                return jsonify(response.data), 200
        return jsonify({"message": "No employees found"}), 200
    
    except Exception as e:
        print(f"Error fetching employees: {str(e)}")
        return jsonify({"error": str(e)}), 500
    

@app_views.route('/employees/<uuid:employee_id>', methods=['GET'])
@login_required
@role_required(['super_admin', 'hr_manager', 'manager', 'user'])
def get_employee(employee_id):
    """
    Get a single employee by ID.
    RLS policies will ensure only authorized users can view the specific employee.
    """
    if not is_valid_uuid(str(employee_id)):
        return jsonify({"error": "Invalid employee ID format"}), 400
    try:
        response = g.supabase_user_client.from_('employees').select('*, departments(name), shift_types(name, start_time, end_time)').eq('id', str(employee_id)).execute()
        if response.data:
            return jsonify(**response.data[0], role=g.user_role), 200
        return jsonify({"error": "Employee not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# get employees by department
@app_views.route('/employees/department/<uuid:department_id>', methods=['GET'])
@login_required
@role_required(['super_admin', 'hr_manager', 'manager'])
def get_employees_by_department(department_id):
    if not is_valid_uuid(str(department_id)):
        return jsonify({"error": "Invalid department ID format"}), 400
    try:
        response = g.supabase_user_client.from_('employees').select('*, departments(name), shift_types(name, start_time, end_time)').eq('department_id', str(department_id)).is_('deleted_at', 'null').execute()
        if response.data:
            return jsonify(response.data), 200
        return jsonify({"message": "No employees found in this department"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app_views.route('/employees/', methods=['POST'])
@login_required
@role_required(['super_admin', 'hr_manager'])
def create_employee():
    """
    Create a new employee record.
    Only accessible by Super Admin and HR Manager.
    """
    data = request.get_json()
    print(data)
    if not data:
        return jsonify({"error": "No data provided, request body must be JSON"}), 400
    try:
        if g.user_role == 'hr_manager' and data["initial_role"] == 'super_admin':
            return jsonify({"error": "HR Manager cannot create Super Admin users"}), 403
        
        response = create_auth_user_and_employee(data)
        employee_id = response.get('employee')['id']
        documents = data.get('documents', [])
        processed_documents = []
        if documents and len(documents) > 0:
            processed_documents = create_employee_document(documents, employee_id)

        return jsonify(**response, documents=processed_documents), 201

    except ValueError as ve:
        # catch pydantic validation errors
        return jsonify({"error": "Validation failed", "details": str(ve)}), 400
    except TypeError as te:
        # catch type errors, often from missing required fields
        return jsonify({"error": "Type error", "details": str(te)}), 400
    except ValidationError as e:
        # catch pydantic validation errors
        return jsonify({"error": "Validation failed", "details": str(e.errors())}), 400
    except Exception as e:
        print(f"Error creating employee: {str(e)}")
        #catch any other exceptions and return a generic error message
        return jsonify({"error": str(e)}), 500


    
@app_views.route('/employees/<uuid:employee_id>', methods=['PUT'])
@login_required
@role_required(['super_admin', 'hr_manager', 'user', 'manager'])
def update_employee(employee_id):
    """
    Update an existing employee record
    - Super Admin, HR Manager: Can update any employee and their system role.
    - Employee (User): Can update their own limited fileds (enforced by RLS WITH CHECK)
    Inpt validation handled by Pydantic.
    """
    if not is_valid_uuid(str(employee_id)):
        return jsonify({"error": "Invalid employee ID formate"}), 400
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided, request body must be JSON"}), 400
    try:
        update_data = EmployeeUpdateSchema(**data)
        print("Update data: ", update_data)
        employee_table_data = update_data.model_dump(exclude_unset=True, exclude={'role'})
        new_role = update_data.role
        print('User new role: ', new_role, update_data)

        if g.user_role in ['super_admin', 'hr_manager']:
            if g.user_role == 'hr_manager' and new_role == 'super_admin':
                return jsonify({"Error": "HR Managers cannot promote users to Super Admin"}), 403
          
            employee_lookup_response = g.service_supabase_client.from_('employees').select('user_id').eq('id', str(employee_id)).execute()
            linked_user_id = None
            if employee_lookup_response.data and employee_lookup_response.data[0] and employee_lookup_response.data[0]['user_id']:
                linked_user_id = employee_lookup_response.data[0]['user_id']
            if linked_user_id == g.current_user:
                return jsonify({"error": "You cannot update your own role."}), 403
            if new_role and new_role in ALLOWED_ROLES:
                if linked_user_id:
                    # Update the user's metadata (role) in Supabase Auth via service
                    success = update_auth_user_role(linked_user_id, new_role, service_supabase_client)
                    if not success:
                        return jsonify({"error": "Failed to update user role in Supabase Auth."}), 500
                else:
                    print(f"Warning: Employee {employee_id} has no linked user_id for role update.")
            print(employee_table_data)
            # Update the employee record in public.employees
            response = g.service_supabase_client.from_('employees').update(employee_table_data).eq('id', str(employee_id)).execute()
            print(response)
            if response.data or new_role:
                return jsonify(response.data[0]), 200
            
            return jsonify({"error": "Failed to update employee or employee not found."}), 404

        elif g.user_role in ['user', "manager"]:
            if new_role:  # Prevent users from trying to change their own role
                return jsonify({"error": "Users are not allowed to change their own role."}), 403
            
            employee_lookup_response = g.supabase_user_client.from_('employees').select('id').eq('user_id', g.current_user).execute()
            if not employee_lookup_response.data or not employee_lookup_response.data[0]:
                return jsonify({"message": "Employee record not found for current user."}), 403
            actual_employee_id_for_user = employee_lookup_response.data[0]['id']

            if str(employee_id) != str(actual_employee_id_for_user):
                 return jsonify({"message": "Permission denied: You can only update your own record."}), 403

            # Use g.supabase_user_client for RLS-aware update. RLS will enforce field restrictions.
            response = g.supabase_user_client.from_('employees').update(employee_table_data).eq('id', str(employee_id)).execute()
            print(response)
            if response.data:
                return jsonify(response.data[0]), 200
            return jsonify({"error": "Failed to update employee or employee not found."}), 404
        else:
            return jsonify({"message": "Permission denied: Insufficient role for update."}), 403
        
    except ValidationError as e:
        # Catch Pydantic validation errors
        return jsonify({"error": "Validation failed", "details": str(e)}), 400
    except ValueError as e:
        return jsonify({"error": "Value error", "details": str(e)}), 400
    except Exception as e:
        print(e)
        return jsonify({"error": "Internal Error", "details": str(e)}), 500



@app_views.route('/employees/<uuid:employee_id>', methods=['DELETE'])
@login_required
@role_required(['super_admin', 'hr_manager']) # Only Super Admin and HR Manager can perform this action
def soft_delete_employee(employee_id):
    """
    Soft deletes an employee record by setting their employment_status to 'terminated'
    and populating the 'deleted_at' timestamp.
    The associated Supabase Auth user is NOT deleted.
    Only Super Admin and HR Manager roles are allowed.
    """
    if not is_valid_uuid(str(employee_id)):
        return jsonify({"error": "Invalid employee ID format."}), 400

    try:
        # Data to update for soft delete
        update_payload = { 
            "user_id": None,
            "employment_status": "terminated",
            "deleted_at": datetime.datetime.now(datetime.timezone.utc).isoformat(), # Use ISO format for TIMESTAMPTZ
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }

        employee_user_req = g.supabase_user_client.from_('employees').select('user_id').eq('id', str(employee_id)).execute()
        if len(employee_user_req.data) < 1:
            return jsonify({"error": "Employee not found."}), 404
        employee_user_id = employee_user_req.data[0]['user_id']
        print(f"Employee {employee_id} has user_id: {employee_user_id}")
        if employee_user_id:
            # Delete the associated Supabase Auth user
            g.service_supabase_client.auth.admin.delete_user(str(employee_user_id))

        # Use service_supabase_client to bypass RLS for this administrative update
        response = g.supabase_user_client.from_('employees').update(update_payload).eq('id', str(employee_id)).execute()

        if response.data:
            return jsonify({"message": f"Employee {employee_id} deleted (terminated) successfully."}), 200
        else:
            return jsonify({"error": "Failed to soft-delete employee or employee not found."}), 404
    except Exception as e:
        traceback.print_exc()
        print(f"Error soft-deleting employee {employee_id}: {str(e)}")
        return jsonify({"error": "Internal Error"}), 500


# employee documents endpoints
@app_views.route('/employees/<uuid:employee_id>/documents', methods=['POST'])
@login_required
@role_required(['super_admin', 'hr_manager', 'user'])
def create_employee_document(employee_id):
    """
    Creates new document(s) for a specific employee.
    Documents in the request body must include the necessary fields and should be an array.
    """
    if not is_valid_uuid(str(employee_id)):
        return jsonify({"error": "Invalid employee ID format"}), 400

    try:
        documents = request.get_json().get('documents', [])
        print(documents)
        if not documents:
            return jsonify({"error": "No documents provided"}), 400

        created_documents = employee_document_service(documents, employee_id)
        return jsonify(created_documents), 201
    except ValidationError as e:
        return jsonify({"error": "Validation failed", "details": e.errors()}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

#update employee_document
@app_views.route('/employee_documents/<uuid:employee_document_id>', methods=['PUT'])
@login_required
@role_required(['super_admin', 'hr_manager', 'user'])
def update_employee_document(employee_document_id):
    if not is_valid_uuid(str(employee_document_id)):
        return jsonify({"error": "Invalid document ID format"}), 400

    try:
        document_data = EmployeeDocumentUpdateSchema(**request.get_json())
        document_upload_payload = document_data.model_dump(exclude_unset=True)
        print(document_data)
        # Update the document
        response = g.supabase_user_client.from_('employee_documents').update(document_upload_payload).eq('id', str(employee_document_id)).execute()
        if response.data:
            return jsonify(response.data[0]), 200
        return jsonify({"error": "Failed to update document"}), 400
    except ValidationError as e:
        return jsonify({"error": "Validation failed", "details": e.errors()}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

#delete employee document
@app_views.route('/employee_documents/<uuid:employee_document_id>', methods=['DELETE'])
@login_required
@role_required(['super_admin', 'hr_manager', 'user', 'manager'])
def delete_employee_document(employee_document_id):
    if not is_valid_uuid(str(employee_document_id)):
        return jsonify({"error": "Invalid document ID format"}), 400
    try:
        # Delete the document
        document  = g.supabase_user_client.from_('employee_documents').select('employee_id').eq('id', str(employee_document_id)).execute()
        if not document.data or not document.data[0]:
            return jsonify({"error": "Document not found"}), 404
        response = g.supabase_user_client.from_('employee_documents').delete().eq('id', str(employee_document_id)).execute()
        print(response)
        if response.data:
            return jsonify({"message": "Document deleted successfully"}), 200
        return jsonify({"error": "Failed to delete document"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
