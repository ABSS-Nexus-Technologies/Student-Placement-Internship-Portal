from datetime import datetime, date, timezone
import collections
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, current_app, abort
from flask_login import current_user
import numpy as np

from app import role_required
from app.models import db, User, Student, Company, Drive, Application, Round, RoundResult, Placement, Notification, ActivityLog
from app.blueprints.admin.forms import BulkImportForm, AnnouncementForm, ReportFilterForm
from app.blueprints.company.forms import DriveForm
from app.services.importer import bulk_import_students
from app.services.reports import generate_placement_excel
from app.services.notification_service import send_notification, notify_eligible_students_for_drive

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard')
@role_required('admin')
def dashboard():
    total_students = Student.query.count()
    total_companies = Company.query.filter_by(approval_status='approved').count()
    pending_companies = Company.query.filter_by(approval_status='pending').count()
    active_drives = Drive.query.filter_by(status='active').count()
    total_applications = Application.query.count()

    # Calculate placed students count
    placed_students = Student.query.join(Application).join(Placement).filter(
        Placement.offer_status.in_(['offered', 'accepted'])
    ).distinct().count()

    placement_pct = round((placed_students / total_students * 100.0), 1) if total_students > 0 else 0.0

    # Chart 1: Branch-wise placements
    branches = ['CSE', 'IT', 'ECE', 'EEE', 'MECH', 'CIVIL']
    branch_reg_counts = []
    branch_placed_counts = []

    for b in branches:
        reg_count = Student.query.filter_by(branch=b).count()
        plc_count = Student.query.filter_by(branch=b).join(Application).join(Placement).filter(
            Placement.offer_status.in_(['offered', 'accepted'])
        ).distinct().count()
        branch_reg_counts.append(reg_count)
        branch_placed_counts.append(plc_count)

    # Chart 2: Monthly Applications (past 6 months)
    # Group applications by month
    apps = Application.query.all()
    monthly_map = collections.defaultdict(int)
    for a in apps:
        if a.applied_on:
            m_label = a.applied_on.strftime('%b %Y')
            monthly_map[m_label] += 1
    
    # Sort months or ensure default labels exist
    if not monthly_map:
        monthly_map[datetime.now().strftime('%b %Y')] = 0

    monthly_labels = list(monthly_map.keys())[-6:]
    monthly_data = [monthly_map[k] for k in monthly_labels]

    # Recent activities
    recent_activities = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(10).all()

    # Pending approvals
    pending_company_list = Company.query.filter_by(approval_status='pending').limit(5).all()

    return render_template(
        'admin/dashboard.html',
        total_students=total_students,
        total_companies=total_companies,
        pending_companies=pending_companies,
        active_drives=active_drives,
        total_applications=total_applications,
        placed_students=placed_students,
        placement_pct=placement_pct,
        branches=branches,
        branch_reg_counts=branch_reg_counts,
        branch_placed_counts=branch_placed_counts,
        monthly_labels=monthly_labels,
        monthly_data=monthly_data,
        recent_activities=recent_activities,
        pending_company_list=pending_company_list
    )


@admin_bp.route('/companies')
@role_required('admin')
def companies():
    status_filter = request.args.get('status', 'all')
    query = Company.query
    if status_filter in ['pending', 'approved', 'rejected']:
        query = query.filter_by(approval_status=status_filter)
    company_list = query.order_by(Company.name.asc()).all()
    return render_template('admin/companies.html', companies=company_list, status_filter=status_filter)


@admin_bp.route('/company/<int:company_id>/<action>', methods=['POST'])
@role_required('admin')
def handle_company_approval(company_id, action):
    company = Company.query.get_or_404(company_id)
    if action not in ['approve', 'reject']:
        abort(400)

    if action == 'approve':
        company.approval_status = 'approved'
        if company.user:
            company.user.status = 'active'
        flash(f"Company '{company.name}' has been approved. They can now log in and post placement drives.", 'success')
        # Notify company
        if company.user:
            send_notification(
                user_id=company.user.user_id,
                message="Your company profile has been approved by the TPO! You may now sign in and post campus recruitment drives.",
                email_subject="Company Account Approved - Campus Placement Portal"
            )
    else:
        company.approval_status = 'rejected'
        if company.user:
            company.user.status = 'rejected'
        flash(f"Company '{company.name}' has been rejected.", 'warning')

    log = ActivityLog(user_id=current_user.user_id, action=f"Admin {action}d company: {company.name}")
    db.session.add(log)
    db.session.commit()

    return redirect(url_for('admin.companies'))


