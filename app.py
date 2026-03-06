from flask import Flask, request, jsonify, session
from flask_cors import CORS
from pymongo import MongoClient
import datetime
import smtplib
from email.message import EmailMessage
import random
import string
from bson import ObjectId
import json

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-in-production'
CORS(app, supports_credentials=True)

# Email Configuration
SENDER_EMAIL = "lifecompanion.donors@gmail.com"
APP_PASSWORD = "uuej kgqe ikwx udjg"

# MongoDB Connection
client = MongoClient('mongodb://localhost:27017/')
db = client['Register']
donors_collection = db['donors']
hospital_collection = db['hospital']
requests_collection = db['requests']
inventory_collection = db['inventory']
campaigns_collection = db['campaigns']
logs_collection = db['system_logs']
donations_collection = db['donations']

# Custom JSON encoder for ObjectId
class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        if isinstance(o, datetime.datetime):
            return o.isoformat()
        return json.JSONEncoder.default(self, o)

app.json_encoder = JSONEncoder

def send_welcome_email(user_email, user_name, role):
    """Send welcome email after registration"""
    msg = EmailMessage()
    msg['Subject'] = f'Welcome to LifeLink - {role.capitalize()} Registration Successful!'
    msg['From'] = SENDER_EMAIL
    msg['To'] = user_email
    
    if role == 'donor':
        content = f"""
        Hi {user_name},

        Thank you for registering as a Blood Donor on LifeLink!

        Your registration is now complete. As a donor, you can:
        - Update your availability status
        - Receive donation requests
        - View your donation history
        - Help save lives in emergencies

        Your willingness to donate makes you a lifesaver!

        Regards,
        LifeLink Team
        """
    else:
        content = f"""
        Hi {user_name},

        Welcome to LifeLink Hospital Network!

        Your hospital registration is now complete. You can now:
        - Post blood/organ requirements
        - Search for available donors
        - Manage emergency requests
        - Coordinate with other hospitals

        Together, we can save more lives.

        Regards,
        LifeLink Team
        """
    
    msg.set_content(content)

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(SENDER_EMAIL, APP_PASSWORD)
            smtp.send_message(msg)
            log_action('email', f'Welcome email sent to {user_email}')
            return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

def log_action(action_type, description):
    """Log system actions"""
    logs_collection.insert_one({
        'action_type': action_type,
        'description': description,
        'timestamp': datetime.datetime.utcnow()
    })

def generate_hospital_id():
    """Generate a unique Hospital ID"""
    while True:
        hid = "HOSP" + "".join(random.choices(string.digits, k=4))
        if not hospital_collection.find_one({"hospital_id": hid}):
            return hid

# Registration endpoint
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    
    fullname = data.get('fullname')
    phone = data.get('phone')
    email = data.get('email')
    password = data.get('password')
    role = data.get('role')
    aadhar = data.get('aadhar')
    weight = data.get('weight')
    dob = data.get('dob')
    city = data.get('city', 'Not specified')
    blood_group = data.get('blood_group', 'Unknown')

    if not all([fullname, phone, email, password, role]):
        return jsonify({"error": "Missing required fields"}), 400

    if role == 'donor':
        if not all([aadhar, weight, dob]):
            return jsonify({"error": "Missing required donor fields"}), 400
        
        if donors_collection.find_one({"aadhar": aadhar}):
            return jsonify({"error": "Aadhar number already registered"}), 400

    if donors_collection.find_one({"email": email}) or hospital_collection.find_one({"email": email}):
        return jsonify({"error": "Email already registered"}), 400

    if donors_collection.find_one({"phone": phone}) or hospital_collection.find_one({"phone": phone}):
        return jsonify({"error": "Mobile number already registered"}), 400

    user_data = {
        "fullname": fullname,
        "phone": phone,
        "email": email,
        "password": password,
        "role": role,
        "city": city,
        "registeredDate": datetime.datetime.utcnow(),
        "is_verified": False if role == 'hospital' else True
    }
    
    hospital_id = None

    if role == 'donor':
        user_data.update({
            'aadhar': aadhar,
            'weight': weight,
            'dob': dob,
            'donor_type': 'both',
            'blood_group': blood_group,
            'available': True,
            'last_donation': None
        })
        result = donors_collection.insert_one(user_data)
    elif role == 'hospital':
        hospital_id = generate_hospital_id()
        user_data.update({
            'hospital_id': hospital_id,
            'license_number': data.get('license_number', 'Pending'),
            'verified': False
        })
        result = hospital_collection.insert_one(user_data)
        
        # Initialize hospital inventory
        inventory_collection.insert_one({
            'hospital_id': hospital_id,
            'blood_inventory': {
                'A+': random.randint(10, 50),
                'A-': random.randint(5, 30),
                'B+': random.randint(10, 40),
                'B-': random.randint(5, 25),
                'O+': random.randint(20, 60),
                'O-': random.randint(5, 20),
                'AB+': random.randint(5, 25),
                'AB-': random.randint(2, 15)
            },
            'last_updated': datetime.datetime.utcnow()
        })
    else:
        return jsonify({"error": "Invalid role"}), 400

    email_sent = send_welcome_email(email, fullname, role)
    
    response_data = {
        "message": f"{role.capitalize()} registered successfully",
        "email_sent": email_sent,
        "user": {
            "name": fullname,
            "email": email,
            "role": role
        }
    }
    
    if hospital_id:
        response_data['hospital_id'] = hospital_id
    
    return jsonify(response_data), 201

