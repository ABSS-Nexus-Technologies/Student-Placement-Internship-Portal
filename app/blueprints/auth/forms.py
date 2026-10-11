from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, FloatField, IntegerField, SelectField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange, ValidationError
from app.models import User, Student

BRANCH_CHOICES = [
    ('CSE', 'Computer Science & Engineering (CSE)'),
    ('IT', 'Information Technology (IT)'),
    ('ECE', 'Electronics & Communication (ECE)'),
    ('EEE', 'Electrical & Electronics (EEE)'),
    ('MECH', 'Mechanical Engineering (MECH)'),
    ('CIVIL', 'Civil Engineering (CIVIL)')
]

class LoginForm(FlaskForm):
    email = StringField('Email Address', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class StudentRegisterForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(max=120)])
    roll_no = StringField('Roll Number', validators=[DataRequired(), Length(max=50)])
    email = StringField('College Email', validators=[DataRequired(), Email(), Length(max=120)])
    branch = SelectField('Branch / Department', choices=BRANCH_CHOICES, validators=[DataRequired()])
    cgpa = FloatField('Current CGPA (0.0 to 10.0)', validators=[
        DataRequired(), 
        NumberRange(min=0.0, max=10.0, message="CGPA must be between 0.00 and 10.00")
    ])
    active_backlogs = IntegerField('Active Backlogs', default=0, validators=[
        NumberRange(min=0, max=50, message="Backlogs cannot be negative")
    ])
    passing_year = IntegerField('Graduation / Batch Year', validators=[
        DataRequired(),
        NumberRange(min=2020, max=2035, message="Please enter a valid batch year")
    ])
    skills = TextAreaField('Key Technical Skills (e.g. Python, React, SQL, AWS)')
    resume = FileField('Resume (PDF format only, max 5MB)', validators=[
        FileAllowed(['pdf'], 'Only PDF files are permitted for resumes.')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(), 
        Length(min=6, message="Password must be at least 6 characters.")
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(), 
        EqualTo('password', message="Passwords must match.")
    ])
    submit = SubmitField('Complete Registration')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.strip().lower()).first():
            raise ValidationError('This email address is already registered.')

    def validate_roll_no(self, field):
        if Student.query.filter_by(roll_no=field.data.strip().upper()).first():
            raise ValidationError('This Roll Number is already registered.')


class CompanyRegisterForm(FlaskForm):
    name = StringField('Company / Corporate Name', validators=[DataRequired(), Length(max=150)])
    email = StringField('Corporate HR Email', validators=[DataRequired(), Email(), Length(max=120)])
    industry = StringField('Industry Domain (e.g. IT & Software, Fintech, Core Engineering)', validators=[DataRequired(), Length(max=100)])
    website = StringField('Company Website (e.g. https://company.com)', validators=[Length(max=200)])
    hr_contact = StringField('HR Contact Person & Phone', validators=[DataRequired(), Length(max=100)])
    password = PasswordField('Password', validators=[
        DataRequired(), 
        Length(min=6, message="Password must be at least 6 characters.")
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(), 
        EqualTo('password', message="Passwords must match.")
    ])
    submit = SubmitField('Register Company (Requires TPO Approval)')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.strip().lower()).first():
            raise ValidationError('This email address is already registered.')
