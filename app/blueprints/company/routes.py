from datetime import datetime, timezone, date
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import current_user

from app import role_required
from app.models import db, Company, Drive, Application, Round, RoundResult, Placement, Student, ActivityLog
from app.blueprints.company.forms import CompanyProfileForm, DriveForm, RoundForm, RoundResultForm, FinalSelectionForm
from app.services.notification_service import (
    notify_eligible_students_for_drive,
    notify_student_round_update,
    notify_student_selection,
    send_notification
)

company_bp = Blueprint('company', __name__)

@company_bp.route('/dashboard')
@role_required('company')
def dashboard():
    company = current_user.company
    if not company:
        abort(404)

    drives = company.drives.order_by(Drive.created_at.desc()).all()
    drive_ids = [d.drive_id for d in drives]

    applications = Application.query.filter(Application.drive_id.in_(drive_ids)).all() if drive_ids else []
    total_applicants = len(applications)
    shortlisted_count = sum(1 for a in applications if a.status == 'shortlisted')
    selected_count = sum(1 for a in applications if a.status == 'selected')

    return render_template(
        'company/dashboard.html',
        company=company,
        drives=drives,
        total_applicants=total_applicants,
        shortlisted_count=shortlisted_count,
        selected_count=selected_count,
        recent_applications=applications[:10]
    )


@company_bp.route('/profile', methods=['GET', 'POST'])
@role_required('company')
def profile():
    company = current_user.company
    form = CompanyProfileForm(obj=company)

    if form.validate_on_submit():
        company.name = form.name.data.strip()
        company.industry = form.industry.data.strip()
        company.website = form.website.data.strip() if form.website.data else ''
        company.hr_contact = form.hr_contact.data.strip()
        db.session.commit()

        log = ActivityLog(user_id=current_user.user_id, action=f"Company profile updated: {company.name}")
        db.session.add(log)
        db.session.commit()

        flash('Company profile updated successfully.', 'success')
        return redirect(url_for('company.profile'))

    return render_template('company/profile.html', company=company, form=form)


@company_bp.route('/drives')
@role_required('company')
def drives():
    company = current_user.company
    company_drives = company.drives.order_by(Drive.created_at.desc()).all()
    return render_template('company/drives.html', company=company, drives=company_drives)


@company_bp.route('/drive/create', methods=['GET', 'POST'])
@role_required('company')
def create_drive():
    company = current_user.company
    form = DriveForm()

    if form.validate_on_submit():
        # Process branches
        branches = form.allowed_branches.data
        if 'ALL' in branches or len(branches) == 0:
            allowed_branches_str = 'ALL'
        else:
            allowed_branches_str = ",".join(branches)

        drive = Drive(
            company_id=company.company_id,
            title=form.title.data.strip(),
            type=form.type.data,
            package_or_stipend=round(form.package_or_stipend.data, 2),
            min_cgpa=round(form.min_cgpa.data, 2),
            max_backlogs=form.max_backlogs.data,
            allowed_branches=allowed_branches_str,
            batch_year=form.batch_year.data,
            last_date=form.last_date.data,
            description=form.description.data.strip() if form.description.data else '',
            status=form.status.data
        )
        db.session.add(drive)
        db.session.commit()

        # Notify eligible students automatically
        notified_count = notify_eligible_students_for_drive(drive)

        log = ActivityLog(
            user_id=current_user.user_id, 
            action=f"Company {company.name} published drive '{drive.title}' ({notified_count} eligible students notified)"
        )
        db.session.add(log)
        db.session.commit()

        flash(f"Campus drive '{drive.title}' published successfully! {notified_count} eligible students have been notified.", 'success')
        return redirect(url_for('company.drives'))

    return render_template('company/create_drive.html', form=form, company=company)


