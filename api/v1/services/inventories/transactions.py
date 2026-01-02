from pydantic import BaseModel, Field
from typing import Optional, Literal
from flask import g
import secrets
import string

class BoxCreateSchema(BaseModel):
    contents_id: str
    contents_type: Literal['product', 'component']
    batch_id: str
    quantity_in_box: int = Field(default=1)
    status: Literal['in_stock', 'sold', 'damaged', 'quarantined'] = Field(default='in_stock')
    location_id: Optional[str] = None
    shelf_code: Optional[str] = None

class BoxUpdateSchema(BaseModel):
    contents_id: Optional[str] = None
    contents_type: Optional[Literal['product', 'component']] = None
    quantity_in_box: Optional[int] = None
    status: Optional[Literal['in_stock', 'sold', 'damaged', 'quarantined']] = None
    location_id: Optional[str] = None
    shelf_code: Optional[str] = None
    batch_id: Optional[str] = None

    class Config:
        extra = "forbid"

class TransactionCreateSchema(BaseModel):
    type: Literal['inbound', 'outbound']
    order_id: Optional[str] = None
    batch_id: Optional[str] = None
    notes: Optional[str] = None
    created_by: str

    class Config:
        extra = "forbid"


def generate_barcode(sku, batch_number) -> str:
    """
    Generate a unique barcode for the box.
    """
    random_string = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    return f"QR-{sku}-{batch_number}-{random_string}"


def add_new_stock(data: dict):
    """
    Add new stock to the inventory.
    """
    """Algorithm

    1. Validate input
    2. Check the type of stock
    
    """
    table = 'products' if data['contents_type'] == 'product' else 'components'
    item_query = g.supabase_user_client.from_(table) \
        .select('name').eq(data['contents_type'] + '_id', data['contents_id']).execute()

    if not item_query.data:
        raise Exception("Item not found")

    item_name = item_query.data[0]['name']
    sku = g.supabase_user_client.from_(table).select('sku').eq(data['contents_type'] + '_id', data['contents_id']).execute().data[0]['sku']
    batch_number = g.supabase_user_client.from_('import_batches').select('batch_number').eq('batch_id', data['batch_id']).execute().data[0]['batch_number']

    # validate_stock = BoxCreateSchema(
    #     content_type=data['contents_type'], 
    #     content_id=data['contents_id'], 
    #     quantity_in_box=data['quantity_in_box'], 
    #     status=data['status'],
    #     batch_id=data['batch_id'],
    #     location_id=data['location_id'],
    #     shelf_code=data['shelf_code']
    # )

    validate_stock = BoxCreateSchema(**data)

    stock_data = validate_stock.model_dump()
    all_stocks = [stock_data.copy() for _ in range(data['boxes_count'])]
    all_barcodes = set()
    for stock in all_stocks:
         stock['barcode'] = generate_barcode(sku, batch_number)
         all_barcodes.add(stock['barcode'])

    response = g.supabase_user_client.from_('boxes').insert(all_stocks).execute()
    if response.data and len(response.data) == data['boxes_count']:
        # g.supabase_user_client.rpc(update_prod) #add function to update product stock
        g.supabase_user_client.rpc('update_stock', {
            'p_contents_type': data['contents_type'], 
            'p_contents_id': data['contents_id'], 
            'p_quantity_change': data['boxes_count'] * data['quantity_in_box']
        }).execute()

        created_by = g.supabase_user_client.from_('employees').select('id').eq('user_id', g.current_user).execute().data[0]['id']

        transaction_data = {
            "type": "inbound",
            "batch_id": data['batch_id'],
            "notes": f'Added {data["boxes_count"]} new boxes of {data["contents_type"]} {sku}',
            "created_by": created_by
        }

        validated_transaction = TransactionCreateSchema(**transaction_data)
        transaction = validated_transaction.model_dump()
        create_transaction = g.supabase_user_client.from_('inventory_transactions').insert(transaction).execute()
        if not create_transaction.data:
            raise Exception("Failed to create inventory transaction")

        return {
            "boxes": response.data,
            "barcodes": list(all_barcodes),
            "transaction": create_transaction.data[0],
            "item_name": item_name,
            "boxes_count": data['boxes_count']
        }
    
    raise Exception("Failed to add new stock")



