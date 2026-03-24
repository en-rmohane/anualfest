from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory, session
import json, os, uuid
import firebase_admin
from firebase_admin import credentials, db, storage
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "annualfest2025secretkey"

# Vercel Configuration: Vercel instances have a read-only filesystem except for /tmp
if os.environ.get("VERCEL"):
    UPLOAD_FOLDER = "/tmp/uploads"
    DATA_FILE = "/tmp/submissions.json"
else:
    UPLOAD_FOLDER = os.path.join("static", "uploads")
    DATA_FILE = "submissions.json"

# Initialize Firebase if credentials exist
firebase_creds = os.environ.get("FIREBASE_CREDENTIALS")
firebase_db_url = os.environ.get("FIREBASE_DATABASE_URL")
firebase_storage_bucket = os.environ.get("FIREBASE_STORAGE_BUCKET")

USE_FIREBASE = False
if firebase_creds and firebase_db_url and firebase_storage_bucket:
    try:
        cred_dict = json.loads(firebase_creds)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred, {
            'databaseURL': firebase_db_url,
            'storageBucket': firebase_storage_bucket
        })
        USE_FIREBASE = True
    except Exception as e:
        print(f"Firebase initialization failed: {e}")

ALLOWED_EXTENSIONS = {"mp3", "wav", "ogg", "m4a", "flac"}
ADMIN_PASSWORD = "admin123"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def load_submissions():
    if USE_FIREBASE:
        try:
            data = db.reference("submissions").get()
            return data if data else []
        except Exception as e:
            print(f"Error reading from Firebase: {e}")
            return []
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return []

def save_submissions(data):
    if USE_FIREBASE:
        try:
            db.reference("submissions").set(data)
            return
        except Exception as e:
            print(f"Error writing to Firebase: {e}")
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

@app.route("/")
def index():
    return render_template("submit.html")

@app.route("/get_upload_url", methods=["POST"])
def get_upload_url():
    if not USE_FIREBASE:
        return jsonify({"success": False, "message": "Firebase not configured"}), 400
    try:
        data = request.json
        filename = data.get("filename", "file.mp3")
        content_type = data.get("content_type", "audio/mpeg")
        
        # Configure CORS for PUT requests from our domain
        bucket = storage.bucket()
        try:
            bucket.cors = [{
                "origin": ["*"],
                "method": ["GET", "PUT", "POST", "OPTIONS", "DELETE"],
                "responseHeader": ["*"],
                "maxAgeSeconds": 3600
            }]
            bucket.patch()
        except Exception as e:
            print("CORS Patch Error:", e)

        ext = filename.rsplit(".", 1)[1].lower() if "." in filename else "mp3"
        music_filename = f"{uuid.uuid4().hex}.{ext}"
        blob = bucket.blob(f"uploads/{music_filename}")
        
        from datetime import timedelta
        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=30),
            method="PUT",
            content_type=content_type
        )
        return jsonify({"success": True, "url": url, "music_filename": music_filename})
    except Exception as e:
        print(f"Error generating upload url: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/submit", methods=["POST"])
