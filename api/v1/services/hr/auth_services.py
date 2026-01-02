from typing import Optional, Dict, Any
from uuid import UUID
from supabase import Client
from flask import g, current_app
from api.v1.services.hr.employee_services import (EmployeeCreateSchema)
from api.v1.services.hr.payroll_services import (
    SalaryComponentCreateSchema
)
from pydantic import ValidationError
import traceback

ALLOWED_ROLES = ['super_admin', 'hr_manager', 'manager', 'employee', 'user']
 
def create_salary_component(
    data: dict,
) -> Dict[str, Any]:
    """
    Creates a salary component for an employee.
    """
    try:
        validated_data = SalaryComponentCreateSchema(**data)
        component_data = validated_data.model_dump(exclude_unset=True)
        
        # Check if the employee exists
        employee_check = g.supabase_user_client.from_('employees').select('id').eq('id', component_data['employee_id']).execute()
        if not employee_check.data:
            return {"error": "Employee not found"}, 404
        
        # Insert the salary component
        response = g.supabase_user_client.from_('salary_components').insert(component_data).execute()
        if response.data:
            return {"message": "Salary component created successfully", "component": response.data[0]}, 201
        return {"error": "Failed to create salary component"}, 500

    except ValidationError as ve:
        current_app.logger.error(f"Validation error creating salary component: {str(ve)}")
        return {"error": str(ve)}, 400
    except Exception as e:
        current_app.logger.error(f"Error creating salary component: {str(e)}")
        return {"error": str(e)}, 500

def create_auth_user_and_employee(
    data: dict,
) -> Dict[str, Any]:
    """
    Creates a Supabase Auth user and a linked employee record.
    Handles rollback if employee record creation fails.
    """
    new_user_id = None

    if not data['email'].endswith('madisonjayng.com'):
        raise ValueError("Invalid  email. Kindly use your madison jay official email.")
    try:
        # 1. Create user in Supabase Auth
        auth_response = g.service_supabase_client.auth.admin.create_user(
          {  
            "email": data['email'],
            "password":data['password'],
            "email_confirm":True,
            "app_metadata": {
                "role": data['initial_role']
            }
        })

        if not auth_response.user:
            raise Exception(f"Failed to create Supabase Auth user: {auth_response.error}")
        print(f"Supabase Auth user created: {auth_response.user.email}")

        new_user_id = auth_response.user.id
        print(f"Supabase Auth user created with ID: {new_user_id} and role: {data['initial_role']}")

        # 2. Prepare employee data, linking to the new Supabase Auth user
        validated_employee_data = EmployeeCreateSchema(**data)
        employee_data = validated_employee_data.model_dump(exclude={'email', 'password', 'initial_role'})
        print(f"Employee data prepared for insertion: {employee_data}")
        employee_data['user_id'] = new_user_id
        employee_data['email'] = data['email']

        # 3. Insert employee record into public.employees table
        employee_insert_response = g.supabase_user_client.from_('employees').insert(employee_data).execute()
        if not employee_insert_response.data:
            raise Exception(f"Failed to create employee record: {employee_insert_response.error}")
    
        # 4. create salary component for the employee
        salary_component_data = {
            "employee_id": employee_insert_response.data[0]['id'],
            "start_date": data.get('hire_date', None),
            "end_date": None,
            "bonus": data.get('bonus', 0.0),
            "base_salary": data.get('salary', 0.0),
            "incentives": data.get('incentives', 0.0)

        }

        salary_component_response = create_salary_component(salary_component_data)
        if salary_component_response[1] != 201:
            raise Exception(f"Failed to create salary component: {salary_component_response[0]['error']}")
        print(f"Salary component created successfully for employee {salary_component_response}")

        return {
            "message": "Employee and Supabase Auth user created successfully.",
            "employee": employee_insert_response.data[0],
            "auth_user_id": new_user_id,
            "assigned_role": data['initial_role'],
            "salary_component": salary_component_response[0]
        }

    except Exception as e:
        # If employee record creation fails, attempt to delete the Auth user
        if new_user_id:
            try:
                g.service_supabase_client.auth.admin.delete_user(new_user_id)
                print(f"Auth user {new_user_id} deleted due to employee record creation failure.", e)
                traceback.print_exc()
            except Exception as delete_error:
                print(f"Failed to delete Auth user {new_user_id} during rollback: {delete_error}")
        raise e # Re-raise the original exception


def update_auth_user_role(
    user_id: UUID,
    new_role: str,
    service_supabase_client: Client
) -> bool:
    """
    Updates the system role of a Supabase Auth user.
    """
    print(f"Updating user {user_id} role to {new_role} in Supabase Auth.")
    try:
        auth_update_response = g.service_supabase_client.auth.admin.update_user_by_id(
            str(user_id), 
            {
                "app_metadata": {"role": new_role}
            }
        )
        if not auth_update_response.user:
            print(f"Warning: Failed to update auth user role for {user_id}. Error: {auth_update_response.error}")
            return False
        print(f"Auth user {user_id} role updated to {new_role}.")
        return True
    except Exception as e:
        print(f"Error updating auth user role for {user_id}: {e}")
        return False
    
