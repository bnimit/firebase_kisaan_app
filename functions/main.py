from flask import Flask
from functions_framework import create_app as create_cloud_function_app
import os

 # Import Firestore client (db)
from utils.db import db 

# Create Flask App
def create_app():
    app = Flask(__name__)
    app.secret_key = os.urandom(24)

    # Register Blueprints
    from products.routes import products_bp
    from users.routes import users_bp
    app.register_blueprint(products_bp, url_prefix='/products')
    app.register_blueprint(users_bp, url_prefix='/users')

    return app

# Expose Flask app as a Firebase HTTP function
app = create_app()

if os.getenv("FLASK_ENV") == "development":
    # Run locally
    if __name__ == "__main__":
        app.run(debug=True, port=8000)
else:
    # Expose as Firebase Cloud Function
    cloud_function = create_cloud_function_app(app)
