import hashlib
import os
from functools import wraps
from flask import session, jsonify

def authenticate_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user_id exists in session
        if 'user_id' not in session:
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)
    return decorated_function

def hash_password(password):
    salt = os.urandom(16)
    hashed_password = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
    return salt + hashed_password  # Combine salt and hashed password

def verify_password(password, stored_password):
    salt = stored_password[:16]
    stored_hash = stored_password[16:]
    hashed_password = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
    return hashed_password == stored_hash