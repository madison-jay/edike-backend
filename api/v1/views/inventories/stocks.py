from flask import g, current_app, jsonify, request
from api.v1.views import app_views
from api.v1.auth import login_required, role_required
from pydantic import ValidationError
from api.v1.utils.pdf_generator import generate_barcode_pdf
from api.v1.services.inventories.transactions import (
    add_new_stock,
    get_all_stocks,
    get_stock_by_id,
    get_stock_by_location,
    sell_stock
)
import traceback
import base64



@app_views.route('/stocks', methods=['GET'], strict_slashes=False)
@role_required(['super_admin', 'manager', 'user'])
@login_required
def fetch_stocks():
    """
    Retrieve all stock entries with product and component breakdown.
    """
    try:
        user = g.supabase_user_client.from_('employees').select('department:department_id(name)').eq('user_id', g.current_user).execute()
        department = user.data[0]['department']['name']
        if department in ['warehouse', 'sales'] or g.user_role == 'super_admin':
            try:
                print
                stocks = get_all_stocks()
                return jsonify({
                    "status": "success",
                    "data": stocks
                }), 200
            except Exception as e:
                current_app.logger.error(f"Error fetching stocks: {str(e)}")
                traceback.print_exc()
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500
        return jsonify({
            "status": "error",
            "message": "You do not have permission to perform this action"
        }), 403
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app_views.route('/stocks/<string:product_id>', methods=['GET'], strict_slashes=False)
@role_required(['super_admin', 'manager', 'user'])
@login_required
def fetch_stock_by_id(product_id):
    """
    Retrieve stock details for a specific product by its ID.
    """
    try:
        user = g.supabase_user_client.from_('employees').select('department:department_id(name)').eq('user_id', g.current_user).execute()
        department = user.data[0]['department']['name']
        if department in ['warehouse', 'sales'] or g.user_role == 'super_admin':
            try:
                stock = get_stock_by_id(product_id)
                if stock:
                    return jsonify({
                        "status": "success",
                        "data": stock
                    }), 200
                else:
                    return jsonify({
                        "status": "error",
                        "message": "Product not found"
                    }), 404
            except Exception as e:
                current_app.logger.error(f"Error fetching stock by ID: {str(e)}")
                traceback.print_exc()
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500
        return jsonify({
            "status": "error",
            "message": "You do not have permission to perform this action"
        }), 403
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app_views.route('/stocks/locations/<string:location_id>', methods=['GET'], strict_slashes=False)
@role_required(['super_admin', 'manager', 'user'])
@login_required
def fetch_stock_by_location(location_id):
    """
    Retrieve stock details for a specific location by its ID.
    """
    try:
        user = g.supabase_user_client.from_('employees').select('department:department_id(name)').eq('user_id', g.current_user).execute()
        department = user.data[0]['department']['name']
        if department in ['warehouse', 'sales'] or g.user_role == 'super_admin':
            try:
                stock = get_stock_by_location(location_id)
                if stock:
                    return jsonify({
                        "status": "success",
                        "data": stock
                    }), 200
                else:
                    return jsonify({
                        "status": "error",
                        "message": "Location not found"
                    }), 404
            except Exception as e:
                current_app.logger.error(f"Error fetching stock by location: {str(e)}")
                traceback.print_exc()
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500
        return jsonify({
            "status": "error",
            "message": "You do not have permission to perform this action"
        }), 403
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app_views.route('/stocks', methods=['POST'], strict_slashes=False)
@role_required(['super_admin', 'manager'])
@login_required
def create_stock_entry():
    """
    Add new stock entry to the inventory + generate PDF labels.
    """
    try:
        user = g.supabase_user_client.from_('employees') \
            .select('department:department_id(name)') \
            .eq('user_id', g.current_user).execute()
        
        department = user.data[0]['department']['name']
        if department != 'warehouse' and g.user_role != 'super_admin':
            return jsonify({"status": "error", "message": "Permission denied"}), 403

        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "Invalid JSON"}), 400


        try:
            # Call service to create boxes and get item name
            transaction = add_new_stock(data)

            # --- Generate PDF ---
            barcode_data = [
                {
                    "barcode": box['barcode'],
                    "quantity_in_box": box['quantity_in_box']
                }
                for box in transaction["boxes"]
            ]

            pdf_buffer = generate_barcode_pdf(
                barcodes_data=barcode_data,
                item_name=transaction["item_name"],
                batch_id=data["batch_id"],
                boxes_count=transaction["boxes_count"],
                quantity_per_box=data["quantity_in_box"],
                password="madison123"
            )

            pdf_base64 = base64.b64encode(pdf_buffer.read()).decode('utf-8')
            pdf_filename = f"{transaction['item_name'].replace(' ', '_')}_{data['batch_id']}.pdf"

            # --- Insert barcodes into DB ---
            for barcode, box in zip(transaction.get("barcodes", []), transaction["boxes"]):
                try:
                    g.service_supabase_client.from_("barcodes").insert({
                        "barcode": barcode,
                        "box_id": box["box_id"],
                        "transaction_id": transaction["transaction"]["transaction_id"]  # ← CORRECT
                    }).execute()
                except Exception as e:
                    current_app.logger.error(f"Barcode insert failed: {str(e)}")

            # --- Return success with PDF ---
            return jsonify({
                "status": "success",
                "data": transaction["boxes"],
                "barcodes": transaction["barcodes"],
                "transaction": transaction["transaction"],
                "pdf": {
                    "filename": pdf_filename,
                    "data": pdf_base64,
                    "password_protected": True,
                    "password_hint": "Use 'madison123' to open"
                }
            }), 201

        except ValueError as ve:
            return jsonify({"status": "error", "message": str(ve)}), 400
        except Exception as e:
            current_app.logger.error(f"Stock entry error: {str(e)}")
            traceback.print_exc()
            return jsonify({"status": "error", "message": str(e)}), 500

    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


