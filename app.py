from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import datetime
import smtplib
from email.message import EmailMessage

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Email Configuration
SENDER_EMAIL = "lifecompanion.donors@gmail.com"
APP_PASSWORD = "uuej kgqe ikwx udjg"

def send_welcome_email(user_email, user_name, role):
    """Send welcome email after registration"""
    msg = EmailMessage()
    msg['Subject'] = f'Welcome to LifeLink - {role.capitalize()} Registration Successful!'
    msg['From'] = SENDER_EMAIL
    msg['To'] = user_email
    
    # Customize message based on role
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
    else:  # hospital
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
            print(f"✅ Welcome email sent to {user_email}")
            return True
    except Exception as e:
        print(f"❌ Email error: {e}")
        return False

# MongoDB Connection
client = MongoClient('mongodb://localhost:27017/')
db = client['Register']
donors_collection = db['donors']
hospital_collection = db['hospital']

import random
import string

# ... existing imports ...

def generate_hospital_id():
    """Generate a unique Hospital ID"""
    while True:
        # Generate HOSP + 4 random digits
        hid = "HOSP" + "".join(random.choices(string.digits, k=4))
        # Ensure it doesn't exist
        if not hospital_collection.find_one({"hospital_id": hid}):
            return hid

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    
    fullname = data.get('fullname')
    phone = data.get('phone')
    email = data.get('email')
    password = data.get('password')
    role = data.get('role')
    
    # New Fields
    aadhar = data.get('aadhar')
    weight = data.get('weight')
    dob = data.get('dob')

    if not all([fullname, phone, email, password, role]):
        return jsonify({"error": "Missing required fields"}), 400

    # Additional validation for donors
    if role == 'donor':
        if not all([aadhar, weight, dob]):
             return jsonify({"error": "Missing required donor fields (Aadhar, Weight, DOB)"}), 400
        
        # Check if Aadhar already exists
        if donors_collection.find_one({"aadhar": aadhar}):
            return jsonify({"error": "Aadhar number already registered"}), 400

    # Check if email already exists
    if donors_collection.find_one({"email": email}) or hospital_collection.find_one({"email": email}):
        return jsonify({"error": "Email already registered"}), 400

    # Check if phone already exists (Global check or Role specific? User asked for hospital, but good practice is global)
    if donors_collection.find_one({"phone": phone}) or hospital_collection.find_one({"phone": phone}):
        return jsonify({"error": "Mobile number already registered"}), 400

    user_data = {
        "fullname": fullname,
        "phone": phone,
        "email": email,
        "password": password,  # In production, hash this!
        "role": role,
        "registeredDate": datetime.datetime.utcnow()
    }
    
    # Initialize response variables
    hospital_id = None

    if role == 'donor':
        user_data['aadhar'] = aadhar
        user_data['weight'] = weight
        user_data['dob'] = dob
        user_data['donor_type'] = 'blood' # Defaulting to blood donor as per request
    elif role == 'hospital':
        hospital_id = generate_hospital_id()
        user_data['hospital_id'] = hospital_id

    try:
        if role == 'donor':
            result = donors_collection.insert_one(user_data)
            user_data['_id'] = str(result.inserted_id)
            print(f"Donor registered: {fullname}")
            
        elif role == 'hospital':
            result = hospital_collection.insert_one(user_data)
            user_data['_id'] = str(result.inserted_id)
            print(f"Hospital registered: {fullname}, ID: {hospital_id}")
            
        else:
            return jsonify({"error": "Invalid role"}), 400
        
        # Send welcome email (in background)
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
            response_data['message'] += f". Your Hospital ID is {hospital_id}. Please save this for login."
        
        return jsonify(response_data), 201
            
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    role = data.get('role')
    identifier = data.get('identifier') # Email for donor, Hospital ID for hospital
    password = data.get('password')
    
    if not all([role, identifier, password]):
        return jsonify({"error": "Missing required fields"}), 400
        
    try:
        user = None
        if role == 'donor':
            user = donors_collection.find_one({"email": identifier, "password": password})
        elif role == 'hospital':
            # Check for Hospital ID
            user = hospital_collection.find_one({"hospital_id": identifier, "password": password})
            
        if user:
            return jsonify({
                "message": "Login successful",
                "role": role,
                "user": {
                    "fullname": user['fullname'],
                    "email": user['email']
                }
            }), 200
        else:
            return jsonify({"error": "Invalid credentials"}), 401
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("Starting Python Flask Server on port 5000...")
    print(f"Email notifications enabled from: {SENDER_EMAIL}")
    app.run(debug=True, port=5000)