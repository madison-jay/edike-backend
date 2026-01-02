from flask import g, current_app, jsonify, request
from api.v1.views import app_views
from api.v1.auth import login_required, role_required
from pydantic import ValidationError
from api.v1.services.inventories.suppliers_services import (
    SupplierCreateSchema,
    SupplierUpdateSchema,
)
from werkzeug.exceptions import BadRequest

@app_views.route('/suppliers', methods=['GET'], strict_slashes=False)
@role_required(['super_admin', 'manager', 'user'])
@login_required
def get_all_suppliers():
    """
    Fetch all suppliers in the system.
    """
    try:
        user = g.supabase_user_client.from_('employees').select('department:department_id(name)').eq('user_id', g.current_user).execute()
        department = user.data[0]['department']['name']
        if department == 'warehouse' or g.user_role == 'super_admin':
            suppliers = g.supabase_user_client.from_('suppliers').select('supplier_id, name, contact_phone, contact_email, address, website, notes, created_at').execute()
            if suppliers.data:
                return jsonify({
                    "status": "success",
                    "data": suppliers.data
                }), 200
            return jsonify({
                "status": "success",
                "data": []
            }), 200
        return jsonify({
            "status": "error",
            "message": "You do not have permission to perform this action"
        }), 403
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app_views.route('/suppliers/<uuid:supplier_id>', methods=['GET'], strict_slashes=False)
@role_required(['super_admin', 'manager', 'user'])
@login_required
def get_supplier(supplier_id):
    """
    Fetch a specific supplier by its ID.
    """
    try:
        user = g.supabase_user_client.from_('employees').select('department:department_id(name)').eq('user_id', g.current_user).execute()
        department = user.data[0]['department']['name']
        if department == 'warehouse' or g.user_role == 'super_admin':
            supplier = g.supabase_user_client.from_('suppliers').select('supplier_id, name, contact_phone, contact_email, address, website, notes, created_at').eq('supplier_id', supplier_id).execute()
            if supplier.data:
                return jsonify({
                    "status": "success",
                    "data": supplier.data
                }), 200
            return jsonify({
                "status": "error",
                "message": "Supplier not found"
            }), 404
        return jsonify({
            "status": "error",
            "message": "You do not have permission to perform this action"
        }), 403
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app_views.route('/suppliers', methods=['POST'], strict_slashes=False)
@role_required(['super_admin', 'manager'])
@login_required
def create_supplier():
    """
    Create a new supplier.
    """
    try:
        user = g.supabase_user_client.from_('employees').select('department:department_id(name)').eq('user_id', g.current_user).execute()
        department = user.data[0]['department']['name']
        if department == 'warehouse' or g.user_role == 'super_admin':
            data = request.get_json()
            try:
                validated_data = SupplierCreateSchema(**data)
                supplier_data = validated_data.model_dump(exclude_unset=True)
                
                # Insert the new supplier
                response = g.supabase_user_client.from_('suppliers').insert(supplier_data).execute()
                if response.data:
                    return jsonify({
                        "status": "success",
                        "message": "Supplier created successfully",
                        "supplier": response.data[0]
                    }), 201
                return jsonify({
                    "status": "error",
                    "message": "Failed to create supplier"
                }), 500

            except ValidationError as ve:
                current_app.logger.error(f"Validation error creating supplier: {str(ve)}")
                return jsonify({
                    "status": "error",
                    "message": str(ve)
                }), 400
        return jsonify({
            "status": "error",
            "message": "You do not have permission to perform this action"
        }), 403
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app_views.route('/suppliers/<uuid:supplier_id>', methods=['PUT'], strict_slashes=False)
@role_required(['super_admin', 'manager'])
@login_required
def update_supplier(supplier_id):
    """
    Update an existing supplier.
    """
    try:
        user = g.supabase_user_client.from_('employees').select('department:department_id(name)').eq('user_id', g.current_user).execute()
        department = user.data[0]['department']['name']
        if department == 'warehouse' or g.user_role == 'super_admin':
            data = request.get_json()
            try:
                validated_data = SupplierUpdateSchema(**data)
                update_data = validated_data.model_dump(exclude_unset=True)
                
                # Update the supplier
                response = g.supabase_user_client.from_('suppliers').update(update_data).eq('supplier_id', supplier_id).execute()
                if response.data:
                    return jsonify({
                        "status": "success",
                        "message": "Supplier updated successfully",
                        "supplier": response.data[0]
                    }), 200
                return jsonify({
                    "status": "error",
                    "message": "Failed to update supplier"
                }), 500

            except ValidationError as ve:
                current_app.logger.error(f"Validation error updating supplier: {str(ve)}")
                return jsonify({
                    "status": "error",
                    "message": str(ve)
                }), 400
        return jsonify({
            "status": "error",
            "message": "You do not have permission to perform this action"
        }), 403
    except BadRequest as br:
        return jsonify({
            "status": "error",
            "message": str(br)
        }), 400
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    

@app_views.route('/suppliers/<uuid:supplier_id>', methods=['DELETE'], strict_slashes=False)
@role_required(['super_admin', 'manager'])
@login_required
def delete_supplier(supplier_id):
    """
    Delete a supplier from the system.
    """
    try:
        user = g.supabase_user_client.from_('employees').select('department:department_id(name)').eq('user_id', g.current_user).execute()
        department = user.data[0]['department']['name']
        if department == 'warehouse' or g.user_role == 'super_admin':
            # Check if the supplier exists
            supplier_check = g.supabase_user_client.from_('suppliers').select('supplier_id').eq('supplier_id', supplier_id).execute()
            if not supplier_check.data:
                return jsonify({
                    "status": "error",
                    "message": "Supplier not found"
                }), 404

            # Delete the supplier
            response = g.supabase_user_client.from_('suppliers').delete().eq('supplier_id', supplier_id).execute()
            if response.data:
                return jsonify({
                    "status": "success",
                    "message": "Supplier deleted successfully"
                }), 200
            return jsonify({
                "status": "error",
                "message": "Failed to delete supplier"
            }), 500
        return jsonify({
            "status": "error",
            "message": "You do not have permission to perform this action"
        }), 403
    except Exception as e:
        current_app.logger.error(f"Error deleting supplier: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500