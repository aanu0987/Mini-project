from flask import Flask, request, jsonify, session, render_template, send_from_directory
from flask_cors import CORS
from pymongo import MongoClient
from pymongo.errors import ConfigurationError
from bson import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from email.message import EmailMessage
from dotenv import load_dotenv
import random
import string
import json
from datetime import datetime, timedelta
from copy import deepcopy
import os
import smtplib
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

TAMILNADU_DISTRICTS = [
    "Ariyalur", "Chengalpattu", "Chennai", "Coimbatore", "Cuddalore", "Dharmapuri",
    "Dindigul", "Erode", "Kallakurichi", "Kancheepuram", "Kanyakumari", "Karur",
    "Krishnagiri", "Madurai", "Mayiladuthurai", "Nagapattinam", "Namakkal", "Nilgiris",
    "Perambalur", "Pudukkottai", "Ramanathapuram", "Ranipet", "Salem", "Sivaganga",
    "Tenkasi", "Thanjavur", "Theni", "Thoothukudi", "Tiruchirappalli", "Tirunelveli",
    "Tirupathur", "Tiruppur", "Tiruvallur", "Tiruvannamalai", "Tiruvarur", "Vellore",
    "Viluppuram", "Virudhunagar"
]

app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here-change-in-production')
CORS(app, supports_credentials=True)

# -------------------- Configuration --------------------
def get_env_value(*keys, default=None):
    """Return the first non-empty environment variable from the provided keys."""
    for key in keys:
        value = os.getenv(key)
        if value:
            return value
    return default

MONGO_URI = get_env_value("MONGO_URI", "MONGODB_URI", "MONGO_URL", "DATABASE_URL", default="mongodb://localhost:27017/")
DB_NAME = get_env_value("MONGO_DB", "MONGODB_DB", "DB_NAME")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "lifelink.donors@gmail.com")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
APP_PASSWORD = "".join((os.getenv("APP_PASSWORD", "ucji znxr sfto ejsa")).split())
EMAIL_NOTIFICATIONS_ENABLED = bool(SENDER_EMAIL and APP_PASSWORD)

class InMemoryResult:
    def __init__(self, inserted_id=None, modified_count=0, deleted_count=0):
        self.inserted_id = inserted_id
        self.modified_count = modified_count
        self.deleted_count = deleted_count


class InMemoryCursor:
    def __init__(self, documents):
        self.documents = documents

    def sort(self, field, direction=1):
        reverse = direction == -1
        self.documents.sort(
            key=lambda item: (item.get(field) is None, str(item.get(field)) if item.get(field) is not None else ""),
            reverse=reverse
        )
        return self

    def limit(self, count):
        self.documents = self.documents[:count]
        return self

    def __iter__(self):
        return iter(self.documents)


class InMemoryCollection:
    def __init__(self, name):
        self.name = name
        self.documents = []

    def create_index(self, *args, **kwargs):
        return None

    def _matches(self, document, query):
        if not query:
            return True

        for key, value in query.items():
            doc_value = document.get(key)
            if isinstance(value, dict):
                if "$in" in value and doc_value not in value["$in"]:
                    return False
                if "$ne" in value and doc_value == value["$ne"]:
                    return False
            elif doc_value != value:
                return False
        return True

    def _apply_projection(self, document, projection=None):
        doc = deepcopy(document)
        if not projection:
            return doc

        excluded = {key for key, value in projection.items() if value == 0}
        if excluded:
            for key in excluded:
                doc.pop(key, None)
        return doc

    def find_one(self, query=None, projection=None):
        for document in self.documents:
            if self._matches(document, query or {}):
                return self._apply_projection(document, projection)
        return None

    def find(self, query=None, projection=None):
        matched = [
            self._apply_projection(document, projection)
            for document in self.documents
            if self._matches(document, query or {})
        ]
        return InMemoryCursor(matched)

    def insert_one(self, document):
        stored = deepcopy(document)
        stored.setdefault("_id", ObjectId())
        self.documents.append(stored)
        return InMemoryResult(inserted_id=stored["_id"])

    def update_one(self, query, update, upsert=False):
        for document in self.documents:
            if self._matches(document, query):
                original = deepcopy(document)
                for key, value in update.get("$set", {}).items():
                    document[key] = value
                for key in update.get("$unset", {}).keys():
                    document.pop(key, None)
                modified = int(document != original)
                return InMemoryResult(modified_count=modified)

        if upsert:
            new_document = deepcopy(query)
            for key, value in update.get("$set", {}).items():
                new_document[key] = value
            result = self.insert_one(new_document)
            return InMemoryResult(inserted_id=result.inserted_id, modified_count=1)

        return InMemoryResult(modified_count=0)

    def delete_one(self, query):
        for index, document in enumerate(self.documents):
            if self._matches(document, query):
                del self.documents[index]
                return InMemoryResult(deleted_count=1)
        return InMemoryResult(deleted_count=0)

    def count_documents(self, query):
        return sum(1 for document in self.documents if self._matches(document, query))


class InMemoryDatabase:
    def __init__(self):
        self.collections = {}

    def __getitem__(self, name):
        if name not in self.collections:
            self.collections[name] = InMemoryCollection(name)
        return self.collections[name]


DB_CONNECTED = False
client = None


def get_database(client):
    """Resolve the MongoDB database from explicit env vars or the URI default database."""
    if DB_NAME:
        return client[DB_NAME]

    try:
        return client.get_default_database()
    except ConfigurationError:
        return client["lifelink"]

# MongoDB Connection
try:
    client = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=int(os.getenv("MONGO_SERVER_SELECTION_TIMEOUT_MS", "5000"))
    )
    client.admin.command("ping")
    db = get_database(client)
    DB_CONNECTED = True
    logger.info(f"Connected to MongoDB database: {db.name}")
except Exception as e:
    logger.warning(f"MongoDB unavailable, using in-memory storage fallback: {e}")
    db = InMemoryDatabase()

def initialize_indexes():
    """Create indexes for MongoDB collections when a real database is available."""
    if not DB_CONNECTED:
        return

    try:
        donors_collection.create_index("email", unique=True)
        donors_collection.create_index("phone", unique=True)
        donors_collection.create_index("aadhar", unique=True, sparse=True)
        donors_collection.create_index("login_id", unique=True, sparse=True)

        hospitals_collection.create_index("email", unique=True)
        hospitals_collection.create_index("hospital_id", unique=True, sparse=True)
        hospitals_collection.create_index("login_id", unique=True, sparse=True)

        sessions_collection.create_index("token", unique=True)
        sessions_collection.create_index("expires_at", expireAfterSeconds=0)
        logger.info("Database indexes ensured successfully")
    except Exception as e:
        logger.warning(f"Index creation warning: {e}")