def submit():
    name = request.form.get("name", "").strip()
    roll = request.form.get("roll", "").strip()
    performance_type = request.form.get("performance_type", "").strip()
    performance_name = request.form.get("performance_name", "").strip()
    performance_number = request.form.get("performance_number", "").strip()
    group_members = request.form.get("group_members", "").strip()
    category = request.form.get("category", "").strip()
    description = request.form.get("description", "").strip()

    if not all([name, roll, performance_type, performance_name, category]):
        return jsonify({"success": False, "message": "Please fill all required fields!"}), 400

    music_filename = None
    music_url = None
    
    # Check if a client-side uploaded filename was sent
    client_music_filename = request.form.get("uploaded_music_filename")
    if client_music_filename and USE_FIREBASE:
        music_filename = client_music_filename
        try:
            bucket = storage.bucket()
            blob = bucket.blob(f"uploads/{music_filename}")
            blob.make_public()
            music_url = blob.public_url
        except Exception as e:
            print(f"Failed to make blob public: {e}")
    else:
        music_file = request.files.get("music_file")
        if music_file and music_file.filename:
            if allowed_file(music_file.filename):
                ext = music_file.filename.rsplit(".", 1)[1].lower()
                music_filename = f"{uuid.uuid4().hex}.{ext}"
                if USE_FIREBASE:
                    try:
                        bucket = storage.bucket()
                        blob = bucket.blob(f"uploads/{music_filename}")
                        blob.upload_from_file(music_file, content_type=music_file.content_type)
                        blob.make_public()
                        music_url = blob.public_url
                    except Exception as e:
                        print(f"Firebase Storage upload failed: {e}")
                        return jsonify({"success": False, "message": "File upload to cloud failed!"}), 500
                else:
                    music_file.save(os.path.join(UPLOAD_FOLDER, music_filename))
            else:
                return jsonify({"success": False, "message": "Only MP3, WAV, OGG, M4A files are allowed!"}), 400

    submissions = load_submissions()
    entry = {
        "id": str(uuid.uuid4()),
        "name": name,
        "roll": roll,
        "performance_type": performance_type,
        "performance_name": performance_name,
        "performance_number": performance_number,
        "group_members": group_members,
        "category": category,
        "description": description,
        "music_file": music_filename,
        "music_url": music_url,
        "submitted_at": datetime.now().strftime("%d %b %Y, %I:%M %p"),
        "status": "Pending"
    }
    submissions.append(entry)
    save_submissions(submissions)
    return jsonify({"success": True, "message": "Your performance has been successfully registered!"})

@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if session.get("admin"):
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        pwd = request.form.get("password", "")
        if pwd == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("dashboard"))
        return render_template("admin_login.html", error="Incorrect password!")
    return render_template("admin_login.html", error=None)

@app.route("/dashboard")
def dashboard():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    submissions = load_submissions()
    return render_template("dashboard.html", submissions=submissions)

@app.route("/admin/update_status", methods=["POST"])
def update_status():
    if not session.get("admin"):
        return jsonify({"success": False}), 403
    data = request.json
    submissions = load_submissions()
    for s in submissions:
        if s["id"] == data["id"]:
            s["status"] = data["status"]
    save_submissions(submissions)
    return jsonify({"success": True})

@app.route("/admin/save", methods=["POST"])
def save_submission():
    if not session.get("admin"):
        return jsonify({"success": False}), 403
    data = request.json
    submissions = load_submissions()
    if data.get("id"):
        for s in submissions:
            if s["id"] == data["id"]:
                s["name"] = data.get("name", s["name"])
                s["roll"] = data.get("roll", s["roll"])
                s["performance_type"] = data.get("performance_type", s["performance_type"])
                s["performance_name"] = data.get("performance_name", s["performance_name"])
                s["performance_number"] = data.get("performance_number", s["performance_number"])
                s["group_members"] = data.get("group_members", s["group_members"])
                s["category"] = data.get("category", s["category"])
                s["description"] = data.get("description", s["description"])
                break
    else:
        entry = {
            "id": str(uuid.uuid4()),
            "name": data.get("name", "Unknown"),
            "roll": data.get("roll", ""),
            "performance_type": data.get("performance_type", "Solo"),
            "performance_name": data.get("performance_name", ""),
            "performance_number": data.get("performance_number", ""),
            "group_members": data.get("group_members", ""),
            "category": data.get("category", "Other"),
            "description": data.get("description", ""),
            "music_file": None,
            "submitted_at": datetime.now().strftime("%d %b %Y, %I:%M %p"),
            "status": "Approved"
        }
        submissions.append(entry)
    save_submissions(submissions)
    return jsonify({"success": True})

@app.route("/admin/delete", methods=["POST"])
def delete_submission():
    if not session.get("admin"):
        return jsonify({"success": False}), 403
    data = request.json
    submissions = load_submissions()
    to_delete = next((s for s in submissions if s["id"] == data["id"]), None)
    if to_delete and to_delete.get("music_file"):
        if USE_FIREBASE:
            try:
                bucket = storage.bucket()
                blob = bucket.blob(f"uploads/{to_delete['music_file']}")
                blob.delete()
            except Exception as e:
                print(f"Error deleting from Firebase Storage: {e}")
        else:
            fpath = os.path.join(UPLOAD_FOLDER, to_delete["music_file"])
            if os.path.exists(fpath):
                os.remove(fpath)
    submissions = [s for s in submissions if s["id"] != data["id"]]
    save_submissions(submissions)
    return jsonify({"success": True})

@app.route("/admin/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("admin_login"))

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
