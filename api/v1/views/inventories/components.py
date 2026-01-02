from flask import g, current_app, jsonify, request
from api.v1.views import app_views
from api.v1.auth import login_required, role_required
from pydantic import ValidationError
from api.v1.services.inventories.components_services import (
    ComponentCreateSchema,
    ComponentUpdateSchema,
)
from uuid import UUID

@app_views.route('/components', methods=['GET'], strict_slashes=False)
@role_required(['super_admin', 'manager', 'user'])
@login_required
def get_all_components():
    """
    Fetch all components in the warehouse.
    """
    try:
        user = g.supabase_user_client.from_('employees').select('department:department_id(name)').eq('user_id', g.current_user).execute()
        department = user.data[0]['department']['name']
        if department == 'warehouse' or g.user_role == 'super_admin':
            components = g.supabase_user_client.from_('components').select('component_id, name, description,  stock_quantity, color, sku, created_at, component_image').execute()
            if components.data:
                return jsonify({
                    "status": "success",
                    "data": components.data
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
    
@app_views.route('/components/<uuid:component_id>', methods=['GET'], strict_slashes=False)
@role_required(['super_admin', 'manager', 'user'])
@login_required
def get_component(component_id):
    """
    Fetch a specific component by its ID.
    """
    try:
        user = g.supabase_user_client.from_('employees').select('department:department_id(name)').eq('user_id', g.current_user).execute()
        department = user.data[0]['department']['name']
        if department == 'warehouse' or g.user_role == 'super_admin':
            component = g.supabase_user_client.from_('components').select('component_id, name, description, stock_quantity, color, sku, created_at, component_image').eq('component_id', component_id).execute()
            if component.data:
                return jsonify({
                    "status": "success",
                    "data": component.data
                }), 200
            return jsonify({
                "status": "error",
                "message": "Component not found"
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
    
@app_views.route('/components', methods=['POST'], strict_slashes=False)
@role_required(['super_admin', 'manager'])
@login_required
def create_component():
    """
    Create a new component in the warehouse.
    """
    try:
        user = g.supabase_user_client.from_('employees').select('department:department_id(name)').eq('user_id', g.current_user).execute()
        department = user.data[0]['department']['name']
        if (department == 'warehouse' and g.user_role == 'manager') or g.user_role == 'super_admin':
            data = request.get_json()
            try:
                validated_data = ComponentCreateSchema(**data)
                component_data = validated_data.model_dump()

                
                # Insert the new component
                response = g.supabase_user_client.from_('components').insert(component_data).execute()
                if response.data:
                    return jsonify({
                        "status": "success",
                        "message": "Component created successfully",
                        "data": response.data[0]
                    }), 201
                return jsonify({
                    "status": "error",
                    "message": "Failed to create component"
                }), 500

            except ValidationError as ve:
                current_app.logger.error(f"Validation error creating component: {str(ve)}")
                return jsonify({
                    "status": "error",
                    "message": str(ve)
                }), 400
        return jsonify({
            "status": "error",
            "message": "You do not have permission to perform this action"
        }), 403
    except Exception as e:
        current_app.logger.error(f"Error creating component: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app_views.route('/components/<uuid:component_id>', methods=['PUT'], strict_slashes=False)
@role_required(['super_admin', 'manager'])
@login_required
def update_component(component_id):
    """
    Update an existing component in the warehouse.
    """
    try:
        user = g.supabase_user_client.from_('employees').select('department:department_id(name)').eq('user_id', g.current_user).execute()
        department = user.data[0]['department']['name']
        if (department == 'warehouse' and g.user_role == 'manager') or g.user_role == 'super_admin':
            data = request.get_json()
            try:
                validated_data = ComponentUpdateSchema(**data)
                update_data = validated_data.model_dump(exclude_unset=True)

                # Check if the component exists
                component_check = g.supabase_user_client.from_('components').select('component_id').eq('component_id', component_id).execute()
                if not component_check.data:
                    return jsonify({
                        "status": "error",
                        "message": "Component not found"
                    }), 404

                # Update the component
                response = g.supabase_user_client.from_('components').update(update_data).eq('component_id', component_id).execute()
                if response.data:
                    return jsonify({
                        "status": "success",
                        "message": "Component updated successfully",
                        "data": response.data[0]
                    }), 200
                return jsonify({
                    "status": "error",
                    "message": "Failed to update component"
                }), 500

            except ValidationError as ve:
                current_app.logger.error(f"Validation error updating component: {str(ve)}")
                return jsonify({
                    "status": "error",
                    "message": str(ve)
                }), 400
        return jsonify({
            "status": "error",
            "message": "You do not have permission to perform this action"
        }), 403
    except Exception as e:
        current_app.logger.error(f"Error updating component: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    
@app_views.route('/components/<uuid:component_id>', methods=['DELETE'], strict_slashes=False)
@role_required(['super_admin', 'manager'])
@login_required
def delete_component(component_id):
    """Delete a component by its ID"""
    try:
        user = g.supabase_user_client.from_('employees').select('department:department_id(name)').eq('user_id', g.current_user).execute()
        department = user.data[0]['department']['name']
        if (department == 'warehouse' and g.user_role == 'manager') or g.user_role == 'super_admin':
            # Check if the component exists
            component_check = g.supabase_user_client.from_('components').select('component_id').eq('component_id', component_id).execute()
            if not component_check.data:
                return jsonify({
                    "status": "error",
                    "message": "Component not found"
                }), 404

            # Delete the component
            response = g.supabase_user_client.from_('components').delete().eq('component_id', component_id).execute()
            if response.data:
                return jsonify({
                    "status": "success",
                    "message": "Component deleted successfully"
                }), 200
            return jsonify({
                "status": "error",
                "message": "Failed to delete component"
            }), 500
        return jsonify({
            "status": "error",
            "message": "You do not have permission to perform this action"
        }), 403
    except Exception as e:
        current_app.logger.error(f"Error deleting component: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500