# Collections
donors_collection = db['donors']
hospitals_collection = db['hospitals']
requests_collection = db['requests']
inventory_collection = db['inventory']
campaigns_collection = db['campaigns']
logs_collection = db['system_logs']
donations_collection = db['donations']
admins_collection = db['admins']
notifications_collection = db['notifications']
sessions_collection = db['sessions']
initialize_indexes()

# -------------------- Frontend Routes --------------------
@app.route('/')
def index():
    """Serve the main index page"""
    return render_template('index.html')

@app.route('/<page>')
def serve_page(page):
    """Serve individual HTML pages"""
    valid_pages = ['blood_donors', 'dashboard', 'login', 'register', 'logout', 
                   'about_us', 'admin', 'hospital_dashboard', 'donor_dashboard']
    
    if page in valid_pages:
        return render_template(f'{page}.html')
    
    return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    return '', 204

# Serve static files
@app.route('/css/<path:filename>')
def serve_css(filename):
    return send_from_directory('static/css', filename)

@app.route('/js/<path:filename>')
def serve_js(filename):
    return send_from_directory('static/js', filename)

# Custom JSON encoder for ObjectId
class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        if isinstance(o, datetime):
            return o.isoformat()
        return json.JSONEncoder.default(self, o)

app.json_encoder = JSONEncoder

# -------------------- Utility Functions --------------------
def send_email(recipient, subject, content):
    """Send email notification"""
    recipient = (recipient or "").strip()
    if not recipient:
        logger.warning("Email skipped because recipient address was empty.")
        return False

    if not EMAIL_NOTIFICATIONS_ENABLED:
        logger.warning(
            "Email notifications are disabled. Set SENDER_EMAIL and APP_PASSWORD to enable SMTP delivery."
        )
        return False

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL
    msg['To'] = recipient
    msg.set_content(content)

    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
            smtp.login(SENDER_EMAIL, APP_PASSWORD)
            smtp.send_message(msg)
        logger.info(f"Email sent to {recipient}")
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error(
            "Email authentication failed. Check SENDER_EMAIL / APP_PASSWORD configuration and ensure the app password is valid."
        )
        return False
    except Exception as e:
        logger.error(f"Email error while sending to {recipient}: {e}")
        return False

def send_welcome_email(user_email, user_name, role, login_id=None, password=None):
    """Send welcome email after registration or approval"""
    if role == 'donor':
        content = f"""
Dear {user_name},

Thank you for registering as a Blood Donor on LifeLink!

Your registration is now complete. Here are your login details:
Login ID: {login_id}
Password: {password}

As a donor, you can:
• Update your availability status
• Receive donation requests from hospitals
• View your donation history
• Track your impact on saved lives

Your willingness to donate makes you a lifesaver!

Download the LifeLink app or visit our website to get started.

Regards,
LifeLink Team
"""
    else:  # hospital
        content = f"""
Dear {user_name},

Welcome to LifeLink Hospital Network!

Your hospital registration has been approved. Here are your login details:
Login ID: {login_id}
Password: {password}

You can now:
• Post blood and organ requirements
• Search for available donors in your area
• Manage emergency requests
• Coordinate with other hospitals
• Track donation history

Together, we can save more lives.

Regards,
LifeLink Team
"""
    
    return send_email(user_email, f'Welcome to LifeLink - Registration Successful!', content)


def send_hospital_pending_email(user_email, user_name):
    """Send hospital registration pending verification email"""
    content = f"""
Dear {user_name},

Thank you for registering with LifeLink Hospital Network.

Your registration is complete and is now pending admin verification.
Please wait while the admin verifies your account details.

You will receive another email with your login ID and password immediately after your account is approved.

Regards,
LifeLink Team
"""

    return send_email(user_email, 'LifeLink Hospital Registration Submitted', content)

def log_action(action_type, description, user_id=None):
    """Log system actions"""
    try:
        logs_collection.insert_one({
            'action_type': action_type,
            'description': description,
            'user_id': user_id,
            'timestamp': datetime.utcnow()
        })
    except Exception as e:
        logger.error(f"Error logging action: {e}")

def generate_unique_id(prefix, collection, field_name="login_id", size=6):
    """Generate unique ID for users"""
    while True:
        generated = prefix + "".join(random.choices(string.digits, k=size))
        if not collection.find_one({field_name: generated}):
            return generated

def generate_token():
    return "".join(random.choices(string.ascii_letters + string.digits, k=48))

def create_session(user_id, role):
    """Create a new session for logged in user"""
    token = generate_token()
    sessions_collection.insert_one({
        "token": token,
        "user_id": str(user_id),
        "role": role,
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(hours=12)
    })
    return token

def parse_bearer_token(auth_header):
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    return auth_header.split(" ", 1)[1]

def get_session(required_roles=None):
    """Get current session from token"""
    token = parse_bearer_token(request.headers.get("Authorization"))
    if not token:
        return None, (jsonify({"error": "Missing authorization token"}), 401)

    session_data = sessions_collection.find_one({"token": token})
    if not session_data:
        return None, (jsonify({"error": "Invalid session"}), 401)

    if session_data["expires_at"] < datetime.utcnow():
        sessions_collection.delete_one({"_id": session_data["_id"]})
        return None, (jsonify({"error": "Session expired"}), 401)

    if required_roles and session_data["role"] not in required_roles:
        return None, (jsonify({"error": "Forbidden"}), 403)

    return session_data, None

def serialize_user(user):
    """Serialize user object for JSON response"""
    if not user:
        return None
    user = dict(user)
    user["_id"] = str(user["_id"])
    user.pop("password", None)
    user.pop("pending_password", None)
    return user

def create_notification(event_type, message, **extra):
    """Create a system notification"""
    try:
        payload = {
            "type": event_type,
            "message": message,
            "created_at": datetime.utcnow(),
            "read": False
        }
        payload.update(extra)
        notifications_collection.insert_one(payload)
    except Exception as e:
        logger.error(f"Error creating notification: {e}")

