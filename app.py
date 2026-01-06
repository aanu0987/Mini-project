from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import datetime

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# MongoDB Connection
# Connect to default local instance
client = MongoClient('mongodb://localhost:27017/')
db = client['Register']  # Database Name: Register
donors_collection = db['donors']  # Collection: donors
hospital_collection = db['hospital']  # Collection: hospital

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    
    fullname = data.get('fullname')
    phone = data.get('phone')
    email = data.get('email')
    password = data.get('password')
    role = data.get('role')

    if not all([fullname, phone, email, password, role]):
        return jsonify({"error": "Missing required fields"}), 400

    user_data = {
        "fullname": fullname,
        "phone": phone,
        "email": email,
        "password": password, # In production, hash this!
        "role": role,
        "registeredDate": datetime.datetime.utcnow()
    }

    try:
        if role == 'donor':
            donors_collection.insert_one(user_data)
            # Convert ObjectId to string for JSON serialization
            user_data['_id'] = str(user_data['_id'])
            print(f"Donor registered: {fullname}")
            return jsonify({"message": "Donor registered successfully"}), 201
            
        elif role == 'hospital':
            hospital_collection.insert_one(user_data)
            user_data['_id'] = str(user_data['_id'])
            print(f"Hospital registered: {fullname}")
            return jsonify({"message": "Hospital registered successfully"}), 201
            
        else:
            return jsonify({"error": "Invalid role"}), 400
            
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("Starting Python Flask Server on port 5000...")
    app.run(debug=True, port=5000)