# Login endpoint
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    role = data.get('role')
    identifier = data.get('identifier')
    password = data.get('password')
    
    if not all([role, identifier, password]):
        return jsonify({"error": "Missing required fields"}), 400
        
    try:
        user = None
        if role == 'donor':
            user = donors_collection.find_one({"email": identifier, "password": password})
            if user:
                session['user_id'] = str(user['_id'])
                session['role'] = 'donor'
        elif role == 'hospital':
            user = hospital_collection.find_one({"hospital_id": identifier, "password": password})
            if user:
                session['user_id'] = str(user['_id'])
                session['role'] = 'hospital'
                session['hospital_id'] = user['hospital_id']
        
        if user:
            log_action('login', f'{role} logged in: {user["email"]}')
            return jsonify({
                "message": "Login successful",
                "role": role,
                "user": {
                    "fullname": user['fullname'],
                    "email": user['email'],
                    "hospital_id": user.get('hospital_id'),
                    "is_verified": user.get('is_verified', True)
                }
            }), 200
        else:
            return jsonify({"error": "Invalid credentials"}), 401
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Logout endpoint
@app.route('/logout', methods=['POST'])
def logout():
    if 'user_id' in session:
        log_action('logout', f'User logged out: {session["user_id"]}')
        session.clear()
        return jsonify({"message": "Logged out successfully"}), 200
    return jsonify({"message": "No active session"}), 200

# Check session endpoint
@app.route('/check-session', methods=['GET'])
def check_session():
    if 'user_id' in session:
        return jsonify({
            "logged_in": True,
            "role": session.get('role'),
            "user_id": session.get('user_id')
        }), 200
    return jsonify({"logged_in": False}), 200

