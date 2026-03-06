from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from bson import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from email.message import EmailMessage
from datetime import datetime, timedelta
import os
import random
import string
import smtplib

app = Flask(__name__)
CORS(app)

# -------------------- Configuration --------------------
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("MONGO_DB", "lifelink")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "lifecompanion.donors@gmail.com")
APP_PASSWORD = os.getenv("APP_PASSWORD", "")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

donors_collection = db["donors"]
hospitals_collection = db["hospitals"]
admins_collection = db["admins"]
notifications_collection = db["notifications"]
sessions_collection = db["sessions"]

# -------------------- Utility --------------------
def send_email(recipient, subject, content):
    if not APP_PASSWORD:
        print(f"⚠️ Email disabled (APP_PASSWORD missing). Intended email to {recipient}: {subject}")
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = recipient
    msg.set_content(content)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(SENDER_EMAIL, APP_PASSWORD)
            smtp.send_message(msg)
        return True
    except Exception as exc:
        print(f"❌ Email error: {exc}")
        return False


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

    session = sessions_collection.find_one({"token": token})
    if not session:
        return None, (jsonify({"error": "Invalid session"}), 401)

    if session["expires_at"] < datetime.utcnow():
        sessions_collection.delete_one({"_id": session["_id"]})
        return None, (jsonify({"error": "Session expired"}), 401)

    if required_roles and session["role"] not in required_roles:
        return None, (jsonify({"error": "Forbidden"}), 403)

    return session, None


def serialize_user(user):
    if not user:
        return None
    user["_id"] = str(user["_id"])
    user.pop("password", None)
    return user


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


# -------------------- Auth & Registration --------------------
@app.route("/auth/register", methods=["POST"])
def register_user():
    data = request.get_json() or {}
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
        if donors_collection.find_one({"aadhar": payload["aadhar"]}):
            return jsonify({"error": "Aadhar already exists"}), 400
        inserted = donors_collection.insert_one(payload)
    else:
        payload.update(
            {
                "hospital_name": fullname,
                "address": (data.get("address") or "").strip(),
                "contact_person": (data.get("contact_person") or "").strip(),
            }
        )
        inserted = hospitals_collection.insert_one(payload)

    send_email(
        email,
        "LifeLink registration submitted",
        "Your registration is submitted and pending admin verification.",
    )

    return jsonify({"message": "Registration submitted for admin verification", "id": str(inserted.inserted_id)}), 201


@app.route("/auth/admin/register", methods=["POST"])
def register_admin():
    data = request.get_json() or {}
    fullname = (data.get("fullname") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password")

    if not all([fullname, email, password]):
        return jsonify({"error": "Missing required fields"}), 400

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
        if not admin or not check_password_hash(admin["password"], password or ""):
            return jsonify({"error": "Invalid credentials"}), 401
        token = create_session(admin["_id"], "admin")
        return jsonify({"message": "Login successful", "token": token, "user": serialize_user(admin)}), 200

    if role not in ["donor", "hospital"]:
        return jsonify({"error": "Role must be donor, hospital, or admin"}), 400

    login_id = (data.get("login_id") or "").strip().upper()
    if not login_id or not password:
        return jsonify({"error": "Missing login_id or password"}), 400

    collection = donors_collection if role == "donor" else hospitals_collection
    user = collection.find_one({"login_id": login_id})

    if not user:
        return jsonify({"error": "Invalid credentials"}), 401

    if user.get("status") != "approved":
        return jsonify({"error": f"Account is {user.get('status')}. Contact admin."}), 403

    if not check_password_hash(user["password"], password):
        return jsonify({"error": "Invalid credentials"}), 401

    token = create_session(user["_id"], role)
    return jsonify({"message": "Login successful", "token": token, "user": serialize_user(user)}), 200


# -------------------- Admin --------------------
@app.route("/admin/pending-users", methods=["GET"])
def pending_users():
    _, error = get_session(required_roles=["admin"])
    if error:
        return error

    donors = [serialize_user(d) for d in donors_collection.find({"status": "pending"})]
    hospitals = [serialize_user(h) for h in hospitals_collection.find({"status": "pending"})]
    return jsonify({"donors": donors, "hospitals": hospitals}), 200


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

    if user_type not in ["donor", "hospital"]:
        return jsonify({"error": "user_type must be donor or hospital"}), 400
    if action not in ["approve", "reject"]:
        return jsonify({"error": "action must be approve or reject"}), 400

    collection = donors_collection if user_type == "donor" else hospitals_collection
    user = collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        return jsonify({"error": "User not found"}), 404

    if action == "approve":
        login_prefix = "DON" if user_type == "donor" else "HSP"
        login_id = generate_unique_id(login_prefix, collection)
        collection.update_one(
            {"_id": user["_id"]},
            {"$set": {"status": "approved", "login_id": login_id, "rejection_reason": None, "verified_at": datetime.utcnow()}},
        )
        send_email(
            user["email"],
            "LifeLink account approved",
            f"Your account is approved. Your login ID is: {login_id}\nUse this login ID with your password to login.",
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
    return jsonify({"message": "User rejected"}), 200


# -------------------- Hospital --------------------
@app.route("/hospital/dashboard", methods=["GET"])
def hospital_dashboard():
    session, error = get_session(required_roles=["hospital"])
    if error:
        return error

    hospital = hospitals_collection.find_one({"_id": ObjectId(session["user_id"])})
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
    session, error = get_session(required_roles=["hospital"])
    if error:
        return error

    hospital = hospitals_collection.find_one({"_id": ObjectId(session["user_id"])})
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

    notifications_collection.insert_one(
        {
            "hospital_id": str(hospital["_id"]),
            "hospital_name": hospital.get("hospital_name", hospital.get("fullname")),
            "type": "request",
            "request_type": request_type,
            "details": details,
            "message": message,
            "created_at": datetime.utcnow(),
        }
    )

    stats = notify_all_users(
        f"LifeLink {request_type.capitalize()} Request Alert",
        message,
    )
    return jsonify({"message": "Request notification sent", "notification_stats": stats}), 200


@app.route("/hospital/received", methods=["POST"])
def hospital_received():
    session, error = get_session(required_roles=["hospital"])
    if error:
        return error

    hospital = hospitals_collection.find_one({"_id": ObjectId(session["user_id"])})
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

    notifications_collection.insert_one(
        {
            "hospital_id": str(hospital["_id"]),
            "hospital_name": hospital.get("hospital_name", hospital.get("fullname")),
            "type": "received",
            "request_type": request_type,
            "message": message,
            "created_at": datetime.utcnow(),
        }
    )

    stats = notify_all_users(
        f"LifeLink {request_type.capitalize()} Received Update",
        message,
    )
    return jsonify({"message": "Received notification sent", "notification_stats": stats}), 200


# -------------------- Donor --------------------
@app.route("/donor/dashboard", methods=["GET"])
def donor_dashboard():
    session, error = get_session(required_roles=["donor"])
    if error:
        return error

    donor = donors_collection.find_one({"_id": ObjectId(session["user_id"])})
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

    request_notifications = []
    for note in notifications_collection.find({"type": {"$in": ["request", "received"]}}).sort("created_at", -1).limit(20):
        note["_id"] = str(note["_id"])
        request_notifications.append(note)

    return jsonify(
        {
            "donor": serialize_user(donor),
            "last_donation_date": donor.get("last_donation_date"),
            "notifications": request_notifications,
            "hospital_contacts": hospital_contacts,
        }
    ), 200


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


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "time": datetime.utcnow().isoformat()}), 200


if __name__ == "__main__":
    print("Starting Flask server on http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