# -------------------- Auth & Registration --------------------
@app.route("/auth/register", methods=["POST"])
def register_user():
    """Register a new donor or hospital"""
    try:
        data = request.get_json(silent=True) or request.form.to_dict() or {}
        role = data.get("role")
        fullname = (data.get("fullname") or "").strip()
        phone = (data.get("phone") or "").strip()
        email = (data.get("email") or "").strip().lower()
        password = data.get("password")
        city = data.get("city")

        logger.info(f"Registration attempt - Role: {role}, Email: {email}")

        if role not in ["donor", "hospital"]:
            return jsonify({"error": "Role must be donor or hospital"}), 400

        if not all([fullname, phone, email, password, city]):
            return jsonify({"error": "Missing required fields"}), 400

        # Check if email already exists in any collection
        if (donors_collection.find_one({"email": email}) or 
            hospitals_collection.find_one({"email": email}) or 
            admins_collection.find_one({"email": email})):
            return jsonify({"error": "Email already registered"}), 400

        if role == "donor":
            # Validate donor specific fields
            donor_type = (data.get("donor_type") or "blood").strip().lower()
            if donor_type != "blood":
                return jsonify({"error": "Only blood donors are allowed to register."}), 400

            aadhar = (data.get("aadhar") or "").strip()
            gender = (data.get("gender") or "").strip().lower()
            weight = data.get("weight")
            dob = data.get("dob")
            blood_group = (data.get("blood_group") or "").strip().upper()
            last_donation_date = data.get("last_donation_date")

            if not all([aadhar, gender, weight, dob, blood_group]):
                return jsonify({"error": "Missing donor fields"}), 400

            # Validate weight
            try:
                weight_float = float(weight)
                if weight_float < 45:
                    return jsonify({"error": "Donor weight must be at least 45 kg"}), 400
            except (TypeError, ValueError):
                return jsonify({"error": "Weight must be a valid number"}), 400

            # Check if Aadhar exists
            if donors_collection.find_one({"aadhar": aadhar}):
                return jsonify({"error": "Aadhar already exists"}), 400

            # Create donor
            login_id = generate_unique_id("DON", donors_collection)
            
            donor_data = {
                "fullname": fullname,
                "phone": phone,
                "email": email,
                "password": generate_password_hash(password),
                "role": role,
                "city": city,
                "status": "approved",  # Donors are auto-approved
                "login_id": login_id,
                "aadhar": aadhar,
                "gender": gender,
                "weight": weight_float,
                "dob": dob,
                "blood_group": blood_group,
                "last_donation_date": last_donation_date,
                "donor_type": "blood",
                "created_at": datetime.utcnow(),
                "verified_at": datetime.utcnow(),
                "available": True
            }
            
            result = donors_collection.insert_one(donor_data)
            
            # Send welcome email
            send_welcome_email(email, fullname, "donor", login_id, password)
            
            # Create notification
            create_notification(
                "registration",
                f"New donor registered: {fullname}",
                user_id=str(result.inserted_id),
                email=email
            )
            
            log_action('register', f'Donor registered: {fullname}', str(result.inserted_id))
            
            return jsonify({
                "message": "Donor registered successfully", 
                "id": str(result.inserted_id), 
                "login_id": login_id
            }), 201

        else:  # Hospital registration
            # Validate hospital fields
            license_number = (data.get("license_number") or "").strip()
            address = (data.get("address") or "").strip()

            if not all([license_number, address]):
                return jsonify({"error": "Missing hospital fields"}), 400

            # Handle certificate upload
            cert_file = request.files.get("certificate_pdf")
            certificate_path = None
            
            if cert_file and cert_file.filename:
                if not cert_file.filename.lower().endswith(".pdf"):
                    return jsonify({"error": "Certificate must be a PDF file"}), 400

                # Create upload directory if it doesn't exist
                upload_dir = os.path.join(app.static_folder, "uploads", "certificates")
                os.makedirs(upload_dir, exist_ok=True)
                
                # Save file with timestamp to avoid duplicates
                timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
                safe_filename = f"{timestamp}_{cert_file.filename.replace(' ', '_')}"
                filepath = os.path.join(upload_dir, safe_filename)
                cert_file.save(filepath)
                certificate_path = f"/static/uploads/certificates/{safe_filename}"
                logger.info(f"Certificate saved: {certificate_path}")
            else:
                return jsonify({"error": "Certificate PDF is required"}), 400

            # Create hospital (pending approval)
            hospital_data = {
                "fullname": fullname,
                "hospital_name": fullname,
                "phone": phone,
                "email": email,
                "password": generate_password_hash(password),
                "pending_password": password,
                "role": role,
                "city": city,
                "address": address,
                "license_number": license_number,
                "certificate_pdf": certificate_path,
                "status": "pending",  # Hospitals need admin approval
                "login_id": None,  # Will be set when approved
                "created_at": datetime.utcnow(),
                "verified": False,
                "is_verified": False
            }
            
            result = hospitals_collection.insert_one(hospital_data)
            
            # Send confirmation email
            send_hospital_pending_email(email, fullname)
            
            # Notify admin
            create_notification(
                "pending_verification",
                f"New hospital registration pending: {fullname}",
                hospital_id=str(result.inserted_id),
                email=email
            )
            
            log_action('register', f'Hospital registered (pending): {fullname}', str(result.inserted_id))
            
            return jsonify({
                "message": "Hospital registration submitted for admin verification", 
                "id": str(result.inserted_id)
            }), 201

    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return jsonify({"error": f"Registration failed: {str(e)}"}), 500

@app.route("/auth/admin/register", methods=["POST"])
def register_admin():
    """Register the first admin (only one allowed)"""
    try:
        data = request.get_json() or {}
        fullname = (data.get("fullname") or "").strip()
        email = (data.get("email") or "").strip().lower()
        password = data.get("password")

        if not all([fullname, email, password]):
            return jsonify({"error": "Missing required fields"}), 400

        # Check if any admin exists
        existing_admin = admins_collection.find_one()
        if existing_admin:
            return jsonify({"error": "Admin account already exists. Only one admin is allowed."}), 400

        # Create admin
        admin_data = {
            "fullname": fullname,
            "email": email,
            "password": generate_password_hash(password),
            "role": "admin",
            "created_at": datetime.utcnow()
        }
        
        admins_collection.insert_one(admin_data)
        
        logger.info(f"Admin registered: {email}")
        
        return jsonify({"message": "Admin registered successfully"}), 201

    except Exception as e:
        logger.error(f"Admin registration error: {str(e)}")
        return jsonify({"error": f"Registration failed: {str(e)}"}), 500

