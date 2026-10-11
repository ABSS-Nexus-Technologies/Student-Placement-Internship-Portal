from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    user_id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'student', 'company', 'admin'
    status = db.Column(db.String(20), nullable=False, default='active')  # 'active', 'pending', 'rejected'
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    student = db.relationship('Student', backref='user', uselist=False, cascade='all, delete-orphan')
    company = db.relationship('Company', backref='user', uselist=False, cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    activities = db.relationship('ActivityLog', backref='user', lazy='dynamic')
    
    def get_id(self):
        return str(self.user_id)
        
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    def is_admin(self):
        return self.role == 'admin'
        
    def is_company(self):
        return self.role == 'company'
        
    def is_student(self):
        return self.role == 'student'

    def __repr__(self):
        return f'<User {self.email} ({self.role})>'


class Student(db.Model):
    __tablename__ = 'students'
    
    student_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    roll_no = db.Column(db.String(50), unique=True, nullable=False, index=True)
    branch = db.Column(db.String(50), nullable=False)  # 'CSE', 'IT', 'ECE', 'EEE', 'MECH', 'CIVIL'
    cgpa = db.Column(db.Float, nullable=False)
    active_backlogs = db.Column(db.Integer, nullable=False, default=0)
    passing_year = db.Column(db.Integer, nullable=False)
    skills = db.Column(db.Text, default='')
    resume_path = db.Column(db.String(255), nullable=True)
    
    # Relationships
    applications = db.relationship('Application', backref='student', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def is_placed(self):
        for app in self.applications:
            if app.placement and app.placement.offer_status in ['offered', 'accepted']:
                return True
        return False

    @property
    def highest_offer(self):
        highest = 0.0
        for app in self.applications:
            if app.placement and app.placement.offer_status in ['offered', 'accepted']:
                if app.placement.package and app.placement.package > highest:
                    highest = app.placement.package
        return highest

    def __repr__(self):
        return f'<Student {self.roll_no} - {self.name}>'


class Company(db.Model):
    __tablename__ = 'companies'
    
    company_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    industry = db.Column(db.String(100), nullable=True)
    website = db.Column(db.String(200), nullable=True)
    hr_contact = db.Column(db.String(100), nullable=True)
    approval_status = db.Column(db.String(20), nullable=False, default='pending')  # 'pending', 'approved', 'rejected'
    
    # Relationships
    drives = db.relationship('Drive', backref='company', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Company {self.name}>'


class Drive(db.Model):
    __tablename__ = 'drives'
    
    drive_id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.company_id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    type = db.Column(db.String(20), nullable=False, default='placement')  # 'placement', 'internship'
    package_or_stipend = db.Column(db.Float, nullable=False)  # LPA for placement, stipend/month for internship
    min_cgpa = db.Column(db.Float, nullable=False, default=0.0)
    max_backlogs = db.Column(db.Integer, nullable=False, default=0)
    allowed_branches = db.Column(db.String(255), nullable=False, default='ALL')  # e.g. 'CSE,IT,ECE' or 'ALL'
    batch_year = db.Column(db.Integer, nullable=False)
    last_date = db.Column(db.Date, nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='active')  # 'active', 'completed', 'cancelled'
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    applications = db.relationship('Application', backref='drive', lazy='dynamic', cascade='all, delete-orphan')
    rounds = db.relationship('Round', backref='drive', lazy='dynamic', cascade='all, delete-orphan', order_by='Round.round_date')

    @property
    def allowed_branches_list(self):
        if not self.allowed_branches or self.allowed_branches.strip().upper() == 'ALL':
            return ['ALL']
        return [b.strip().upper() for b in self.allowed_branches.split(',') if b.strip()]

    def __repr__(self):
        return f'<Drive {self.title} - {self.company.name if self.company else "Unknown"}>'


class Application(db.Model):
    __tablename__ = 'applications'
    __table_args__ = (
        db.UniqueConstraint('drive_id', 'student_id', name='uq_drive_student_application'),
    )
    
    application_id = db.Column(db.Integer, primary_key=True)
    drive_id = db.Column(db.Integer, db.ForeignKey('drives.drive_id', ondelete='CASCADE'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.student_id', ondelete='CASCADE'), nullable=False)
    applied_on = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    current_round = db.Column(db.String(100), default='Applied')
    status = db.Column(db.String(20), nullable=False, default='applied')  # 'applied', 'shortlisted', 'rejected', 'selected'
    
    # Relationships
    round_results = db.relationship('RoundResult', backref='application', lazy='dynamic', cascade='all, delete-orphan')
    placement = db.relationship('Placement', backref='application', uselist=False, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Application {self.application_id}: Student {self.student_id} -> Drive {self.drive_id}>'


class Round(db.Model):
    __tablename__ = 'rounds'
    
    round_id = db.Column(db.Integer, primary_key=True)
    drive_id = db.Column(db.Integer, db.ForeignKey('drives.drive_id', ondelete='CASCADE'), nullable=False)
    round_name = db.Column(db.String(100), nullable=False)
    round_date = db.Column(db.DateTime, nullable=False)
    mode = db.Column(db.String(20), nullable=False, default='online')  # 'online', 'offline'
    
    # Relationships
    results = db.relationship('RoundResult', backref='round', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Round {self.round_name} (Drive {self.drive_id})>'


class RoundResult(db.Model):
    __tablename__ = 'round_results'
    __table_args__ = (
        db.UniqueConstraint('application_id', 'round_id', name='uq_application_round_result'),
    )
    
    result_id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('applications.application_id', ondelete='CASCADE'), nullable=False)
    round_id = db.Column(db.Integer, db.ForeignKey('rounds.round_id', ondelete='CASCADE'), nullable=False)
    result = db.Column(db.String(20), nullable=False, default='pending')  # 'cleared', 'failed', 'absent', 'pending'
    remarks = db.Column(db.String(255), nullable=True)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<RoundResult App {self.application_id} Round {self.round_id}: {self.result}>'


class Placement(db.Model):
    __tablename__ = 'placements'
    
    placement_id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('applications.application_id', ondelete='CASCADE'), unique=True, nullable=False)
    offer_date = db.Column(db.Date, nullable=False)
    package = db.Column(db.Float, nullable=False)  # in LPA
    offer_status = db.Column(db.String(20), nullable=False, default='offered')  # 'offered', 'accepted', 'declined'

    def __repr__(self):
        return f'<Placement App {self.application_id}: {self.package} LPA ({self.offer_status})>'


class Notification(db.Model):
    __tablename__ = 'notifications'
    
    notification_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    sent_on = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    is_read = db.Column(db.Boolean, default=False, nullable=False)

    def __repr__(self):
        return f'<Notification {self.notification_id} for User {self.user_id}>'


class ActivityLog(db.Model):
    __tablename__ = 'activity_log'
    
    log_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='SET NULL'), nullable=True)
    action = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<ActivityLog {self.log_id}: {self.action}>'
