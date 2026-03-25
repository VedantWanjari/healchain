# HealChain 🩺📋

**HealChain** is a comprehensive healthcare data management platform that enables secure doctor-patient collaboration, dynamic health monitoring, and centralized medical record management. Built with Flask and responsive web design, it provides a practical solution for healthcare providers to track patient health metrics and communicate effectively.

---

## 📌 Current Status

This is an **active development project** currently in **MVP (Minimum Viable Product)** phase. The platform is fully functional for demo and testing purposes with core features implemented.

🚨 **Important Disclaimer**
- HealChain is **NOT** a production-ready healthcare platform
- It is **NOT** suitable for storing real patient medical data
- Use only with **test/dummy data** for learning and demonstration
- For real healthcare applications, use HIPAA-compliant systems
- This project is intended for **educational and development purposes only**

---

## ✨ Current Features

### 👥 User Management
- ✅ **Doctor Registration & Login** - Complete registration with clinic details, license info, and credentials
- ✅ **Patient Registration & Login** - Doctor-assigned patient accounts with automatic ID generation
- ✅ **Role-Based Access Control** - Separate dashboards for doctors and patients
- ✅ **Password Security** - Hashed passwords using Werkzeug security

### 📊 Doctor Features
- ✅ **Patient Management** - View assigned patients, manage patient list
- ✅ **Dynamic Requirements** - Create custom health metrics per patient (e.g., blood sugar, weight, BP)
- ✅ **Patient Data Tracking** - View all recorded patient health data with timestamps
- ✅ **Data Export** - Download patient records as CSV files
- ✅ **ZIP Bundles** - Export complete patient data packages (CSV + uploaded files)
- ✅ **Patient Monitoring** - Track daily health observations and trends
- ✅ **Doctor Assignment** - Reassign patients to other doctors in the system
- ✅ **Patient Messaging** - Receive and read messages from assigned patients

### 🏥 Patient Features
- ✅ **Smart Dashboard** - Tab-based interface for easy navigation
- ✅ **Record Required Data** - Submit doctor-requested health metrics via dynamic forms
- ✅ **Miscellaneous Records** - Log additional observations and upload documents
- ✅ **Doctor Communication** - Send messages to assigned doctor (200 word limit)
- ✅ **Profile Management** - View personal health information
- ✅ **History Tracking** - View all submitted records with dates and times
- ✅ **File Uploads** - Attach documents for required and miscellaneous data

### 🔐 Data Management
- ✅ **Dual Storage** - CSV for tabular data, JSON for structured records
- ✅ **File Upload Support** - Store patient-uploaded documents securely
- ✅ **Dynamic Schema** - Automatically add new health metric columns as needed
- ✅ **Data Organization** - Separate folders for ID proofs, patient photos, and patient files

