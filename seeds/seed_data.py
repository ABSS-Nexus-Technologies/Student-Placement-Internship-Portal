import os
import sys
from datetime import datetime, date, timedelta, timezone

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.models import db, User, Student, Company, Drive, Application, Round, RoundResult, Placement, Notification, ActivityLog

def generate_minimal_pdf(file_path):
    """Creates a valid, lightweight PDF file for resume demonstration."""
    pdf_content = (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
        b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>/Contents 4 0 R>>endobj\n"
        b"4 0 obj<</Length 51>>stream\n"
        b"BT /F1 18 Tf 50 700 Td (Smart TPO Verified Resume - Sample Document) Tj ET\n"
        b"endstream\n"
        b"endobj\n"
        b"xref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000216 00000 n \n"
        b"trailer<</Size 5/Root 1 0 R>>\nstartxref\n318\n%%EOF\n"
    )
    with open(file_path, "wb") as f:
        f.write(pdf_content)

def seed_database():
    app = create_app()
    with app.app_context():
        print("Cleaning up old tables and creating fresh schema...")
        db.drop_all()
        db.create_all()

        upload_dir = app.config['UPLOAD_FOLDER']
        os.makedirs(upload_dir, exist_ok=True)
        sample_pdf_name = "sample_student_resume.pdf"
        generate_minimal_pdf(os.path.join(upload_dir, sample_pdf_name))

        # -------------------------------------------------------------
        # 1. ADMIN USER
        # -------------------------------------------------------------
        print("Creating Admin account...")
        admin_user = User(
            email='admin@tpo.college.edu',
            role='admin',
            status='active'
        )
        admin_user.set_password('Admin@123')
        db.session.add(admin_user)
        db.session.flush()

        log_admin = ActivityLog(user_id=admin_user.user_id, action="Initialized Training & Placement Office Database")
        db.session.add(log_admin)

        # -------------------------------------------------------------
        # 2. SAMPLE COMPANIES (3 Approved + 1 Pending Approval)
        # -------------------------------------------------------------
        print("Creating Sample Companies...")
        companies_data = [
            {
                'email': 'hr@google.com',
                'password': 'Company@123',
                'name': 'Google India Pvt. Ltd.',
                'industry': 'Software & Cloud Services',
                'website': 'https://careers.google.com',
                'hr_contact': 'Sundar HR (+91 9876500001)',
                'status': 'approved'
            },
            {
                'email': 'hr@microsoft.com',
                'password': 'Company@123',
                'name': 'Microsoft India Development Center',
                'industry': 'Enterprise Software & AI Systems',
                'website': 'https://careers.microsoft.com',
                'hr_contact': 'Satya HR (+91 9876500002)',
                'status': 'approved'
            },
            {
                'email': 'hr@infosys.com',
                'password': 'Company@123',
                'name': 'Infosys Technologies Ltd.',
                'industry': 'IT Consulting & Digital Services',
                'website': 'https://www.infosys.com/careers',
                'hr_contact': 'Narayana HR (+91 9876500003)',
                'status': 'approved'
            },
            {
                'email': 'hr@innovate-tech.io',
                'password': 'Company@123',
                'name': 'Innovate Technologies Labs',
                'industry': 'Fintech & Web3',
                'website': 'https://innovate-tech.io',
                'hr_contact': 'Pooja Recruiter (+91 9876500004)',
                'status': 'pending'  # Demonstrates admin pending approval flow!
            }
        ]

        created_companies = {}
        for cdata in companies_data:
            cuser = User(
                email=cdata['email'],
                role='company',
                status='active' if cdata['status'] == 'approved' else 'pending'
            )
            cuser.set_password(cdata['password'])
            db.session.add(cuser)
            db.session.flush()

            comp = Company(
                user_id=cuser.user_id,
                name=cdata['name'],
                industry=cdata['industry'],
                website=cdata['website'],
                hr_contact=cdata['hr_contact'],
                approval_status=cdata['status']
            )
            db.session.add(comp)
            db.session.flush()
            created_companies[cdata['name']] = comp

        # -------------------------------------------------------------
        # 3. SAMPLE STUDENTS (30 Students Across Branches)
        # -------------------------------------------------------------
        print("Creating 30 Sample Students across branches...")
        students_info = [
            # CSE Students (10)
            ("Aarav Sharma", "22CS0101", "cs01@student.college.edu", "CSE", 9.45, 0, "Python, Flask, C++, Data Structures, Docker"),
            ("Ananya Verma", "22CS0102", "cs02@student.college.edu", "CSE", 8.85, 0, "React, Node.js, PostgreSQL, TypeScript"),
            ("Rohan Patel", "22CS0103", "cs03@student.college.edu", "CSE", 8.20, 0, "Java, Spring Boot, MySQL, Microservices"),
            ("Priya Iyer", "22CS0104", "cs04@student.college.edu", "CSE", 9.15, 0, "Machine Learning, Python, PyTorch, SQL"),
            ("Vikram Singh", "22CS0105", "cs05@student.college.edu", "CSE", 7.65, 0, "Go, Kubernetes, Cloud Computing, Linux"),
            ("Sneha Rao", "22CS0106", "cs06@student.college.edu", "CSE", 8.50, 0, "Full Stack Web, JavaScript, MongoDB, Express"),
            ("Aditya Nair", "22CS0107", "cs07@student.college.edu", "CSE", 6.80, 1, "C++, Java, OOP, DBMS"),
            ("Pooja Gupta", "22CS0108", "cs08@student.college.edu", "CSE", 7.95, 0, "Flutter, Android, Mobile Dev, Dart"),
            ("Rahul Joshi", "22CS0109", "cs09@student.college.edu", "CSE", 6.40, 2, "Python, HTML/CSS, Git"),
            ("Neha Kulkarni", "22CS0110", "cs10@student.college.edu", "CSE", 9.75, 0, "Distributed Systems, Algorithms, Rust, C++"),

            # IT Students (8)
            ("Kavya Pillai", "22IT0201", "it01@student.college.edu", "IT", 9.20, 0, "Cloud Engineering, AWS, Python, Terraform"),
            ("Karan Malhotra", "22IT0202", "it02@student.college.edu", "IT", 8.40, 0, "Network Security, Ethical Hacking, Linux, Python"),
            ("Meera Menon", "22IT0203", "it03@student.college.edu", "IT", 8.10, 0, "Data Analytics, Tableau, SQL, PowerBI"),
            ("Siddharth Deshmukh", "22IT0204", "it04@student.college.edu", "IT", 7.70, 0, "Web Development, Django, PostgreSQL, Git"),
            ("Riya Sen", "22IT0205", "it05@student.college.edu", "IT", 7.15, 1, "Java, OOP, Database Systems"),
            ("Arjun Mehta", "22IT0206", "it06@student.college.edu", "IT", 8.90, 0, "DevOps, CI/CD, Jenkins, Docker, Bash"),
            ("Divya Choudhary", "22IT0207", "it07@student.college.edu", "IT", 6.95, 0, "Front-end, Vue.js, Tailwind CSS"),
            ("Manish Tiwari", "22IT0208", "it08@student.college.edu", "IT", 7.50, 0, "Python, Automation, Selenium, API Testing"),

            # ECE Students (6)
            ("Nikhil Reddy", "22EC0301", "ec01@student.college.edu", "ECE", 8.60, 0, "Embedded C, Microcontrollers, IoT, Python"),
            ("Tanvi Shah", "22EC0302", "ec02@student.college.edu", "ECE", 8.25, 0, "VLSI Design, Verilog, Digital Electronics"),
            ("Varun Bhatt", "22EC0303", "ec03@student.college.edu", "ECE", 7.80, 0, "Robotics, Arduino, C++, Signal Processing"),
            ("Shreya Mukherjee", "22EC0304", "ec04@student.college.edu", "ECE", 9.05, 0, "Signal Processing, MATLAB, Python, Wireless Comms"),
            ("Abhishek Das", "22EC0305", "ec05@student.college.edu", "ECE", 6.85, 1, "PCB Design, Hardware Debugging, C"),
            ("Ishita Banerjee", "22EC0306", "ec06@student.college.edu", "ECE", 7.40, 0, "Telecommunications, RF Design, Networking"),

            # EEE Students (2)
            ("Gaurav Mishra", "22EE0401", "ee01@student.college.edu", "EEE", 8.15, 0, "Power Systems, MATLAB, Electrical Drives"),
            ("Anjali Saxena", "22EE0402", "ee02@student.college.edu", "EEE", 7.30, 0, "Control Systems, Renewable Energy, Python"),

            # MECH Students (2)
            ("Harsh Vardhan", "22ME0501", "me01@student.college.edu", "MECH", 7.90, 0, "AutoCAD, SolidWorks, ANSYS, Finite Element Analysis"),
            ("Bhavna Yadav", "22ME0502", "me02@student.college.edu", "MECH", 7.20, 0, "Thermal Engineering, Fluid Mechanics, Manufacturing"),

            # CIVIL Students (2)
            ("Deepak Chawla", "22CV0601", "cv01@student.college.edu", "CIVIL", 7.60, 0, "Structural Analysis, AutoCAD Civil 3D, Surveying"),
            ("Swati Pandey", "22CV0602", "cv02@student.college.edu", "CIVIL", 8.00, 0, "Geotechnical Engineering, Project Management")
        ]

        created_students = []
        for name, roll, email, branch, cgpa, backlogs, skills in students_info:
            suser = User(
                email=email,
                role='student',
                status='active'
            )
            # Student password set to Roll Number
            suser.set_password(roll)
            db.session.add(suser)
            db.session.flush()

            student = Student(
                user_id=suser.user_id,
                name=name,
                roll_no=roll,
                branch=branch,
                cgpa=cgpa,
                active_backlogs=backlogs,
                passing_year=2026,
                skills=skills,
                resume_path=sample_pdf_name
            )
            db.session.add(student)
            db.session.flush()
            created_students.append(student)

        # -------------------------------------------------------------
        # 4. SAMPLE DRIVES (5 Drives)
        # -------------------------------------------------------------
        print("Creating 5 Sample Campus Drives...")
        google = created_companies['Google India Pvt. Ltd.']
        microsoft = created_companies['Microsoft India Development Center']
        infosys = created_companies['Infosys Technologies Ltd.']

        today = date.today()

        drives_data = [
            {
                'company_id': google.company_id,
                'title': 'Software Development Engineer (SDE 1)',
                'type': 'placement',
                'package_or_stipend': 32.0,  # 32 LPA
                'min_cgpa': 8.0,
                'max_backlogs': 0,
                'allowed_branches': 'CSE,IT',
                'batch_year': 2026,
                'last_date': today + timedelta(days=30),
                'description': 'Building next-generation distributed systems, machine learning pipelines, and cloud computing infrastructure at Google scale.',
                'status': 'active'
            },
            {
                'company_id': microsoft.company_id,
                'title': 'Cloud & AI Solutions Engineer',
                'type': 'placement',
                'package_or_stipend': 24.5,  # 24.5 LPA
                'min_cgpa': 7.5,
                'max_backlogs': 0,
                'allowed_branches': 'CSE,IT,ECE',
                'batch_year': 2026,
                'last_date': today + timedelta(days=25),
                'description': 'Deliver enterprise cloud architecture, generative AI copilots, and intelligent edge solutions on Microsoft Azure.',
                'status': 'active'
            },
            {
                'company_id': microsoft.company_id,
                'title': 'Summer Software Engineering Intern',
                'type': 'internship',
                'package_or_stipend': 1.25,  # 1.25L monthly stipend
                'min_cgpa': 7.0,
                'max_backlogs': 0,
                'allowed_branches': 'ALL',
                'batch_year': 2026,
                'last_date': today + timedelta(days=15),
                'description': '8-week intensive summer technology internship with real-world project mentorship, leading to Pre-Placement Offers (PPOs).',
                'status': 'active'
            },
            {
                'company_id': infosys.company_id,
                'title': 'Specialist Programmer (SP)',
                'type': 'placement',
                'package_or_stipend': 9.5,  # 9.5 LPA
                'min_cgpa': 6.5,
                'max_backlogs': 1,
                'allowed_branches': 'ALL',
                'batch_year': 2026,
                'last_date': today + timedelta(days=20),
                'description': 'Elite programming role focused on complex algorithm optimization, full-stack microservices, and client digital transformation.',
                'status': 'active'
            },
            {
                'company_id': infosys.company_id,
                'title': 'Digital Systems Engineer',
                'type': 'placement',
                'package_or_stipend': 4.5,  # 4.5 LPA
                'min_cgpa': 6.0,
                'max_backlogs': 2,
                'allowed_branches': 'ALL',
                'batch_year': 2026,
                'last_date': today + timedelta(days=10),
                'description': 'Core technology role spanning enterprise software maintenance, QA testing, DevOps pipelines, and database management.',
                'status': 'active'
            }
        ]

        created_drives = []
        for ddata in drives_data:
            drive = Drive(**ddata)
            db.session.add(drive)
            db.session.flush()
            created_drives.append(drive)

        # -------------------------------------------------------------
        # 5. ROUNDS FOR DRIVES
        # -------------------------------------------------------------
        print("Scheduling Assessment Rounds...")
        # Rounds for Google SDE
        g_round1 = Round(drive_id=created_drives[0].drive_id, round_name="Online Coding Assessment (LeetCode Hard)", round_date=datetime.now(timezone.utc) + timedelta(days=5), mode="online")
        g_round2 = Round(drive_id=created_drives[0].drive_id, round_name="Technical Problem Solving & DSA Interview", round_date=datetime.now(timezone.utc) + timedelta(days=8), mode="online")
        g_round3 = Round(drive_id=created_drives[0].drive_id, round_name="Googliness & Leadership Fitment", round_date=datetime.now(timezone.utc) + timedelta(days=10), mode="online")
        db.session.add_all([g_round1, g_round2, g_round3])

        # Rounds for Microsoft Cloud
        m_round1 = Round(drive_id=created_drives[1].drive_id, round_name="Online Technical & Cognitive Test", round_date=datetime.now(timezone.utc) + timedelta(days=4), mode="online")
        m_round2 = Round(drive_id=created_drives[1].drive_id, round_name="System Architecture & Coding Round", round_date=datetime.now(timezone.utc) + timedelta(days=7), mode="online")
        m_round3 = Round(drive_id=created_drives[1].drive_id, round_name="Executive Leadership & HR Round", round_date=datetime.now(timezone.utc) + timedelta(days=9), mode="offline")
        db.session.add_all([m_round1, m_round2, m_round3])

        # Rounds for Infosys SP
        i_round1 = Round(drive_id=created_drives[3].drive_id, round_name="HackWithInfy Coding Round", round_date=datetime.now(timezone.utc) + timedelta(days=3), mode="online")
        i_round2 = Round(drive_id=created_drives[3].drive_id, round_name="Technical Interview & Project Defense", round_date=datetime.now(timezone.utc) + timedelta(days=6), mode="offline")
        db.session.add_all([i_round1, i_round2])

        db.session.flush()

        # -------------------------------------------------------------
        # 6. APPLICATIONS, EVALUATIONS & FINAL PLACEMENTS
        # -------------------------------------------------------------
        print("Submitting Applications, Round Results, and Placements...")

        # Let's apply top CSE & IT students to Google SDE
        # Eligible students: CGPA >= 8.0, Branch CSE/IT, Backlogs 0
        google_drive = created_drives[0]
        google_applicants = [s for s in created_students if s.branch in ['CSE', 'IT'] and s.cgpa >= 8.0 and s.active_backlogs == 0]

        for idx, student in enumerate(google_applicants):
            app = Application(
                drive_id=google_drive.drive_id,
                student_id=student.student_id,
                applied_on=datetime.now(timezone.utc) - timedelta(days=2),
                current_round="Googliness & Leadership Fitment" if idx < 3 else "Online Coding Assessment",
                status="selected" if idx < 2 else ("shortlisted" if idx < 4 else "applied")
            )
            db.session.add(app)
            db.session.flush()

            # Record round results
            if idx < 4:
                rr1 = RoundResult(application_id=app.application_id, round_id=g_round1.round_id, result="cleared", remarks="Scored 100% on algorithm problems")
                db.session.add(rr1)
            if idx < 3:
                rr2 = RoundResult(application_id=app.application_id, round_id=g_round2.round_id, result="cleared", remarks="Strong system design and analytical skills")
                db.session.add(rr2)

            # Placements for top 2
            if idx < 2:
                rr3 = RoundResult(application_id=app.application_id, round_id=g_round3.round_id, result="cleared", remarks="Excellent fit for Google values")
                db.session.add(rr3)
                placement = Placement(
                    application_id=app.application_id,
                    offer_date=today - timedelta(days=1),
                    package=32.0,
                    offer_status="accepted"
                )
                db.session.add(placement)
                # Notification
                notif = Notification(
                    user_id=student.user_id,
                    message="🎉 Congratulations! You have received an official placement offer from Google India (32.0 LPA)!",
                    sent_on=datetime.now(timezone.utc)
                )
                db.session.add(notif)

        # Microsoft Applications
        ms_drive = created_drives[1]
        ms_applicants = [s for s in created_students if s.branch in ['CSE', 'IT', 'ECE'] and s.cgpa >= 7.5 and s.active_backlogs == 0]

        for idx, student in enumerate(ms_applicants[:6]):
            # Skip if already placed at Google
            if student.is_placed:
                continue

            app = Application(
                drive_id=ms_drive.drive_id,
                student_id=student.student_id,
                applied_on=datetime.now(timezone.utc) - timedelta(days=3),
                current_round="System Architecture & Coding Round",
                status="selected" if idx in [1, 2] else "shortlisted"
            )
            db.session.add(app)
            db.session.flush()

            rr1 = RoundResult(application_id=app.application_id, round_id=m_round1.round_id, result="cleared", remarks="Cleared online round")
            db.session.add(rr1)

            if idx in [1, 2]:
                rr2 = RoundResult(application_id=app.application_id, round_id=m_round2.round_id, result="cleared", remarks="Passed technical interview")
                rr3 = RoundResult(application_id=app.application_id, round_id=m_round3.round_id, result="cleared", remarks="Recommended for Cloud AI role")
                db.session.add_all([rr2, rr3])

                placement = Placement(
                    application_id=app.application_id,
                    offer_date=today,
                    package=24.5,
                    offer_status="offered"
                )
                db.session.add(placement)
                notif = Notification(
                    user_id=student.user_id,
                    message="🎉 Congratulations! You have received an offer from Microsoft India (24.5 LPA)!",
                    sent_on=datetime.now(timezone.utc)
                )
                db.session.add(notif)

        # Infosys SP Applications
        infy_drive = created_drives[3]
        infy_applicants = [s for s in created_students if s.cgpa >= 6.5 and s.active_backlogs <= 1]

        for idx, student in enumerate(infy_applicants[:8]):
            if student.is_placed:
                continue

            app = Application(
                drive_id=infy_drive.drive_id,
                student_id=student.student_id,
                applied_on=datetime.now(timezone.utc) - timedelta(days=1),
                current_round="Technical Interview" if idx < 3 else "Applied",
                status="selected" if idx in [3, 4] else "shortlisted"
            )
            db.session.add(app)
            db.session.flush()

            if idx in [3, 4]:
                placement = Placement(
                    application_id=app.application_id,
                    offer_date=today,
                    package=9.5,
                    offer_status="accepted"
                )
                db.session.add(placement)

        # Activity Logs
        db.session.add(ActivityLog(user_id=admin_user.user_id, action="Approved company accreditation for Google, Microsoft, and Infosys"))
        db.session.add(ActivityLog(user_id=google.user_id, action="Google published campus drive 'Software Development Engineer (SDE 1)'"))
        db.session.add(ActivityLog(user_id=microsoft.user_id, action="Microsoft published campus drive 'Cloud & AI Solutions Engineer'"))

        db.session.commit()
        print("\n" + "="*70)
        print("SEEDING COMPLETED SUCCESSFULLY!")
        print("="*70)
        print("Demo Credentials:")
        print("1. Admin:   Email: admin@tpo.college.edu    | Password: Admin@123")
        print("2. Company: Email: hr@google.com            | Password: Company@123")
        print("            Email: hr@microsoft.com         | Password: Company@123")
        print("            Email: hr@infosys.com           | Password: Company@123")
        print("   (Pending): hr@innovate-tech.io          | Password: Company@123")
        print("3. Student: Email: cs01@student.college.edu | Password: 22CS0101")
        print("            Email: cs02@student.college.edu | Password: 22CS0102")
        print("            Email: it01@student.college.edu | Password: 22IT0201")
        print("            (Each student's password is their Roll Number)")
        print("="*70 + "\n")

if __name__ == '__main__':
    seed_database()