def get_all_stocks():
    """
    Check available stock for products and components with breakdown.
    """
    products = g.supabase_user_client.from_('products').select(
        'product_id, sku, name, stock_quantity, '
        'bom(component_id, quantity, components(sku, name, stock_quantity))'
    ).execute().data

    # Fetch components
    components = g.supabase_user_client.from_('components').select(
        'component_id, sku, name, stock_quantity'
    ).execute().data

    # Format products with breakdown
    product_stock = [
        {
            "product_id": p['product_id'],
            "sku": p['sku'],
            "name": p['name'],
            "stock_quantity": p['stock_quantity'],
            "components_needed": [
                {
                    "component_id": item['component_id'],
                    "sku": item['components']['sku'],
                    "name": item['components']['name'],
                    "required_quantity": item['quantity'],
                    "available_quantity": item['components']['stock_quantity']
                } for item in p['bom'] or []
            ]
        } for p in products
    ]

    # Format components
    component_stock = [
        {
            "component_id": c['component_id'],
            "sku": c['sku'],
            "name": c['name'],
            "stock_quantity": c['stock_quantity']
        } for c in components
    ]

    return {
        "products": product_stock,
        "components": component_stock,
        "message": f"Retrieved stock for {len(product_stock)} products and {len(component_stock)} components"
    }


def get_stock_by_id(product_id: str):
    """
    Get stock details for a specific product or component by ID.
    """
    # Check if the ID belongs to a product
    product = g.supabase_user_client.from_('products').select(
        'product_id, sku, name, stock_quantity, '
        'bom(component_id, quantity, components(sku, name, stock_quantity))'
    ).eq('product_id', product_id).execute().data

    if product:
        p = product[0]
        return {
            "type": "product",
            "product_id": p['product_id'],
            "sku": p['sku'],
            "name": p['name'],
            "stock_quantity": p['stock_quantity'],
            "components_needed": [
                {
                    "component_id": item['component_id'],
                    "sku": item['components']['sku'],
                    "name": item['components']['name'],
                    "required_quantity": item['quantity'],
                    "available_quantity": item['components']['stock_quantity']
                } for item in p['bom'] or []
            ]
        }

    # Check if the ID belongs to a component
    component = g.supabase_user_client.from_('components').select(
        'component_id, sku, name, stock_quantity'
    ).eq('component_id', product_id).execute().data

    if component:
        c = component[0]
        return {
            "type": "component",
            "component_id": c['component_id'],
            "sku": c['sku'],
            "name": c['name'],
            "stock_quantity": c['stock_quantity']
        }

    raise Exception("Product or Component not found")


