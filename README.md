# Smart Student Placement & Internship Portal

An enterprise-grade, automated web platform built for a college **Training & Placement Office (TPO)**. The system eliminates manual spreadsheet chaos and unorganized WhatsApp-based notices by automating student registrations, recruiter accreditations, strict multi-factor eligibility verification, round evaluations, in-portal & email notifications, live executive analytics, and styled Excel report downloads.

---

## 🚀 Key Features & Highlights

### 1. Role-Based Access Control (RBAC)
- **Student Portal:** Verified self-registration, profile management, PDF resume upload/preview, **automated eligibility matching** (students see only eligible drives, with diagnostic reasons for ineligible ones), 1-click application submission, and round-by-round interview tracking.
- **Company / Recruiter Portal:** Corporate onboarding (requires Admin/TPO approval before login is activated), drive posting (placement & internship with CGPA, backlog, and branch criteria), applicant shortlisting/rejection, round scheduling (Aptitude, Technical, HR), and final offer extension.
- **Admin / TPO Portal:** Accreditation approval/rejection for recruiters and students, drive management, candidate pipeline monitoring, bulk student Excel/CSV import with validation, system-wide broadcast announcements, live Chart.js analytics, and formatted multi-format Excel downloads.

### 2. Standalone Eligibility Engine (`app/services/eligibility.py`)
A unit-tested evaluation module enforcing 6 institutional rules:
1. **CGPA Threshold:** Student CGPA $\ge$ Drive minimum CGPA.
2. **Backlog Ceiling:** Student active backlogs $\le$ Drive maximum allowed backlogs.
3. **Branch Allocation:** Student branch $\in$ Drive allowed branches (or `ALL`).
4. **Batch Year Matching:** Student passing year $=$ Drive target batch year.
5. **Application Deadline:** Drive last date has not expired.
6. **TPO Placement Policy:** Checks if the student is already placed; enforces dream company salary multiplier policies if re-applying is enabled.

### 3. Styled Excel Reports (`app/services/reports.py`)
Generates production-grade `.xlsx` files using `openpyxl` & `pandas`:
- **Report Formats:** Student-Wise, Company-Wise, Branch-Wise, and Year-Wise.
- **Executive Summary Sheet:** Embedded KPI dashboard showing Total Registered, Total Placed, Placement %, Highest LPA, Average LPA, Median LPA, and Applied Filter Parameters.
- **Styling:** Navy blue header fill (`#1E3A8A`), bold white font, thin borders, auto-calculated column widths, and frozen top header panes.

### 4. Bulk Student Importer (`app/services/importer.py`)
- Accepts `.xlsx`, `.xls`, and `.csv` files.
- Automatically rejects duplicate roll numbers and emails (against both existing database and within the file).
- Rejects any row with CGPA outside `[0.00, 10.00]`.
- Displays an interactive, per-row validation error table.

### 5. Automated Alerts & Notifications (`app/services/notification_service.py`)
- Dispatches in-portal notification alerts and emails (via `Flask-Mail` with console fallback).
- Triggered on new eligible drive publication, round scheduling, stage clearance/elimination, and offer letters.

---

## 🛠️ Technology Stack

| Component | Technology |
|---|---|
| **Backend Framework** | Python 3.10+ / Flask |
| **Authentication & RBAC** | Flask-Login, Werkzeug Security (scrypt/pbkdf2 hashing) |
| **Database & ORM** | Flask-SQLAlchemy (SQLite default, switchable via `DATABASE_URL` to PostgreSQL/MySQL) |
| **Security & Forms** | Flask-WTF, WTForms, CSRF Protection |
| **Frontend UI** | HTML5, Vanilla CSS Design System, Bootstrap 5, Bootstrap Icons |
| **Visual Analytics** | Chart.js (Branch Placements & Monthly Trends) |
| **Excel Engine** | pandas, openpyxl |
| **Email Service** | Flask-Mail (SMTP with robust console logging fallback) |
| **Test Suite** | pytest (19 unit & integration tests) |

---

## 📂 Project Directory Structure