@app_views.route('/stocks/sell', methods=['POST'], strict_slashes=False)
@role_required(['super_admin', 'manager'])
@login_required
def sell_stock_in_batch():
    """
    Sell multiple boxes in batch.
    Expected payload:
    [
        {
            "box_id": "uuid-string",
            "requested_quantity": int,
            "order_id": "uuid-string"
        }
    ]
    """
    try:
        # Permission check
        user = g.supabase_user_client.from_('employees') \
            .select('department:department_id(name)') \
            .eq('user_id', g.current_user).execute()
        
        department = user.data[0]['department']['name'] if user.data else None
        if department != 'warehouse' and g.user_role != 'super_admin':
            return jsonify({"status": "error", "message": "Permission denied"}), 403

        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No JSON data provided"}), 400

        if not isinstance(data, list):
            return jsonify({"status": "error", "message": "Expected a list of items"}), 400

        if len(data) == 0:
            return jsonify({"status": "error", "message": "Empty items list"}), 400

        for i, item in enumerate(data):
            if not isinstance(item, dict):
                return jsonify({"status": "error", "message": f"Item {i} is not a valid object"}), 400
            if "box_id" not in item or "requested_quantity" not in item or "order_id" not in item:
                return jsonify({"status": "error", "message": f"Missing fields in item {i}"}), 400
            if not isinstance(item["requested_quantity"], int) or item["requested_quantity"] <= 0:
                return jsonify({"status": "error", "message": f"Invalid requested_quantity in item {i}"}), 400


        result = sell_stock(data)

        return jsonify({
            "status": "success",
            "data": result,
            "message": "Stock sold successfully"
        }), 200

    except ValueError as ve:
        return jsonify({"status": "error", "message": str(ve)}), 400
    except Exception as e:
        current_app.logger.error(f"Sell stock error: {str(e)}")
        traceback.print_exc()
        return jsonify({"status": "error", "message": "Internal server error"}), 500