@admin_bp.route('/students')
@role_required('admin')
def students():
    branch_filter = request.args.get('branch', '')
    year_filter = request.args.get('year', type=int)
    search_query = request.args.get('q', '').strip()

    query = Student.query
    if branch_filter:
        query = query.filter_by(branch=branch_filter)
    if year_filter:
        query = query.filter_by(passing_year=year_filter)
    if search_query:
        query = query.filter(
            (Student.name.ilike(f"%{search_query}%")) | 
            (Student.roll_no.ilike(f"%{search_query}%"))
        )

    student_list = query.order_by(Student.roll_no.asc()).all()
    return render_template(
        'admin/students.html',
        students=student_list,
        branch_filter=branch_filter,
        year_filter=year_filter,
        search_query=search_query
    )


@admin_bp.route('/drives')
@role_required('admin')
def drives():
    drive_list = Drive.query.order_by(Drive.created_at.desc()).all()
    return render_template('admin/drives.html', drives=drive_list)


@admin_bp.route('/drive/create', methods=['GET', 'POST'])
@role_required('admin')
def create_drive():
    form = DriveForm()
    # Add company selection for admin
    approved_companies = Company.query.filter_by(approval_status='approved').all()
    if not approved_companies:
        flash("No approved companies found. Please approve at least one company first.", "warning")
        return redirect(url_for('admin.companies'))

    company_id = request.form.get('company_id', type=int) or (approved_companies[0].company_id if approved_companies else 0)

    if form.validate_on_submit():
        branches = form.allowed_branches.data
        allowed_branches_str = 'ALL' if ('ALL' in branches or len(branches) == 0) else ",".join(branches)

        drive = Drive(
            company_id=company_id,
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

        notified_count = notify_eligible_students_for_drive(drive)
        log = ActivityLog(user_id=current_user.user_id, action=f"Admin created drive '{drive.title}' for {drive.company.name}")
        db.session.add(log)
        db.session.commit()

        flash(f"Campus drive created successfully! {notified_count} eligible students notified.", 'success')
        return redirect(url_for('admin.drives'))

    return render_template('admin/create_drive.html', form=form, companies=approved_companies)


@admin_bp.route('/drive/<int:drive_id>/status', methods=['POST'])
@role_required('admin')
def change_drive_status(drive_id):
    drive = Drive.query.get_or_404(drive_id)
    new_status = request.form.get('status')
    if new_status in ['active', 'completed', 'cancelled']:
        drive.status = new_status
        db.session.commit()
        log = ActivityLog(user_id=current_user.user_id, action=f"Admin changed drive {drive.title} status to {new_status}")
        db.session.add(log)
        db.session.commit()
        flash(f"Drive status updated to '{new_status.title()}'.", 'success')
    return redirect(url_for('admin.drives'))


@admin_bp.route('/applications')
@role_required('admin')
def applications():
    status_filter = request.args.get('status', 'all')
    query = Application.query
    if status_filter in ['applied', 'shortlisted', 'rejected', 'selected']:
        query = query.filter_by(status=status_filter)
    app_list = query.order_by(Application.applied_on.desc()).all()
    return render_template('admin/applications.html', applications=app_list, status_filter=status_filter)


@admin_bp.route('/bulk_import', methods=['GET', 'POST'])
@role_required('admin')
def bulk_import():
    form = BulkImportForm()
    import_results = None

    if form.validate_on_submit():
        file = form.file.data
        filename = file.filename
        import_results = bulk_import_students(file.stream, filename, admin_user_id=current_user.user_id)
        
        if import_results['success_count'] > 0:
            flash(f"Successfully imported {import_results['success_count']} students into the portal!", 'success')
        if import_results['error_count'] > 0:
            flash(f"Encountered {import_results['error_count']} errors during import. See detailed rejection report below.", 'danger')

    return render_template('admin/bulk_import.html', form=form, results=import_results)


@admin_bp.route('/announcements', methods=['GET', 'POST'])
@role_required('admin')
def announcements():
    form = AnnouncementForm()

    if form.validate_on_submit():
        audience = form.target_audience.data
        subject = form.subject.data.strip()
        body = form.message.data.strip()

        target_users = []
        if audience == 'all':
            target_users = User.query.filter(User.role.in_(['student', 'company'])).all()
        elif audience == 'students':
            target_users = User.query.filter_by(role='student').all()
        elif audience == 'companies':
            target_users = User.query.filter_by(role='company', status='active').all()
        elif audience == 'branch':
            br = form.branch.data
            target_students = Student.query.filter_by(branch=br).all()
            target_users = [s.user for s in target_students if s.user]
        elif audience == 'batch':
            by = form.batch_year.data
            target_students = Student.query.filter_by(passing_year=by).all()
            target_users = [s.user for s in target_students if s.user]

        sent_count = 0
        for u in target_users:
            send_notification(
                user_id=u.user_id,
                message=f"[Announcement] {subject}: {body[:100]}...",
                email_subject=f"TPO Announcement: {subject}",
                email_body=f"Dear User,\n\n{body}\n\nTraining & Placement Cell"
            )
            sent_count += 1

        log = ActivityLog(user_id=current_user.user_id, action=f"Admin broadcasted announcement '{subject}' to {sent_count} users")
        db.session.add(log)
        db.session.commit()

        flash(f"Announcement broadcast successfully sent to {sent_count} users!", 'success')
        return redirect(url_for('admin.announcements'))

    return render_template('admin/announcements.html', form=form)


@admin_bp.route('/reports', methods=['GET', 'POST'])
@role_required('admin')
def reports():
    form = ReportFilterForm()
    # Populate company choices
    companies_list = Company.query.filter_by(approval_status='approved').order_by(Company.name.asc()).all()
    form.company_id.choices = [(0, 'All Companies')] + [(c.company_id, c.name) for c in companies_list]

    if form.validate_on_submit():
        report_type = form.report_type.data
        batch_year = form.batch_year.data
        branch = form.branch.data
        comp_id = form.company_id.data
        start_date = form.start_date.data
        end_date = form.end_date.data

        # Gather students according to filters
        student_query = Student.query
        if branch:
            student_query = student_query.filter_by(branch=branch)
        if batch_year:
            student_query = student_query.filter_by(passing_year=batch_year)
        students = student_query.all()

        # Build student records with placement data
        student_records = []
        for s in students:
            # Check placements
            placed_apps = [a for a in s.applications if a.placement and a.placement.offer_status in ['offered', 'accepted']]
            
            # Apply company & date filter if specified
            if comp_id and comp_id > 0:
                placed_apps = [a for a in placed_apps if a.drive.company_id == comp_id]
            if start_date:
                placed_apps = [a for a in placed_apps if a.placement.offer_date >= start_date]
            if end_date:
                placed_apps = [a for a in placed_apps if a.placement.offer_date <= end_date]

            is_placed = len(placed_apps) > 0
            best_placement = max(placed_apps, key=lambda a: a.placement.package) if is_placed else None

            student_records.append({
                'student_id': s.student_id,
                'name': s.name,
                'roll_no': s.roll_no,
                'branch': s.branch,
                'passing_year': s.passing_year,
                'cgpa': s.cgpa,
                'active_backlogs': s.active_backlogs,
                'is_placed': is_placed,
                'company_name': best_placement.drive.company.name if best_placement else '-',
                'drive_title': best_placement.drive.title if best_placement else '-',
                'package': best_placement.placement.package if best_placement else 0.0,
                'offer_date': best_placement.placement.offer_date.strftime('%Y-%m-%d') if best_placement else '-'
            })

        # Company summary aggregation
        company_records = []
        all_companies = Company.query.filter_by(approval_status='approved').all() if not comp_id else Company.query.filter_by(company_id=comp_id).all()
        for c in all_companies:
            drives = c.drives.all()
            drive_ids = [d.drive_id for d in drives]
            c_apps = Application.query.filter(Application.drive_id.in_(drive_ids)).all() if drive_ids else []
            c_placements = [a.placement for a in c_apps if a.placement and a.placement.offer_status in ['offered', 'accepted']]
            c_pkgs = [p.package for p in c_placements if p.package]

            company_records.append({
                'name': c.name,
                'industry': c.industry or '-',
                'total_drives': len(drives),
                'total_applicants': len(c_apps),
                'placed_count': len(c_placements),
                'highest_pkg': round(float(np.max(c_pkgs)), 2) if c_pkgs else 0.0,
                'avg_pkg': round(float(np.mean(c_pkgs)), 2) if c_pkgs else 0.0
            })

        # Branch summary aggregation
        branch_records = []
        branches_list = ['CSE', 'IT', 'ECE', 'EEE', 'MECH', 'CIVIL']
        for b in branches_list:
            b_students = [s for s in student_records if s['branch'] == b]
            b_reg = len(b_students)
            b_placed = [s for s in b_students if s['is_placed']]
            b_plc_count = len(b_placed)
            b_pct = round((b_plc_count / b_reg * 100.0), 2) if b_reg > 0 else 0.0
            b_pkgs = [s['package'] for s in b_placed if s['package'] > 0]
            branch_records.append({
                'branch': b,
                'registered': b_reg,
                'placed': b_plc_count,
                'placement_pct': b_pct,
                'highest_pkg': round(float(np.max(b_pkgs)), 2) if b_pkgs else 0.0,
                'avg_pkg': round(float(np.mean(b_pkgs)), 2) if b_pkgs else 0.0,
                'median_pkg': round(float(np.median(b_pkgs)), 2) if b_pkgs else 0.0
            })

        # Year summary aggregation
        year_records = []
        years_list = sorted(list({s['passing_year'] for s in student_records})) if student_records else [2026]
        for y in years_list:
            y_students = [s for s in student_records if s['passing_year'] == y]
            y_reg = len(y_students)
            y_placed = [s for s in y_students if s['is_placed']]
            y_plc_count = len(y_placed)
            y_pct = round((y_plc_count / y_reg * 100.0), 2) if y_reg > 0 else 0.0
            y_pkgs = [s['package'] for s in y_placed if s['package'] > 0]
            year_records.append({
                'batch_year': y,
                'registered': y_reg,
                'placed': y_plc_count,
                'placement_pct': y_pct,
                'highest_pkg': round(float(np.max(y_pkgs)), 2) if y_pkgs else 0.0,
                'avg_pkg': round(float(np.mean(y_pkgs)), 2) if y_pkgs else 0.0,
                'median_pkg': round(float(np.median(y_pkgs)), 2) if y_pkgs else 0.0
            })

        raw_data = {
            'students': student_records,
            'company_summary': company_records,
            'branch_summary': branch_records,
            'year_summary': year_records
        }

        filters = {
            'Report_Format': report_type,
            'Batch_Year': batch_year or 'All Years',
            'Branch': branch or 'All Branches',
            'Company': dict(form.company_id.choices).get(comp_id, 'All Companies'),
            'Date_Range': f"{start_date or 'Start'} to {end_date or 'End'}"
        }

        excel_stream = generate_placement_excel(report_type, raw_data, filters)
        now_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        download_name = f"TPO_{report_type}_{now_str}.xlsx"

        log = ActivityLog(user_id=current_user.user_id, action=f"Admin generated and downloaded {report_type} Excel report")
        db.session.add(log)
        db.session.commit()

        return send_file(
            excel_stream,
            as_attachment=True,
            download_name=download_name,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    return render_template('admin/reports.html', form=form)


@admin_bp.route('/activity_logs')
@role_required('admin')
def activity_logs():
    logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(150).all()
    return render_template('admin/activity_logs.html', logs=logs)
