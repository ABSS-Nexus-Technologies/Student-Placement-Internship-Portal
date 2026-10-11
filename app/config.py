import os

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'smart-tpo-super-secret-key-2026-prod-grade')
    
    # Database: SQLite by default, configurable via DATABASE_URL to MySQL or PostgreSQL
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f"sqlite:///{os.path.join(BASE_DIR, 'placement_portal.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Upload settings
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'uploads', 'resumes')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB max upload
    ALLOWED_EXTENSIONS = {'pdf'}
    
    # Email configuration (Flask-Mail)
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', None)
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', None)
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'tpo-noreply@college.edu')
    
    # TPO Placement Policy Settings
    # If True: placed students can only apply to 'dream' drives or higher package
    # If False / strict: placed students cannot apply to any other drive once placed
    ALLOW_PLACED_STUDENTS_TO_REAPPLY = os.environ.get('ALLOW_PLACED_TO_REAPPLY', 'false').lower() in ['true', 'on', '1']
    MIN_PACKAGE_MULTIPLIER_FOR_DREAM = float(os.environ.get('DREAM_MULTIPLIER', 1.5))
    
    # WTForms CSRF
    WTF_CSRF_ENABLED = True
