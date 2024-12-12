from flask import Blueprint, request, jsonify, session
from utils.db import db
from utils.authy import hash_password, verify_password
from pydantic import ValidationError
from products.routes import haversine
from utils.schemas import UserSchema
from flask import make_response

users_bp = Blueprint('users', __name__)

# Helper function for error handling
def handle_validation_error(error):
    return make_response(jsonify({"error": "Validation error", "details": error.errors()}), 400)

# Register User
@users_bp.route('/register', methods=['POST'])
def register_user():
    try:
        # Validate request data against UserSchema
        user_data = UserSchema(**request.json)
    except ValidationError as e:
        return handle_validation_error(e)
    
    # Hash the password if provided
    user_dict = user_data.dict()
    if user_dict.get("password"):
        user_dict["password"] = hash_password(user_dict["password"])
    
    # Add the user to Firestore
    doc_ref = db.collection('users').add(user_dict)
    return jsonify({
        "success": True,
        "message": "User registered successfully",
        "id": doc_ref[1].id
    }), 201

# Login User
@users_bp.route('/login', methods=['POST'])
def login_user():
    try:
        # Validate only phone_number and password for login
        login_data = UserSchema(**request.json, email=None, name=None)
    except ValidationError as e:
        return handle_validation_error(e)
    
    users = db.collection('users').where('phone_number', '==', login_data.phone_number).stream()
    user = next(users, None)
    
    if user and verify_password(login_data.password, user.to_dict()['password']):
        session['user_id'] = user.id  # Store user ID in session
        return jsonify({"success": True, "message": "Logged in successfully"}), 200
    
    return jsonify({"error": "Invalid credentials"}), 401

# Logout User
@users_bp.route('/logout', methods=['POST'])
def logout_user():
    session.pop('user_id', None)
    return jsonify({"success": True, "message": "Logged out successfully"}), 200

# Find Users by Filters
@users_bp.route('/find', methods=['GET'])
def find_users():
    user_type = request.args.get('type')
    description_keyword = request.args.get('description')
    focus_area_keyword = request.args.get('focus_area')
    lat = request.args.get('lat', type=float)
    lng = request.args.get('lng', type=float)
    radius = request.args.get('radius', type=float)

    query = db.collection('users')
    
    # Filter by user type
    if user_type:
        query = query.where('type', '==', user_type)
    
    # Fetch matching users
    users = query.stream()
    filtered_users = []

    for user in users:
        user_data = user.to_dict()
        
        # Filter by description keyword
        if description_keyword and description_keyword.lower() not in (user_data.get('description', '').lower()):
            continue

        # Filter by focus area
        if focus_area_keyword and focus_area_keyword.lower() not in (user_data.get('focus_area', '').lower()):
            continue

        # Filter by location and radius
        if lat is not None and lng is not None and radius is not None:
            user_location = user_data.get('location')
            if not user_location:
                continue
            
            user_lat = user_location.get('latitude')
            user_lng = user_location.get('longitude')
            
            distance = haversine(lat, lng, user_lat, user_lng)
            if distance > radius:
                continue
            
            user_data['distance'] = distance  # Include distance in the result
        
        filtered_users.append(user_data)
    
    return jsonify(filtered_users), 200

# Find Users by Location Only
@users_bp.route('/find_by_location', methods=['GET'])
def find_users_by_location():
    lat = request.args.get('lat', type=float)
    lng = request.args.get('lng', type=float)
    radius = request.args.get('radius', type=float, default=10)  # Default to 10 km radius

    if lat is None or lng is None:
        return jsonify({"error": "Latitude and longitude are required parameters"}), 400

    # Fetch users with location data
    users_ref = db.collection('users').where('location', '!=', None).stream()
    nearby_users = []

    for user in users_ref:
        user_data = user.to_dict()
        user_location = user_data.get('location')
        
        if not user_location:
            continue

        user_lat = user_location.get('latitude')
        user_lng = user_location.get('longitude')
        distance = haversine(lat, lng, user_lat, user_lng)

        if distance <= radius:
            user_data['distance'] = distance
            nearby_users.append(user_data)

    # Sort by distance (closest first)
    nearby_users.sort(key=lambda x: x['distance'])

    return jsonify(nearby_users), 200