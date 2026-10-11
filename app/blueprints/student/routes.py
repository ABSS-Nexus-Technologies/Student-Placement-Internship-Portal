import os
import uuid
from datetime import datetime, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, send_from_directory, abort
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app import role_required
from app.models import db, Student, Drive, Application, Round, RoundResult, Notification, ActivityLog
from app.blueprints.student.forms import StudentProfileForm
from app.services.eligibility import check_eligibility
from app.services.notification_service import send_notification

student_bp = Blueprint('student', __name__)

@student_bp.route('/dashboard')
@role_required('student')
def dashboard():
    student = current_user.student
    if not student:
        flash("Student profile not found. Please contact administration.", "danger")
        return redirect(url_for('auth.logout'))

    # Active drives
    all_drives = Drive.query.filter_by(status='active').order_by(Drive.last_date.asc()).all()
    
    # Calculate eligibility for all active drives
    eligible_drives = []
    applied_drive_ids = {app.drive_id for app in student.applications}

    for drive in all_drives:
        eligibility = check_eligibility(
            student=student,
            drive=drive,
            allow_placed_to_reapply=current_app.config.get('ALLOW_PLACED_STUDENTS_TO_REAPPLY', False),
            dream_multiplier=current_app.config.get('MIN_PACKAGE_MULTIPLIER_FOR_DREAM', 1.5)
        )
        if eligibility.is_eligible:
            eligible_drives.append({
                'drive': drive,
                'has_applied': drive.drive_id in applied_drive_ids,
                'eligibility': eligibility
            })

    # Student applications
    applications = student.applications.order_by(Application.applied_on.desc()).all()
    
    # Placements
    placements = [app.placement for app in applications if app.placement and app.placement.offer_status in ['offered', 'accepted']]
    
    # Recent notifications
    recent_notifs = Notification.query.filter_by(user_id=current_user.user_id).order_by(Notification.sent_on.desc()).limit(5).all()

    return render_template(
        'student/dashboard.html',
        student=student,
        eligible_drives=eligible_drives[:5],
        total_eligible_count=len(eligible_drives),
        applications=applications,
        placements=placements,
        recent_notifs=recent_notifs
    )


@student_bp.route('/profile', methods=['GET', 'POST'])
@role_required('student')
def profile():
    student = current_user.student
    form = StudentProfileForm(obj=student)

    if form.validate_on_submit():
        student.name = form.name.data.strip()
        student.branch = form.branch.data
        student.cgpa = round(form.cgpa.data, 2)
        student.active_backlogs = form.active_backlogs.data or 0
        student.passing_year = form.passing_year.data
        student.skills = form.skills.data.strip() if form.skills.data else ''

        if form.resume.data:
            file = form.resume.data
            safe_name = secure_filename(file.filename)
            unique_name = f"{uuid.uuid4().hex[:10]}_{student.roll_no}_{safe_name}"
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_name)
            file.save(file_path)
            
            # Optionally remove old file if exists
            if student.resume_path:
                old_path = os.path.join(current_app.config['UPLOAD_FOLDER'], student.resume_path)
                if os.path.exists(old_path):
                    try:
                        os.remove(old_path)
                    except Exception:
                        pass
            student.resume_path = unique_name

        db.session.commit()

        log = ActivityLog(user_id=current_user.user_id, action=f"Student {student.roll_no} updated profile")
        db.session.add(log)
        db.session.commit()

        flash('Your profile has been updated successfully!', 'success')
        return redirect(url_for('student.profile'))

    return render_template('student/profile.html', student=student, form=form)


@student_bp.route('/drives')
@role_required('student')
def drives():
    student = current_user.student
    show_all = request.args.get('view', 'eligible') == 'all'
    
    active_drives = Drive.query.filter_by(status='active').order_by(Drive.last_date.asc()).all()
    applied_drive_ids = {app.drive_id for app in student.applications}

    eligible_drives_data = []
    ineligible_drives_data = []

    for drive in active_drives:
        eligibility = check_eligibility(
            student=student,
            drive=drive,
            allow_placed_to_reapply=current_app.config.get('ALLOW_PLACED_STUDENTS_TO_REAPPLY', False),
            dream_multiplier=current_app.config.get('MIN_PACKAGE_MULTIPLIER_FOR_DREAM', 1.5)
        )
        item = {
            'drive': drive,
            'has_applied': drive.drive_id in applied_drive_ids,
            'eligibility': eligibility
        }
        if eligibility.is_eligible:
            eligible_drives_data.append(item)
        else:
            ineligible_drives_data.append(item)

    return render_template(
        'student/eligible_drives.html',
        student=student,
        eligible_drives=eligible_drives_data,
        ineligible_drives=ineligible_drives_data,
        show_all=show_all
    )


