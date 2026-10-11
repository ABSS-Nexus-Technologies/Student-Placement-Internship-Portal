import logging
from datetime import datetime, timezone
from flask import current_app
from flask_mail import Message
from app.models import db, Notification, Student, User
from app.services.eligibility import check_eligibility

logger = logging.getLogger(__name__)

def send_notification(user_id, message, email_subject=None, email_body=None):
    """
    Creates an in-portal notification record and attempts to send an email via Flask-Mail.
    Falls back to console logging if SMTP is unconfigured or fails.
    """
    try:
        # In-Portal Notification
        notif = Notification(
            user_id=user_id,
            message=message,
            sent_on=datetime.now(timezone.utc),
            is_read=False
        )
        db.session.add(notif)
        db.session.commit()
    except Exception as e:
        logger.error(f"Failed to record in-portal notification for user {user_id}: {e}")
        db.session.rollback()

    # Email Notification
    user = User.query.get(user_id)
    if not user or not user.email:
        return

    subject = email_subject or "Update from Training & Placement Office"
    body = email_body or message

    mail_ext = current_app.extensions.get('mail') if current_app else None
    mail_username = current_app.config.get('MAIL_USERNAME') if current_app else None

    # If SMTP is configured and mail extension is loaded
    if mail_ext and mail_username:
        try:
            msg = Message(
                subject=f"[TPO Portal] {subject}",
                recipients=[user.email],
                body=f"Hello,\n\n{body}\n\nBest regards,\nTraining & Placement Office",
                sender=current_app.config.get('MAIL_DEFAULT_SENDER')
            )
            mail_ext.send(msg)
            logger.info(f"Email sent successfully to {user.email}")
            return
        except Exception as e:
            logger.warning(f"SMTP sending failed ({e}). Falling back to console log.")

    # Console logging fallback
    print(f"\n[EMAIL CONSOLE LOG] To: {user.email} | Subject: {subject}\nBody: {body}\n{'-'*60}")


def notify_eligible_students_for_drive(drive):
    """
    Finds all eligible students for a newly published drive and notifies them.
    """
    students = Student.query.filter_by(passing_year=drive.batch_year).all()
    count = 0
    for student in students:
        result = check_eligibility(
            student=student,
            drive=drive,
            allow_placed_to_reapply=current_app.config.get('ALLOW_PLACED_STUDENTS_TO_REAPPLY', False),
            dream_multiplier=current_app.config.get('MIN_PACKAGE_MULTIPLIER_FOR_DREAM', 1.5)
        )
        if result.is_eligible and student.user:
            msg = (
                f"New Eligible Drive: {drive.company.name} has posted '{drive.title}' "
                f"({drive.package_or_stipend} LPA). Deadline: {drive.last_date.strftime('%d %b %Y')}."
            )
            send_notification(
                user_id=student.user.user_id,
                message=msg,
                email_subject=f"New Drive Alert: {drive.company.name} - {drive.title}",
                email_body=(
                    f"You are eligible to apply for '{drive.title}' at {drive.company.name}.\n"
                    f"Package/Stipend: {drive.package_or_stipend} LPA\n"
                    f"Minimum CGPA: {drive.min_cgpa}\n"
                    f"Last Date to Apply: {drive.last_date.strftime('%d %b %Y')}\n\n"
                    f"Log in to the portal to apply with one click."
                )
            )
            count += 1
    return count


def notify_student_round_update(application, round_name, result, remarks=None):
    """
    Notifies a student when their round status or interview result is updated.
    """
    if not application.student or not application.student.user:
        return
    
    comp_name = application.drive.company.name
    drive_title = application.drive.title
    remarks_str = f" Notes: {remarks}" if remarks else ""
    
    msg = f"Round Update ({comp_name} - {drive_title}): Result for '{round_name}' is '{result.upper()}'.{remarks_str}"
    send_notification(
        user_id=application.student.user.user_id,
        message=msg,
        email_subject=f"Round Result Update: {comp_name} - {round_name}",
        email_body=(
            f"Your application status for {comp_name} ({drive_title}) has been updated.\n"
            f"Round: {round_name}\n"
            f"Result: {result.upper()}\n"
            f"{remarks_str}\n\n"
            f"Please check the portal for next round schedules and instructions."
        )
    )


def notify_student_selection(application, package, offer_date):
    """
    Notifies a student when they receive a final job or internship offer.
    """
    if not application.student or not application.student.user:
        return
        
    comp_name = application.drive.company.name
    drive_title = application.drive.title
    
    msg = (
        f"🎉 Congratulations! You have received a final offer from {comp_name} for "
        f"'{drive_title}' with a package of {package} LPA! Offer Date: {offer_date.strftime('%d %b %Y')}."
    )
    send_notification(
        user_id=application.student.user.user_id,
        message=msg,
        email_subject=f"🎉 Offer Letter Alert: Congratulations from {comp_name}!",
        email_body=(
            f"Hearty Congratulations!\n\n"
            f"You have been officially selected by {comp_name} for the position of '{drive_title}'.\n"
            f"Package Offered: {package} LPA\n"
            f"Offer Date: {offer_date.strftime('%d %b %Y')}\n\n"
            f"The Training & Placement Office commends your achievement!"
        )
    )