@app.route("/auth/login", methods=["POST"])
def login():
    """Login user (donor, hospital, or admin)"""
    try:
        data = request.get_json(silent=True) or request.form.to_dict() or {}
        role = data.get("role")
        password = data.get("password")

        logger.info(f"Login attempt - Role: {role}")

        if role == "admin":
            email = (data.get("email") or "").strip().lower()
            admin = admins_collection.find_one({"email": email})
            
            if not admin or not check_password_hash(admin.get("password", ""), password or ""):
                return jsonify({"error": "Invalid credentials"}), 401
            
            token = create_session(admin["_id"], "admin")
            log_action('login', f'Admin logged in: {email}', str(admin["_id"]))
            
            return jsonify({
                "message": "Login successful", 
                "token": token, 
                "user": serialize_user(admin)
            }), 200

        # Donor or Hospital login
        if role not in ["donor", "hospital"]:
            return jsonify({"error": "Role must be donor, hospital, or admin"}), 400

        login_id = (data.get("login_id") or "").strip().upper()
        email = (data.get("email") or "").strip().lower()

        # Handle if email was passed in login_id field
        if login_id and "@" in login_id:
            email = login_id.lower()
            login_id = ""

        if (not login_id and not email) or not password:
            return jsonify({"error": "Missing login credentials"}), 400

        # Find user
        collection = donors_collection if role == "donor" else hospitals_collection
        query = {"login_id": login_id} if login_id else {"email": email}
        user = collection.find_one(query)

        if not user:
            return jsonify({"error": "User not found. Please register first."}), 401

        # Check status
        if user.get("status") != "approved":
            status_msg = {
                "pending": "Your account is pending admin approval.",
                "rejected": f"Your account was rejected. Reason: {user.get('rejection_reason', 'Not specified')}"
            }.get(user.get("status"), "Account not approved")
            
            return jsonify({"error": status_msg}), 403

        # Verify password
        if not check_password_hash(user.get("password", ""), password):
            return jsonify({"error": "Invalid password"}), 401

        # Create session
        token = create_session(user["_id"], role)
        log_action('login', f'{role.capitalize()} logged in: {user.get("email")}', str(user["_id"]))
        
        return jsonify({
            "message": "Login successful", 
            "token": token, 
            "user": serialize_user(user)
        }), 200

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({"error": f"Login failed: {str(e)}"}), 500

@app.route("/auth/logout", methods=["POST"])
def logout():
    """Logout user by invalidating session"""
    token = parse_bearer_token(request.headers.get("Authorization"))
    if token:
        sessions_collection.delete_one({"token": token})
    return jsonify({"message": "Logout successful"}), 200

# -------------------- Admin Routes --------------------
@app.route("/admin/pending-users", methods=["GET"])
def pending_users():
    """Get all pending hospital verifications"""
    session_data, error = get_session(required_roles=["admin"])
    if error:
        return error

    try:
        hospitals = []
        for h in hospitals_collection.find({"status": "pending"}).sort("created_at", -1):
            hospital = serialize_user(h)
            hospitals.append(hospital)
        
        return jsonify({"hospitals": hospitals}), 200
    except Exception as e:
        logger.error(f"Error fetching pending users: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/admin/all-users", methods=["GET"])
def all_users():
    """Get all users (donors and hospitals)"""
    session_data, error = get_session(required_roles=["admin"])
    if error:
        return error

    try:
        donors = [serialize_user(d) for d in donors_collection.find().sort("created_at", -1)]
        hospitals = [serialize_user(h) for h in hospitals_collection.find().sort("created_at", -1)]
        
        return jsonify({"donors": donors, "hospitals": hospitals}), 200
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/admin/notifications", methods=["GET"])
def admin_notifications():
    """Get admin notifications"""
    session_data, error = get_session(required_roles=["admin"])
    if error:
        return error

    try:
        notifications = list(notifications_collection.find().sort("created_at", -1).limit(50))
        for n in notifications:
            n["_id"] = str(n["_id"])
            if isinstance(n.get("created_at"), datetime):
                n["created_at"] = n["created_at"].isoformat()
        
        return jsonify({"notifications": notifications}), 200
    except Exception as e:
        logger.error(f"Error fetching notifications: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/admin/verify-user", methods=["POST"])
def verify_user():
    """Approve or reject a hospital registration"""
    session_data, error = get_session(required_roles=["admin"])
    if error:
        return error

    try:
        data = request.get_json() or {}
        user_type = data.get("user_type")  # Only hospital supported
        user_id = data.get("user_id")
        action = data.get("action")  # approve/reject
        rejection_reason = (data.get("rejection_reason") or "").strip()

        if user_type != "hospital":
            return jsonify({"error": "Only hospital verification is supported"}), 400
        
        if action not in ["approve", "reject"]:
            return jsonify({"error": "action must be approve or reject"}), 400

        try:
            object_id = ObjectId(user_id)
        except Exception:
            return jsonify({"error": "Invalid user_id"}), 400

        hospital = hospitals_collection.find_one({"_id": object_id})
        if not hospital:
            return jsonify({"error": "Hospital not found"}), 404

        if action == "approve":
            # Generate login ID for hospital
            login_id = generate_unique_id("HSP", hospitals_collection)
            approval_password = hospital.get("pending_password")

            if not approval_password:
                approval_password = "".join(random.choices(string.ascii_letters + string.digits, k=10))

            # Update hospital status
            hospitals_collection.update_one(
                {"_id": object_id},
                {"$set": {
                    "status": "approved",
                    "login_id": login_id,
                    "verified": True,
                    "is_verified": True,
                    "rejection_reason": None,
                    "verified_at": datetime.utcnow(),
                    "password": generate_password_hash(approval_password)
                }, "$unset": {"pending_password": ""}}
            )
            
            # Send approval email with login ID and password
            send_welcome_email(
                hospital["email"],
                hospital.get("hospital_name", hospital.get("fullname")),
                "hospital",
                login_id,
                approval_password
            )
            
            # Create notification
            create_notification(
                "verification",
                f"Hospital {hospital.get('fullname')} approved with login ID {login_id}",
                hospital_id=user_id,
                action="approved"
            )
            
            log_action('verify', f'Hospital approved: {hospital.get("fullname")}', user_id)
            
            return jsonify({
                "message": "Hospital approved successfully", 
                "login_id": login_id
            }), 200

        else:  # reject
            if not rejection_reason:
                return jsonify({"error": "Rejection reason required"}), 400

            hospitals_collection.update_one(
                {"_id": object_id},
                {"$set": {
                    "status": "rejected",
                    "rejection_reason": rejection_reason,
                    "verified_at": datetime.utcnow()
                }, "$unset": {"pending_password": ""}}
            )
            
            # Send rejection email
            send_email(
                hospital["email"],
                "LifeLink Hospital Registration Status",
                f"""
Dear {hospital.get('fullname')},

Thank you for your interest in joining LifeLink Hospital Network.

Unfortunately, your registration could not be approved at this time.
Reason: {rejection_reason}

If you believe this is an error or would like to reapply with corrected information,
please contact our support team.

Regards,
LifeLink Team
                """
            )
            
            # Create notification
            create_notification(
                "verification",
                f"Hospital {hospital.get('fullname')} rejected. Reason: {rejection_reason}",
                hospital_id=user_id,
                action="rejected"
            )
            
            log_action('verify', f'Hospital rejected: {hospital.get("fullname")}', user_id)
            
            return jsonify({"message": "Hospital rejected"}), 200

    except Exception as e:
        logger.error(f"Verification error: {str(e)}")
        return jsonify({"error": str(e)}), 500