#get all transactions history
@app_views.route('/inventory/transactions', methods=['GET'], strict_slashes=False)
@role_required(['super_admin', 'manager', 'user'])
@login_required
def fetch_inventory_transactions():
    """
    Retrieve all inventory transactions.
    """
    try:
        user = g.supabase_user_client.from_('employees').select('department:department_id(name)').eq('user_id', g.current_user).execute()
        department = user.data[0]['department']['name']
        if department in ['warehouse'] or g.user_role == 'super_admin':
            try:
                transactions = []
                if g.user_role == 'user':
                    transactions = g.service_supabase_client.from_('inventory_transactions').select('*').eq('created_by', user.data[0]['id']).order('transaction_date', desc=True).execute()
                else:
                    transactions = g.service_supabase_client.from_('inventory_transactions').select('*').order('transaction_date', desc=True).execute()
                return jsonify({
                    "status": "success",
                    "data": transactions.data
                }), 200
            except Exception as e:
                current_app.logger.error(f"Error fetching inventory transactions: {str(e)}")
                traceback.print_exc()
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500
        return jsonify({
            "status": "error",
            "message": "You do not have permission to perform this action"
        }), 403
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app_views.route('/stocks/barcode/<string:barcode>', methods=['GET'], strict_slashes=False)
@role_required(['super_admin', 'manager', 'user'])
@login_required
def get_box_by_barcode(barcode):
    # Use SERVICE client (bypasses RLS)
    res = (g.service_supabase_client
           .from_('barcodes')
           .select('barcode, box_id, boxes!inner(contents_id, contents_type, quantity_in_box)')
           .eq('barcode', barcode)
           .execute())

    if not res.data:
        return jsonify({"status": "error", "message": "Barcode not found"}), 404

    box = res.data[0]['boxes']
    barcode_data = res.data[0]

    # Determine table and column
    if box['contents_type'] == 'product':
        table = 'products'
        id_col = 'product_id'
        name_col = 'name'
    else:
        table = 'components'
        id_col = 'component_id'
        name_col = 'name'

    # Use correct column names
    item = (g.service_supabase_client
            .from_(table)
            .select(f'{id_col}, {name_col}')
            .eq(id_col, box['contents_id'])
            .single()
            .execute())

    if not item.data:
        return jsonify({"status": "error", "message": f"{box['contents_type'].title()} not found"}), 404

    # Build response
    result = {
        "barcode": barcode_data['barcode'],
        "box_id": barcode_data['box_id'],
        "boxes": {
            "product_id": item.data[id_col] if box['contents_type'] == 'product' else None,
            "product_name": item.data[name_col] if box['contents_type'] == 'product' else None,
            "component_id": item.data[id_col] if box['contents_type'] == 'component' else None,
            "component_name": item.data[name_col] if box['contents_type'] == 'component' else None,
            "quantity_in_box": box['quantity_in_box']
        }
    }

    return jsonify({"status": "success", "data": result}), 200

#Fetch all barcodes for a transaction
@app_views.route('/inventory/transactions/<string:transaction_id>/barcodes', methods=['GET'], strict_slashes=False)
@role_required(['super_admin', 'manager', 'user'])
@login_required
def fetch_barcodes_by_transaction(transaction_id):
    """
    Retrieve all barcodes associated with a specific inventory transaction.
    """
    try:
        user = g.supabase_user_client.from_('employees').select('department:department_id(name)').eq('user_id', g.current_user).execute()
        department = user.data[0]['department']['name']
        if department in ['warehouse', 'sales'] or g.user_role == 'super_admin':
            try:
                barcodes_response = g.service_supabase_client.from_('barcodes').select('*').eq('transaction_id', transaction_id).execute()
                if barcodes_response.data:
                    return jsonify({
                        "status": "success",
                        "data": barcodes_response.data
                    }), 200
                else:
                    return jsonify({
                        "status": "error",
                        "message": "No barcodes found for this transaction"
                    }), 404
            except Exception as e:
                current_app.logger.error(f"Error fetching barcodes by transaction: {str(e)}")
                traceback.print_exc()
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500
        return jsonify({
            "status": "error",
            "message": "You do not have permission to perform this action"
        }), 403
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500 

    