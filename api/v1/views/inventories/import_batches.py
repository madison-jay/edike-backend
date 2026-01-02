from flask import g, current_app, jsonify, request
from api.v1.views import app_views
from api.v1.auth import login_required, role_required
from pydantic import ValidationError
from api.v1.services.inventories.import_services import (
    ImportServiceCreateSchema,
    ImportServiceUpdateSchema,
)

@app_views.route('/import_batches', methods=['GET'], strict_slashes=False)
@role_required(['super_admin', 'manager', 'user'])
def get_import_batches():
    """
    Fetch all import batches in the system.
    """
    try:
        user = g.supabase_user_client.from_('employees').select('department:department_id(name)').eq('user_id', g.current_user).execute()
        department = user.data[0]['department']['name']
        if department == 'warehouse' or g.user_role == 'super_admin':
            import_batches = g.supabase_user_client.from_('import_batches').select('*').execute()
            if import_batches.data:
                return jsonify({
                    "status": "success",
                    "data": import_batches.data
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

@app_views.route('/import_batches/<uuid:batch_id>', methods=['GET'], strict_slashes=False)
@role_required(['super_admin', 'manager', 'user'])
def get_import_batch(batch_id):
    """
    Fetch a specific import batch by its ID.
    """
    try:
        user = g.supabase_user_client.from_('employees').select('department:department_id(name)').eq('user_id', g.current_user).execute()
        department = user.data[0]['department']['name']
        if department == 'warehouse' or g.user_role == 'super_admin':
            import_batch = g.supabase_user_client.from_('import_batches').select('*').eq('batch_id', batch_id).execute()
            if import_batch.data:
                return jsonify({
                    "status": "success",
                    "data": import_batch.data
                }), 200
            return jsonify({
                "status": "error",
                "message": "Import batch not found"
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
    
@app_views.route('/import_batches', methods=['POST'], strict_slashes=False)
@role_required(['super_admin', 'manager'])
@login_required
def create_import_batch():
    """
    Create a new import batch.
    """
    try:
        user = g.supabase_user_client.from_('employees').select('department:department_id(name)').eq('user_id', g.current_user).execute()
        department = user.data[0]['department']['name']
        if department == 'warehouse' or g.user_role == 'super_admin':
            data = request.get_json()
            validated_data = ImportServiceCreateSchema(**data)
            
            batch_data = validated_data.model_dump()
            print(batch_data)
            
            response = g.supabase_user_client.from_('import_batches').insert(batch_data).execute()
            if response.data:
                return jsonify({
                    "status": "success",
                    "message": "Import batch created successfully",
                    "data": response.data[0]
                }), 201
            return jsonify({
                "status": "error",
                "message": "Failed to create import batch"
            }), 500
        return jsonify({
            "status": "error",
            "message": "You do not have permission to perform this action"
        }), 403
    except ValidationError as ve:
        current_app.logger.error(f"Validation error creating import batch: {str(ve)}")
        return jsonify({
            "status": "error",
            "message": str(ve)
        }), 400
    except Exception as e:
        current_app.logger.error(f"Error creating import batch: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    
@app_views.route('/import_batches/<uuid:batch_id>', methods=['PUT'], strict_slashes=False)
@role_required(['super_admin', 'manager'])
@login_required
def update_import_batch(batch_id):
    """
    Update an existing import batch.
    """
    try:
        user = g.supabase_user_client.from_('employees').select('department:department_id(name)').eq('user_id', g.current_user).execute()
        department = user.data[0]['department']['name']
        if (department == 'warehouse' and g.user_role == 'manager') or g.user_role == 'super_admin':
            data = request.get_json()
            validated_data = ImportServiceUpdateSchema(**data)
            batch_data = validated_data.model_dump(exclude_unset=True)
            
            # Check if the import batch exists
            batch_check = g.supabase_user_client.from_('import_batches').select('batch_id').eq('batch_id', batch_id).execute()
            if not batch_check.data:
                return jsonify({
                    "status": "error",
                    "message": "Import batch not found"
                }), 404
            
            response = g.supabase_user_client.from_('import_batches').update(batch_data).eq('batch_id', batch_id).execute()
            if response.data:
                return jsonify({
                    "status": "success",
                    "message": "Import batch updated successfully",
                    "data": response.data[0]
                }), 200
            return jsonify({
                "status": "error",
                "message": "Failed to update import batch"
            }), 500
        return jsonify({
            "status": "error",
            "message": "You do not have permission to perform this action"
        }), 403
    except ValidationError as ve:
        current_app.logger.error(f"Validation error updating import batch: {str(ve)}")
        return jsonify({
            "status": "error",
            "message": str(ve)
        }), 400
    except Exception as e:
        current_app.logger.error(f"Error updating import batch: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    

@app_views.route('/import_batches/<uuid:batch_id>', methods=['DELETE'], strict_slashes=False)
@role_required(['super_admin', 'manager'])
@login_required
def delete_import_batch(batch_id):
    """
    Delete an import batch from the system.
    """
    try:
        user = g.supabase_user_client.from_('employees').select('department:department_id(name)').eq('user_id', g.current_user).execute()
        department = user.data[0]['department']['name']
        if department == 'warehouse' or g.user_role == 'super_admin':
            # Check if the import batch exists
            batch_check = g.supabase_user_client.from_('import_batches').select('batch_id').eq('batch_id', batch_id).execute()
            if not batch_check.data:
                return jsonify({
                    "status": "error",
                    "message": "Import batch not found"
                }), 404
            
            response = g.supabase_user_client.from_('import_batches').delete().eq('batch_id', batch_id).execute()
            if response.data:
                return jsonify({
                    "status": "success",
                    "message": "Import batch deleted successfully"
                }), 200
            return jsonify({
                "status": "error",
                "message": "Failed to delete import batch"
            }), 500
        return jsonify({
            "status": "error",
            "message": "You do not have permission to perform this action"
        }), 403
    except Exception as e:
        current_app.logger.error(f"Error deleting import batch: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500