from flask import g, current_app, jsonify, request
from api.v1.views import app_views
from api.v1.auth import login_required, role_required
from pydantic import ValidationError
from api.v1.services.sales.customers import (
    CustomerCreateSchema,
    CustomerUpdateSchema,
)


@app_views.route('/customers', methods=['GET'], strict_slashes=False)
@role_required(['super_admin', 'manager', 'user'])
@login_required
def fetch_customers():
    """
    Retrieve all customers.
    """
    try:
        user = g.supabase_user_client.from_('employees').select('department:department_id(name)').eq('user_id', g.current_user).execute()
        department = user.data[0]['department']['name']
        if department != 'sales' and g.user_role != 'super_admin':
            return jsonify({
                "status": "error",
                "message": "You do not have permission to perform this action"
            }), 403
        customers = g.supabase_user_client.from_('customers').select('*').execute()
        if not customers.data:
            return jsonify({
                "status": "success",
                "data": [],
                "message": "No customers found"
            }), 200

        return jsonify({
            "status": "success",
            "data": customers.data
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error fetching customers: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    
@app_views.route('/customers/<customer_id>', methods=['GET'], strict_slashes=False)
@role_required(['super_admin', 'manager', 'user'])
@login_required
def fetch_customer(customer_id):
    """
    Retrieve a specific customer by ID.
    """
    try:
        user = g.supabase_user_client.from_('employees').select('department:department_id(name)').eq('user_id', g.current_user).execute()
        department = user.data[0]['department']['name']
        if department not in ['sales', 'warehouse'] and g.user_role != 'super_admin':
            return jsonify({
                "status": "error",
                "message": "You do not have permission to perform this action"
            }), 403
        customer = g.supabase_user_client.from_('customers').select('*').eq('customer_id', customer_id).execute()
        if not customer.data:
            return jsonify({
                "status": "success",
                "data": {},
                "message": "Customer not found"
            }), 200

        return jsonify({
            "status": "success",
            "data": customer.data[0]
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error fetching customer: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app_views.route('/customers', methods=['POST'], strict_slashes=False)
@role_required(['super_admin', 'manager'])
@login_required
def create_customer():
    """
    Create a new customer.
    """
    try:
        user = g.supabase_user_client.from_('employees').select('department:department_id(name)').eq('user_id', g.current_user).execute()
        department = user.data[0]['department']['name']
        if department != 'sales' and g.user_role != 'super_admin':
            return jsonify({
                "status": "error",
                "message": "You do not have permission to perform this action"
            }), 403
        
        try:
            data = request.get_json()
            validated_customer = CustomerCreateSchema(**data)
        except ValidationError as ve:
            return jsonify({
                "status": "error",
                "message": ve.errors()
            }), 400
        customer_data = validated_customer.model_dump()

        new_customer = g.supabase_user_client.from_('customers').insert(customer_data).execute()
        if not new_customer.data:
            return jsonify({
                "status": "error",
                "message": "Failed to create customer"
            }), 500

        return jsonify({
            "status": "success",
            "data": new_customer.data[0],
            "message": "Customer created successfully"
        }), 201

    except ValidationError as ve:
        current_app.logger.error(f"Validation error: {ve.errors()}")
        return jsonify({
            "status": "error",
            "message": ve.errors()
        }), 400

    except Exception as e:
        current_app.logger.error(f"Error creating customer: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    

@app_views.route('/customers/<customer_id>', methods=['PUT'], strict_slashes=False)
@role_required(['super_admin', 'manager'])
@login_required
def update_customer(customer_id):
    """
    Update an existing customer.
    """
    try:
        user = g.supabase_user_client.from_('employees').select('department:department_id(name)').eq('user_id', g.current_user).execute()
        department = user.data[0]['department']['name']
        if department != 'sales' and g.user_role != 'super_admin':
            return jsonify({
                "status": "error",
                "message": "You do not have permission to perform this action"
            }), 403
        
        try:
            data = request.get_json()
            validated_customer = CustomerUpdateSchema(**data)
        except ValidationError as ve:
            return jsonify({
                "status": "error",
                "message": ve.errors()
            }), 400
        customer_data = validated_customer.model_dump()
        customer_data['updated_by'] = g.current_user

        updated_customer = g.supabase_user_client.from_('customers').update(customer_data).eq('customer_id', customer_id).execute()
        if not updated_customer.data:
            return jsonify({
                "status": "error",
                "message": "Failed to update customer or customer not found"
            }), 500

        return jsonify({
            "status": "success",
            "data": updated_customer.data[0],
            "message": "Customer updated successfully"
        }), 200

    except ValidationError as ve:
        current_app.logger.error(f"Validation error: {ve.errors()}")
        return jsonify({
            "status": "error",
            "message": ve.errors()
        }), 400

    except Exception as e:
        current_app.logger.error(f"Error updating customer: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500