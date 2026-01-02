from flask import g, current_app, jsonify, request
from api.v1.views import app_views
from api.v1.auth import login_required, role_required
from pydantic import ValidationError
from api.v1.services.sales.order_services import (
    OrderCreateSchema,
    OrderUpdateSchema,
    generate_unique_order_number
)
import traceback



@app_views.route('/orders', methods=['GET'], strict_slashes=False)
@role_required(['super_admin', 'manager', 'user'])
@login_required
def fetch_orders():
    """
    Retrieve all sales orders.
    """
    try:
        user = g.supabase_user_client.from_('employees').select('department:department_id(name)').eq('user_id', g.current_user).execute()
        department = user.data[0]['department']['name']
        if department not in ['sales', 'warehouse'] and g.user_role != 'super_admin':
            return jsonify({
                "status": "error",
                "message": "You do not have permission to perform this action"
            }), 403
        orders = g.supabase_user_client.from_('orders').select('*, order_details(product_id(name, price), quantity)').execute()
        if not orders.data:
            return jsonify({
                "status": "success",
                "data": [],
                "message": "No orders found"
            }), 200

        return jsonify({
            "status": "success",
            "data": orders.data
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error fetching orders: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    


@app_views.route('/orders/<order_id>', methods=['GET'], strict_slashes=False)
@role_required(['super_admin', 'manager', 'user'])
@login_required
def fetch_order(order_id):
    """
    Retrieve a specific sales order by ID.
    """
    try:
        order = g.supabase_user_client.from_('orders').select('*, order_details(product_id(name, price), quantity)').eq('order_id', order_id).execute()
        if not order.data:
            return jsonify({
                "status": "success",
                "data": None,
                "message": "Order not found"
            }), 404

        return jsonify({
            "status": "success",
            "data": order.data
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error fetching order: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app_views.route('/orders', methods=['POST'], strict_slashes=False)
@role_required(['super_admin', 'manager', 'user'])
@login_required
def create_order():
    """
    Create a new sales order.
    expects JSON body with:
    {
        "customer_id": "string",
        "order_number": "string",
        "delivery_date": "YYYY-MM-DD", (optional)
        "status": "pending" | "shipped" | "delivered" | "processing" | "canceled", (optional, default: "pending")
        "total_amount": float,
        "dispatch_address": "string",
        "phone_number": "string",
        "notes": "string" (optional)
        "products" [
            {
                "product_id": "string",
                "quantity": int,
            },
            ...
        ]
    }
    """
    try:
        user = g.supabase_user_client.from_('employees').select('department:department_id(name)').eq('user_id', g.current_user).execute()
        department = user.data[0]['department']['name']
        if department != 'sales' and g.user_role != 'super_admin':
            return jsonify({
                "status": "error",
                "message": "You do not have permission to perform this action"
            }), 403
        data = request.get_json()

        if not data.get('products'):
            return jsonify({
                "status": "error",
                "message": "Products list cannot be empty"
            }), 400
        
        validated_data = OrderCreateSchema(**data)
        order_data = validated_data.model_dump(exclude={'products', 'apply_discount', 'apply_vat'})
        created_by = g.supabase_user_client.from_('employees').select('id').eq('user_id', g.current_user).execute().data
        if not created_by:
            return jsonify({
                "status": "error",
                "message": "Employee record not found for the current user"
            }), 400
        order_data['created_by'] = created_by[0]['id']
        order_data['order_number'] = generate_unique_order_number()

        create_order = g.supabase_user_client.from_('orders').insert(order_data).execute()
        if not create_order.data:
            return jsonify({
                "status": "error",
                "message": "Failed to create order"
            }), 500
        
        products = data['products']

        for item in products:
            order_item_data = {
                "order_id": create_order.data[0]['order_id'],
                "product_id": item['product_id'],
                "quantity": item['quantity'],
            }
            g.supabase_user_client.from_('order_details').insert(order_item_data).execute()

        return jsonify({
            "status": "success",
            "data": create_order.data
        }), 201

    except ValidationError as ve:
        current_app.logger.error(f"Validation error: {ve.errors()}")
        return jsonify({
            "status": "error",
            "message": ve.errors()
        }), 400
    except Exception as e:
        traceback.print_exc()
        current_app.logger.error(f"Error creating order: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app_views.route('/orders/<order_id>', methods=['PUT'], strict_slashes=False)
@role_required(['super_admin', 'manager'])
@login_required
def update_order(order_id):
    try:
        # Get employee + department
        emp_res = g.supabase_user_client.from_('employees')\
            .select('id, department:department_id(name)')\
            .eq('user_id', g.current_user)\
            .execute()
        
        if not emp_res.data:
            return jsonify({"status": "error", "message": "Employee not found"}), 400

        employee = emp_res.data[0]
        department = employee['department']['name']

        # Permission: sales, warehouse, or super_admin
        if department not in ['sales', 'warehouse'] and g.user_role != 'super_admin':
            return jsonify({
                "status": "error",
                "message": "You do not have permission to perform this action"
            }), 403

        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400

        validated_data = OrderUpdateSchema(**data)
        order_data = validated_data.model_dump(exclude_unset=True)

        # Restrict warehouse fields
        if department == 'warehouse':
            allowed = {'status', 'tracking_number', 'dispatched_at', 'notes'}
            order_data = {k: v for k, v in order_data.items() if k in allowed}
            if not order_data:
                return jsonify({"status": "error", "message": "No valid fields to update"}), 400

        # Set updated_by to employee.id (not auth uid)
        order_data['updated_by'] = employee['id']

        # CRITICAL: Use correct table
        update_res = g.supabase_user_client.from_('orders')\
            .update(order_data)\
            .eq('order_id', order_id)\
            .execute()

        # Debug
        current_app.logger.info(f"Update response: {update_res}")

        if not update_res.data:
            # Check if order exists
            check = g.supabase_user_client.from_('orders')\
                .select('order_id')\
                .eq('order_id', order_id)\
                .execute()
            if not check.data:
                return jsonify({"status": "error", "message": "Order not found"}), 404
            else:
                return jsonify({"status": "error", "message": "Update failed (RLS or validation)"}), 403

        return jsonify({"status": "success", "data": update_res.data}), 200

    except ValidationError as ve:
        return jsonify({"status": "error", "message": ve.errors()}), 400
    except Exception as e:
        current_app.logger.error(f"Error in update_order: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500