# -------------------- Hospital Routes --------------------
@app.route("/hospital/dashboard", methods=["GET"])
def hospital_dashboard():
    """Get hospital dashboard data"""
    session_data, error = get_session(required_roles=["hospital"])
    if error:
        return error

    try:
        hospital = hospitals_collection.find_one({"_id": ObjectId(session_data["user_id"])})
        if not hospital:
            return jsonify({"error": "Hospital not found"}), 404

        # Get recent notifications for this hospital
        recent = list(notifications_collection.find(
            {"hospital_id": str(hospital["_id"])}
        ).sort("created_at", -1).limit(20))
        
        for item in recent:
            item["_id"] = str(item["_id"])
            if isinstance(item.get("created_at"), datetime):
                item["created_at"] = item["created_at"].isoformat()

        # Get pending requests
        pending_requests = list(requests_collection.find({
            "hospital_id": str(hospital["_id"]),
            "status": "pending"
        }).sort("created_at", -1))

        # Get donors in same city
        nearby_donors = list(donors_collection.find({
            "city": hospital.get("city"),
            "status": "approved",
            "available": True
        }).limit(20))

        return jsonify({
            "hospital": serialize_user(hospital),
            "notifications": recent,
            "pending_requests": pending_requests,
            "nearby_donors": [serialize_user(d) for d in nearby_donors]
        }), 200

    except Exception as e:
        logger.error(f"Hospital dashboard error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/hospital/request", methods=["POST"])
def hospital_request():
    """Create a new donation request"""
    session_data, error = get_session(required_roles=["hospital"])
    if error:
        return error

    try:
        hospital = hospitals_collection.find_one({"_id": ObjectId(session_data["user_id"])})
        if not hospital:
            return jsonify({"error": "Hospital not found"}), 404

        data = request.get_json() or {}
        request_type = (data.get("request_type") or "").lower()  # organ/blood
        details = (data.get("details") or "").strip()
        blood_group = data.get("blood_group")
        quantity = data.get("quantity", 1)
        urgency = data.get("urgency", "normal")
        patient_name = data.get("patient_name")

        if request_type not in ["organ", "blood"]:
            return jsonify({"error": "request_type must be organ or blood"}), 400

        if request_type == "blood" and not blood_group:
            return jsonify({"error": "Blood group required for blood requests"}), 400

        # Create request record
        request_data = {
            "hospital_id": str(hospital["_id"]),
            "hospital_name": hospital.get("hospital_name", hospital.get("fullname")),
            "hospital_phone": hospital.get("phone"),
            "hospital_city": hospital.get("city"),
            "request_type": request_type,
            "blood_group": blood_group,
            "quantity": quantity,
            "urgency": urgency,
            "patient_name": patient_name,
            "details": details,
            "status": "pending",
            "created_at": datetime.utcnow()
        }
        
        request_result = requests_collection.insert_one(request_data)

        # Create notification message
        message = (
            f"URGENT: {hospital.get('hospital_name', hospital.get('fullname'))} "
            f"requires {request_type.upper()}"
        )
        
        if request_type == "blood" and blood_group:
            message += f" - Blood Group: {blood_group}"
        
        if quantity:
            message += f" (Quantity: {quantity} units)"
        
        if urgency == "emergency":
            message = "🚨 EMERGENCY - " + message
        
        message += f"\nContact: {hospital.get('phone')}"
        
        if details:
            message += f"\nDetails: {details}"

        # Create notification
        create_notification(
            "request",
            message,
            hospital_id=str(hospital["_id"]),
            hospital_name=hospital.get("hospital_name", hospital.get("fullname")),
            request_type=request_type,
            request_id=str(request_result.inserted_id),
            urgency=urgency
        )

        # Find matching donors and notify them
        if request_type == "blood" and blood_group:
            matching_donors = donors_collection.find({
                "blood_group": blood_group,
                "city": hospital.get("city"),
                "status": "approved",
                "available": True
            })
            
            for donor in matching_donors:
                # Send SMS if phone available
                if donor.get("phone"):
                    # You would integrate SMS here
                    pass
                
                # Send email
                if donor.get("email"):
                    send_email(
                        donor["email"],
                        f"URGENT: Blood Donation Request in {hospital.get('city')}",
                        f"""
Dear {donor.get('fullname')},

A hospital in your area needs your help!

{message}

If you're available to donate, please contact the hospital directly.

Thank you for being a lifesaver!

LifeLink Team
                        """
                    )

        log_action('request', f'{request_type.capitalize()} request created', str(hospital["_id"]))
        
        return jsonify({
            "message": "Request created successfully",
            "request_id": str(request_result.inserted_id)
        }), 200

    except Exception as e:
        logger.error(f"Error creating request: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/hospital/received", methods=["POST"])
