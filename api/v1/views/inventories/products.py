# products view
from pydantic import ValidationError
from api.v1.services.inventories.products_services import ProductsCreateScheme, ProductsUpdateScheme
from flask import request, g, Blueprint, jsonify
from api.v1.views import app_views
from api.v1.auth import login_required, role_required
import traceback
from werkzeug.exceptions import BadRequest

#departments 
# sales, warehouse, hr, finance, IT, super_admin


@app_views.route('/products', methods=['GET'], strict_slashes=False)
@role_required(['super_admin', 'manager', 'user'])
@login_required
def get_all_products():
    """
    fetch all the available poroducts in the database
    """
    try:
        print(g.current_user)
        user = g.supabase_user_client.from_('employees').select('id, department:department_id(name)').eq('user_id', g.current_user).execute()
       
        department = user.data[0]['department']['name']
        print(department)
        if department in ['warehouse', 'sales']  or g.user_role == 'super_admin':
            products = g.supabase_user_client.from_('products').select('product_id, sku,name, description, price, color, created_at, product_image').execute()
            if products.data:
                return jsonify({
                    "status": "success",
                    "data": products.data
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
            

@app_views.route('/products/<uuid:product_id>', methods=['GET'], strict_slashes=False)
@role_required(['super_admin', 'manager', 'user'])
@login_required
def get_product(product_id):
    """
    fetch a specific product by its ID
    """
    try:
        user = g.supabase_user_client.from_('employees').select('department:department_id(name)').eq('user_id', g.current_user).execute()
        department = user.data[0]['department']['name']
        if department == 'warehouse' or g.user_role == 'super_admin':
            product = g.supabase_user_client.from_('products').select('product_id, sku,name, description, price, color, created_at, product_image').eq('product_id', product_id).execute()
            if product.data:
                return jsonify({
                    "status": "success",
                    "data": product.data
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


@app_views.route('/products', methods=['POST'], strict_slashes=False)
@role_required(['super_admin', 'manager'])
@login_required
def create_product():
    """
    create a new product
    """
    try:
        user = g.supabase_user_client.from_('employees').select('id, department:department_id(name)').eq('user_id', g.current_user).execute()
      
        department = user.data[0]['department']['name']
        if department == 'warehouse' or g.user_role == 'super_admin':
            print(request.get_json())
            data = request.get_json()
            validated_data = ProductsCreateScheme(**data)
            print(validated_data)
            product_data = validated_data.model_dump()
            print(product_data)
            new_product = g.supabase_user_client.from_('products').insert(product_data).execute()
            if  new_product.data:
                return jsonify({
                    "status": "success",
                    "data": new_product.data[0]
                }), 201
            return jsonify({
                "status": "error",
                "message": new_product.data
            }), 400
        return jsonify({
            "status": "error",
            "message": "You do not have permission to perform this action"
        }), 403
    except ValidationError as ve:
        return jsonify({
            "status": "error",
            "message": ve.errors()
        }), 400
    except BadRequest as br:
        return jsonify({
            "status": "error",
            "message": "Invalid JSON payload",
            "details": str(br)
        }), 400
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    
@app_views.route('/products/<uuid:product_id>', methods=['PUT'], strict_slashes=False)
@role_required(['super_admin', 'manager'])
@login_required
def update_product(product_id):
    """
    update a product by its ID
    """
    try:
        user = g.supabase_user_client.from_('employees').select('department:department_id(name)').eq('user_id', g.current_user).execute()
        department = user.data[0]['department']['name']
        if (department == 'warehouse' and g.user_role == 'manager') or g.user_role == 'super_admin':
            data = request.get_json()
            validated_data = ProductsUpdateScheme(**data)
            product_data = validated_data.model_dump(exclude_unset=True)
            if not product_data:
                return jsonify({
                    "status": "error",
                    "message": "No data provided for update"
                }), 400
            updated_product = g.supabase_user_client.from_('products').update(product_data).eq('product_id', product_id).execute()
            if updated_product.data:
                return jsonify({
                    "status": "success",
                    "data": updated_product.data[0]
                }), 200
            return jsonify({
                "status": "error",
                "message": "Product not found or no changes made"
            }), 404
        return jsonify({
            "status": "error",
            "message": "You do not have permission to perform this action"
        }), 403
    
    except ValidationError as ve:
        return jsonify({
            "status": "error",
            "message": ve.errors()
        }), 400
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    
@app_views.route('/products/<uuid:product_id>', methods=['DELETE'], strict_slashes=False)
@role_required(['super_admin', 'manager'])
@login_required
def delete_product(product_id):
    """
    delete a product by its ID
    """
    try:
        user = g.supabase_user_client.from_('employees').select('department:department_id(name)').eq('user_id', g.current_user).execute()
        department = user.data[0]['department']['name']
        if (department == 'warehouse' and g.user_role == 'manager') or g.user_role == 'super_admin':
            deleted_product = g.supabase_user_client.from_('products').delete().eq('product_id', product_id).execute()
            if deleted_product.data:
                return jsonify({
                    "status": "success",
                    "message": "Product deleted successfully"
                }), 200
            return jsonify({
                "status": "error",
                "message": "Product not found"
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


## add a component to a product's BOM 
@app_views.route('/products/<uuid:product_id>/component', methods=['POST'], strict_slashes=False)
@role_required(['super_admin', 'manager'])
@login_required
def add_component_to_product_bom(product_id):
    """
    Add a component to a product's Bill of Materials (BOM)
    """
    try:
        user = g.supabase_user_client.from_('employees').select('id, department:department_id(name)').eq('user_id', g.current_user).execute()
      
        department = user.data[0]['department']['name']
        if department == 'warehouse' or g.user_role == 'super_admin':
            data = request.get_json()
            # Validate input data
            if 'component_id' not in data or 'quantity' not in data:
                return jsonify({
                    "status": "error",
                    "message": "component_id and quantity are required fields"
                }), 400
            
            # Check if the product exists
            product_check = g.supabase_user_client.from_('products').select('product_id').eq('product_id', product_id).execute()
            if not product_check.data:
                return jsonify({
                    "status": "error",
                    "message": "Product not found"
                }), 404
            
            # Check if the component exists
            component_check = g.supabase_user_client.from_('components').select('component_id').eq('component_id', data['component_id']).execute()
            if not component_check.data:
                return jsonify({
                    "status": "error",
                    "message": "Component not found"
                }), 404
            
            # Add the component to the product's BOM
            bom_data = {
                "product_id": str(product_id),
                "component_id": str(data['component_id']),
                "quantity": data['quantity']
            }
            new_bom_item = g.supabase_user_client.from_('bom').insert(bom_data).execute()
            if new_bom_item.data:
                return jsonify({
                    "status": "success",
                    "data": new_bom_item.data[0]
                }), 201
            return jsonify({
                "status": "error",
                "message": new_bom_item.error.message if new_bom_item.error else "Failed to add component to BOM"
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

# remove a component from a product's BOM
@app_views.route('/products/<uuid:product_id>/component/<uuid:component_id>', methods=['DELETE'], strict_slashes=False)
@role_required(['super_admin', 'manager'])
@login_required
def remove_component_from_product_bom(product_id, component_id):
    """remove a component from a product's Bill of Materials (BOM)"""
    try:
        user = g.supabase_user_client.from_('employees').select('department:department_id(name)').eq('user_id', g.current_user).execute()
        department = user.data[0]['department']['name']
        if (department == 'warehouse' and g.user_role == 'manager') or g.user_role == 'super_admin':
            # Check if the BOM entry exists
            bom_check = g.supabase_user_client.from_('bom').select('id').eq('product_id', product_id).eq('component_id', component_id).execute()
            if not bom_check.data:
                return jsonify({
                    "status": "error",
                    "message": "BOM entry not found"
                }), 404
            
            # Remove the component from the product's BOM
            deleted_bom_item = g.supabase_user_client.from_('bom').delete().eq('product_id', product_id).eq('component_id', component_id).execute()
            if deleted_bom_item.data:
                return jsonify({
                    "status": "success",
                    "message": "Component removed from BOM successfully"
                }), 200
            return jsonify({
                "status": "error",
                "message": "Failed to remove component from BOM"
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