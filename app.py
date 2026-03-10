from flask import Flask, request, jsonify, session, render_template, send_from_directory
from flask_cors import CORS
from pymongo import MongoClient
from bson import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from email.message import EmailMessage
import random
import string
import json
from datetime import datetime, timedelta
import os
import smtplib


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
            template_folder='templates',  # HTML files go here
            static_folder='static')        # CSS, JS files go here
app.secret_key = 'your-secret-key-here-change-in-production'
CORS(app, supports_credentials=True)

# -------------------- Configuration --------------------
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("MONGO_DB", "lifelink")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "lifecompanion.donors@gmail.com")
APP_PASSWORD = os.getenv("APP_PASSWORD", "")

# MongoDB Connection
client = MongoClient(MONGO_URI)
db = client[DB_NAME]

donors_collection = db['donors']
hospital_collection = db['hospital']
requests_collection = db['requests']
inventory_collection = db['inventory']
campaigns_collection = db['campaigns']
logs_collection = db['system_logs']
donations_collection = db['donations']
hospitals_collection = db['hospitals']
admins_collection = db['admins']
notifications_collection = db['notifications']
sessions_collection = db['sessions']

# -------------------- Frontend Routes --------------------
@app.route('/')
def index():
    """Serve the main index page"""
    return render_template('index.html')

@app.route('/<page>')
def serve_page(page):
    """Serve individual HTML pages"""
    # List of valid pages
    valid_pages = ['blood_donors', 'dashboard', 'login', 'register', 'logout', 'about_us', 'admin', 'hospital_dashboard', 'donor_dashboard']
    
    if page in valid_pages:
        return render_template(f'{page}.html')
    
    # If page not found, return index
    return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    """Handle favicon requests"""
    return '', 204

# Serve static files (CSS, JS)
@app.route('/css/<path:filename>')
def serve_css(filename):
    """Serve CSS files"""
    return send_from_directory('static/css', filename)

@app.route('/js/<path:filename>')
def serve_js(filename):
    """Serve JavaScript files"""
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
    if not APP_PASSWORD:
        print(f"⚠️ Email disabled (APP_PASSWORD missing). Intended email to {recipient}: {subject}")
        return False

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL
    msg['To'] = recipient
    msg.set_content(content)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(SENDER_EMAIL, APP_PASSWORD)
            smtp.send_message(msg)
            log_action('email', f'Email sent to {recipient}')
            return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

def send_welcome_email(user_email, user_name, role):
    """Send welcome email after registration"""
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
    
    return send_email(user_email, f'Welcome to LifeLink - {role.capitalize()} Registration Successful!', content)


def send_sms(phone, content):
    """Best-effort SMS sending. Uses Twilio env vars when available; otherwise logs only."""
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_from = os.getenv("TWILIO_PHONE")

    if not sid or not token or not twilio_from:
        print(f"⚠️ SMS disabled (Twilio env missing). Intended SMS to {phone}: {content[:100]}")
        return False

    try:
        from twilio.rest import Client as TwilioClient  # optional dependency
        twilio_client = TwilioClient(sid, token)
        twilio_client.messages.create(body=content, from_=twilio_from, to=phone)
        return True
    except Exception as exc:
        print(f"❌ SMS error: {exc}")
        return False


def log_action(action_type, description):
    """Log system actions"""
    logs_collection.insert_one({
        'action_type': action_type,
        'description': description,
        'timestamp': datetime.utcnow()
    })


def generate_hospital_id():
    """Generate unique hospital ID"""
    while True:
        hid = "HOSP" + "".join(random.choices(string.digits, k=4))
        if not hospital_collection.find_one({"hospital_id": hid}):
            return hid


def generate_unique_id(prefix, collection, field_name="login_id", size=6):
    while True:
        generated = prefix + "".join(random.choices(string.digits, k=size))
        if not collection.find_one({field_name: generated}):
            return generated


def generate_token():
    return "".join(random.choices(string.ascii_letters + string.digits, k=48))


