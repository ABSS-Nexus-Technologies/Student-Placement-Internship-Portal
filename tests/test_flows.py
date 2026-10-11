import io
from datetime import date, timedelta
from app.models import db, User, Student, Company, Drive, Application, Placement
from app.services.importer import bulk_import_students

def test_role_based_access_control(client, app):
    with app.app_context():
        # Create student user
        stu_user = User(email='test_stu@college.edu', role='student', status='active')
        stu_user.set_password('pass123')
        db.session.add(stu_user)
        db.session.flush()
        student = Student(user_id=stu_user.user_id, name="Test", roll_no="T01", branch="CSE", cgpa=8.0, active_backlogs=0, passing_year=2026)
        db.session.add(student)
        db.session.commit()

    # Login as student
    client.post('/auth/login', data={'email': 'test_stu@college.edu', 'password': 'pass123'}, follow_redirects=True)

    # Attempt to access admin dashboard -> must be 403
    resp_admin = client.get('/admin/dashboard')
    assert resp_admin.status_code == 403

    # Attempt to access company dashboard -> must be 403
    resp_comp = client.get('/company/dashboard')
    assert resp_comp.status_code == 403

    # Access student dashboard -> must be 200
    resp_stu = client.get('/student/dashboard')
    assert resp_stu.status_code == 200


def test_bulk_import_validation(app):
    with app.app_context():
        csv_data = (
            "name,roll_no,email,branch,cgpa,passing_year,active_backlogs,skills\n"
            "Alice Valid,22CS0901,alice@college.edu,CSE,8.5,2026,0,Python\n"
            "Bob HighCGPA,22CS0902,bob@college.edu,CSE,12.5,2026,0,Java\n"  # Invalid CGPA > 10
            "Charlie Dup,22CS0901,charlie@college.edu,CSE,7.5,2026,0,C++\n"  # Duplicate Roll No
            "Dave NegCGPA,22CS0903,dave@college.edu,CSE,-1.0,2026,0,SQL\n"  # Invalid CGPA < 0
        )
        stream = io.StringIO(csv_data)
        res = bulk_import_students(stream, "test_students.csv")

        assert res['success_count'] == 1
        assert res['error_count'] == 3
        errors_str = " ".join([e['error'] for e in res['errors']])
        assert "Invalid CGPA" in errors_str
        assert "Duplicate Roll Number" in errors_str


def test_end_to_end_recruitment_lifecycle(client, app):
    with app.app_context():
        # 1. Create Admin
        admin = User(email='admin@college.edu', role='admin', status='active')
        admin.set_password('Admin@123')
        db.session.add(admin)
        db.session.commit()

    # 2. Company Registration
    comp_reg_resp = client.post('/auth/register/company', data={
        'name': 'Acme Corp',
        'email': 'hr@acme.com',
        'industry': 'Software',
        'website': 'https://acme.com',
        'hr_contact': 'HR John (+91 9999999999)',
        'password': 'AcmePassword@123',
        'confirm_password': 'AcmePassword@123'
    }, follow_redirects=True)
    assert comp_reg_resp.status_code == 200

    # Verify company user is created with pending status
    with app.app_context():
        cuser = User.query.filter_by(email='hr@acme.com').first()
        assert cuser is not None
        assert cuser.status == 'pending'

    # Try login before admin approval -> should be blocked with pending message
    login_attempt = client.post('/auth/login', data={'email': 'hr@acme.com', 'password': 'AcmePassword@123'}, follow_redirects=True)
    assert b"Admin/TPO approval" in login_attempt.data

    # 3. Admin logs in and approves company
    client.post('/auth/login', data={'email': 'admin@college.edu', 'password': 'Admin@123'}, follow_redirects=True)
    with app.app_context():
        comp_id = Company.query.filter_by(name='Acme Corp').first().company_id
    client.post(f'/admin/company/{comp_id}/approve', follow_redirects=True)

    with app.app_context():
        assert Company.query.get(comp_id).approval_status == 'approved'
        assert User.query.filter_by(email='hr@acme.com').first().status == 'active'

    client.get('/auth/logout', follow_redirects=True)

    # 4. Student Registration
    stu_reg_resp = client.post('/auth/register/student', data={
        'name': 'Kavita Roy',
        'roll_no': '22CS0888',
        'email': 'kavita@college.edu',
        'branch': 'CSE',
        'cgpa': 9.1,
        'active_backlogs': 0,
        'passing_year': 2026,
        'skills': 'Python, Flask, Docker',
        'password': 'Student@123',
        'confirm_password': 'Student@123'
    }, follow_redirects=True)
    assert stu_reg_resp.status_code == 200

    # 5. Approved Company logs in and posts a campus drive
    client.post('/auth/login', data={'email': 'hr@acme.com', 'password': 'AcmePassword@123'}, follow_redirects=True)
    today = date.today()
    drive_post_resp = client.post('/company/drive/create', data={
        'title': 'Junior Software Engineer',
        'type': 'placement',
        'package_or_stipend': 14.0,
        'min_cgpa': 8.0,
        'max_backlogs': 0,
        'allowed_branches': ['CSE', 'IT'],
        'batch_year': 2026,
        'last_date': (today + timedelta(days=20)).strftime('%Y-%m-%d'),
        'description': 'Backend Python developer position',
        'status': 'active'
    }, follow_redirects=True)
    assert drive_post_resp.status_code == 200

    with app.app_context():
        drive = Drive.query.filter_by(title='Junior Software Engineer').first()
        assert drive is not None
        drive_id = drive.drive_id

    client.get('/auth/logout', follow_redirects=True)

    # 6. Set student resume path and login
    with app.app_context():
        stu = Student.query.filter_by(roll_no='22CS0888').first()
        stu.resume_path = 'dummy_resume.pdf'
        db.session.commit()

    client.post('/auth/login', data={'email': 'kavita@college.edu', 'password': 'Student@123'}, follow_redirects=True)

    apply_resp = client.post(f'/student/apply/{drive_id}', follow_redirects=True)
    assert apply_resp.status_code == 200
    assert b"Successfully applied" in apply_resp.data

    with app.app_context():
        app_record = Application.query.filter_by(drive_id=drive_id).first()
        assert app_record is not None
        assert app_record.status == 'applied'
        app_id = app_record.application_id

    client.get('/auth/logout', follow_redirects=True)

    # 7. Recruiter logs in, shortlists, and marks final selection
    client.post('/auth/login', data={'email': 'hr@acme.com', 'password': 'AcmePassword@123'}, follow_redirects=True)
    shortlist_resp = client.post(f'/company/application/{app_id}/status', data={'status': 'shortlisted'}, follow_redirects=True)
    assert shortlist_resp.status_code == 200

    select_resp = client.post(f'/company/application/{app_id}/select', data={
        'package': 14.0,
        'offer_date': today.strftime('%Y-%m-%d'),
        'offer_status': 'accepted'
    }, follow_redirects=True)
    assert select_resp.status_code == 200

    with app.app_context():
        updated_app = Application.query.get(app_id)
        assert updated_app.status == 'selected'
        assert updated_app.placement is not None
        assert updated_app.placement.package == 14.0

    client.get('/auth/logout', follow_redirects=True)

    # 8. Admin logs in and generates Excel report
    client.post('/auth/login', data={'email': 'admin@college.edu', 'password': 'Admin@123'}, follow_redirects=True)
    report_resp = client.post('/admin/reports', data={
        'report_type': 'student_wise',
        'batch_year': 2026,
        'branch': '',
        'company_id': 0
    })
    assert report_resp.status_code == 200
    assert "spreadsheetml" in report_resp.content_type