@company_bp.route('/drive/<int:drive_id>/edit', methods=['GET', 'POST'])
@role_required('company')
def edit_drive(drive_id):
    company = current_user.company
    drive = Drive.query.filter_by(drive_id=drive_id, company_id=company.company_id).first_or_404()
    
    form = DriveForm(obj=drive)
    if request.method == 'GET':
        if drive.allowed_branches == 'ALL':
            form.allowed_branches.data = ['ALL']
        else:
            form.allowed_branches.data = drive.allowed_branches.split(',')

    if form.validate_on_submit():
        branches = form.allowed_branches.data
        if 'ALL' in branches or len(branches) == 0:
            drive.allowed_branches = 'ALL'
        else:
            drive.allowed_branches = ",".join(branches)

        drive.title = form.title.data.strip()
        drive.type = form.type.data
        drive.package_or_stipend = round(form.package_or_stipend.data, 2)
        drive.min_cgpa = round(form.min_cgpa.data, 2)
        drive.max_backlogs = form.max_backlogs.data
        drive.batch_year = form.batch_year.data
        drive.last_date = form.last_date.data
        drive.description = form.description.data.strip() if form.description.data else ''
        drive.status = form.status.data
        db.session.commit()

        log = ActivityLog(user_id=current_user.user_id, action=f"Updated drive '{drive.title}' (ID: {drive.drive_id})")
        db.session.add(log)
        db.session.commit()

        flash(f"Drive '{drive.title}' updated successfully.", 'success')
        return redirect(url_for('company.drives'))

    return render_template('company/edit_drive.html', form=form, drive=drive, company=company)


@company_bp.route('/drive/<int:drive_id>/applicants')
@role_required('company')
def drive_applicants(drive_id):
    company = current_user.company
    drive = Drive.query.filter_by(drive_id=drive_id, company_id=company.company_id).first_or_404()
    applications = drive.applications.order_by(Application.applied_on.desc()).all()
    rounds = drive.rounds.all()

    return render_template(
        'company/drive_applicants.html',
        drive=drive,
        company=company,
        applications=applications,
        rounds=rounds
    )


@company_bp.route('/application/<int:application_id>/status', methods=['POST'])
@role_required('company')
def update_application_status(application_id):
    company = current_user.company
    application = Application.query.get_or_404(application_id)
    
    # Ownership verification
    if application.drive.company_id != company.company_id:
        abort(403)

    new_status = request.form.get('status')
    if new_status in ['applied', 'shortlisted', 'rejected']:
        application.status = new_status
        db.session.commit()

        # Send notification to student
        status_label = "Shortlisted" if new_status == 'shortlisted' else "Rejected"
        if application.student and application.student.user:
            send_notification(
                user_id=application.student.user.user_id,
                message=f"Application Status: You have been {status_label} for {application.drive.company.name} - {application.drive.title}."
            )

        log = ActivityLog(
            user_id=current_user.user_id,
            action=f"Changed applicant {application.student.roll_no} status to '{new_status}' for drive '{application.drive.title}'"
        )
        db.session.add(log)
        db.session.commit()

        flash(f"Candidate status updated to {new_status.title()}.", 'success')

    return redirect(url_for('company.drive_applicants', drive_id=application.drive_id))


@company_bp.route('/drive/<int:drive_id>/rounds', methods=['GET', 'POST'])
@role_required('company')
def manage_rounds(drive_id):
    company = current_user.company
    drive = Drive.query.filter_by(drive_id=drive_id, company_id=company.company_id).first_or_404()
    round_form = RoundForm()

    if round_form.validate_on_submit():
        new_round = Round(
            drive_id=drive.drive_id,
            round_name=round_form.round_name.data.strip(),
            round_date=round_form.round_date.data,
            mode=round_form.mode.data
        )
        db.session.add(new_round)
        db.session.commit()

        # Notify shortlisted students about the new round
        for app in drive.applications:
            if app.status in ['applied', 'shortlisted'] and app.student and app.student.user:
                send_notification(
                    user_id=app.student.user.user_id,
                    message=(
                        f"Round Scheduled: '{new_round.round_name}' for {drive.company.name} - {drive.title} "
                        f"on {new_round.round_date.strftime('%d %b %Y at %I:%M %p')} ({new_round.mode.upper()})."
                    )
                )

        flash(f"Round '{new_round.round_name}' added successfully.", 'success')
        return redirect(url_for('company.manage_rounds', drive_id=drive.drive_id))

    rounds = drive.rounds.all()
    applications = drive.applications.all()

    return render_template(
        'company/manage_rounds.html',
        drive=drive,
        company=company,
        rounds=rounds,
        applications=applications,
        form=round_form
    )


