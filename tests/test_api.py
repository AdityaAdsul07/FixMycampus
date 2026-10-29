import re

import main
from conftest import ISSUE, login


# ---------- authentication & roles ----------

def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_register_always_creates_student_even_if_admin_requested(client):
    r = client.post("/api/auth/register", json={
        "email": "sneaky@test.edu", "full_name": "Sneaky User",
        "password": "Sneaky1234", "role": "admin"})
    assert r.status_code == 201
    assert r.json()["user"]["role"] == "student"


def test_register_rejects_weak_password_and_bad_email(client):
    base = {"email": "weak@test.edu", "full_name": "Weak Pass"}
    assert client.post("/api/auth/register", json={**base, "password": "short1"}).status_code == 422
    assert client.post("/api/auth/register", json={**base, "password": "onlyletters"}).status_code == 422
    assert client.post("/api/auth/register",
                       json={"email": "not-an-email", "full_name": "X Y", "password": "Valid1234"}).status_code == 422


def test_duplicate_email_rejected(client, student_headers):
    r = client.post("/api/auth/register", json={
        "email": "STUDENT@test.edu", "full_name": "Again", "password": "Student123"})
    assert r.status_code == 400


def test_login_rate_limit(client):
    for _ in range(main.MAX_LOGIN_FAILURES):
        assert client.post("/api/auth/login",
                           json={"email": "admin@test.edu", "password": "wrong"}).status_code == 401
    assert client.post("/api/auth/login",
                       json={"email": "admin@test.edu", "password": "AdminPass123"}).status_code == 429


def test_me_requires_token(client, admin_headers):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers=admin_headers).json()["role"] == "admin"


# ---------- issues ----------

def test_create_issue_anonymously(new_issue):
    assert re.fullmatch(r"FMC-[0-9A-F]{8}", new_issue["tracking_id"])
    assert new_issue["status"] == "Submitted"
    assert new_issue["created_at"].endswith("Z")  # explicit UTC so browsers show local time


def test_issue_validation_trims_whitespace(client):
    bad = {**ISSUE, "title": "   ab   "}
    assert client.post("/api/issues", json=bad).status_code == 422


def test_public_view_hides_reporter(client, new_issue, admin_headers):
    public = client.get(f"/api/issues/{new_issue['tracking_id']}").json()
    assert public["reporter_name"] == "Anonymous"
    full = client.get(f"/api/issues/{new_issue['tracking_id']}", headers=admin_headers).json()
    assert full["reporter_name"] == "Aditya"
    listing = client.get("/api/issues").json()
    assert all(i["reporter_name"] == "Anonymous" for i in listing)


def test_reporter_sees_own_name_and_my_reports(client, student_headers):
    r = client.post("/api/issues", json=ISSUE, headers=student_headers)
    assert r.json()["reporter_name"] == "Aditya"
    mine = client.get("/api/issues?my_reports=true", headers=student_headers).json()
    assert [i["tracking_id"] for i in mine] == [r.json()["tracking_id"]]
    assert client.get("/api/issues?my_reports=true").status_code == 401


def test_unknown_tracking_id_404(client):
    assert client.get("/api/issues/FMC-00000000").status_code == 404


# ---------- protected actions ----------

def test_status_update_requires_staff_or_admin(client, new_issue, student_headers, admin_headers):
    url = f"/api/issues/{new_issue['tracking_id']}/status"
    body = {"status": "In Progress"}
    assert client.patch(url, json=body).status_code == 401
    assert client.patch(url, json=body, headers=student_headers).status_code == 403
    r = client.patch(url, json={**body, "note": "Electrician on the way"}, headers=admin_headers)
    assert r.status_code == 200 and r.json()["status"] == "In Progress"


def test_timeline_records_changes_and_hides_staff_names_publicly(client, new_issue, admin_headers):
    tid = new_issue["tracking_id"]
    client.patch(f"/api/issues/{tid}/status",
                 json={"status": "Resolved", "note": "Fan replaced"}, headers=admin_headers)
    public = client.get(f"/api/issues/{tid}/history").json()
    assert [e["status"] for e in public] == ["Submitted", "Resolved"]
    assert public[1]["note"] == "Fan replaced"
    assert public[1]["actor"] == "Campus team"
    internal = client.get(f"/api/issues/{tid}/history", headers=admin_headers).json()
    assert internal[1]["actor"] == "Campus Administrator"