def create_session(user_id, role):
    token = generate_token()
    sessions_collection.insert_one(
        {
            "token": token,
            "user_id": str(user_id),
            "role": role,
            "expires_at": datetime.utcnow() + timedelta(hours=12),
        }
    )
    return token


def parse_bearer_token(auth_header):
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    return auth_header.split(" ", 1)[1]


def get_session(required_roles=None):
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
    if not user:
        return None
    user["_id"] = str(user["_id"])
    user.pop("password", None)
    return user


def serialize_notification(item):
    if not item:
        return None
    item["_id"] = str(item["_id"])
    created = item.get("created_at")
    if isinstance(created, datetime):
        item["created_at"] = created.isoformat()
    return item


def notify_all_users(subject, message):
    recipients = list(donors_collection.find({"status": "approved"})) + list(
        hospitals_collection.find({"status": "approved"})
    )
    email_count = 0
    sms_count = 0
    for user in recipients:
        if user.get("email") and send_email(user["email"], subject, message):
            email_count += 1
        if user.get("phone") and send_sms(user["phone"], message):
            sms_count += 1
    return {"email_sent": email_count, "sms_sent": sms_count}


def create_notification(event_type, message, **extra):
    payload = {
        "type": event_type,
        "message": message,
        "created_at": datetime.utcnow(),
    }
    payload.update(extra)
    notifications_collection.insert_one(payload)