def hospital_received():
    """Mark donation as received"""
    session_data, error = get_session(required_roles=["hospital"])
    if error:
        return error

    try:
        hospital = hospitals_collection.find_one({"_id": ObjectId(session_data["user_id"])})
        if not hospital:
            return jsonify({"error": "Hospital not found"}), 404

        data = request.get_json() or {}
        request_type = (data.get("request_type") or "").lower()
        request_id = data.get("request_id")

        if request_type not in ["organ", "blood"]:
            return jsonify({"error": "request_type must be organ or blood"}), 400

        # Update request if ID provided
        if request_id:
            requests_collection.update_one(
                {"_id": ObjectId(request_id)},
                {"$set": {
                    "status": "completed",
                    "completed_at": datetime.utcnow()
                }}
            )

        # Create thank you message
        message = (
            f"❤️ Thank you message from {hospital.get('hospital_name', hospital.get('fullname'))}\n\n"
            f"We have received the {request_type} donation. "
            f"Your generosity has helped save a life today!"
        )

        # Create notification
        create_notification(
            "received",
            message,
            hospital_id=str(hospital["_id"]),
            hospital_name=hospital.get("hospital_name", hospital.get("fullname")),
            request_type=request_type
        )

        # Send thank you to all donors
        donors = donors_collection.find({
            "city": hospital.get("city"),
            "status": "approved"
        })
        
        for donor in donors:
            if donor.get("email"):
                send_email(
                    donor["email"],
                    f"Thank You from {hospital.get('hospital_name')} - Life Saved!",
                    f"""
Dear {donor.get('fullname')},

{message}

Your willingness to donate makes a difference. Thank you for being part of the LifeLink community!

Regards,
LifeLink Team
                    """
                )

        log_action('received', f'{request_type.capitalize()} received', str(hospital["_id"]))
        
        return jsonify({"message": "Thank you notification sent"}), 200

    except Exception as e:
        logger.error(f"Error marking received: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/hospital/profile", methods=["PATCH"])
def update_hospital_profile():
    """Update hospital profile"""
    session_data, error = get_session(required_roles=["hospital"])
    if error:
        return error

    try:
        hospital = hospitals_collection.find_one({"_id": ObjectId(session_data["user_id"])})
        if not hospital:
            return jsonify({"error": "Hospital not found"}), 404

        data = request.get_json() or {}
        allowed_fields = ["hospital_name", "phone", "address", "city", "license_number"]
        update_payload = {}

        for field in allowed_fields:
            if field in data and data[field]:
                update_payload[field] = data[field].strip()
                if field == "hospital_name":
                    update_payload["fullname"] = data[field].strip()

        if "city" in update_payload and update_payload["city"] not in TAMILNADU_DISTRICTS:
            return jsonify({"error": "Please select a valid Tamil Nadu district"}), 400

        if not update_payload:
            return jsonify({"error": "No valid fields to update"}), 400

        hospitals_collection.update_one(
            {"_id": hospital["_id"]},
            {"$set": update_payload}
        )
        
        updated = hospitals_collection.find_one({"_id": hospital["_id"]})
        log_action('update', f'Hospital profile updated: {hospital.get("fullname")}', str(hospital["_id"]))
        
        return jsonify({
            "message": "Hospital profile updated",
            "hospital": serialize_user(updated)
        }), 200

    except Exception as e:
        logger.error(f"Error updating hospital: {e}")
        return jsonify({"error": str(e)}), 500

# -------------------- Donor Routes --------------------
@app.route("/donor/dashboard", methods=["GET"])
def donor_dashboard():
    """Get donor dashboard data"""
    session_data, error = get_session(required_roles=["donor"])
    if error:
        return error

    try:
        donor = donors_collection.find_one({"_id": ObjectId(session_data["user_id"])})
        if not donor:
            return jsonify({"error": "Donor not found"}), 404

        # Get approved hospitals
        hospitals = [{
            "hospital_name": h.get("hospital_name", h.get("fullname")),
            "phone": h.get("phone"),
            "email": h.get("email"),
            "city": h.get("city"),
            "address": h.get("address")
        } for h in hospitals_collection.find({"status": "approved"})]

        # Get recent requests/notifications
        notifications = list(notifications_collection.find({
            "type": {"$in": ["request", "received"]}
        }).sort("created_at", -1).limit(50))

        for n in notifications:
            n["_id"] = str(n["_id"])
            if isinstance(n.get("created_at"), datetime):
                n["created_at"] = n["created_at"].isoformat()

        # Calculate age from DOB
        age = None
        dob_raw = donor.get("dob")
        if dob_raw:
            try:
                if isinstance(dob_raw, str):
                    dob_date = datetime.strptime(dob_raw, "%Y-%m-%d").date()
                else:
                    dob_date = dob_raw
                today = datetime.utcnow().date()
                age = today.year - dob_date.year - ((today.month, today.day) < (dob_date.month, dob_date.day))
            except (ValueError, TypeError):
                age = None

        # Get donation count
        donation_count = donations_collection.count_documents({
            "donor_id": str(donor["_id"])
        })

        return jsonify({
            "donor": serialize_user(donor),
            "last_donation_date": donor.get("last_donation_date"),
            "age": age,
            "total_donations": donation_count,
            "hospital_contacts": hospitals,
            "hospital_notifications": notifications
        }), 200

    except Exception as e:
        logger.error(f"Donor dashboard error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/donor/profile", methods=["PATCH"])
