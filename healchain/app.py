from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, abort, make_response
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os
import csv
import json
import re
import logging
from datetime import datetime
from functools import wraps
from io import StringIO, BytesIO
import zipfile
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
_secret_key = os.environ.get("SECRET_KEY")
if not _secret_key:
    logger.warning("SECRET_KEY environment variable not set; using insecure fallback. Please set SECRET_KEY in production.")
    _secret_key = "healchain-fallback-dev-key"
app.secret_key = _secret_key

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
IDPROOF_DIR = os.path.join(UPLOAD_DIR, "idproof")
PHOTOS_DIR = os.path.join(UPLOAD_DIR, "photos")
# ADDED: patient file uploads (for miscellaneous or required uploads)
PATIENT_FILES_DIR = os.path.join(UPLOAD_DIR, "patient_files")

# Web-accessible static uploads for photos
STATIC_UPLOADS_DIR = os.path.join(BASE_DIR, "static", "uploads")
STATIC_PHOTOS_DIR = os.path.join(STATIC_UPLOADS_DIR, "photos")

# Ensure directories exist
for d in [DATA_DIR, UPLOAD_DIR, IDPROOF_DIR, PHOTOS_DIR, STATIC_UPLOADS_DIR, STATIC_PHOTOS_DIR, PATIENT_FILES_DIR]:
    os.makedirs(d, exist_ok=True)

# File paths
FILES = {
    "doctors_csv": os.path.join(DATA_DIR, "doctors.csv"),
    "doctors_json": os.path.join(DATA_DIR, "doctors.json"),
    "patients_csv": os.path.join(DATA_DIR, "patients.csv"),
    "patients_json": os.path.join(DATA_DIR, "patients.json"),
    "feedback_csv": os.path.join(DATA_DIR, "feedback.csv"),
    "feedback_json": os.path.join(DATA_DIR, "feedback.json"),
    "daily_csv": os.path.join(DATA_DIR, "daily_data.csv"),
    "daily_json": os.path.join(DATA_DIR, "daily_data.json"),
    # ADDED: requirements per patient stored as JSON and CSV for tabular export
    "requirements_json": os.path.join(DATA_DIR, "requirements.json"),
    # ADDED: patient-misc entries CSV/JSON (for miscellaneous records)
    "misc_csv": os.path.join(DATA_DIR, "misc_data.csv"),
    "misc_json": os.path.join(DATA_DIR, "misc_data.json"),
    # ADDED: messages sent by patient (contact doctor)
    "messages_csv": os.path.join(DATA_DIR, "messages.csv"),
    "messages_json": os.path.join(DATA_DIR, "messages.json"),
}

# Initialize CSVs with headers if missing
def init_csv(path, headers):
    if not os.path.exists(path):
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)

init_csv(FILES["doctors_csv"], [
    "doctor_id","name","clinic","specialization","address",
    "email","contact","experience","license","timings","photo_path","idproof_path","password"
])

init_csv(FILES["patients_csv"], [
    "patient_id","doctor_name","patient_name","age","gender","password"
])

init_csv(FILES["feedback_csv"], [
    "timestamp","name","email","message"
])

# daily_data CSV header kept but new dynamic fields will be handled by requirements management
init_csv(FILES["daily_csv"], [
    "date","patient_id","time","notes"  # core columns; specific data columns appended dynamically
])

init_csv(FILES["misc_csv"], [
    "date","patient_id","time","notes","upload_path"
])

init_csv(FILES["messages_csv"], [
    "timestamp","patient_id","doctor_id","message"
])

# Ensure requirements JSON exists
if not os.path.exists(FILES["requirements_json"]):
    with open(FILES["requirements_json"], "w", encoding="utf-8") as f:
        json.dump({}, f, indent=2)

# Helpers for JSON append
def append_json(path, record):
    data = []
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
    data.append(record)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# ID helpers (unchanged)
def _slug_name_part(name, maxlen=6):
    if not name:
        return "USR"
    letters = re.sub(r'[^A-Za-z]', '', name).upper()
    return (letters[:maxlen] or "USR")

def generate_unique_id(prefix, name, csv_path, id_field):
    base = _slug_name_part(name, maxlen=6)
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    candidate = f"{prefix}{base}{ts}"

    existing = set()
    if os.path.exists(csv_path):
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                existing_id = r.get(id_field, "")
                if existing_id:
                    existing.add(existing_id)

    uniq = candidate
    counter = 1
    while uniq in existing:
        uniq = f"{candidate}_{counter}"
        counter += 1
    return uniq

def _slug_safe_alnum(s, maxlen=12):
    if not s:
        return "UNK"
    val = re.sub(r'[^A-Za-z0-9]', '', s).upper()
    return val[:maxlen] or "UNK"