def test_assignment_is_admin_only_and_validated(client, new_issue, student_headers, admin_headers):
    url = f"/api/issues/{new_issue['tracking_id']}/assign"
    me = client.get("/api/auth/me", headers=admin_headers).json()
    assert client.patch(url, json={"assigned_to_id": me["id"]}).status_code == 401
    assert client.patch(url, json={"assigned_to_id": me["id"]}, headers=student_headers).status_code == 403
    student_id = client.get("/api/auth/me", headers=student_headers).json()["id"]
    assert client.patch(url, json={"assigned_to_id": student_id}, headers=admin_headers).status_code == 400
    r = client.patch(url, json={"assigned_to_id": me["id"]}, headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "Assigned" and r.json()["assigned_staff_name"] == "Campus Administrator"


def test_only_admin_creates_staff_and_staff_can_triage(client, new_issue, student_headers, admin_headers):
    staff = {"email": "tech@test.edu", "full_name": "Ravi Technician", "password": "Staff12345"}
    assert client.post("/api/admin/staff", json=staff).status_code == 401
    assert client.post("/api/admin/staff", json=staff, headers=student_headers).status_code == 403
    assert client.post("/api/admin/staff", json=staff, headers=admin_headers).json()["role"] == "staff"

    staff_headers = login(client, "tech@test.edu", "Staff12345")
    url = f"/api/issues/{new_issue['tracking_id']}/status"
    assert client.patch(url, json={"status": "Under Review"}, headers=staff_headers).status_code == 200
    # staff cannot assign (admin only)
    assert client.patch(f"/api/issues/{new_issue['tracking_id']}/assign",
                        json={"assigned_to_id": 1}, headers=staff_headers).status_code == 403
    assert client.get("/api/staff", headers=staff_headers).status_code == 200
    assert client.get("/api/staff", headers=student_headers).status_code == 403


def test_stats(client, new_issue):
    stats = client.get("/api/stats").json()
    assert stats["total"] == sum(stats["by_status"].values())
    assert stats["by_category"]["Electrical"] >= 1
    assert stats["open"] <= stats["total"]


def test_status_transition_rules_and_resolution_remarks(client, new_issue, admin_headers):
    tid = new_issue["tracking_id"]
    url = f"/api/issues/{tid}/status"

    # Step 1: Illegal transition from Submitted -> Closed should be rejected with 400
    res_bad = client.patch(url, json={"status": "Closed"}, headers=admin_headers)
    assert res_bad.status_code == 400
    assert "Cannot transition issue" in res_bad.json()["detail"]

    # Step 2: Valid transition Submitted -> In Progress
    res_progress = client.patch(url, json={"status": "In Progress"}, headers=admin_headers)
    assert res_progress.status_code == 200
    assert res_progress.json()["status"] == "In Progress"

    # Step 3: Valid transition In Progress -> Resolved with resolution remarks
    res_resolved = client.patch(
        url,
        json={"status": "Resolved", "resolution_notes": "Replaced faulty capacitor and tested."},
        headers=admin_headers,
    )
    assert res_resolved.status_code == 200
    assert res_resolved.json()["status"] == "Resolved"
    assert res_resolved.json()["resolution_notes"] == "Replaced faulty capacitor and tested."

    # Step 4: Valid transition Resolved -> Closed
    res_closed = client.patch(url, json={"status": "Closed"}, headers=admin_headers)
    assert res_closed.status_code == 200
    assert res_closed.json()["status"] == "Closed"

    # Step 5: Verify get_issue returns resolution_notes
    issue_data = client.get(f"/api/issues/{tid}").json()
    assert issue_data["resolution_notes"] == "Replaced faulty capacitor and tested."


def test_stats_extended_keys(client, new_issue):
    stats = client.get("/api/stats").json()
    assert "total" in stats
    assert "open" in stats
    assert "submitted" in stats
    assert "in_progress" in stats
    assert "resolved" in stats
    assert stats["total"] >= 1
    assert stats["open"] >= 0