def update_donor_profile():
    """Update donor profile"""
    session_data, error = get_session(required_roles=["donor"])
    if error:
        return error

    try:
        donor = donors_collection.find_one({"_id": ObjectId(session_data["user_id"])})
        if not donor:
            return jsonify({"error": "Donor not found"}), 404

        data = request.get_json() or {}
        allowed_fields = [
            "fullname",
            "phone",
            "weight",
            "last_donation_date",
            "dob",
            "blood_group",
            "available",
            "address",
            "city"
        ]
        update_payload = {}

        for field in allowed_fields:
            if field in data and data[field] is not None:
                if field == "blood_group" and isinstance(data[field], str):
                    update_payload[field] = data[field].strip().upper()
                elif field in ["fullname", "phone", "address", "city"] and isinstance(data[field], str):
                    update_payload[field] = data[field].strip()
                else:
                    update_payload[field] = data[field]

        if not update_payload:
            return jsonify({"error": "No valid fields to update"}), 400

        # Validate weight if provided
        if "weight" in update_payload:
            try:
                new_weight = float(update_payload["weight"])
                if new_weight < 45:
                    return jsonify({"error": "Weight must be at least 45 kg"}), 400
                update_payload["weight"] = new_weight
            except (TypeError, ValueError):
                return jsonify({"error": "Weight must be a valid number"}), 400

        if "city" in update_payload:
            if not update_payload["city"]:
                return jsonify({"error": "City cannot be empty"}), 400
            if update_payload["city"] not in TAMILNADU_DISTRICTS:
                return jsonify({"error": "City must be a valid Tamil Nadu district"}), 400

        if "phone" in update_payload and not update_payload["phone"]:
            return jsonify({"error": "Phone number cannot be empty"}), 400

        if "address" in update_payload and not update_payload["address"]:
            return jsonify({"error": "Address cannot be empty"}), 400

        donors_collection.update_one(
            {"_id": donor["_id"]},
            {"$set": update_payload}
        )
        
        updated = donors_collection.find_one({"_id": donor["_id"]})
        log_action('update', f'Donor profile updated: {donor.get("fullname")}', str(donor["_id"]))
        
        return jsonify({
            "message": "Profile updated",
            "donor": serialize_user(updated)
        }), 200

    except Exception as e:
        logger.error(f"Error updating donor: {e}")
        return jsonify({"error": str(e)}), 500

# -------------------- Public APIs --------------------
@app.route("/api/donors", methods=["GET"])
def list_donors():
    """Public list of approved blood donors"""
    try:
        donors = []
        for donor in donors_collection.find({
            "status": "approved",
            "donor_type": "blood"
        }).limit(100):
            donors.append({
                "fullname": donor.get("fullname"),
                "phone": donor.get("phone"),
                "blood_group": donor.get("blood_group"),
                "city": donor.get("city"),
                "last_donation_date": donor.get("last_donation_date"),
                "available": donor.get("available", True)
            })
        
        return jsonify(donors), 200
    except Exception as e:
        logger.error(f"Error listing donors: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/hospitals", methods=["GET"])
