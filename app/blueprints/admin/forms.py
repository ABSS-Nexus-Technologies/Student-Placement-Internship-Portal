from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, TextAreaField, SelectField, IntegerField, DateField, SubmitField
from wtforms.validators import DataRequired, Optional, Length, NumberRange
from app.blueprints.auth.forms import BRANCH_CHOICES

AUDIENCE_CHOICES = [
    ('all', 'Entire Portal (All Students & Companies)'),
    ('students', 'All Students'),
    ('companies', 'All Registered Companies'),
    ('branch', 'Specific Branch Students'),
    ('batch', 'Specific Batch Year Students')
]

REPORT_TYPE_CHOICES = [
    ('student_wise', 'Student-Wise Detailed Report'),
    ('company_wise', 'Company-Wise Placement Summary'),
    ('branch_wise', 'Branch-Wise Analytics Report'),
    ('year_wise', 'Year-Wise Batch Comparison Report')
]

class BulkImportForm(FlaskForm):
    file = FileField('Excel or CSV Student List', validators=[
        FileRequired(message="Please select a file to upload."),
        FileAllowed(['xlsx', 'xls', 'csv'], 'Only .xlsx, .xls, and .csv files are supported.')
    ])
    submit = SubmitField('Upload and Process Bulk Import')


class AnnouncementForm(FlaskForm):
    target_audience = SelectField('Target Audience', choices=AUDIENCE_CHOICES, default='all')
    branch = SelectField('Target Branch (if branch selected)', choices=[('', 'All Branches')] + BRANCH_CHOICES, validators=[Optional()])
    batch_year = IntegerField('Target Batch Year (if batch selected)', validators=[Optional(), NumberRange(min=2020, max=2035)])
    subject = StringField('Announcement Subject', validators=[DataRequired(), Length(max=150)])
    message = TextAreaField('Announcement Message Body', validators=[DataRequired()])
    submit = SubmitField('Broadcast Announcement')


class ReportFilterForm(FlaskForm):
    report_type = SelectField('Select Report Format', choices=REPORT_TYPE_CHOICES, default='student_wise')
    batch_year = IntegerField('Filter by Batch Year', validators=[Optional(), NumberRange(min=2020, max=2035)])
    branch = SelectField('Filter by Branch', choices=[('', 'All Branches')] + BRANCH_CHOICES, validators=[Optional()])
    company_id = SelectField('Filter by Company', choices=[(0, 'All Companies')], coerce=int, validators=[Optional()])
    start_date = DateField('From Date', format='%Y-%m-%d', validators=[Optional()])
    end_date = DateField('To Date', format='%Y-%m-%d', validators=[Optional()])
    submit = SubmitField('Generate & Download Styled Excel')