### 🎨 User Interface
- ✅ **Responsive Design** - Works on desktop, tablet, and mobile (CSS media queries)
- ✅ **Dark Theme** - Modern dark interface with teal accents (#009688)
- ✅ **Intuitive Navigation** - Tab-based dashboards and clear call-to-actions
- ✅ **Real-time Validation** - Client-side form validation and word counters
- ✅ **Error Handling** - User-friendly error messages and alerts

### 📱 Public Pages
- ✅ Home Page - Platform overview
- ✅ About Page - Project information
- ✅ Doctors Directory - Browse registered doctors
- ✅ Monitoring Dashboard - System status overview
- ✅ Contact Page - Get in touch

---

## 📦 Tech Stack

### Backend
- **Framework:** Flask 3.0.0 - Python web framework
- **Server:** Gunicorn (production) / Flask dev server (development)
- **Language:** Python 3.8+
- **Storage:** CSV + JSON files (local filesystem)
- **Security:** Werkzeug (password hashing), session-based authentication

### Frontend
- **HTML5** - Semantic markup
- **CSS3** - Responsive design with media queries
- **Vanilla JavaScript** - No framework dependencies
- **Templating:** Jinja2 (Flask templates)

### Architecture
- **File-Based Storage** - CSV and JSON for data persistence
- **Session-Based Auth** - Flask session management
- **Stateless Routes** - RESTful endpoint design
- **Local File System** - Direct filesystem access for uploads

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/VedantWanjari/healchain.git
cd healchain
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Run the application**
```bash
python healchain/app.py
```

The application will start at `http://localhost:5000`

---

## 🔐 Default Access

### Test Credentials (for demo purposes)

**Example Doctor Account:**
- User ID: `DOC_DEMO_20250325`
- Password: (create one during registration)

**Example Patient Account:**
- User ID: `DOC_DEMO_TESTPAT_20250325`
- Password: (create one during registration)

**To Create New Accounts:**
1. Navigate to `/account` for account creation options
2. Choose Doctor or Patient registration
3. Fill in required details
4. Login with generated credentials

---

## 📁 Project Structure

```
healchain/
├── app.py                 # Main Flask application (1178 lines)
├── templates/             # Jinja2 HTML templates (24 files)
│   ├── home.htm
│   ├── login.htm
│   ├── doctor_dashboard.htm
│   ├── patient_dashboard_v2.htm
│   ├── patient_daily_data.htm
│   ├── manage_requirements.htm
│   └── ... (19 more templates)
├── static/                # Static assets
│   ├── img/              # Images and logos
│   ├── uploads/          # User uploaded files
│   │   ├── photos/
│   │   └── patient_files/
│   └── css/              # (Future: Extract inline CSS)
├── data/                  # Data storage
│   ├── doctors.csv
│   ├── doctors.json
│   ├── patients.csv
│   ├── patients.json
│   ├── daily_data.csv
│   ├── daily_data.json
│   ├── misc_data.csv
│   ├── misc_data.json
│   ├── messages.csv
│   ├── messages.json
│   ├── requirements.json
│   ├── feedback.csv
│   ├── feedback.json
│   └── uploads/          # All user files
└── requirements.txt       # Python dependencies
```

---

## 🔄 Key Workflows

### Doctor Workflow
1. Register as doctor with clinic details
2. Login to doctor dashboard
3. View assigned patients
4. Create custom health metrics (requirements) for each patient
5. Monitor patient-submitted data in real-time
6. Download patient records (CSV or ZIP)
7. Communicate with patients via messaging

### Patient Workflow
1. Register with assigned doctor (or self-register)
2. Login to patient dashboard
3. View doctor-assigned health metrics to track
4. Submit daily health data (blood sugar, weight, etc.)
5. Upload miscellaneous documents
6. Send messages to doctor
7. View historical data and records

---

## 💾 Data Storage

### CSV Format (Tabular Data)
- `doctors.csv` - Doctor profiles and credentials
- `patients.csv` - Patient demographics and doctor assignment
- `daily_data.csv` - Patient health metrics (dynamic columns)
- `misc_data.csv` - Miscellaneous patient records
- `messages.csv` - Doctor-patient communication
- `feedback.csv` - User feedback

### JSON Format (Structured Data)
- `doctors.json` - Doctor records (backup)
- `patients.json` - Patient records (backup)
- `requirements.json` - Health metrics per patient
- `daily_data.json` - Health data records
- `misc_data.json` - Miscellaneous records
- `messages.json` - Message history

### File Uploads
- `/data/uploads/idproof/` - Doctor ID proofs
- `/data/uploads/photos/` - Doctor and patient photos
- `/data/uploads/patient_files/` - Patient document uploads
- `/static/uploads/` - Web-accessible uploads

---

## 🛠️ API Endpoints

### Authentication
- `GET /login` - Login page
- `POST /login` - Process login
- `GET /logout` - Logout

### Registration
- `GET /doctor/register` - Doctor registration form
- `POST /doctor/register` - Create doctor account
- `GET /patient/register` - Patient registration form
- `POST /patient/register` - Create patient account

### Doctor Routes
- `GET /doctor/dashboard` - Doctor dashboard
- `GET /doctor/view` - Select patient to view
- `GET /doctor/patient/<patient_id>` - View patient data
- `GET /doctor/patient/<patient_id>/manage_requirements` - Manage health metrics
- `POST /doctor/patient/<patient_id>/manage_requirements` - Create/update requirements
- `GET /doctor/patient/<patient_id>/assign` - Reassign patient
- `POST /doctor/patient/<patient_id>/download` - Download patient data

### Patient Routes
- `GET /patient/dashboard` - Patient dashboard
- `GET /patient/record_required` - Record health metrics form
- `POST /patient/record_required` - Submit health metrics
- `GET /patient/record_misc` - Record misc data form
- `POST /patient/record_misc` - Submit misc data
- `POST /patient/contact_doctor` - Send message to doctor
- `GET /patient/history` - View health history

### Public Routes
- `GET /` - Home page
- `GET /about` - About page
- `GET /doctors` - Doctor directory
- `GET /monitoring` - Monitoring dashboard
- `GET /contact` - Contact page

---

## 🔐 Security Features

### Implemented ✅
- Password hashing using Werkzeug
- Session-based authentication
- Role-based access control (RBAC)
- File upload validation (secure_filename)
- SQL injection prevention (CSV/JSON - no SQL)

### Not Implemented ⚠️
- CSRF protection (Flask-WTF needed)
- Input validation & sanitization
- Rate limiting
- API authentication (JWT/OAuth)
- HTTPS/SSL enforcement (production)
- Data encryption at rest

---

## 🚧 Known Limitations

1. **File-Based Storage** - Not suitable for large-scale production
   - No database indexing
   - Sequential file reads
   - Poor concurrent access handling

2. **No Input Validation** - Vulnerable to malformed data
   - Frontend only - can be bypassed
   - No backend validation

3. **No Error Handling** - App may crash on unexpected input
   - Missing try-catch blocks
   - No graceful error messages

4. **Security Gaps**
   - Hardcoded secret key (should use .env)
   - No rate limiting
   - No CSRF protection
   - No API authentication

5. **Scalability Issues**
   - CSV files become slow with large datasets
   - No caching layer
   - Single-threaded by default

---

## 🗺️ Roadmap

### Phase 1: Stability (v1.1)
- [ ] Add input validation (marshmallow)
- [ ] Implement comprehensive error handling
- [ ] Add CSRF protection (Flask-WTF)
- [ ] Setup logging system
- [ ] Write unit tests

### Phase 2: Database Migration (v1.2)
- [ ] Migrate from CSV to SQLAlchemy + PostgreSQL
- [ ] Add database indexing
- [ ] Implement transactions
- [ ] Setup database migrations (Alembic)

### Phase 3: Enhancement (v1.3)
- [ ] Add API documentation (Swagger)
- [ ] Implement pagination for data
- [ ] Add advanced search/filtering
- [ ] Setup Docker deployment
- [ ] Add GitHub Actions CI/CD

### Phase 4: Blockchain Integration (v2.0)
- [ ] Integrate Web3.py for blockchain
- [ ] Deploy smart contract for consent
- [ ] Store data hashes on-chain
- [ ] Add immutable audit logs
- [ ] Implement encryption layer

---

## 📊 Project Statistics

| Metric | Value |
|--------|-------|
| Backend Code | 1,178 lines (app.py) |
| HTML Templates | 24 files |
| Total Routes | 30+ endpoints |
| Data Models | 6 CSV + 6 JSON |
| Features | 30+ |
| Tech Dependencies | 4 core (Flask, Werkzeug, etc.) |

---

## ⚠️ Disclaimer & Legal

**IMPORTANT NOTICE:**

This project is a demonstration platform and **NOT**:
- A certified healthcare platform
- HIPAA compliant
- Suitable for real patient data
- Approved by medical regulatory bodies
- A substitute for real healthcare systems

For any real healthcare needs, use only certified, regulated, and compliant healthcare management systems.

---

## 👨‍💻 Author

**Vedant Wanjari**
- GitHub: [@VedantWanjari](https://github.com/VedantWanjari)
- Project: [HealChain Repository](https://github.com/VedantWanjari/healchain)

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Unless otherwise stated, all code in this repository is licensed under the MIT License.

**Important:** Users deploying this code are fully responsible for compliance with all applicable laws and regulations, including HIPAA, FDA requirements, and data protection laws.

---

**Last Updated:** March 25, 2026  
**Version:** 1.0.0 (MVP)  
**Status:** 🟢 Active Development
This repository is maintained as a research prototype and may not be actively updated to comply with future regulatory changes.