def sell_stock(data: list):
    """
    Sell stock by reducing box quantities and creating an outbound transaction.
    
    Expected input:
    [
        {
            "box_id": "uuid",
            "requested_quantity": int,
            "order_id": "uuid"   ← same for all items in batch
        }
    ]
    """
    if not isinstance(data, list) or len(data) == 0:
        raise ValueError("Expected non-empty list of items to sell")

    sold_boxes = []
    
    # Get employee ID for transaction
    employee_res = g.supabase_user_client.from_('employees') \
        .select('id').eq('user_id', g.current_user).single().execute()
    
    if not employee_res.data:
        raise Exception("Employee record not found")
    
    created_by = employee_res.data['id']

    total_sold = 0

    # Process each item in the batch
    for item in data:
        box_id = item.get("box_id")
        requested_qty = item.get("requested_quantity")
        order_id = item.get("order_id")

        if not box_id or not isinstance(requested_qty, int) or requested_qty <= 0:
            raise ValueError(f"Invalid item data: {item}")

        # Fetch box (must be in_stock)
        box_res = g.supabase_user_client.from_('boxes') \
            .select('*') \
            .eq('box_id', box_id) \
            .eq('status', 'in_stock') \
            .single().execute()

        if not box_res.data:
            raise ValueError(f"Box {box_id} not found or not available for sale")

        box = box_res.data

        if requested_qty > box['quantity_in_box']:
            raise ValueError(
                f"Requested {requested_qty} but only {box['quantity_in_box']} available in box {box_id}"
            )

        # Update box
        new_quantity = box['quantity_in_box'] - requested_qty
        new_status = 'sold' if new_quantity == 0 else 'in_stock'

        update_payload = {
            "quantity_in_box": new_quantity,
            "status": new_status
        }

        g.supabase_user_client.from_('boxes') \
            .update(update_payload) \
            .eq('box_id', box_id) \
            .execute()

        # Reduce total stock via RPC
        g.supabase_user_client.rpc('update_stock', {
            'p_contents_type': box['contents_type'],
            'p_contents_id': box['contents_id'],
            'p_quantity_change': -requested_qty  # Negative = reduce
        }).execute()

        sold_boxes.append({
            "box_id": box_id,
            "sold_quantity": requested_qty,
            "remaining_quantity": new_quantity,
            "new_status": new_status
        })

        total_sold += requested_qty

    # Create single outbound transaction for the whole batch
    transaction_data = {
        "type": "outbound",
        "order_id": data[0].get("order_id"),  # All items should have same order_id
        "notes": f"Sold {total_sold} units from {len(data)} box(es) for order",
        "created_by": created_by
    }

    try:
        validated = TransactionCreateSchema(**transaction_data)
        tx = validated.model_dump()
        result = g.supabase_user_client.from_('inventory_transactions') \
            .insert(tx).execute()

        if not result.data:
            raise Exception("Failed to record transaction")
    except Exception as e:
        raise Exception(f"Transaction failed: {str(e)}")

    return {
        "sold_boxes": sold_boxes,
        "total_units_sold": total_sold,
        "transaction Recorded": True
    }

def get_stock_by_location(location_id: str):
    """
    Get all stock entries at a specific location.
    Get the number of each products and components available at that location.

    """
    location = g.supabase_user_client.from_('locations').select('*').eq('id', location_id).execute().data
    if not location:
        raise Exception("Location not found")
    location = location[0]
    
    # boxes = g.supabase_user_client.rpc('get_stock_by_location', {'p_location_id': location_id}).execute().data
    # if not boxes:
    #     raise Exception("No stock found at this location")
    # print(boxes)  # Debugging line
    # return []

    boxes = g.supabase_user_client.from_('boxes').select('*').eq('location_id', location_id).execute().data
    if not boxes:
        return []

    products = {}
    components = {}

    for box in boxes:
        if box['contents_type'] == 'product':
            if box['contents_id'] not in products:
                product_info = g.supabase_user_client.from_('products').select('sku, name').eq('product_id', box['contents_id']).execute().data
                if product_info:
                    products[box['contents_id']] = {
                        "product_id": box['contents_id'],
                        "sku": product_info[0]['sku'],
                        "name": product_info[0]['name'],
                        "stock_quantity": 0
                    }
            products[box['contents_id']]['stock_quantity'] += box['quantity_in_box']
        elif box['contents_type'] == 'component':
            if box['contents_id'] not in components:
                component_info = g.supabase_user_client.from_('components').select('sku, name').eq('component_id', box['contents_id']).execute().data
                if component_info:
                    components[box['contents_id']] = {
                        "component_id": box['contents_id'],
                        "sku": component_info[0]['sku'],
                        "name": component_info[0]['name'],
                        "stock_quantity": 0
                    }
            components[box['contents_id']]['stock_quantity'] += box['quantity_in_box']
            
    return {
        "products": list(products.values()),
        "components": list(components.values())
    }