@student_bp.route('/apply/<int:drive_id>', methods=['POST'])
@role_required('student')
def apply_drive(drive_id):
    student = current_user.student
    drive = Drive.query.get_or_404(drive_id)

    # Check if drive is active
    if drive.status != 'active':
        flash('This drive is no longer accepting applications.', 'danger')
        return redirect(url_for('student.drives'))

    # Check if already applied
    existing_app = Application.query.filter_by(drive_id=drive.drive_id, student_id=student.student_id).first()
    if existing_app:
        flash(f"You have already applied for '{drive.title}' at {drive.company.name}.", 'warning')
        return redirect(url_for('student.applications'))

    # Eligibility validation
    eligibility = check_eligibility(
        student=student,
        drive=drive,
        allow_placed_to_reapply=current_app.config.get('ALLOW_PLACED_STUDENTS_TO_REAPPLY', False),
        dream_multiplier=current_app.config.get('MIN_PACKAGE_MULTIPLIER_FOR_DREAM', 1.5)
    )

    if not eligibility.is_eligible:
        reasons_msg = "; ".join(eligibility.reasons)
        flash(f"Cannot apply: You do not meet the criteria for this drive. ({reasons_msg})", 'danger')
        return redirect(url_for('student.drives'))

    # Ensure student has a resume uploaded
    if not student.resume_path:
        flash('Please upload your resume in the Profile section before applying for campus drives.', 'warning')
        return redirect(url_for('student.profile'))

    # Create application
    application = Application(
        drive_id=drive.drive_id,
        student_id=student.student_id,
        applied_on=datetime.now(timezone.utc),
        current_round='Applied',
        status='applied'
    )
    db.session.add(application)

    log = ActivityLog(
        user_id=current_user.user_id,
        action=f"Student {student.roll_no} applied for drive: {drive.title} ({drive.company.name})"
    )
    db.session.add(log)
    db.session.commit()

    # In-portal & email notification
    send_notification(
        user_id=current_user.user_id,
        message=f"Application Submitted: You have successfully applied for '{drive.title}' at {drive.company.name}.",
        email_subject=f"Application Confirmed: {drive.company.name} - {drive.title}",
        email_body=(
            f"Dear {student.name},\n\n"
            f"Your application for '{drive.title}' at {drive.company.name} has been submitted successfully.\n"
            f"Package/Stipend: {drive.package_or_stipend} LPA\n"
            f"You will receive notifications once the company shortlists candidates and announces round dates."
        )
    )

    flash(f"Successfully applied for '{drive.title}' at {drive.company.name}!", 'success')
    return redirect(url_for('student.applications'))


@student_bp.route('/applications')
@role_required('student')
def applications():
    student = current_user.student
    student_apps = student.applications.order_by(Application.applied_on.desc()).all()
    return render_template('student/applications.html', student=student, applications=student_apps)


@student_bp.route('/notifications')
@role_required('student')
def notifications():
    notifs = Notification.query.filter_by(user_id=current_user.user_id).order_by(Notification.sent_on.desc()).all()
    # Mark all as read
    for n in notifs:
        n.is_read = True
    db.session.commit()
    return render_template('student/notifications.html', notifications=notifs)


@student_bp.route('/resume/<filename>')
@role_required('student', 'company', 'admin')
def download_resume(filename):
    # Verify file security and permission
    safe_name = secure_filename(filename)
    # If student, verify they own this file
    if current_user.is_student():
        if current_user.student.resume_path != safe_name:
            abort(403)
    folder = current_app.config['UPLOAD_FOLDER']
    if not os.path.exists(os.path.join(folder, safe_name)):
        abort(404)
    return send_from_directory(folder, safe_name, as_attachment=False)