# Get dashboard stats
@app.route('/api/stats', methods=['GET'])
def get_stats():
    try:
        donors_count = donors_collection.count_documents({})
        hospitals_count = hospital_collection.count_documents({})
        
        # Calculate total donations
        donations_count = donations_collection.count_documents({})
        
        # Calculate organs received (for demo, using donations count)
        organs_received = donations_count
        
        # Calculate active recipients (for demo)
        recipients_count = requests_collection.count_documents({"status": "pending"})
        
        return jsonify({
            "donors": donors_count,
            "hospitals": hospitals_count,
            "saved": organs_received,
            "recipients": recipients_count,
            "donations": donations_count
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Get all donors
@app.route('/api/donors', methods=['GET'])
def get_donors():
    try:
        donors = list(donors_collection.find({}, {
            'password': 0,
            'aadhar': 0
        }))
        return jsonify(donors), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Get all users (for admin)
@app.route('/api/users', methods=['GET'])
def get_users():
    try:
        donors = list(donors_collection.find({}, {'password': 0}))
        hospitals = list(hospital_collection.find({}, {'password': 0}))
        
        # Add type field to each user
        for donor in donors:
            donor['user_type'] = 'donor'
        for hospital in hospitals:
            hospital['user_type'] = 'hospital'
        
        all_users = donors + hospitals
        return jsonify(all_users), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Get pending hospitals
@app.route('/api/pending-hospitals', methods=['GET'])
def get_pending_hospitals():
    try:
        pending = list(hospital_collection.find({"verified": False}, {'password': 0}))
        return jsonify(pending), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Verify hospital
@app.route('/api/verify-hospital/<hospital_id>', methods=['POST'])
def verify_hospital(hospital_id):
    try:
        result = hospital_collection.update_one(
            {"_id": ObjectId(hospital_id)},
            {"$set": {"verified": True, "is_verified": True}}
        )
        if result.modified_count > 0:
            log_action('verify', f'Hospital verified: {hospital_id}')
            return jsonify({"message": "Hospital verified successfully"}), 200
        return jsonify({"error": "Hospital not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Delete user
@app.route('/api/delete-user/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    try:
        # Try to delete from donors first
        result = donors_collection.delete_one({"_id": ObjectId(user_id)})
        if result.deleted_count == 0:
            result = hospital_collection.delete_one({"_id": ObjectId(user_id)})
        
        if result.deleted_count > 0:
            log_action('delete', f'User deleted: {user_id}')
            return jsonify({"message": "User deleted successfully"}), 200
        return jsonify({"error": "User not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Get hospital data
@app.route('/api/hospital/<hospital_id>', methods=['GET'])
def get_hospital_data(hospital_id):
    try:
        hospital = hospital_collection.find_one({"hospital_id": hospital_id}, {'password': 0})
        if not hospital:
            return jsonify({"error": "Hospital not found"}), 404
        
        # Get hospital inventory
        inventory = inventory_collection.find_one({"hospital_id": hospital_id})
        
        # Get pending requests for this hospital
        requests = list(requests_collection.find({"hospital_id": hospital_id}))
        
        # Get donors in the same city
        donors = list(donors_collection.find({
            "city": hospital.get('city'),
            "available": True
        }, {'password': 0, 'aadhar': 0}))
        
        return jsonify({
            "hospital": hospital,
            "inventory": inventory,
            "requests": requests,
            "donors": donors
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Get system logs
@app.route('/api/system-logs', methods=['GET'])
def get_system_logs():
    try:
        logs = list(logs_collection.find().sort('timestamp', -1).limit(50))
        return jsonify(logs), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Create blood request
@app.route('/api/request-blood', methods=['POST'])
def request_blood():
    try:
        data = request.json
        data['status'] = 'pending'
        data['created_at'] = datetime.datetime.utcnow()
        data['donation_type'] = 'blood'
        
        result = requests_collection.insert_one(data)
        
        log_action('request', f'Blood request created: {result.inserted_id}')
        
        return jsonify({
            "message": "Request created successfully",
            "request_id": str(result.inserted_id)
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Approve request
@app.route('/api/approve-request', methods=['POST'])
def approve_request():
    try:
        data = request.json
        request_id = data.get('request_id')
        
        result = requests_collection.update_one(
            {"_id": ObjectId(request_id)},
            {"$set": {"status": "approved", "approved_at": datetime.datetime.utcnow()}}
        )
        
        if result.modified_count > 0:
            # Add to donations
            request_data = requests_collection.find_one({"_id": ObjectId(request_id)})
            donations_collection.insert_one({
                'request_id': request_id,
                'donor_name': request_data.get('donor_name', 'Unknown'),
                'donation_type': request_data.get('donation_type', 'blood'),
                'donation_date': datetime.datetime.utcnow(),
                'status': 'completed'
            })
            
            log_action('approve', f'Request approved: {request_id}')
            return jsonify({"message": "Request approved"}), 200
        return jsonify({"error": "Request not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Update inventory
@app.route('/api/update-inventory', methods=['POST'])
def update_inventory():
    try:
        data = request.json
        hospital_id = data.get('hospital_id')
        inventory = data.get('inventory')
        
        result = inventory_collection.update_one(
            {"hospital_id": hospital_id},
            {"$set": {
                "blood_inventory": inventory,
                "last_updated": datetime.datetime.utcnow()
            }}
        )
        
        log_action('inventory', f'Inventory updated for hospital: {hospital_id}')
        
        return jsonify({"message": "Inventory updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Get recent donations
@app.route('/api/recent-donations', methods=['GET'])
def get_recent_donations():
    try:
        donations = list(donations_collection.find().sort('donation_date', -1).limit(10))
        return jsonify(donations), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("Starting Python Flask Server on port 5000...")
    print("Creating indexes...")
    
    # Create indexes for better performance
    donors_collection.create_index("email", unique=True)
    donors_collection.create_index("phone", unique=True)
    donors_collection.create_index("aadhar", unique=True)
    hospital_collection.create_index("email", unique=True)
    hospital_collection.create_index("hospital_id", unique=True)
    
    print("Server ready!")
    app.run(debug=True, port=5000)