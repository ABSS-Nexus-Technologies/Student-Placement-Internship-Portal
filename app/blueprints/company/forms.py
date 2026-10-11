from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, IntegerField, SelectField, SelectMultipleField, TextAreaField, DateField, DateTimeLocalField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional
from app.blueprints.auth.forms import BRANCH_CHOICES

DRIVE_TYPE_CHOICES = [
    ('placement', 'Full-time Placement (LPA)'),
    ('internship', 'Internship / Pre-Placement Offer (PPO)')
]

ROUND_MODE_CHOICES = [
    ('online', 'Online / Virtual Platform'),
    ('offline', 'In-Person / On Campus')
]

ROUND_RESULT_CHOICES = [
    ('cleared', 'Cleared / Advanced to Next Stage'),
    ('failed', 'Eliminated / Not Cleared'),
    ('absent', 'Absent'),
    ('pending', 'Pending Evaluation')
]

OFFER_STATUS_CHOICES = [
    ('offered', 'Offer Extended'),
    ('accepted', 'Offer Accepted by Student'),
    ('declined', 'Offer Declined by Student')
]

class CompanyProfileForm(FlaskForm):
    name = StringField('Company Name', validators=[DataRequired(), Length(max=150)])
    industry = StringField('Industry Domain', validators=[DataRequired(), Length(max=100)])
    website = StringField('Website URL', validators=[Optional(), Length(max=200)])
    hr_contact = StringField('HR Contact Person & Email/Phone', validators=[DataRequired(), Length(max=100)])
    submit = SubmitField('Update Company Profile')


class DriveForm(FlaskForm):
    title = StringField('Drive Title / Role', validators=[DataRequired(), Length(max=150)])
    type = SelectField('Drive Type', choices=DRIVE_TYPE_CHOICES, validators=[DataRequired()])
    package_or_stipend = FloatField('Package (LPA) or Monthly Stipend (INR)', validators=[
        DataRequired(), 
        NumberRange(min=0.1, message="Please enter a valid package/stipend")
    ])
    min_cgpa = FloatField('Minimum CGPA Required', default=6.0, validators=[
        DataRequired(),
        NumberRange(min=0.0, max=10.0, message="CGPA must be between 0.00 and 10.00")
    ])
    max_backlogs = IntegerField('Maximum Allowed Active Backlogs', default=0, validators=[
        NumberRange(min=0, max=10, message="Backlogs cannot be negative")
    ])
    allowed_branches = SelectMultipleField(
        'Eligible Branches (select multiple or all)',
        choices=[('ALL', 'ALL Branches (Open to All)')] + BRANCH_CHOICES,
        default=['ALL'],
        validators=[DataRequired()]
    )
    batch_year = IntegerField('Target Batch Year', validators=[
        DataRequired(),
        NumberRange(min=2020, max=2035)
    ])
    last_date = DateField('Application Deadline (YYYY-MM-DD)', format='%Y-%m-%d', validators=[DataRequired()])
    description = TextAreaField('Job Description, Responsibilities & Eligibility Details')
    status = SelectField('Drive Status', choices=[('active', 'Active'), ('completed', 'Completed'), ('cancelled', 'Cancelled')], default='active')
    submit = SubmitField('Publish Campus Drive')


class RoundForm(FlaskForm):
    round_name = StringField('Round Title (e.g. Online Aptitude Test, Tech Interview 1, HR)', validators=[DataRequired(), Length(max=100)])
    round_date = DateTimeLocalField('Scheduled Date & Time', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    mode = SelectField('Assessment Mode', choices=ROUND_MODE_CHOICES, validators=[DataRequired()])
    submit = SubmitField('Add Round')


class RoundResultForm(FlaskForm):
    result = SelectField('Round Status', choices=ROUND_RESULT_CHOICES, validators=[DataRequired()])
    remarks = StringField('Remarks / Feedback', validators=[Optional(), Length(max=255)])
    submit = SubmitField('Save Result')


class FinalSelectionForm(FlaskForm):
    package = FloatField('Final Offered Package (LPA)', validators=[
        DataRequired(), 
        NumberRange(min=0.1, message="Enter a valid package amount")
    ])
    offer_date = DateField('Offer Date', format='%Y-%m-%d', validators=[DataRequired()])
    offer_status = SelectField('Offer Status', choices=OFFER_STATUS_CHOICES, default='offered')
    submit = SubmitField('Confirm Final Selection & Extend Offer')