# -------------------- Auth & Registration --------------------
@app.route("/auth/register", methods=["POST"])
def register_user():
    data = request.get_json(silent=True) or request.form.to_dict() or {}
    role = data.get("role")
    fullname = (data.get("fullname") or "").strip()
    phone = (data.get("phone") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password")

    if role not in ["donor", "hospital"]:
        return jsonify({"error": "Role must be donor or hospital"}), 400

    if not all([fullname, phone, email, password]):
        return jsonify({"error": "Missing required fields"}), 400

    # donor-only enforcement
    if role == "donor":
        donor_type = (data.get("donor_type") or "blood").strip().lower()
        if donor_type != "blood":
            return jsonify({"error": "Only blood donors are allowed to register."}), 400

    if donors_collection.find_one({"email": email}) or hospitals_collection.find_one({"email": email}) or admins_collection.find_one({"email": email}):
        return jsonify({"error": "Email already registered"}), 400

    payload = {
        "fullname": fullname,
        "phone": phone,
        "email": email,
        "password": generate_password_hash(password),
        "role": role,
        "status": "pending",
        "login_id": None,
        "rejection_reason": None,
        "created_at": datetime.utcnow(),
    }

    if role == "donor":
        payload.update(
            {
                "aadhar": (data.get("aadhar") or "").strip(),
                "weight": data.get("weight"),
                "dob": data.get("dob"),
                "blood_group": (data.get("blood_group") or "").strip().upper(),
                "last_donation_date": data.get("last_donation_date"),
                "donor_type": "blood",
            }
        )
        if not all([payload["aadhar"], payload["weight"], payload["dob"], payload["blood_group"]]):
            return jsonify({"error": "Missing donor fields"}), 400
        try:
            donor_weight = float(payload["weight"])
        except (TypeError, ValueError):
            return jsonify({"error": "Weight must be a valid number"}), 400
        if donor_weight < 45:
            return jsonify({"error": "Donor weight must be at least 45 kg"}), 400
        payload["weight"] = donor_weight
        if donors_collection.find_one({"aadhar": payload["aadhar"]}):
            return jsonify({"error": "Aadhar already exists"}), 400
        payload["status"] = "approved"
        payload["login_id"] = generate_unique_id("DON", donors_collection)
        payload["verified_at"] = datetime.utcnow()
        inserted = donors_collection.insert_one(payload)
    else:
        city = (data.get("city") or "").strip()
        if city not in TAMILNADU_DISTRICTS:
            return jsonify({"error": "Please select a valid Tamil Nadu district"}), 400

        cert_file = request.files.get("certificate_pdf")
        certificate_path = None
        if cert_file:
            filename = (cert_file.filename or "").strip()
            if not filename.lower().endswith(".pdf"):
                return jsonify({"error": "Certificate must be a PDF file"}), 400

            upload_dir = os.path.join(app.static_folder, "uploads", "certificates")
            os.makedirs(upload_dir, exist_ok=True)
            safe_name = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_{filename.replace(' ', '_')}"
            cert_file.save(os.path.join(upload_dir, safe_name))
            certificate_path = f"/static/uploads/certificates/{safe_name}"

        payload.update(
            {
                "hospital_name": fullname,
                "address": (data.get("address") or "").strip(),
                "city": city,
                "certificate_pdf": certificate_path,
                "license_number": (data.get("license_number") or "").strip(),
            }
        )
        if not payload["hospital_name"]:
            return jsonify({"error": "Hospital name is required"}), 400
        if not payload["certificate_pdf"]:
            return jsonify({"error": "NBAH/JCI certificate PDF is required"}), 400
        inserted = hospitals_collection.insert_one(payload)

    send_email(
        email,
        "LifeLink registration submitted",
        "Your registration is submitted and pending admin verification."
        if role == "hospital"
        else f"Your donor account is ready. Login ID: {payload['login_id']}",
    )

    message = "Registration submitted for admin verification" if role == "hospital" else "Donor registered successfully"
    return jsonify({"message": message, "id": str(inserted.inserted_id), "login_id": payload.get("login_id")}), 201


@app.route("/auth/admin/register", methods=["POST"])
def register_admin():
    data = request.get_json() or {}
    fullname = (data.get("fullname") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password")

    if not all([fullname, email, password]):
        return jsonify({"error": "Missing required fields"}), 400

    existing_admin = admins_collection.find_one()
    if existing_admin:
        return jsonify({"error": "Admin account already exists. Only one admin is allowed."}), 400

    if admins_collection.find_one({"email": email}):
        return jsonify({"error": "Admin already exists"}), 400

    admins_collection.insert_one(
        {
            "fullname": fullname,
            "email": email,
            "password": generate_password_hash(password),
            "role": "admin",
            "created_at": datetime.utcnow(),
        }
    )

    return jsonify({"message": "Admin registered successfully"}), 201


@app.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    role = data.get("role")
    password = data.get("password")

    if role == "admin":
        email = (data.get("email") or "").strip().lower()
        admin = admins_collection.find_one({"email": email})
        admin_password = admin.get("password", "") if admin else ""
        is_admin_valid = admin and (
            check_password_hash(admin_password, password or "")
            or admin_password == (password or "")
        )
        if not is_admin_valid:
            return jsonify({"error": "Invalid credentials"}), 401
        token = create_session(admin["_id"], "admin")
        return jsonify({"message": "Login successful", "token": token, "user": serialize_user(admin)}), 200

    if role not in ["donor", "hospital"]:
        return jsonify({"error": "Role must be donor, hospital, or admin"}), 400

    login_id = (data.get("login_id") or "").strip().upper()
    email = (data.get("email") or "").strip().lower()
    if not (login_id or email) or not password:
        return jsonify({"error": "Missing login_id/email or password"}), 400

    collection = donors_collection if role == "donor" else hospitals_collection
    query = {"login_id": login_id} if login_id else {"email": email}
    user = collection.find_one(query)

    if not user:
        return jsonify({"error": "Register as donor or hospital"}), 401

    if user.get("status") != "approved":
        return jsonify({"error": f"Account is {user.get('status')}. Contact admin."}), 403

    if not check_password_hash(user["password"], password):
        return jsonify({"error": "Invalid credentials"}), 401

    token = create_session(user["_id"], role)
    return jsonify({"message": "Login successful", "token": token, "user": serialize_user(user)}), 200


@app.route("/auth/logout", methods=["POST"])
def logout():
    token = parse_bearer_token(request.headers.get("Authorization"))
    if token:
        sessions_collection.delete_one({"token": token})
    return jsonify({"message": "Logout successful"}), 200


# -------------------- Admin --------------------
@app.route("/admin/pending-users", methods=["GET"])
def pending_users():
    _, error = get_session(required_roles=["admin"])
    if error:
        return error

    hospitals = [serialize_user(h) for h in hospitals_collection.find({"status": "pending"})]
    return jsonify({"hospitals": hospitals}), 200


@app.route("/admin/all-users", methods=["GET"])
def all_users():
    _, error = get_session(required_roles=["admin"])
    if error:
        return error

    donors = [serialize_user(d) for d in donors_collection.find().sort("created_at", -1)]
    hospitals = [serialize_user(h) for h in hospitals_collection.find().sort("created_at", -1)]
    return jsonify({"donors": donors, "hospitals": hospitals}), 200


@app.route("/admin/notifications", methods=["GET"])
def admin_notifications():
    _, error = get_session(required_roles=["admin"])
    if error:
        return error

    notes = [serialize_notification(n) for n in notifications_collection.find().sort("created_at", -1).limit(100)]
    return jsonify({"notifications": notes}), 200


@app.route("/admin/verify-user", methods=["POST"])
def verify_user():
    _, error = get_session(required_roles=["admin"])
    if error:
        return error

    data = request.get_json() or {}
    user_type = data.get("user_type")  # donor/hospital
    user_id = data.get("user_id")
    action = data.get("action")  # approve/reject
    rejection_reason = (data.get("rejection_reason") or "").strip()

    if user_type != "hospital":
        return jsonify({"error": "Only hospital verification is supported"}), 400
    if action not in ["approve", "reject"]:
        return jsonify({"error": "action must be approve or reject"}), 400

    collection = hospitals_collection
    try:
        object_id = ObjectId(user_id)
    except Exception:
        return jsonify({"error": "Invalid user_id"}), 400

    user = collection.find_one({"_id": object_id})
    if not user:
        return jsonify({"error": "User not found"}), 404

    if action == "approve":
        login_id = generate_unique_id("HSP", collection)
        collection.update_one(
            {"_id": user["_id"]},
            {"$set": {"status": "approved", "login_id": login_id, "rejection_reason": None, "verified_at": datetime.utcnow()}},
        )
        send_email(
            user["email"],
            "LifeLink account approved",
            f"Your account is approved. Your login ID is: {login_id}\nUse this login ID with your password to login.",
        )
        create_notification(
            "verification",
            f"{user_type.title()} {user.get('fullname')} approved with login ID {login_id}",
            user_type=user_type,
            user_email=user.get("email"),
            action="approved",
        )
        return jsonify({"message": "User approved", "login_id": login_id}), 200

    if not rejection_reason:
        return jsonify({"error": "Rejection reason required"}), 400

    collection.update_one(
        {"_id": user["_id"]},
        {"$set": {"status": "rejected", "rejection_reason": rejection_reason, "verified_at": datetime.utcnow()}},
    )
    send_email(
        user["email"],
        "LifeLink account rejected",
        f"Your account registration was rejected. Reason: {rejection_reason}",
    )
    create_notification(
        "verification",
        f"{user_type.title()} {user.get('fullname')} rejected. Reason: {rejection_reason}",
        user_type=user_type,
        user_email=user.get("email"),
        action="rejected",
    )
    return jsonify({"message": "User rejected"}), 200


# -------------------- Hospital --------------------
@app.route("/hospital/dashboard", methods=["GET"])
def hospital_dashboard():
    session_data, error = get_session(required_roles=["hospital"])
    if error:
        return error

    hospital = hospitals_collection.find_one({"_id": ObjectId(session_data["user_id"])})
    if not hospital:
        return jsonify({"error": "Hospital not found"}), 404

    recent = list(
        notifications_collection.find({"hospital_id": str(hospital["_id"])}).sort("created_at", -1).limit(10)
    )
    for item in recent:
        item["_id"] = str(item["_id"])

    return jsonify({"hospital": serialize_user(hospital), "notifications": recent}), 200


@app.route("/hospital/request", methods=["POST"])
def hospital_request():
    session_data, error = get_session(required_roles=["hospital"])
    if error:
        return error

    hospital = hospitals_collection.find_one({"_id": ObjectId(session_data["user_id"])})
    if not hospital:
        return jsonify({"error": "Hospital not found"}), 404

    data = request.get_json() or {}
    request_type = (data.get("request_type") or "").lower()  # organ/blood
    details = (data.get("details") or "").strip()

    if request_type not in ["organ", "blood"]:
        return jsonify({"error": "request_type must be organ or blood"}), 400

    message = (
        f"{hospital.get('hospital_name', hospital.get('fullname'))} has requested {request_type}.\n"
        f"Details: {details or 'Emergency support required.'}\n"
        f"Contact: {hospital.get('phone')}"
    )

    create_notification(
        "request",
        message,
        hospital_id=str(hospital["_id"]),
        hospital_name=hospital.get("hospital_name", hospital.get("fullname")),
        request_type=request_type,
        details=details,
    )

    stats = notify_all_users(
        f"LifeLink {request_type.capitalize()} Request Alert",
        message,
    )
    return jsonify({"message": "Request notification sent", "notification_stats": stats}), 200


@app.route("/hospital/received", methods=["POST"])
def hospital_received():
    session_data, error = get_session(required_roles=["hospital"])
    if error:
        return error

    hospital = hospitals_collection.find_one({"_id": ObjectId(session_data["user_id"])})
    if not hospital:
        return jsonify({"error": "Hospital not found"}), 404

    data = request.get_json() or {}
    request_type = (data.get("request_type") or "").lower()

    if request_type not in ["organ", "blood"]:
        return jsonify({"error": "request_type must be organ or blood"}), 400

    message = (
        f"{hospital.get('hospital_name', hospital.get('fullname'))} has received the requested {request_type}. "
        "Thank you for your timely support and generosity."
    )

    create_notification(
        "received",
        message,
        hospital_id=str(hospital["_id"]),
        hospital_name=hospital.get("hospital_name", hospital.get("fullname")),
        request_type=request_type,
    )

    stats = notify_all_users(
        f"LifeLink {request_type.capitalize()} Received Update",
        message,
    )
    return jsonify({"message": "Received notification sent", "notification_stats": stats}), 200


# -------------------- Donor --------------------
@app.route("/donor/dashboard", methods=["GET"])
def donor_dashboard():
    session_data, error = get_session(required_roles=["donor"])
    if error:
        return error

    donor = donors_collection.find_one({"_id": ObjectId(session_data["user_id"])})
    if not donor:
        return jsonify({"error": "Donor not found"}), 404

    hospital_contacts = [
        {
            "hospital_name": h.get("hospital_name", h.get("fullname")),
            "phone": h.get("phone"),
            "email": h.get("email"),
        }
        for h in hospitals_collection.find({"status": "approved"})
    ]

    hospital_notifications = [
        serialize_notification(item)
        for item in notifications_collection.find(
            {"type": {"$in": ["request", "received"]}}
        )
        .sort("created_at", -1)
        .limit(20)
    ]

    age = None
    dob_raw = donor.get("dob")
    if dob_raw:
        try:
            dob_date = datetime.strptime(dob_raw, "%Y-%m-%d").date()
            today = datetime.utcnow().date()
            age = today.year - dob_date.year - ((today.month, today.day) < (dob_date.month, dob_date.day))
        except ValueError:
            age = None

    return jsonify(
        {
            "donor": serialize_user(donor),
            "last_donation_date": donor.get("last_donation_date"),
            "age": age,
            "hospital_contacts": hospital_contacts,
            "hospital_notifications": hospital_notifications,
        }
    ), 200


@app.route("/donor/profile", methods=["PATCH"])
def update_donor_profile():
    session_data, error = get_session(required_roles=["donor"])
    if error:
        return error

    donor = donors_collection.find_one({"_id": ObjectId(session_data["user_id"])})
    if not donor:
        return jsonify({"error": "Donor not found"}), 404

    data = request.get_json() or {}
    allowed_fields = ["weight", "last_donation_date", "dob"]
    update_payload = {field: data[field] for field in allowed_fields if field in data}

    if "blood_group" in update_payload and isinstance(update_payload["blood_group"], str):
        update_payload["blood_group"] = update_payload["blood_group"].strip().upper()

    if not update_payload:
        return jsonify({"error": "No valid fields to update"}), 400

    if "weight" in update_payload:
        try:
            new_weight = float(update_payload["weight"])
        except (TypeError, ValueError):
            return jsonify({"error": "Weight must be a valid number"}), 400
        if new_weight < 45:
            return jsonify({"error": "Weight must be at least 45 kg"}), 400
        update_payload["weight"] = new_weight

    donors_collection.update_one({"_id": donor["_id"]}, {"$set": update_payload})
    updated = donors_collection.find_one({"_id": donor["_id"]})
    return jsonify({"message": "Profile updated", "donor": serialize_user(updated)}), 200


# -------------------- Public APIs --------------------
@app.route("/api/donors", methods=["GET"])
def list_donors():
    donors = []
    for donor in donors_collection.find({"status": "approved", "donor_type": "blood"}):
        donors.append(
            {
                "fullname": donor.get("fullname"),
                "phone": donor.get("phone"),
                "blood_group": donor.get("blood_group"),
                "last_donation_date": donor.get("last_donation_date"),
            }
        )
    return jsonify(donors), 200


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


@app.route('/api/pending-hospitals', methods=['GET'])
def get_pending_hospitals():
    try:
        pending = list(hospital_collection.find({"verified": False}, {'password': 0}))
        return jsonify(pending), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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


@app.route('/api/system-logs', methods=['GET'])
def get_system_logs():
    try:
        logs = list(logs_collection.find().sort('timestamp', -1).limit(50))
        return jsonify(logs), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/request-blood', methods=['POST'])
def request_blood():
    try:
        data = request.json
        data['status'] = 'pending'
        data['created_at'] = datetime.utcnow()
        data['donation_type'] = 'blood'
        
        result = requests_collection.insert_one(data)
        
        log_action('request', f'Blood request created: {result.inserted_id}')
        
        return jsonify({
            "message": "Request created successfully",
            "request_id": str(result.inserted_id)
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/approve-request', methods=['POST'])
def approve_request():
    try:
        data = request.json
        request_id = data.get('request_id')
        
        result = requests_collection.update_one(
            {"_id": ObjectId(request_id)},
            {"$set": {"status": "approved", "approved_at": datetime.utcnow()}}
        )
        
        if result.modified_count > 0:
            # Add to donations
            request_data = requests_collection.find_one({"_id": ObjectId(request_id)})
            donations_collection.insert_one({
                'request_id': request_id,
                'donor_name': request_data.get('donor_name', 'Unknown'),
                'donation_type': request_data.get('donation_type', 'blood'),
                'donation_date': datetime.utcnow(),
                'status': 'completed'
            })
            
            log_action('approve', f'Request approved: {request_id}')
            return jsonify({"message": "Request approved"}), 200
        return jsonify({"error": "Request not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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
                "last_updated": datetime.utcnow()
            }}
        )
        
        log_action('inventory', f'Inventory updated for hospital: {hospital_id}')
        
        return jsonify({"message": "Inventory updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/recent-donations', methods=['GET'])
def get_recent_donations():
    try:
        donations = list(donations_collection.find().sort('donation_date', -1).limit(10))
        return jsonify(donations), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "time": datetime.utcnow().isoformat()}), 200


if __name__ == '__main__':
    port = int(os.getenv("PORT", "5000"))
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"

    print(f"Starting Python Flask Server on port {port}...")
    print("Creating indexes...")

    # Create indexes for better performance
    donors_collection.create_index("email", unique=True)
    donors_collection.create_index("phone", unique=True)
    donors_collection.create_index("aadhar", unique=True)
    hospital_collection.create_index("email", unique=True)
    hospital_collection.create_index("hospital_id", unique=True)

    print("Server ready!")
    print(f"Access the application at: http://localhost:{port}")
    app.run(host="0.0.0.0", debug=debug_mode, port=port)