def list_hospitals():
    """Public list of approved hospitals"""
    try:
        hospitals = []
        for hospital in hospitals_collection.find({"status": "approved"}).limit(100):
            hospitals.append({
                "hospital_name": hospital.get("hospital_name") or hospital.get("fullname"),
                "phone": hospital.get("phone"),
                "address": hospital.get("address"),
                "city": hospital.get("city")
            })

        return jsonify(hospitals), 200
    except Exception as e:
        logger.error(f"Error listing hospitals: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get system statistics"""
    try:
        donors_count = donors_collection.count_documents({"status": "approved"})
        hospitals_count = hospitals_collection.count_documents({"status": "approved"})
        donations_count = donations_collection.count_documents({})
        
        # For demo purposes, use some calculations
        saved_lives = donations_count * 2  # Each donation can save up to 2 lives
        
        return jsonify({
            "donors": donors_count,
            "hospitals": hospitals_count,
            "saved": saved_lives,
            "donations": donations_count
        }), 200
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/users', methods=['GET'])
def get_users():
    """Get all users (admin only)"""
    session_data, error = get_session(required_roles=["admin"])
    if error:
        return error

    try:
        donors = list(donors_collection.find({}, {'password': 0, 'pending_password': 0}))
        hospitals = list(hospitals_collection.find({}, {'password': 0, 'pending_password': 0}))
        
        # Add type field
        for donor in donors:
            donor['user_type'] = 'donor'
            donor['_id'] = str(donor['_id'])
        
        for hospital in hospitals:
            hospital['user_type'] = 'hospital'
            hospital['_id'] = str(hospital['_id'])
        
        all_users = donors + hospitals
        return jsonify(all_users), 200
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/pending-hospitals', methods=['GET'])
def get_pending_hospitals():
    """Get pending hospitals (admin only)"""
    session_data, error = get_session(required_roles=["admin"])
    if error:
        return error

    try:
        pending = list(hospitals_collection.find(
            {"status": "pending"}, 
            {'password': 0, 'pending_password': 0}
        ))
        
        for hospital in pending:
            hospital['_id'] = str(hospital['_id'])
        
        return jsonify(pending), 200
    except Exception as e:
        logger.error(f"Error getting pending hospitals: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/verify-hospital/<hospital_id>', methods=['POST'])
def verify_hospital_api(hospital_id):
    """Verify a hospital (admin only)"""
    session_data, error = get_session(required_roles=["admin"])
    if error:
        return error

    try:
        hospital = hospitals_collection.find_one({"_id": ObjectId(hospital_id)})
        if not hospital:
            return jsonify({"error": "Hospital not found"}), 404

        approval_password = hospital.get("pending_password")
        update_fields = {
            "verified": True,
            "is_verified": True,
            "status": "approved"
        }

        if not approval_password:
            approval_password = "".join(random.choices(string.ascii_letters + string.digits, k=10))
            update_fields["password"] = generate_password_hash(approval_password)

        result = hospitals_collection.update_one(
            {"_id": ObjectId(hospital_id)},
            {"$set": update_fields, "$unset": {"pending_password": ""}}
        )
        
        if result.modified_count > 0:
            refreshed_hospital = hospitals_collection.find_one({"_id": ObjectId(hospital_id)})
            login_id = refreshed_hospital.get("login_id")

            # Generate login ID if not exists
            if not login_id:
                login_id = generate_unique_id("HSP", hospitals_collection)
                hospitals_collection.update_one(
                    {"_id": ObjectId(hospital_id)},
                    {"$set": {"login_id": login_id}}
                )

            # Send welcome email
            send_welcome_email(
                refreshed_hospital["email"],
                refreshed_hospital.get("hospital_name", refreshed_hospital.get("fullname")),
                "hospital",
                login_id,
                approval_password
            )
            
            log_action('verify', f'Hospital verified via API: {hospital_id}')
            return jsonify({"message": "Hospital verified successfully", "login_id": login_id}), 200
        
        return jsonify({"error": "Hospital not found"}), 404
    except Exception as e:
        logger.error(f"Error verifying hospital: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/delete-user/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Delete a user (admin only)"""
    session_data, error = get_session(required_roles=["admin"])
    if error:
        return error

    try:
        # Try donors first
        result = donors_collection.delete_one({"_id": ObjectId(user_id)})
        if result.deleted_count == 0:
            result = hospitals_collection.delete_one({"_id": ObjectId(user_id)})
        
        if result.deleted_count > 0:
            log_action('delete', f'User deleted: {user_id}')
            return jsonify({"message": "User deleted successfully"}), 200
        
        return jsonify({"error": "User not found"}), 404
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/hospital/<hospital_id>', methods=['GET'])
def get_hospital_data(hospital_id):
    """Get hospital data by ID"""
    session_data, error = get_session(required_roles=["hospital", "admin"])
    if error and not session_data:
        return error

    try:
        hospital = hospitals_collection.find_one(
            {"hospital_id": hospital_id}, 
            {'password': 0, 'pending_password': 0}
        )
        
        if not hospital:
            hospital = hospitals_collection.find_one(
                {"_id": ObjectId(hospital_id) if ObjectId.is_valid(hospital_id) else None},
                {'password': 0, 'pending_password': 0}
            )
        
        if not hospital:
            return jsonify({"error": "Hospital not found"}), 404
        
        hospital['_id'] = str(hospital['_id'])
        
        # Get inventory
        inventory = inventory_collection.find_one({"hospital_id": str(hospital['_id'])})
        
        # Get requests
        requests = list(requests_collection.find({"hospital_id": str(hospital['_id'])}))
        for req in requests:
            req['_id'] = str(req['_id'])
        
        # Get donors in same city
        donors = list(donors_collection.find({
            "city": hospital.get('city'),
            "available": True,
            "status": "approved"
        }, {'password': 0, 'aadhar': 0}).limit(50))
        
        for donor in donors:
            donor['_id'] = str(donor['_id'])
        
        return jsonify({
            "hospital": hospital,
            "inventory": inventory,
            "requests": requests,
            "donors": donors
        }), 200
    except Exception as e:
        logger.error(f"Error getting hospital data: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/system-logs', methods=['GET'])
def get_system_logs():
    """Get system logs (admin only)"""
    session_data, error = get_session(required_roles=["admin"])
    if error:
        return error

    try:
        logs = list(logs_collection.find().sort('timestamp', -1).limit(100))
        for log in logs:
            log['_id'] = str(log['_id'])
            if isinstance(log.get('timestamp'), datetime):
                log['timestamp'] = log['timestamp'].isoformat()
        
        return jsonify(logs), 200
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/request-blood', methods=['POST'])
def request_blood_api():
    """Create a blood request"""
    session_data, error = get_session(required_roles=["hospital"])
    if error:
        return error

    try:
        data = request.json
        data['status'] = 'pending'
        data['created_at'] = datetime.utcnow()
        data['donation_type'] = 'blood'
        
        if 'hospital_id' not in data and session_data:
            data['hospital_id'] = session_data['user_id']
        
        result = requests_collection.insert_one(data)
        
        log_action('request', f'Blood request created: {result.inserted_id}')
        
        return jsonify({
            "message": "Request created successfully",
            "request_id": str(result.inserted_id)
        }), 201
    except Exception as e:
        logger.error(f"Error creating blood request: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/approve-request', methods=['POST'])
def approve_request():
    """Approve a donation request"""
    session_data, error = get_session(required_roles=["hospital", "admin"])
    if error:
        return error

    try:
        data = request.json
        request_id = data.get('request_id')
        
        if not request_id:
            return jsonify({"error": "Request ID required"}), 400
        
        result = requests_collection.update_one(
            {"_id": ObjectId(request_id)},
            {"$set": {
                "status": "approved", 
                "approved_at": datetime.utcnow()
            }}
        )
        
        if result.modified_count > 0:
            # Add to donations
            request_data = requests_collection.find_one({"_id": ObjectId(request_id)})
            if request_data:
                donation_data = {
                    'request_id': request_id,
                    'hospital_id': request_data.get('hospital_id'),
                    'donor_name': request_data.get('donor_name', 'Unknown'),
                    'donation_type': request_data.get('donation_type', 'blood'),
                    'donation_date': datetime.utcnow(),
                    'status': 'completed'
                }
                donations_collection.insert_one(donation_data)
            
            log_action('approve', f'Request approved: {request_id}')
            return jsonify({"message": "Request approved"}), 200
        
        return jsonify({"error": "Request not found"}), 404
    except Exception as e:
        logger.error(f"Error approving request: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/update-inventory', methods=['POST'])
def update_inventory():
    """Update hospital blood inventory"""
    session_data, error = get_session(required_roles=["hospital"])
    if error:
        return error

    try:
        data = request.json
        hospital_id = data.get('hospital_id', session_data['user_id'])
        inventory = data.get('inventory')
        
        if not inventory:
            return jsonify({"error": "Inventory data required"}), 400
        
        result = inventory_collection.update_one(
            {"hospital_id": hospital_id},
            {"$set": {
                "blood_inventory": inventory,
                "last_updated": datetime.utcnow()
            }},
            upsert=True
        )
        
        log_action('inventory', f'Inventory updated for hospital: {hospital_id}')
        
        return jsonify({"message": "Inventory updated successfully"}), 200
    except Exception as e:
        logger.error(f"Error updating inventory: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/recent-donations', methods=['GET'])
def get_recent_donations():
    """Get recent donations"""
    try:
        donations = list(donations_collection.find().sort('donation_date', -1).limit(20))
        for donation in donations:
            donation['_id'] = str(donation['_id'])
            if isinstance(donation.get('donation_date'), datetime):
                donation['donation_date'] = donation['donation_date'].isoformat()
        
        return jsonify(donations), 200
    except Exception as e:
        logger.error(f"Error getting recent donations: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "time": datetime.utcnow().isoformat(),
        "database": "connected" if DB_CONNECTED else "in-memory fallback"
    }), 200

# -------------------- Error Handlers --------------------
@app.errorhandler(404)
def not_found_error(error):
    if request.path.startswith('/api/'):
        return jsonify({"error": "Endpoint not found"}), 404
    return render_template('index.html')

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    if request.path.startswith('/api/'):
        return jsonify({"error": "Internal server error"}), 500
    return render_template('index.html')

if __name__ == '__main__':
    port = int(os.getenv("PORT", "5000"))
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"

    print("=" * 50)
    print(f"Starting LifeLink Server on port {port}")
    print("=" * 50)
    
    initialize_indexes()

    print(f"✓ Server ready at: http://localhost:{port}")
    print("=" * 50)
    
    app.run(host="0.0.0.0", debug=debug_mode, port=port)