def generate_patient_id(doctor_id, patient_name, csv_path):
    doc_part = (doctor_id or "DOC").upper()
    pat_part = _slug_safe_alnum(patient_name, maxlen=12)
    ts = datetime.now().strftime("%Y%m%dT%H%M%S")
    base = f"{doc_part}_{pat_part}_{ts}"

    existing = set()
    if os.path.exists(csv_path):
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                existing_id = (r.get("patient_id") or "").strip()
                if existing_id:
                    existing.add(existing_id)

    pid = base
    suffix = 1
    while pid in existing:
        pid = f"{base}_{suffix}"
        suffix += 1
    return pid

# Authentication decorator (unchanged)
def login_required(role=None):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if 'userid' not in session or 'role' not in session:
                return redirect(url_for('login'))
            if role and session.get('role') != role:
                if session.get('role') == 'doctor':
                    return redirect(url_for('doctor_dashboard'))
                elif session.get('role') == 'patient':
                    return redirect(url_for('patient_dashboard'))
                return redirect(url_for('login'))
            return fn(*args, **kwargs)
        return wrapper
    return decorator

# ---------- Data loaders / helpers (modified/added) ----------
def load_doctor_by_id(doctor_id):
    if not os.path.exists(FILES["doctors_csv"]):
        return None
    with open(FILES["doctors_csv"], "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r.get("doctor_id") == doctor_id:
                return r
    return None

def load_all_doctors():
    doctors = []
    if not os.path.exists(FILES["doctors_csv"]):
        return doctors
    with open(FILES["doctors_csv"], "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            photo = (r.get("photo_path") or "").strip()
            public_photo = "/static/img/logo.png"
            if photo:
                if photo.startswith("/static/"):
                    public_photo = photo
                else:
                    bn = os.path.basename(photo)
                    candidate = os.path.join(STATIC_PHOTOS_DIR, bn)
                    if os.path.exists(candidate):
                        public_photo = f"/static/uploads/photos/{bn}"
                    else:
                        candidate2 = os.path.join(PHOTOS_DIR, bn)
                        if os.path.exists(candidate2):
                            try:
                                dst = os.path.join(STATIC_PHOTOS_DIR, bn)
                                if not os.path.exists(dst):
                                    os.replace(candidate2, dst)
                                public_photo = f"/static/uploads/photos/{bn}"
                            except Exception:
                                public_photo = photo
                        else:
                            public_photo = photo
            doctors.append({
                "doctor_id": r.get("doctor_id"),
                "name": r.get("name"),
                "clinic": r.get("clinic"),
                "specialization": r.get("specialization"),
                "photo_path": public_photo
            })
    return doctors

def load_patients_for_doctor(doctor_id):
    res = []
    doctor = load_doctor_by_id(doctor_id)
    if not doctor:
        return res
    doctor_name = doctor.get("name")
    if not os.path.exists(FILES["patients_csv"]):
        return res
    with open(FILES["patients_csv"], "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r.get("doctor_name") == doctor_name:
                res.append({
                    "patient_id": r.get("patient_id"),
                    "patient_name": r.get("patient_name"),
                    "age": r.get("age"),
                    "gender": r.get("gender"),
                    "doctor_name": r.get("doctor_name")
                })
    return res

def load_patient_by_id(patient_id):
    if not os.path.exists(FILES["patients_csv"]):
        return None
    with open(FILES["patients_csv"], "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r.get("patient_id") == patient_id:
                return {
                    "patient_id": r.get("patient_id"),
                    "patient_name": r.get("patient_name"),
                    "age": r.get("age"),
                    "gender": r.get("gender"),
                    "doctor_name": r.get("doctor_name")
                }
    return None

def load_daily_rows_for_patient(patient_id):
    """
    Loads the dynamic CSV daily_data.csv for the patient.
    This file has core columns: date, patient_id, time, notes
    and additional columns created by requirements (e.g., weight_kg, bp).
    We return each row as dict (column->value)
    """
    rows = []
    if not os.path.exists(FILES["daily_csv"]):
        return rows
    with open(FILES["daily_csv"], "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r.get("patient_id") == patient_id:
                rows.append(r)
    try:
        rows.sort(key=lambda x: (x.get("date") or ""), reverse=True)
    except Exception:
        pass
    return rows

# ADDED: Requirements helpers
def load_requirements_all():
    if not os.path.exists(FILES["requirements_json"]):
        return {}
    with open(FILES["requirements_json"], "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_requirements_all(data):
    with open(FILES["requirements_json"], "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def ensure_daily_csv_has_columns(cols):
    """
    Ensure the daily CSV header contains the provided columns.
    If missing, rewrite header adding new columns (existing rows are preserved).
    """
    path = FILES["daily_csv"]
    # Read existing rows
    existing_rows = []
    existing_header = []
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            existing_header = reader.fieldnames or []
            for r in reader:
                existing_rows.append(r)
    else:
        existing_header = []

    new_header = list(existing_header)
    for c in cols:
        if c not in new_header:
            new_header.append(c)
    # If header unchanged, nothing to do
    if new_header == existing_header and os.path.exists(path):
        return

    # Rewrite CSV with new header; ensure missing fields in rows are blank
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=new_header)
        writer.writeheader()
        for r in existing_rows:
            row = {k: r.get(k, "") for k in new_header}
            writer.writerow(row)

def write_daily_row(patient_id, record_dict):
    """
    record_dict contains keys for columns and their values, must include 'date' and 'time' maybe 'notes'.
    We will ensure the daily CSV header includes all keys (except patient_id always present) and append row.
    """
    path = FILES["daily_csv"]
    # Ensure core header exists
    core = ["date", "patient_id", "time", "notes"]
    all_keys = set(core) | set(record_dict.keys())
    # Write header if required
    ensure_daily_csv_has_columns(list(all_keys))
    # Append row
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=(open(path, "r", encoding="utf-8").read().splitlines()[0].split(",")))
        # Build row with all header fields
        header = writer.fieldnames
        row = {k: "" for k in header}
        row.update(record_dict)
        row["patient_id"] = patient_id
        writer.writerow(row)
    # Also append to daily_json for easy reading (preserve structure)
    append_json(FILES["daily_json"], {"patient_id": patient_id, **record_dict})

# ---------- New: ZIP generation helper and download routes ----------
def generate_patient_zip(patient_id):
    """
    Build an in-memory ZIP containing:
      - <patient_id>_daily_data.csv : filtered rows from daily_data.csv (header preserved)
      - <patient_id>_misc_records.csv : filtered rows from misc_data.csv (header preserved)
      - uploads/* : all files under PATIENT_FILES_DIR/<patient_id> kept under uploads/
    Returns BytesIO pointing to start of ZIP.
    """
    zip_buf = BytesIO()
    with zipfile.ZipFile(zip_buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        # 1) daily_data.csv filtered
        daily_path = FILES.get("daily_csv")
        if daily_path and os.path.exists(daily_path):
            with open(daily_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                rows = list(reader)
            if rows:
                header = rows[0]
                out = StringIO()
                writer = csv.writer(out)
                writer.writerow(header)
                pid_idx = None
                try:
                    pid_idx = header.index("patient_id")
                except ValueError:
                    pid_idx = None
                for r in rows[1:]:
                    if pid_idx is not None and pid_idx < len(r) and r[pid_idx] == patient_id:
                        writer.writerow(r)
                csv_bytes = ("\ufeff" + out.getvalue()).encode("utf-8")
                zf.writestr(f"{patient_id}_daily_data.csv", csv_bytes)

        # 2) misc_data.csv filtered
        misc_path = FILES.get("misc_csv")
        if misc_path and os.path.exists(misc_path):
            with open(misc_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                rows = list(reader)
            if rows:
                header = rows[0]
                out = StringIO()
                writer = csv.writer(out)
                writer.writerow(header)
                pid_idx = None
                try:
                    pid_idx = header.index("patient_id")
                except ValueError:
                    pid_idx = None
                for r in rows[1:]:
                    if pid_idx is not None and pid_idx < len(r) and r[pid_idx] == patient_id:
                        writer.writerow(r)
                csv_bytes = ("\ufeff" + out.getvalue()).encode("utf-8")
                zf.writestr(f"{patient_id}_misc_records.csv", csv_bytes)

        # 3) patient uploaded files
        patient_files_folder = os.path.join(PATIENT_FILES_DIR, patient_id)
        if os.path.exists(patient_files_folder):
            for root, _, files in os.walk(patient_files_folder):
                for fname in files:
                    full = os.path.join(root, fname)
                    arcname = os.path.join("uploads", os.path.relpath(full, patient_files_folder))
                    try:
                        zf.write(full, arcname=arcname)
                    except Exception:
                        try:
                            with open(full, "rb") as rf:
                                zf.writestr(arcname, rf.read())
                        except Exception:
                            # skip file on failure
                            pass

    zip_buf.seek(0)
    return zip_buf

@app.route("/doctor/patient/download_by_form", methods=["POST"])
@login_required(role="doctor")
def download_patient_data_from_form():
    """
    Wrapper to accept the form on doctor_view.htm that posts selected_patient.
    """
    patient_id = request.form.get("selected_patient", "").strip()
    if not patient_id:
        flash("Please select a patient to download.")
        return redirect(url_for("doctor_view"))
    return download_patient_data(patient_id)

@app.route("/doctor/patient/<patient_id>/download", methods=["POST"])
@login_required(role="doctor")
def download_patient_data(patient_id):
    """
    Path-style download: returns ZIP for patient_id if current doctor is authorized.
    """
    doctor_id = session.get("userid")
    doctor = load_doctor_by_id(doctor_id)
    if not doctor:
        abort(403)
    patient = load_patient_by_id(patient_id)
    if not patient:
        abort(404)
    if patient.get("doctor_name") != doctor.get("name"):
        abort(403)

    zip_buf = generate_patient_zip(patient_id)
    download_name = f"{patient_id}_data_{datetime.utcnow().strftime('%Y%m%d')}.zip"
    return send_file(
        zip_buf,
        mimetype="application/zip",
        as_attachment=True,
        download_name=download_name
    )

# ---------- Routes (existing + new) ----------
@app.route("/")
def home():
    return render_template("home.htm")

@app.route("/about")
def about():
    return render_template("about.htm")

@app.route("/monitoring")
def monitoring():
    return render_template("monitoring.htm")

@app.route("/contact")
def contact():
    return render_template("contact.htm")

@app.route("/login", methods=["GET"])
def login():
    return render_template("login.htm")

@app.route("/account")
def account():
    return render_template("account.htm")

@app.route("/doctor/register", methods=["GET"])
def doctor_register():
    return render_template("doctor_register.htm")

@app.route("/patient/register", methods=["GET"])
def patient_register():
    return render_template("patient_register.htm")

@app.route("/doctor/dashboard")
@login_required(role="doctor")
def doctor_dashboard():
    doctor_id = session.get("userid")
    doctor_info = load_doctor_by_id(doctor_id) or {}
    patients_for_doctor = load_patients_for_doctor(doctor_id)
    return render_template("doctor_dashboard.htm", doctor=doctor_info, patients=patients_for_doctor)

# MODIFIED patient dashboard route: render new patient dashboard layout
@app.route("/patient/dashboard")
@login_required(role="patient")
def patient_dashboard():
    patient_id = session.get("userid")
    patient_info = load_patient_by_id(patient_id) or {}
    # load requirements for this patient
    reqs = load_requirements_all().get(patient_id, [])
    return render_template("patient_dashboard_v2.htm", patient=patient_info, requirements=reqs)

# doctor view / patient selection (unchanged)
@app.route("/doctor/view", methods=["GET", "POST"])
@login_required(role="doctor")
def doctor_view():
    doctor_id = session.get("userid")
    registered_patients = load_patients_for_doctor(doctor_id)
    if request.method == "POST":
        selected_patient = request.form.get("selected_patient", "").strip()
        if not selected_patient:
            flash("Please select a patient.")
            return redirect(url_for("doctor_view"))
        return redirect(url_for("doctor_patient_detail", patient_id=selected_patient))
    return render_template("doctor_view.htm", registered_patients=registered_patients)

@app.route("/doctor/patient/register", methods=["GET"])
@login_required(role="doctor")
def doctor_patient_register():
    doctor_id = session.get("userid")
    doctor_info = load_doctor_by_id(doctor_id) or {}
    return render_template("doctorpatientregister.htm", doctor=doctor_info)

# doctor patient detail -- updated to show the Manage Data / Assign options
@app.route("/doctor/patient/<patient_id>")
@login_required(role="doctor")
def doctor_patient_detail(patient_id):
    doctor_id = session.get("userid")
    doctor = load_doctor_by_id(doctor_id)
    if not doctor:
        abort(403)
    patient = load_patient_by_id(patient_id)
    if not patient:
        abort(404)
    if patient.get("doctor_name") != doctor.get("name"):
        abort(403)

    rows = load_daily_rows_for_patient(patient_id)
    # compute summary metrics for standard columns if present
    avg_blood_sugar = "—"
    avg_weight = "—"
    latest_bp = None
    sugars = []
    weights = []
    if rows:
        for r in rows:
            try:
                v = float((r.get("blood_sugar") or r.get("blood_sugar_mgdl") or "") or 0)
                sugars.append(v)
            except Exception:
                pass
            try:
                w = float((r.get("weight_kg") or r.get("weight") or "") or 0)
                weights.append(w)
            except Exception:
                pass
        if sugars:
            avg_blood_sugar = round(sum(sugars) / len(sugars), 2)
        if weights:
            avg_weight = round(sum(weights) / len(weights), 2)
        # pick latest bp if any column like blood_pressure exists
        latest_bp = rows[0].get("blood_pressure") or rows[0].get("bp") or None

    patient_ctx = {
        "id": patient.get("patient_id"),
        "name": patient.get("patient_name"),
        "age": patient.get("age"),
        "sex": patient.get("gender")
    }
    # load requirements
    reqs = load_requirements_all().get(patient_id, [])
    # load messages
    messages = []
    if os.path.exists(FILES["messages_csv"]):
        with open(FILES["messages_csv"], "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for m in reader:
                if m.get("patient_id") == patient_id:
                    messages.append(m)
    misc = []
    if os.path.exists(FILES["misc_csv"]):
        with open(FILES["misc_csv"], "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                if r.get("patient_id") == patient_id:
                    misc.append(r)


    return render_template(
    "patient_daily_data.htm",
    patient=patient_ctx,
    rows=rows,
    avg_blood_sugar=avg_blood_sugar,
    avg_weight=avg_weight,
    latest_bp=latest_bp,
    requirements=reqs,
    messages=messages,
    misc=misc  # ✅ Add this line
)


# Export CSV (unchanged core, but daily CSV header may be dynamic)
@app.route("/doctor/patient/<patient_id>/export.csv")
@login_required(role="doctor")
def export_patient_csv(patient_id):
    doctor_id = session.get("userid")
    doctor = load_doctor_by_id(doctor_id)
    if not doctor:
        abort(403)
    patient = load_patient_by_id(patient_id)
    if not patient:
        abort(404)
    if patient.get("doctor_name") != doctor.get("name"):
        abort(403)
    rows = load_daily_rows_for_patient(patient_id)
    # Build header from file
    path = FILES["daily_csv"]
    if not os.path.exists(path):
        si = StringIO()
        si.write("")
        csv_text = si.getvalue()
    else:
        with open(path, "r", encoding="utf-8") as f:
            csv_text = f.read()
    bom = '\ufeff'
    data = (bom + csv_text).encode('utf-8')
    bio = BytesIO()
    bio.write(data)
    bio.seek(0)
    filename = f"{patient_id}_records_{datetime.utcnow().strftime('%Y%m%d')}.csv"
    return send_file(
        bio,
        mimetype="text/csv; charset=utf-8",
        as_attachment=True,
        download_name=filename
    )


@app.route('/data/uploads/patient_files/<path:filename>')
def serve_patient_file(filename):
    full_path = os.path.join(PATIENT_FILES_DIR, filename)
    if os.path.exists(full_path):
        return send_file(full_path)
    abort(404)


# Doctors listing and profile routes (unchanged)
@app.route("/doctors")
def doctors():
    doctors_list = load_all_doctors()
    return render_template("doctors.htm", doctors=doctors_list)

@app.route("/doctors/<doctor_id>")
def doctor_profile(doctor_id):
    doc = load_doctor_by_id(doctor_id)
    if not doc:
        abort(404)
    photo = (doc.get("photo_path") or "").strip()
    public_photo = "/static/img/logo.png"
    if photo:
        if photo.startswith("/static/"):
            public_photo = photo
        else:
            bn = os.path.basename(photo)
            candidate = os.path.join(STATIC_PHOTOS_DIR, bn)
            if os.path.exists(candidate):
                public_photo = f"/static/uploads/photos/{bn}"
            else:
                candidate2 = os.path.join(PHOTOS_DIR, bn)
                if os.path.exists(candidate2):
                    try:
                        dst = os.path.join(STATIC_PHOTOS_DIR, bn)
                        if not os.path.exists(dst):
                            os.replace(candidate2, dst)
                        public_photo = f"/static/uploads/photos/{bn}"
                    except Exception:
                        public_photo = photo
                else:
                    public_photo = photo
    profile = {
        "doctor_id": doc.get("doctor_id"),
        "name": doc.get("name"),
        "clinic": doc.get("clinic"),
        "specialization": doc.get("specialization"),
        "address": doc.get("address"),
        "email": doc.get("email"),
        "contact": doc.get("contact"),
        "experience": doc.get("experience"),
        "license": doc.get("license"),
        "timings": doc.get("timings"),
        "photo_path": public_photo
    }
    return render_template("doctor_profile.htm", doctor=profile)

# Feedback submission (unchanged)
@app.route("/submit_feedback", methods=["POST"])
def submit_feedback():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    message = request.form.get("message", "").strip()
    ts = datetime.now().isoformat(timespec="seconds")
    with open(FILES["feedback_csv"], "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([ts, name, email, message])
    append_json(FILES["feedback_json"], {
        "timestamp": ts,
        "name": name, "email": email, "message": message
    })
    flash("Your feedback is recorded.")
    return redirect(url_for("home"))

# Doctor patient profile (unchanged interface route)
@app.route("/doctor/patient/<patient_id>/profile")
@login_required(role="doctor")
def doctor_patient_profile(patient_id):
    doctor_id = session.get("userid")
    doctor = load_doctor_by_id(doctor_id)
    if not doctor:
        abort(403)
    patient = load_patient_by_id(patient_id)
    if not patient:
        abort(404)
    if patient.get("doctor_name") != doctor.get("name"):
        abort(403)
    return render_template("patient_profile.htm", patient=patient)

# Doctor register (POST) — unchanged
@app.route("/doctor/register", methods=["POST"])
def doctor_register_post():
    form = request.form
    name = form.get("name", "").strip()
    clinic = form.get("clinic", "").strip()
    specialization = form.get("specialization", "").strip()
    address = form.get("address", "").strip()
    email = form.get("email", "").strip()
    contact = form.get("contact", "").strip()
    experience = form.get("experience", "").strip()
    license_id = form.get("license", "").strip()
    timings = form.get("timings", "").strip()
    password = form.get("password", "").strip()
    confirm = form.get("confirm", "").strip()

    if password != confirm:
        flash("Passwords do not match.")
        return redirect(url_for("doctor_register"))

    idproof_file = request.files.get("idproof")
    photo_file = request.files.get("photo")

    doctor_id = generate_unique_id("DOC", name, FILES["doctors_csv"], "doctor_id")

    idproof_path = ""
    photo_path = ""

    # save idproof in data/uploads/idproof (private)
    if idproof_file and idproof_file.filename:
        fn = secure_filename(f"{doctor_id}_{idproof_file.filename}")
        save_path = os.path.join(IDPROOF_DIR, fn)
        idproof_file.save(save_path)
        idproof_path = os.path.relpath(save_path, BASE_DIR)

    # save photo into static/uploads/photos so templates can serve it
    if photo_file and photo_file.filename:
        fn = secure_filename(f"{doctor_id}_{photo_file.filename}")
        save_path_static = os.path.join(STATIC_PHOTOS_DIR, fn)
        photo_file.save(save_path_static)
        photo_path = f"/static/uploads/photos/{fn}"

    hashed_password = generate_password_hash(password)

    with open(FILES["doctors_csv"], "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            doctor_id, name, clinic, specialization, address,
            email, contact, experience, license_id, timings,
            photo_path, idproof_path, hashed_password
        ])

    append_json(FILES["doctors_json"], {
        "doctor_id": doctor_id,
        "name": name, "clinic": clinic, "specialization": specialization, "address": address,
        "email": email, "contact": contact, "experience": experience, "license": license_id,
        "timings": timings, "photo_path": photo_path, "idproof_path": idproof_path,
        "password": hashed_password
    })

    flash(f"Doctor registered. Your UserID is {doctor_id}")
    return redirect(url_for("login"))

# Doctor-side patient register (POST) (unchanged)
@app.route("/doctor/patient/register", methods=["POST"])
@login_required(role="doctor")
def doctor_patient_register_post():
    form = request.form
    doctor_id = session.get("userid")
    doctor_name = None

    if os.path.exists(FILES["doctors_csv"]):
        with open(FILES["doctors_csv"], "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("doctor_id") == doctor_id:
                    doctor_name = row.get("name")
                    break

    if not doctor_name:
        doctor_name = form.get("doctor", "").strip()

    patient_name = form.get("patient", "").strip()
    age = form.get("age", "").strip()
    gender = form.get("gender", "").strip()
    password = form.get("password", "").strip()

    patient_id = generate_patient_id(doctor_id or doctor_name or "DOC", patient_name, FILES["patients_csv"])
    hashed = generate_password_hash(password)

    with open(FILES["patients_csv"], "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([patient_id, doctor_name, patient_name, age, gender, hashed])

    append_json(FILES["patients_json"], {
        "patient_id": patient_id, "doctor_name": doctor_name,
        "patient_name": patient_name, "age": age, "gender": gender,
        "password": hashed
    })

    flash(f"Patient registered. Assigned ID: {patient_id}")
    return redirect(url_for("doctor_dashboard"))

@app.route("/patient/register", methods=["POST"])
def patient_register_post():
    form = request.form
    doctor_name = form.get("doctor", "").strip()
    patient_name = form.get("patient", "").strip()
    age = form.get("age", "").strip()
    gender = form.get("gender", "").strip()
    patient_id_field = form.get("patientid", "").strip()
    password = form.get("password", "").strip()

    if not patient_id_field:
        doctor_identifier = doctor_name or "DOC"
        patient_id_field = generate_patient_id(doctor_identifier, patient_name, FILES["patients_csv"])

    hashed = generate_password_hash(password)

    with open(FILES["patients_csv"], "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([patient_id_field, doctor_name, patient_name, age, gender, hashed])

    append_json(FILES["patients_json"], {
        "patient_id": patient_id_field, "doctor_name": doctor_name,
        "patient_name": patient_name, "age": age, "gender": gender,
        "password": hashed
    })

    flash(f"Patient registered. Your UserID is {patient_id_field}")
    return redirect(url_for("login"))

@app.route("/login", methods=["POST"])
def login_post():
    user_id = request.form.get("userid", "").strip()
    password = request.form.get("password", "").strip()
    role = request.form.get("role", "").strip().lower()

    if role not in ("doctor", "patient"):
        return render_template("login.htm", error="Please select a role (Doctor or Patient).")

    if role == "doctor" and os.path.exists(FILES["doctors_csv"]):
        with open(FILES["doctors_csv"], "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("doctor_id") == user_id:
                    stored = row.get("password", "")
                    if stored and check_password_hash(stored, password):
                        session.clear()
                        session["userid"] = user_id
                        session["role"] = "doctor"
                        return redirect(url_for("doctor_dashboard"))
                    break

    if role == "patient" and os.path.exists(FILES["patients_csv"]):
        with open(FILES["patients_csv"], "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("patient_id") == user_id:
                    stored = row.get("password", "")
                    if stored and check_password_hash(stored, password):
                        session.clear()
                        session["userid"] = user_id
                        session["role"] = "patient"
                        return redirect(url_for("patient_dashboard"))
                    break

    return render_template("login.htm", error="Invalid credentials or role mismatch.")

# ---------- New: Manage Data Requirements (Doctor) ----------
@app.route("/doctor/patient/<patient_id>/manage_requirements", methods=["GET", "POST"])
@login_required(role="doctor")
def manage_requirements(patient_id):
    doctor_id = session.get("userid")
    doctor = load_doctor_by_id(doctor_id)
    if not doctor:
        abort(403)
    patient = load_patient_by_id(patient_id)
    if not patient:
        abort(404)
    # only allow the patient's assigned doctor to manage
    if patient.get("doctor_name") != doctor.get("name"):
        abort(403)

    all_reqs = load_requirements_all()
    patient_reqs = all_reqs.get(patient_id, [])

    if request.method == "POST":
        # Expect multiple possible actions: add, update, remove
        action = request.form.get("action", "add")
        if action == "add":
            # Fields from form: field_name, label, unit, input_type (text/number/upload), upload_formats (csv;jpg)
            fname = request.form.get("field_name", "").strip()
            label = request.form.get("label", "").strip() or fname
            unit = request.form.get("unit", "").strip()
            input_type = request.form.get("input_type", "text").strip()
            upload_formats = request.form.get("upload_formats", "").strip()  # csv separated by ;
            # Warning range optional (min,max)
            warn_min = request.form.get("warn_min", "").strip()
            warn_max = request.form.get("warn_max", "").strip()
            # default storage: field key will be slugified
            key = re.sub(r'[^A-Za-z0-9_]', '_', fname).lower() or f"field_{len(patient_reqs)+1}"
            # If key exists, append index
            existing_keys = {r.get("key") for r in patient_reqs}
            base_key = key
            idx = 1
            while key in existing_keys:
                key = f"{base_key}_{idx}"; idx += 1

            record = {
                "key": key,
                "label": label,
                "unit": unit,
                "input_type": input_type,  # text, number, upload
                "upload_formats": upload_formats,  # semicolon separated extensions without dots, e.g. pdf;jpg
                "warn_min": warn_min,
                "warn_max": warn_max
            }
            patient_reqs.append(record)
            all_reqs[patient_id] = patient_reqs
            save_requirements_all(all_reqs)
            flash("Requirement added.")
            return redirect(url_for("manage_requirements", patient_id=patient_id))
        elif action == "remove":
            key = request.form.get("key")
            patient_reqs = [r for r in patient_reqs if r.get("key") != key]
            all_reqs[patient_id] = patient_reqs
            save_requirements_all(all_reqs)
            flash("Requirement removed.")
            return redirect(url_for("manage_requirements", patient_id=patient_id))
        elif action == "update":
            key = request.form.get("key")
            for r in patient_reqs:
                if r.get("key") == key:
                    r["label"] = request.form.get("label", r["label"]).strip()
                    r["unit"] = request.form.get("unit", r["unit"]).strip()
                    r["input_type"] = request.form.get("input_type", r["input_type"]).strip()
                    r["upload_formats"] = request.form.get("upload_formats", r.get("upload_formats", "")).strip()
                    r["warn_min"] = request.form.get("warn_min", r.get("warn_min", "")).strip()
                    r["warn_max"] = request.form.get("warn_max", r.get("warn_max", "")).strip()
                    break
            all_reqs[patient_id] = patient_reqs
            save_requirements_all(all_reqs)
            flash("Requirement updated.")
            return redirect(url_for("manage_requirements", patient_id=patient_id))

    return render_template("manage_requirements.htm", patient=patient, requirements=patient_reqs)

# ---------- New: Assign another doctor ----------
@app.route("/doctor/patient/<patient_id>/assign", methods=["GET", "POST"])
@login_required(role="doctor")
def assign_doctor(patient_id):
    doctor_id = session.get("userid")
    doctor = load_doctor_by_id(doctor_id)
    if not doctor:
        abort(403)
    patient = load_patient_by_id(patient_id)
    if not patient:
        abort(404)
    if patient.get("doctor_name") != doctor.get("name"):
        abort(403)

    if request.method == "POST":
        new_doc_id = request.form.get("new_doctor_id", "").strip()
        keep_recording = request.form.get("keep_recording", "no").lower() == "yes"
        # validate new doctor id
        new_doc = load_doctor_by_id(new_doc_id)
        if not new_doc:
            flash("Doctor ID not found.")
            return redirect(url_for("assign_doctor", patient_id=patient_id))
        # Update patients.csv: we will append a new row representing same patient_id but new doctor mapping
        # To keep data consistent we will rewrite patients.csv replacing the row's doctor_name but keep patient_id same
        patients = []
        found = False
        with open(FILES["patients_csv"], "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                if r.get("patient_id") == patient_id:
                    r["doctor_name"] = new_doc.get("name")
                    found = True
                patients.append(r)
        # write back
        if patients:
            fieldnames = patients[0].keys()
            with open(FILES["patients_csv"], "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for r in patients:
                    writer.writerow(r)
        # Save an assignment note in requirements JSON (metadata) to indicate if keep_recording is true
        all_reqs = load_requirements_all()
        meta = all_reqs.get("_meta", {})
        meta.setdefault("assignments", {})
        meta["assignments"][patient_id] = {
            "from_doctor": doctor.get("doctor_id"),
            "to_doctor": new_doc_id,
            "keep_recording": bool(keep_recording),
            "timestamp": datetime.utcnow().isoformat(timespec="seconds")
        }
        all_reqs["_meta"] = meta
        save_requirements_all(all_reqs)
        flash("Patient reassigned.")
        return redirect(url_for("doctor_dashboard"))

    # Provide a short list of doctors for autocomplete display
    doctors = load_all_doctors()
    return render_template("assign_doctor.htm", patient=patient, doctors=doctors)

# ---------- Modified patient-facing routes: record required / miscellaneous / contact ----------
@app.route("/patient/record_required", methods=["GET", "POST"])
@login_required(role="patient")
def patient_record_required():
    patient_id = session.get("userid")
    patient = load_patient_by_id(patient_id)
    if not patient:
        abort(404)
    reqs = load_requirements_all().get(patient_id, [])
    if request.method == "POST":
        # collect date, time, notes, and specific fields
        date = request.form.get("date", "").strip() or datetime.utcnow().date().isoformat()
        time = request.form.get("time", "").strip() or datetime.utcnow().time().strftime("%H:%M:%S")
        notes = request.form.get("notes", "").strip()
        # prepare record dict
        record = {"date": date, "time": time, "notes": notes}
        # handle fields; if upload, save file and add upload path
        for r in reqs:
            key = r.get("key")
            itype = r.get("input_type", "text")
            if itype == "upload":
                f = request.files.get(key)
                if f and f.filename:
                    patient_dir = os.path.join(PATIENT_FILES_DIR, patient_id)
                    os.makedirs(patient_dir, exist_ok=True)
                    fn = secure_filename(f"{key}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{f.filename}")
                    save_path = os.path.join(patient_dir, fn)
                    f.save(save_path)
                    # store relative path
                    web_path = os.path.relpath(save_path, BASE_DIR).replace("\\", "/")
                    record[key] = f"/{web_path}"

            else:
                record[key] = request.form.get(key, "").strip()
        # write record (ensure header includes these keys)
        write_daily_row(patient_id, record)
        flash("Record saved.")
        return redirect(url_for("patient_dashboard"))
    return render_template("record_required.htm", patient=patient, requirements=reqs)

@app.route("/patient/record_misc", methods=["GET", "POST"])
@login_required(role="patient")
def patient_record_misc():
    patient_id = session.get("userid")
    patient = load_patient_by_id(patient_id)
    if not patient:
        abort(404)
    if request.method == "POST":
        date = request.form.get("date", "").strip() or datetime.utcnow().date().isoformat()
        time = request.form.get("time", "").strip() or datetime.utcnow().time().strftime("%H:%M:%S")
        notes = request.form.get("notes", "").strip()
        f = request.files.get("upload")
        upload_path = ""
        if f and f.filename:
            patient_dir = os.path.join(PATIENT_FILES_DIR, patient_id)
            os.makedirs(patient_dir, exist_ok=True)
            fn = secure_filename(f"misc_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{f.filename}")
            save_path = os.path.join(patient_dir, fn)
            f.save(save_path)
            web_path = os.path.relpath(save_path, BASE_DIR).replace("\\", "/")
            upload_path = f"/{web_path}"

        with open(FILES["misc_csv"], "a", newline="", encoding="utf-8") as fcsv:
            writer = csv.writer(fcsv)
            writer.writerow([date, patient_id, time, notes, upload_path])
        append_json(FILES["misc_json"], {
            "date": date, "patient_id": patient_id, "time": time, "notes": notes, "upload_path": upload_path
        })
        flash("Miscellaneous record saved.")
        return redirect(url_for("patient_dashboard"))
    return render_template("record_misc.htm", patient=patient)

# Contact doctor (message) from patient
@app.route("/patient/contact_doctor", methods=["POST"])
@login_required(role="patient")
def patient_contact_doctor():
    patient_id = session.get("userid")
    patient = load_patient_by_id(patient_id)
    if not patient:
        abort(404)
    message = request.form.get("message", "").strip()
    if len(message) > 200:
        flash("Message too long (limit 200 words).")
        return redirect(url_for("patient_dashboard"))
    # save message for patient's assigned doctor
    doctor_name = patient.get("doctor_name")
    # try to find doctor_id
    doctor_id = None
    with open(FILES["doctors_csv"], "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("name") == doctor_name:
                doctor_id = row.get("doctor_id")
                break
    ts = datetime.utcnow().isoformat(timespec="seconds")
    with open(FILES["messages_csv"], "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([ts, patient_id, doctor_id or "", message])
    append_json(FILES["messages_json"], {
        "timestamp": ts, "patient_id": patient_id, "doctor_id": doctor_id or "", "message": message
    })
    flash("Message sent to doctor.")
    return redirect(url_for("patient_dashboard"))

# patient history view: show daily records and misc records
@app.route("/patient/history")
@login_required(role="patient")
def patient_history():
    patient_id = session.get("userid")
    patient = load_patient_by_id(patient_id)
    if not patient:
        abort(404)
    daily = load_daily_rows_for_patient(patient_id)
    misc = []
    if os.path.exists(FILES["misc_csv"]):
        with open(FILES["misc_csv"], "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                if r.get("patient_id") == patient_id:
                    misc.append(r)
    return render_template("patient_history.htm", patient=patient, daily=daily, misc=misc)

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.")
    return redirect(url_for("home"))


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(e):
    return render_template("500.html"), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
