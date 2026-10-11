import pandas as pd
import re
from datetime import datetime
from app.models import db, User, Student, ActivityLog

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')

def normalize_column_name(col):
    return str(col).strip().lower().replace(' ', '_').replace('-', '_')

def bulk_import_students(file_stream, filename, admin_user_id=None):
    """
    Imports students from a CSV or Excel file.
    Validates:
    - Required fields: name, roll_no, email, branch, cgpa, passing_year
    - Duplicate roll number in file or DB
    - Duplicate email in file or DB
    - CGPA between 0.0 and 10.0
    - Passing year as valid 4-digit integer
    - Backlogs >= 0
    Returns:
    {
        'total_rows': int,
        'success_count': int,
        'error_count': int,
        'errors': list of {'row': int, 'roll_no': str, 'name': str, 'error': str},
        'imported_students': list
    }
    """
    filename_lower = filename.lower()
    try:
        if filename_lower.endswith('.csv'):
            df = pd.read_csv(file_stream)
        elif filename_lower.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file_stream)
        else:
            return {
                'total_rows': 0,
                'success_count': 0,
                'error_count': 1,
                'errors': [{'row': 0, 'roll_no': '-', 'name': '-', 'error': 'Unsupported file format. Please upload .xlsx, .xls, or .csv'}],
                'imported_students': []
            }
    except Exception as e:
        return {
            'total_rows': 0,
            'success_count': 0,
            'error_count': 1,
            'errors': [{'row': 0, 'roll_no': '-', 'name': '-', 'error': f'Failed to parse file: {str(e)}'}],
            'imported_students': []
        }

    # Normalize column names
    column_mapping = {}
    for col in df.columns:
        norm = normalize_column_name(col)
        if norm in ['roll_no', 'rollno', 'roll_number', 'roll']:
            column_mapping[col] = 'roll_no'
        elif norm in ['name', 'student_name', 'full_name']:
            column_mapping[col] = 'name'
        elif norm in ['email', 'email_address', 'mail']:
            column_mapping[col] = 'email'
        elif norm in ['branch', 'department', 'dept', 'stream']:
            column_mapping[col] = 'branch'
        elif norm in ['cgpa', 'gpa']:
            column_mapping[col] = 'cgpa'
        elif norm in ['passing_year', 'batch_year', 'year', 'passout_year', 'batch']:
            column_mapping[col] = 'passing_year'
        elif norm in ['active_backlogs', 'backlogs', 'backlog', 'active_backlog']:
            column_mapping[col] = 'active_backlogs'
        elif norm in ['skills', 'skill_set']:
            column_mapping[col] = 'skills'

    df.rename(columns=column_mapping, inplace=True)

    required_fields = ['name', 'roll_no', 'email', 'branch', 'cgpa', 'passing_year']
    missing_fields = [f for f in required_fields if f not in df.columns]
    if missing_fields:
        return {
            'total_rows': len(df),
            'success_count': 0,
            'error_count': len(df),
            'errors': [{
                'row': 0,
                'roll_no': '-',
                'name': '-',
                'error': f"Missing required columns in file: {', '.join(missing_fields)}"
            }],
            'imported_students': []
        }

    # Query existing database roll numbers and emails in batch
    existing_rolls = {r[0].strip().upper() for r in db.session.query(Student.roll_no).all()}
    existing_emails = {e[0].strip().lower() for e in db.session.query(User.email).all()}

    file_rolls_seen = set()
    file_emails_seen = set()

    errors = []
    imported_students = []

    for index, row in df.iterrows():
        excel_row_num = index + 2  # 1-indexed, +1 for header
        row_roll = str(row.get('roll_no', '')).strip().upper()
        row_name = str(row.get('name', '')).strip()
        row_email = str(row.get('email', '')).strip().lower()
        row_branch = str(row.get('branch', '')).strip().upper()

        if pd.isna(row_roll) or not row_roll or row_roll == 'NAN':
            errors.append({'row': excel_row_num, 'roll_no': '-', 'name': row_name, 'error': 'Roll Number is missing'})
            continue

        if pd.isna(row_name) or not row_name or row_name == 'NAN':
            errors.append({'row': excel_row_num, 'roll_no': row_roll, 'name': '-', 'error': 'Student Name is missing'})
            continue

        if pd.isna(row_email) or not row_email or not EMAIL_REGEX.match(row_email):
            errors.append({'row': excel_row_num, 'roll_no': row_roll, 'name': row_name, 'error': f'Invalid email address: {row_email}'})
            continue

        # Duplicate Checks
        if row_roll in existing_rolls:
            errors.append({'row': excel_row_num, 'roll_no': row_roll, 'name': row_name, 'error': f'Duplicate Roll Number: {row_roll} already exists in database'})
            continue

        if row_roll in file_rolls_seen:
            errors.append({'row': excel_row_num, 'roll_no': row_roll, 'name': row_name, 'error': f'Duplicate Roll Number in upload file: {row_roll}'})
            continue

        if row_email in existing_emails:
            errors.append({'row': excel_row_num, 'roll_no': row_roll, 'name': row_name, 'error': f'Duplicate Email: {row_email} already exists in database'})
            continue

        if row_email in file_emails_seen:
            errors.append({'row': excel_row_num, 'roll_no': row_roll, 'name': row_name, 'error': f'Duplicate Email in upload file: {row_email}'})
            continue

        # CGPA Validation: outside 0 to 10
        try:
            row_cgpa = float(row.get('cgpa', -1))
            if row_cgpa < 0.0 or row_cgpa > 10.0 or pd.isna(row_cgpa):
                errors.append({'row': excel_row_num, 'roll_no': row_roll, 'name': row_name, 'error': f'Invalid CGPA: {row_cgpa} (must be between 0.0 and 10.0)'})
                continue
        except (ValueError, TypeError):
            errors.append({'row': excel_row_num, 'roll_no': row_roll, 'name': row_name, 'error': f"Invalid CGPA value: {row.get('cgpa')}"})
            continue

        # Passing Year Validation
        try:
            row_year = int(row.get('passing_year', 0))
            if row_year < 2000 or row_year > 2050:
                errors.append({'row': excel_row_num, 'roll_no': row_roll, 'name': row_name, 'error': f'Invalid Passing Year: {row_year}'})
                continue
        except (ValueError, TypeError):
            errors.append({'row': excel_row_num, 'roll_no': row_roll, 'name': row_name, 'error': f"Invalid Passing Year value: {row.get('passing_year')}"})
            continue

        # Backlogs Validation
        try:
            raw_backlogs = row.get('active_backlogs', 0)
            row_backlogs = int(raw_backlogs) if not pd.isna(raw_backlogs) else 0
            if row_backlogs < 0:
                errors.append({'row': excel_row_num, 'roll_no': row_roll, 'name': row_name, 'error': 'Active backlogs cannot be negative'})
                continue
        except (ValueError, TypeError):
            row_backlogs = 0

        skills_val = str(row.get('skills', '')) if not pd.isna(row.get('skills')) else ''

        # Mark as seen
        file_rolls_seen.add(row_roll)
        file_emails_seen.add(row_email)

        # Create User and Student objects
        try:
            user = User(
                email=row_email,
                role='student',
                status='active'
            )
            # Default password is roll_no
            user.set_password(row_roll)
            db.session.add(user)
            db.session.flush()  # to obtain user_id

            student = Student(
                user_id=user.user_id,
                name=row_name,
                roll_no=row_roll,
                branch=row_branch,
                cgpa=round(row_cgpa, 2),
                active_backlogs=row_backlogs,
                passing_year=row_year,
                skills=skills_val
            )
            db.session.add(student)
            imported_students.append({
                'roll_no': row_roll,
                'name': row_name,
                'email': row_email,
                'branch': row_branch,
                'cgpa': row_cgpa
            })
            existing_rolls.add(row_roll)
            existing_emails.add(row_email)

        except Exception as insert_err:
            errors.append({'row': excel_row_num, 'roll_no': row_roll, 'name': row_name, 'error': f'Database error: {str(insert_err)}'})

    if imported_students:
        try:
            db.session.commit()
            if admin_user_id:
                log = ActivityLog(
                    user_id=admin_user_id,
                    action=f"Bulk imported {len(imported_students)} students from file '{filename}'"
                )
                db.session.add(log)
                db.session.commit()
        except Exception as commit_err:
            db.session.rollback()
            return {
                'total_rows': len(df),
                'success_count': 0,
                'error_count': len(df),
                'errors': [{'row': 0, 'roll_no': '-', 'name': '-', 'error': f'Commit failed: {str(commit_err)}'}],
                'imported_students': []
            }

    return {
        'total_rows': len(df),
        'success_count': len(imported_students),
        'error_count': len(errors),
        'errors': errors,
        'imported_students': imported_students
    }
