from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, FloatField, IntegerField, SelectField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange
from app.blueprints.auth.forms import BRANCH_CHOICES

class StudentProfileForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(max=120)])
    roll_no = StringField('Roll Number', render_kw={'readonly': True})
    branch = SelectField('Branch / Department', choices=BRANCH_CHOICES, validators=[DataRequired()])
    cgpa = FloatField('Current CGPA', validators=[
        DataRequired(), 
        NumberRange(min=0.0, max=10.0, message="CGPA must be between 0.00 and 10.00")
    ])
    active_backlogs = IntegerField('Active Backlogs', validators=[
        NumberRange(min=0, max=50, message="Backlogs cannot be negative")
    ])
    passing_year = IntegerField('Batch / Passing Year', validators=[
        DataRequired(),
        NumberRange(min=2020, max=2035)
    ])
    skills = TextAreaField('Key Technical Skills')
    resume = FileField('Upload New Resume (PDF only, max 5MB)', validators=[
        FileAllowed(['pdf'], 'Only PDF files are permitted for resumes.')
    ])
    submit = SubmitField('Save Profile Changes')
