"""Fill FixMyCampus with demo data for presentations.  DEMO ONLY - known passwords!

    python seed_demo.py            # add demo accounts + sample issues
    python seed_demo.py --reset    # delete the database first, then seed
"""
import os
import random
import sys
from datetime import timedelta

DEMO_ADMIN = ("admin@fixmycampus.edu", "Admin@1234")
DEMO_STAFF = ("staff@fixmycampus.edu", "Staff@1234", "Ravi Kumar (Electrician)")
DEMO_STUDENT = ("student@fixmycampus.edu", "Student@1234", "Demo Student")

if "--reset" in sys.argv:
    from pathlib import Path
    db_file = Path(__file__).resolve().parent / "fixmycampus.db"
    if db_file.exists():
        db_file.unlink()
        print("Old database deleted.")

# Make the first-run admin use the known demo password (only matters on a fresh database).
os.environ.setdefault("ADMIN_EMAIL", DEMO_ADMIN[0])
os.environ.setdefault("ADMIN_PASSWORD", DEMO_ADMIN[1])

from sqlalchemy import select  # noqa: E402

import main  # noqa: E402
from main import Issue, IssueEvent, User, UserRole, hash_password, utcnow  # noqa: E402

SAMPLES = [
    ("Ceiling fan not working", "Electrical", "Block A, Room 204", "High", "Resolved"),
    ("Water leakage near drinking fountain", "Water Supply", "Library, Ground floor", "Urgent", "In Progress"),
    ("Projector not turning on", "Classroom", "Block B, Room 110", "Normal", "Assigned"),
    ("Broken bench in courtyard", "Furniture", "Central Courtyard", "Low", "Submitted"),
    ("Wi-Fi extremely slow in hostel", "Internet", "Boys Hostel, 2nd floor", "High", "Under Review"),
    ("Washroom tap leaking", "Washroom", "Block C, 1st floor", "Normal", "Resolved"),
    ("Dustbins overflowing", "Cleanliness", "Canteen entrance", "Normal", "Closed"),
    ("Loose live wire near staircase", "Safety", "Block A, Staircase 2", "Urgent", "Resolved"),
    ("Streetlight not working", "Electrical", "Main Gate road", "High", "Submitted"),
    ("Whiteboard marker supply empty", "Classroom", "Block B, Room 105", "Low", "Closed"),
    ("Smelly drain in washroom", "Washroom", "Block D, Ground floor", "Normal", "In Progress"),
    ("Chairs broken in seminar hall", "Furniture", "Seminar Hall", "Normal", "Assigned"),
    ("Fire extinguisher expired", "Safety", "Lab corridor", "High", "Under Review"),
    ("No water in hostel washrooms", "Water Supply", "Girls Hostel, 3rd floor", "Urgent", "Resolved"),
    ("Spam posters on notice board", "Other", "Admin building lobby", "Low", "Rejected"),
    ("AC not cooling in computer lab", "Electrical", "Computer Lab 2", "High", "In Progress"),
]

FLOW = ["Submitted", "Under Review", "Assigned", "In Progress", "Resolved", "Closed"]
NOTES = {
    "Under Review": "Request verified by the facility team",
    "Assigned": "Assigned to maintenance staff",
    "In Progress": "Work has started",
    "Resolved": "Problem fixed and checked",
    "Closed": "Closed after reporter confirmation",
    "Rejected": "Not a campus maintenance issue",
}


def get_or_create(db, email, password, name, role, dept=None):
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email, full_name=name, hashed_password=hash_password(password),
                    role=role, department=dept)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def main_seed():
    main.upgrade_db_schema()
    main.seed_default_admin()
    random.seed(7)
    with main.SessionLocal() as db:
        admin = db.scalar(select(User).where(User.email == DEMO_ADMIN[0]))
        staff = get_or_create(db, DEMO_STAFF[0], DEMO_STAFF[1], DEMO_STAFF[2], UserRole.STAFF.value, "Maintenance")
        student = get_or_create(db, DEMO_STUDENT[0], DEMO_STUDENT[1], DEMO_STUDENT[2], UserRole.STUDENT.value, "CSE")

        if db.scalar(select(Issue).limit(1)) is not None:
            print("Issues already exist - skipping sample issues (use --reset for a clean demo).")
        else:
            now = utcnow()
            for index, (title, category, location, priority, final_status) in enumerate(SAMPLES):
                created = now - timedelta(days=random.randint(0, 27), hours=random.randint(0, 20))
                issue = Issue(
                    tracking_id=f"FMC-{0xA1B2C3D4 + index * 0x1F3A5:08X}",
                    title=title,
                    description=f"{title}. Reported at {location}; please check as soon as possible.",
                    category=category, location=location, priority=priority,
                    reporter_name=student.full_name if index % 3 == 0 else random.choice(
                        ["Priya S.", "Rahul M.", "Sneha K.", "Omkar P.", "Ayesha N."]),
                    user_id=student.id if index % 3 == 0 else None,
                    status="Submitted", created_at=created, updated_at=created,
                )
                db.add(issue)
                db.flush()
                db.add(IssueEvent(issue_id=issue.id, status="Submitted", note="Issue reported",
                                  actor="Reporter", created_at=created))
                path = ["Rejected"] if final_status == "Rejected" else FLOW[1:FLOW.index(final_status) + 1]
                when = created
                for step in path:
                    when += timedelta(hours=random.randint(2, 30))
                    issue.status, issue.updated_at = step, when
                    if step == "Assigned":
                        issue.assigned_to_id, issue.assigned_staff_name = staff.id, staff.full_name
                    db.add(IssueEvent(issue_id=issue.id, status=step, note=NOTES[step],
                                      actor=admin.full_name if admin else "Campus Administrator",
                                      created_at=when))
            db.commit()
            print(f"Added {len(SAMPLES)} sample issues with activity timelines.")

    print("\nDemo accounts")
    print(f"  Admin    {DEMO_ADMIN[0]} / {DEMO_ADMIN[1]}   (if the admin already existed, its password is unchanged)")
    print(f"  Staff    {DEMO_STAFF[0]} / {DEMO_STAFF[1]}")
    print(f"  Student  {DEMO_STUDENT[0]} / {DEMO_STUDENT[1]}")


if __name__ == "__main__":
    main_seed()