```
Smart Student Placement & Internship Portal/
├── app/
│   ├── __init__.py                 # Application factory, extensions & error handlers
│   ├── config.py                   # Centralized configuration & environment variables
│   ├── models.py                   # Database schemas with foreign keys and relationships
│   ├── blueprints/
│   │   ├── auth/                   # Authentication (login, registration, logout)
│   │   ├── student/                # Student dashboard, profile, eligible drives, apply
│   │   ├── company/                # Recruiter drives, applicants, rounds, selections
│   │   ├── admin/                  # Admin KPIs, approvals, bulk import, reports
│   │   └── main/                   # Public landing page
│   ├── services/
│   │   ├── eligibility.py          # Standalone student eligibility engine
│   │   ├── reports.py              # Formatted openpyxl Excel reports generator
│   │   ├── importer.py             # CSV/Excel bulk student importer & validator
│   │   └── notification_service.py # In-portal alerts and email dispatcher
│   ├── static/
│   │   ├── css/style.css           # Custom design system with variables & glassmorphism
│   │   └── js/main.js              # Sidebar toggle, dynamic alerts, confirmations
│   ├── templates/                  # Jinja2 templates per blueprint + base.html
│   └── uploads/resumes/            # PDF resume storage
├── seeds/
│   └── seed_data.py                # Database seeder (1 admin, 4 companies, 30 students, 5 drives)
├── tests/
│   ├── conftest.py                 # Pytest fixtures and in-memory test database
│   ├── test_eligibility.py         # Unit tests for eligibility criteria
│   ├── test_reports.py             # Unit tests for KPI calculations and Excel formatting
│   └── test_flows.py               # End-to-end recruitment lifecycle and RBAC tests
├── requirements.txt
├── run.py                          # Application entry point
└── README.md
```

---

## ⚡ Installation & Quick Start

### 1. Clone & Set Up Virtual Environment
```bash
cd "Smart Student Placement & Internship Portal"
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Initialize & Seed Database
Populates 1 TPO Admin, 4 sample companies, 30 students across branches, 5 campus drives, evaluation rounds, and placements:
```bash
python seeds/seed_data.py
```

### 4. Run the Application
```bash
python run.py
```
The application will start on: **`http://127.0.0.1:5001/`**

---

## 🔑 Demo Login Credentials

### 1. TPO Admin
- **Email:** `admin@tpo.college.edu`
- **Password:** `Admin@123`
- *Access:* Dashboard KPIs, Company Approvals, Student Directory, Bulk Importer, Broadcast Alerts, Styled Excel Reports.

### 2. Recruiting Companies (Approved)
- **Google India:** `hr@google.com` / `Company@123`
- **Microsoft India:** `hr@microsoft.com` / `Company@123`
- **Infosys Technologies:** `hr@infosys.com` / `Company@123`
- *Access:* Manage Drives, Review Eligible Applicants, Schedule Rounds, Clear/Reject Candidates, Confirm Final Offers.

*(Pending Company to test Approval flow: `hr@innovate-tech.io` / `Company@123`)*

### 3. Students
- **CSE Top Student:** `cs01@student.college.edu` / `22CS0101` (CGPA 9.45, Placed at Google 32 LPA)
- **IT Student:** `it01@student.college.edu` / `22IT0201` (CGPA 9.20, Eligible for all Tech Drives)
- **ECE Student:** `ec01@student.college.edu` / `22EC0301` (CGPA 8.60)
- *(Note: Each sample student's password is their Roll Number in uppercase, e.g., `22CS0102`)*

---

## 🧪 Running Unit & Integration Tests

Run the full automated test suite covering eligibility logic, openpyxl workbook creation, role isolation, and complete recruitment flow:
```bash
source .venv/bin/activate
PYTHONPATH=. pytest -v
```
**Results:** `19 passed in ~1.1s` (100% pass rate).

---

## 📊 End-to-End User Flow Walkthrough

1. **Student Registration:** A student registers at `/auth/register/student` with branch, CGPA, backlogs, and PDF resume.
2. **Company Registration & Approval:** A recruiter registers at `/auth/register/company`. Their account is set to `pending`. Admin logs in and approves the company from `/admin/companies`.
3. **Posting Drives:** The recruiter logs in and creates a drive specifying minimum CGPA, backlog limit, batch year, and eligible branches. The notification service automatically alerts all eligible students.
4. **1-Click Application:** The student views their personalized `/student/drives` list. The eligibility engine verifies credentials in real time. The student applies with one click.
5. **Interview Rounds & Clearance:** The recruiter schedules rounds (Aptitude, Technical, HR) at `/company/drive/<id>/rounds` and records student clearance results.
6. **Selection & Offer:** The recruiter records the final package and offer date. The student receives an in-portal alert and congratulatory email.
7. **Excel Export:** The TPO Admin visits `/admin/reports`, filters by batch or branch, and downloads the formatted `.xlsx` report with executive KPI summaries.
