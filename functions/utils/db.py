from firebase_admin import credentials, initialize_app, get_app, firestore

try:
    # Check if Firebase has already been initialized
    get_app()
except ValueError:
    # Initialize Firebase Admin SDK
    cred = credentials.Certificate("key.json")  # Update with your service account path
    initialize_app(cred)

# Firestore client
db = firestore.client()