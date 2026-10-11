from datetime import date, timedelta
from app.services.eligibility import check_eligibility

class MockStudent:
    def __init__(self, name="Test Student", roll_no="22CS0101", branch="CSE", cgpa=8.5, backlogs=0, passing_year=2026, is_placed=False, highest_offer=0.0):
        self.name = name
        self.roll_no = roll_no
        self.branch = branch
        self.cgpa = cgpa
        self.active_backlogs = backlogs
        self.passing_year = passing_year
        self.is_placed = is_placed
        self.highest_offer = highest_offer

class MockDrive:
    def __init__(self, title="Test Role", drive_type="placement", package=12.0, min_cgpa=7.0, max_backlogs=0, allowed_branches="CSE,IT", batch_year=2026, last_date=None):
        self.title = title
        self.type = drive_type
        self.package_or_stipend = package
        self.min_cgpa = min_cgpa
        self.max_backlogs = max_backlogs
        self.allowed_branches = allowed_branches
        self.batch_year = batch_year
        self.last_date = last_date or (date.today() + timedelta(days=10))

    @property
    def allowed_branches_list(self):
        if not self.allowed_branches or self.allowed_branches.strip().upper() == 'ALL':
            return ['ALL']
        return [b.strip().upper() for b in self.allowed_branches.split(',') if b.strip()]


def test_eligible_when_all_criteria_met():
    student = MockStudent(branch="CSE", cgpa=8.5, backlogs=0, passing_year=2026)
    drive = MockDrive(min_cgpa=7.5, max_backlogs=0, allowed_branches="CSE,IT", batch_year=2026)
    res = check_eligibility(student, drive)
    assert res.is_eligible is True
    assert len(res.failed_criteria) == 0
    assert "All eligibility criteria met" in res.reasons[0]


def test_ineligible_due_to_low_cgpa():
    student = MockStudent(cgpa=6.9)
    drive = MockDrive(min_cgpa=7.0)
    res = check_eligibility(student, drive)
    assert res.is_eligible is False
    assert "cgpa" in res.failed_criteria
    assert any("below minimum requirement" in r for r in res.reasons)


def test_ineligible_due_to_active_backlogs():
    student = MockStudent(backlogs=2)
    drive = MockDrive(max_backlogs=0)
    res = check_eligibility(student, drive)
    assert res.is_eligible is False
    assert "backlogs" in res.failed_criteria
    assert any("exceed maximum allowed" in r for r in res.reasons)


def test_ineligible_due_to_branch():
    student = MockStudent(branch="MECH")
    drive = MockDrive(allowed_branches="CSE,IT")
    res = check_eligibility(student, drive)
    assert res.is_eligible is False
    assert "branch" in res.failed_criteria
    assert any("Branch 'MECH' is not eligible" in r for r in res.reasons)


def test_eligible_when_branch_is_all():
    student = MockStudent(branch="CIVIL")
    drive = MockDrive(allowed_branches="ALL")
    res = check_eligibility(student, drive)
    assert res.is_eligible is True
    assert "branch" not in res.failed_criteria


def test_ineligible_due_to_passing_year_mismatch():
    student = MockStudent(passing_year=2025)
    drive = MockDrive(batch_year=2026)
    res = check_eligibility(student, drive)
    assert res.is_eligible is False
    assert "batch_year" in res.failed_criteria
    assert any("Passing year 2025 does not match" in r for r in res.reasons)


def test_ineligible_due_to_passed_deadline():
    student = MockStudent()
    past_date = date.today() - timedelta(days=2)
    drive = MockDrive(last_date=past_date)
    res = check_eligibility(student, drive)
    assert res.is_eligible is False
    assert "deadline" in res.failed_criteria
    assert any("deadline has passed" in r for r in res.reasons)


def test_already_placed_policy_strict():
    # When already placed and policy disallows further applications
    student = MockStudent(is_placed=True, highest_offer=10.0)
    drive = MockDrive(package=15.0)
    res = check_eligibility(student, drive, allow_placed_to_reapply=False)
    assert res.is_eligible is False
    assert "already_placed" in res.failed_criteria


def test_already_placed_policy_dream_allowed():
    # Placed with 10 LPA. Drive offers 18 LPA. Multiplier is 1.5 -> requires >= 15 LPA.
    student = MockStudent(is_placed=True, highest_offer=10.0)
    drive = MockDrive(package=18.0)
    res = check_eligibility(student, drive, allow_placed_to_reapply=True, dream_multiplier=1.5)
    assert res.is_eligible is True
    assert "already_placed" not in res.failed_criteria


def test_already_placed_policy_dream_rejected_low_package():
    # Placed with 10 LPA. Drive offers 12 LPA. Multiplier is 1.5 -> requires >= 15 LPA.
    student = MockStudent(is_placed=True, highest_offer=10.0)
    drive = MockDrive(package=12.0)
    res = check_eligibility(student, drive, allow_placed_to_reapply=True, dream_multiplier=1.5)
    assert res.is_eligible is False
    assert "already_placed" in res.failed_criteria
    assert any("TPO Dream Policy" in r for r in res.reasons)


def test_multiple_failure_reasons_accumulated():
    student = MockStudent(cgpa=5.5, backlogs=3, branch="CIVIL", passing_year=2024)
    drive = MockDrive(min_cgpa=8.0, max_backlogs=0, allowed_branches="CSE", batch_year=2026)
    res = check_eligibility(student, drive)
    assert res.is_eligible is False
    assert set(res.failed_criteria) == {"cgpa", "backlogs", "branch", "batch_year"}
    assert len(res.reasons) == 4
