import os
from datetime import datetime, timezone
from functools import wraps
from flask import Flask, render_template, abort, current_app
from flask_login import LoginManager, current_user, login_required
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail

from app.config import Config
from app.models import db, User, Notification

login_manager = LoginManager()
csrf = CSRFProtect()
mail = Mail()


def role_required(*allowed_roles):
    """
    Decorator restricting route access to specified roles.
    Raises 403 HTTP Forbidden if current_user's role does not match.
    """
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return login_manager.unauthorized()
            if current_user.role not in allowed_roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = "Please sign in to access this portal section."
    login_manager.login_message_category = "warning"
    
    csrf.init_app(app)
    mail.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Context processors for navigation and notifications
    @app.context_processor
    def inject_context():
        unread_notifs_count = 0
        if current_user.is_authenticated:
            unread_notifs_count = Notification.query.filter_by(
                user_id=current_user.user_id,
                is_read=False
            ).count()
        return {
            'unread_notifs_count': unread_notifs_count,
            'current_year': datetime.now(timezone.utc).year,
            'now': datetime.now(timezone.utc)
        }

    # Register blueprints
    from app.blueprints.auth.routes import auth_bp
    from app.blueprints.student.routes import student_bp
    from app.blueprints.company.routes import company_bp
    from app.blueprints.admin.routes import admin_bp
    from app.blueprints.main.routes import main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(student_bp, url_prefix='/student')
    app.register_blueprint(company_bp, url_prefix='/company')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # Error Handlers
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    return app
