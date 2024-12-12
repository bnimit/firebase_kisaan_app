from flask import Blueprint, request, jsonify
from utils.db import db
from utils.authy import authenticate_login
from utils.schemas import OrderSchema
from pydantic import ValidationError
from datetime import datetime

orders_bp = Blueprint('orders', __name__)

# Helper function for validation error handling
def handle_validation_error(error):
    return jsonify({"error": "Validation error", "details": error.errors()}), 400

# Create Order
@orders_bp.route('/', methods=['POST'])
def create_order():
    try:
        order_data = OrderSchema(**request.json)
    except ValidationError as e:
        return handle_validation_error(e)

    # Save order to Firestore
    order_dict = order_data.dict()
    doc_ref = db.collection('orders').add(order_dict)
    return jsonify({
        "success": True,
        "message": "Order created successfully",
        "id": doc_ref[1].id
    }), 201

# Fetch Order by ID
@orders_bp.route('/<string:order_id>', methods=['GET'])
def get_order_by_id(order_id):
    doc = db.collection('orders').document(order_id).get()
    if doc.exists:
        return jsonify(doc.to_dict()), 200
    else:
        return jsonify({"error": "Order not found"}), 404

# Fetch All Orders by a User
@orders_bp.route('/user/<string:user_id>', methods=['GET'])
def get_orders_by_user(user_id):
    orders_ref = db.collection('orders').where('user_id', '==', user_id).stream()
    orders = [doc.to_dict() for doc in orders_ref]
    return jsonify(orders), 200

# Fetch Orders by Date Range
@orders_bp.route('/date_range', methods=['GET'])
def get_orders_by_date_range():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if not start_date or not end_date:
        return jsonify({"error": "Both start_date and end_date are required parameters"}), 400

    try:
        start_date = datetime.fromisoformat(start_date)
        end_date = datetime.fromisoformat(end_date)
    except ValueError:
        return jsonify({"error": "Invalid date format. Use ISO 8601 format"}), 400

    orders_ref = db.collection('orders').where('order_date', '>=', start_date).where('order_date', '<=', end_date).stream()
    orders = [doc.to_dict() for doc in orders_ref]
    return jsonify(orders), 200

# Update Order Status
@orders_bp.route('/<string:order_id>', methods=['PATCH'])
def update_order_status(order_id):
    new_status = request.json.get('order_status')

    if new_status not in ['created', 'packed', 'shipped', 'delivered']:
        return jsonify({"error": "Invalid order status"}), 400

    order_ref = db.collection('orders').document(order_id)
    order = order_ref.get()

    if not order.exists:
        return jsonify({"error": "Order not found"}), 404

    order_ref.update({"order_status": new_status})
    return jsonify({"success": True, "message": "Order status updated successfully"}), 200

# Delete Order
@orders_bp.route('/<string:order_id>', methods=['DELETE'])
def delete_order(order_id):
    order_ref = db.collection('orders').document(order_id)
    order = order_ref.get()

    if not order.exists:
        return jsonify({"error": "Order not found"}), 404

    order_ref.delete()
    return jsonify({"success": True, "message": "Order deleted successfully"}), 200