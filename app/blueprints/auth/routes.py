import os
import uuid
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from urllib.parse import urlparse

from app.models import db, User, Student, Company, ActivityLog
from app.blueprints.auth.forms import LoginForm, StudentRegisterForm, CompanyRegisterForm

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin():
            return redirect(url_for('admin.dashboard'))
        elif current_user.is_company():
            return redirect(url_for('company.dashboard'))
        elif current_user.is_student():
            return redirect(url_for('student.dashboard'))
        return redirect(url_for('main.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid email or password. Please try again.', 'danger')
            return render_template('auth/login.html', form=form)

        # Check approval status
        if user.status == 'pending':
            if user.role == 'company':
                flash('Your company registration is awaiting Admin/TPO approval before you can sign in. You will be notified once reviewed.', 'warning')
            else:
                flash('Your account is currently pending administrative verification.', 'warning')
            return render_template('auth/login.html', form=form)

        if user.status == 'rejected':
            flash('Your account has been deactivated or rejected by the TPO administrator.', 'danger')
            return render_template('auth/login.html', form=form)

        login_user(user, remember=form.remember_me.data)
        
        # Log sign in activity
        log = ActivityLog(user_id=user.user_id, action=f"User {user.email} signed in ({user.role})")
        db.session.add(log)
        db.session.commit()

        flash(f'Welcome back! Signed in as {user.role.title()}.', 'success')
        
        # Safe next URL redirection
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            if user.is_admin():
                next_page = url_for('admin.dashboard')
            elif user.is_company():
                next_page = url_for('company.dashboard')
            else:
                next_page = url_for('student.dashboard')
        return redirect(next_page)

    return render_template('auth/login.html', form=form)


@auth_bp.route('/register/student', methods=['GET', 'POST'])
def register_student():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = StudentRegisterForm()
    if form.validate_on_submit():
        # Handle resume upload if supplied
        resume_filename = None
        if form.resume.data:
            file = form.resume.data
            safe_name = secure_filename(file.filename)
            unique_name = f"{uuid.uuid4().hex[:10]}_{form.roll_no.data.strip().upper()}_{safe_name}"
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_name)
            file.save(file_path)
            resume_filename = unique_name

        # Create user
        user = User(
            email=form.email.data.strip().lower(),
            role='student',
            status='active'
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()

        # Create student profile
        student = Student(
            user_id=user.user_id,
            name=form.name.data.strip(),
            roll_no=form.roll_no.data.strip().upper(),
            branch=form.branch.data,
            cgpa=round(form.cgpa.data, 2),
            active_backlogs=form.active_backlogs.data or 0,
            passing_year=form.passing_year.data,
            skills=form.skills.data.strip() if form.skills.data else '',
            resume_path=resume_filename
        )
        db.session.add(student)

        log = ActivityLog(user_id=user.user_id, action=f"New student registered: {student.roll_no} - {student.name}")
        db.session.add(log)
        db.session.commit()

        flash('Your student account has been created successfully! You can now log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register_student.html', form=form)


@auth_bp.route('/register/company', methods=['GET', 'POST'])
def register_company():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = CompanyRegisterForm()
    if form.validate_on_submit():
        # Create user with pending status
        user = User(
            email=form.email.data.strip().lower(),
            role='company',
            status='pending'  # Requires Admin/TPO approval before login works!
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()

        # Create company profile
        company = Company(
            user_id=user.user_id,
            name=form.name.data.strip(),
            industry=form.industry.data.strip() if form.industry.data else '',
            website=form.website.data.strip() if form.website.data else '',
            hr_contact=form.hr_contact.data.strip() if form.hr_contact.data else '',
            approval_status='pending'
        )
        db.session.add(company)

        log = ActivityLog(user_id=user.user_id, action=f"New company registration requested: {company.name}")
        db.session.add(log)
        db.session.commit()

        flash(
            'Company registration submitted successfully! As per policy, your account is pending approval by the Training & Placement Office. Once approved, you will be able to log in and post drives.',
            'info'
        )
        return redirect(url_for('auth.login'))

    return render_template('auth/register_company.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    user_email = current_user.email
    user_id = current_user.user_id
    logout_user()
    log = ActivityLog(user_id=user_id, action=f"User {user_email} logged out")
    db.session.add(log)
    db.session.commit()
    flash('You have been logged out securely.', 'info')
    return redirect(url_for('auth.login'))
