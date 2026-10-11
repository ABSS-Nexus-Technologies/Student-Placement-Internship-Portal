from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user
from app.models import Drive, Company, Student, Placement

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.is_admin():
            return redirect(url_for('admin.dashboard'))
        elif current_user.is_company():
            return redirect(url_for('company.dashboard'))
        elif current_user.is_student():
            return redirect(url_for('student.dashboard'))

    # Public landing page stats
    total_companies = Company.query.filter_by(approval_status='approved').count()
    active_drives = Drive.query.filter_by(status='active').count()
    placed_count = Placement.query.filter(Placement.offer_status.in_(['offered', 'accepted'])).count()
    featured_drives = Drive.query.filter_by(status='active').order_by(Drive.package_or_stipend.desc()).limit(3).all()

    return render_template(
        'main/index.html',
        total_companies=total_companies,
        active_drives=active_drives,
        placed_count=placed_count,
        featured_drives=featured_drives
    )
