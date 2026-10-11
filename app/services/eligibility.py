from datetime import date, datetime
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class EligibilityResult:
    is_eligible: bool
    reasons: List[str] = field(default_factory=list)
    failed_criteria: List[str] = field(default_factory=list)
    criteria_status: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    @property
    def reason_summary(self) -> str:
        if self.is_eligible:
            return "Eligible: All criteria met."
        return "Not Eligible: " + "; ".join(self.reasons)


def check_eligibility(
    student, 
    drive, 
    allow_placed_to_reapply: bool = False,
    dream_multiplier: float = 1.5,
    reference_date: Optional[date] = None
) -> EligibilityResult:
    """
    Evaluates student eligibility for a specific drive according to TPO criteria:
    1. CGPA >= drive.min_cgpa
    2. active_backlogs <= drive.max_backlogs
    3. student.branch in drive.allowed_branches (or 'ALL')
    4. student.passing_year == drive.batch_year
    5. drive.last_date >= reference_date (deadline not passed)
    6. TPO already placed policy:
       - If student is not placed, pass.
       - If student is placed and allow_placed_to_reapply is False, fail.
       - If student is placed and allow_placed_to_reapply is True:
         student may only apply if drive package >= (student.highest_offer * dream_multiplier).
    """
    if reference_date is None:
        reference_date = date.today()
    elif isinstance(reference_date, datetime):
        reference_date = reference_date.date()

    reasons: List[str] = []
    failed_criteria: List[str] = []
    criteria_status: Dict[str, Dict[str, Any]] = {}

    # 1. CGPA Check
    cgpa_pass = student.cgpa >= drive.min_cgpa
    criteria_status['cgpa'] = {
        'student_val': student.cgpa,
        'required_val': drive.min_cgpa,
        'passed': cgpa_pass
    }
    if not cgpa_pass:
        failed_criteria.append('cgpa')
        reasons.append(f"CGPA {student.cgpa:.2f} is below minimum requirement of {drive.min_cgpa:.2f}")

    # 2. Backlogs Check
    backlog_pass = student.active_backlogs <= drive.max_backlogs
    criteria_status['backlogs'] = {
        'student_val': student.active_backlogs,
        'required_val': drive.max_backlogs,
        'passed': backlog_pass
    }
    if not backlog_pass:
        failed_criteria.append('backlogs')
        reasons.append(
            f"Active backlogs ({student.active_backlogs}) exceed maximum allowed ({drive.max_backlogs})"
        )

    # 3. Branch Check
    student_branch = (student.branch or '').strip().upper()
    allowed_branches_list = drive.allowed_branches_list
    branch_pass = ('ALL' in allowed_branches_list) or (student_branch in allowed_branches_list)
    criteria_status['branch'] = {
        'student_val': student_branch,
        'required_val': drive.allowed_branches,
        'passed': branch_pass
    }
    if not branch_pass:
        failed_criteria.append('branch')
        reasons.append(
            f"Branch '{student_branch}' is not eligible (allowed: {drive.allowed_branches})"
        )

    # 4. Batch / Passing Year Check
    year_pass = student.passing_year == drive.batch_year
    criteria_status['batch_year'] = {
        'student_val': student.passing_year,
        'required_val': drive.batch_year,
        'passed': year_pass
    }
    if not year_pass:
        failed_criteria.append('batch_year')
        reasons.append(
            f"Passing year {student.passing_year} does not match required batch year {drive.batch_year}"
        )

    # 5. Application Deadline Check
    drive_last_date = drive.last_date
    if isinstance(drive_last_date, datetime):
        drive_last_date = drive_last_date.date()
    deadline_pass = drive_last_date >= reference_date
    criteria_status['deadline'] = {
        'student_val': reference_date.isoformat(),
        'required_val': drive_last_date.isoformat(),
        'passed': deadline_pass
    }
    if not deadline_pass:
        failed_criteria.append('deadline')
        reasons.append(f"Application deadline has passed ({drive_last_date.strftime('%Y-%m-%d')})")

    # 6. Already Placed Policy Check
    placed_pass = True
    is_placed = getattr(student, 'is_placed', False)
    highest_offer = getattr(student, 'highest_offer', 0.0)
    
    if is_placed:
        if not allow_placed_to_reapply:
            placed_pass = False
            failed_criteria.append('already_placed')
            reasons.append("TPO Policy: Student is already placed and cannot apply to further drives.")
        else:
            # Dream drive rule: package must be >= highest_offer * dream_multiplier
            min_dream_package = highest_offer * dream_multiplier
            if drive.type == 'placement' and drive.package_or_stipend < min_dream_package:
                placed_pass = False
                failed_criteria.append('already_placed')
                reasons.append(
                    f"TPO Dream Policy: Current offer is {highest_offer} LPA. "
                    f"Eligible only for drives offering at least {min_dream_package:.2f} LPA (found {drive.package_or_stipend:.2f} LPA)."
                )

    criteria_status['placed_policy'] = {
        'student_is_placed': is_placed,
        'highest_offer': highest_offer,
        'passed': placed_pass
    }

    is_eligible = len(failed_criteria) == 0
    if is_eligible:
        reasons.append("All eligibility criteria met.")

    return EligibilityResult(
        is_eligible=is_eligible,
        reasons=reasons,
        failed_criteria=failed_criteria,
        criteria_status=criteria_status
    )