@company_bp.route('/round/<int:round_id>/update_result', methods=['POST'])
@role_required('company')
def update_round_result(round_id):
    company = current_user.company
    round_obj = Round.query.get_or_404(round_id)

    if round_obj.drive.company_id != company.company_id:
        abort(403)

    application_id = request.form.get('application_id', type=int)
    result_val = request.form.get('result')  # cleared, failed, absent, pending
    remarks = request.form.get('remarks', '')

    application = Application.query.get_or_404(application_id)
    if application.drive_id != round_obj.drive_id:
        abort(400)

    # Find or create RoundResult
    round_result = RoundResult.query.filter_by(application_id=application_id, round_id=round_id).first()
    if not round_result:
        round_result = RoundResult(
            application_id=application_id,
            round_id=round_id,
            result=result_val,
            remarks=remarks
        )
        db.session.add(round_result)
    else:
        round_result.result = result_val
        round_result.remarks = remarks

    # Update application's current_round and status if cleared
    if result_val == 'cleared':
        application.current_round = round_obj.round_name
        application.status = 'shortlisted'
    elif result_val == 'failed':
        application.status = 'rejected'

    db.session.commit()

    # Send notification to candidate
    notify_student_round_update(application, round_obj.round_name, result_val, remarks)

    log = ActivityLog(
        user_id=current_user.user_id,
        action=f"Updated round '{round_obj.round_name}' result for candidate {application.student.roll_no}: {result_val}"
    )
    db.session.add(log)
    db.session.commit()

    flash(f"Result for {application.student.name} recorded as {result_val.title()}.", 'success')
    return redirect(url_for('company.manage_rounds', drive_id=round_obj.drive_id))


@company_bp.route('/application/<int:application_id>/select', methods=['POST'])
@role_required('company')
def select_candidate(application_id):
    company = current_user.company
    application = Application.query.get_or_404(application_id)

    if application.drive.company_id != company.company_id:
        abort(403)

    package = float(request.form.get('package', application.drive.package_or_stipend))
    offer_date_str = request.form.get('offer_date')
    offer_status = request.form.get('offer_status', 'offered')

    try:
        offer_date = datetime.strptime(offer_date_str, '%Y-%m-%d').date() if offer_date_str else date.today()
    except ValueError:
        offer_date = date.today()

    # Find or create Placement
    placement = Placement.query.filter_by(application_id=application_id).first()
    if not placement:
        placement = Placement(
            application_id=application_id,
            package=package,
            offer_date=offer_date,
            offer_status=offer_status
        )
        db.session.add(placement)
    else:
        placement.package = package
        placement.offer_date = offer_date
        placement.offer_status = offer_status

    application.status = 'selected'
    application.current_round = 'Selected'
    db.session.commit()

    # Dispatch congratulations notification
    notify_student_selection(application, package, offer_date)

    log = ActivityLog(
        user_id=current_user.user_id,
        action=f"Selected candidate {application.student.roll_no} for drive '{application.drive.title}' with {package} LPA"
    )
    db.session.add(log)
    db.session.commit()

    flash(f"🎉 Final selection recorded for {application.student.name}! Offer of {package} LPA extended.", 'success')
    return redirect(url_for('company.drive_applicants', drive_id=application.drive_id))
