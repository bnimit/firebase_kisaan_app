from flask import Blueprint, request, jsonify
from utils.db import db, firestore
from utils.authy import authenticate_login
from utils.schemas import ProductSchema
from pydantic import ValidationError
import csv
import io
import math

products_bp = Blueprint('products', __name__)

# Helper function to calculate distance between two coordinates (Haversine formula)
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def serialize_firestore_document(doc):
    """Convert Firestore document data to JSON-serializable format."""
    data = doc.to_dict()
    for key, value in data.items():
        if isinstance(value, firestore.GeoPoint):
            data[key] = {
                "latitude": value.latitude,
                "longitude": value.longitude
            }
    return data

# Helper function for validation error handling
def handle_validation_error(error):
    return jsonify({"error": "Validation error", "details": error.errors()}), 400

# Create Product
@products_bp.route('/', methods=['POST'])
def create_product():
    try:
        # Validate incoming request data using ProductSchema
        product_data = ProductSchema(**request.json)
    except ValidationError as e:
        return handle_validation_error(e)

    # Prepare data for Firestore
    product_dict = product_data.dict()
    if 'location' in product_dict and product_dict['location']:
        loc = product_dict.pop('location')
        product_dict['location'] = firestore.GeoPoint(loc['latitude'], loc['longitude'])

    # Add to Firestore
    doc_ref = db.collection('products').add(product_dict)
    return jsonify({
        "success": True,
        "message": "Product created successfully",
        "id": doc_ref[1].id
    }), 201

# Fetch All Products
@products_bp.route('/', methods=['GET'])
def get_all_products():
    products = db.collection('products').stream()
    product_list = [serialize_firestore_document(doc) for doc in products]
    return jsonify(product_list), 200

# Fetch Product by ID
@products_bp.route('/<string:product_id>', methods=['GET'])
def get_product_by_id(product_id):
    doc = db.collection('products').document(product_id).get()
    if doc.exists:
        return jsonify(serialize_firestore_document(doc)), 200
    else:
        return jsonify({"error": "Product not found"}), 404

# Fetch Products by Location
@products_bp.route('/location', methods=['GET'])
def get_products_by_location():
    lat = request.args.get('lat', type=float)
    lng = request.args.get('lng', type=float)

    if lat is None or lng is None:
        return jsonify({"error": "Latitude and longitude are required parameters"}), 400

    geo_point = firestore.GeoPoint(lat, lng)
    query = db.collection('products').where('location', '==', geo_point).stream()
    products = [serialize_firestore_document(doc) for doc in query]

    if products:
        return jsonify(products), 200
    else:
        return jsonify({"error": "No products found at the given location"}), 404

# Fetch Products within a Range of a Given Location
@products_bp.route('/filter_by_location', methods=['GET'])
def filter_products_by_location():
    # Get query parameters
    lat = request.args.get('lat', type=float)
    lng = request.args.get('lng', type=float)
    radius = request.args.get('radius', type=float, default=10)  # Default to 10 km radius

    if lat is None or lng is None:
        return jsonify({"error": "Latitude and longitude are required parameters"}), 400

    # Fetch all products with a location field
    products_ref = db.collection('products').where('location', '!=', None).stream()
    products = []

    for product in products_ref:
        product_data = serialize_firestore_document(product)
        if 'location' in product_data:
            product_lat = product_data['location']['latitude']
            product_lng = product_data['location']['longitude']
            distance = haversine(lat, lng, product_lat, product_lng)

            if distance <= radius:
                product_data['distance'] = distance  # Add distance to the result
                products.append(product_data)

    # Sort products by distance (closest first)
    products.sort(key=lambda x: x['distance'])

    if products:
        return jsonify(products), 200
    else:
        return jsonify({"error": "No products found within the given range"}), 404
    
# Bulk Create Products from CSV
@products_bp.route('/bulk_upload', methods=['POST'])
def bulk_upload_products():
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No file selected for uploading"}), 400

    try:
        # Read CSV file
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_reader = csv.DictReader(stream)

        # Prepare batch for Firestore
        batch = db.batch()
        errors = []
        count = 0

        for row_number, row in enumerate(csv_reader, start=1):
            try:
                # Validate each row using ProductSchema
                product_data = ProductSchema(**row)

                # Prepare location field as GeoPoint if present
                if 'location' in product_data.dict() and product_data.location:
                    loc = product_data.location
                    product_data.location = firestore.GeoPoint(loc['latitude'], loc['longitude'])

                # Add the product to the Firestore batch
                doc_ref = db.collection('products').document()
                batch.set(doc_ref, product_data.dict())
                count += 1
            except ValidationError as e:
                # Collect validation errors for reporting
                errors.append({"row": row_number, "error": handle_validation_error(e)})

        # Commit batch to Firestore
        batch.commit()

        response = {
            "success": True,
            "message": f"{count} products uploaded successfully.",
            "errors": errors
        }
        return jsonify(response), 200
    except Exception as e:
        return jsonify({"error": "An error occurred while processing the file", "details": str(e)}), 500