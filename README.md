# 🏫 FixMyCampus — Campus Facility & Grievance Management System

> A full-stack web platform where students report campus problems (broken fans, water leaks, faulty wiring…), track them with a unique ID, and where staff and administrators triage, assign and resolve them — with a complete activity timeline for every issue.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB.svg?logo=python&logoColor=white)](https://www.python.org)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00.svg)](https://www.sqlalchemy.org)
[![Tests](https://img.shields.io/badge/tests-16%20passing-brightgreen.svg)](tests/test_api.py)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ✨ Features

**Students / public**
- Report an issue in seconds (title, category, location, priority, description) — no account needed.
- Get a unique tracking ID (`FMC-XXXXXXXX`) and follow progress on the **Track** page with a **progress timeline**.
- Optional account: logged-in students get their name pre-filled and their reports linked to them.
- The public list **never shows who reported** an issue.

**Staff & administrators** (login required)
- Dashboard with live KPI cards, search, status/priority filters and **4 Chart.js analytics charts**.
- Update status inline (`Submitted → Under Review → Assigned → In Progress → Resolved → Closed / Rejected`).
- **Report details modal** with the full **activity timeline** (who changed what, and when).
- **Admins can assign** an issue to a staff member (with a note the reporter can see).
- Admins create staff accounts through a protected endpoint.

## 🔐 Security

| Concern | How it is handled |
| :--- | :--- |
| Passwords | bcrypt (12 rounds); min. 8 characters with a letter and a number |
| Sessions | JWT (HS256), 24 h expiry, sent as a `Bearer` token |
| Role-based access | `student` / `staff` / `admin`; protected routes use `require_staff_or_admin` / `require_admin` |
| Privilege escalation | Public sign-up **always** creates a student — a role can't be requested |
| Secrets | No secret or password in the source. `JWT_SECRET` from the environment, otherwise a random one is generated into a git-ignored file. First admin password comes from `ADMIN_PASSWORD` or is generated and printed once |
| Brute force | Login is limited to 5 failed attempts per 5 minutes (per IP + email) |
| Privacy | Public API hides reporter names and staff names; only staff and the reporter see them |
| XSS | Frontend renders with `textContent` / escaped HTML |
| CORS | Restricted to the frontend origin (configurable with `CORS_ORIGINS`) |
| Timestamps | Sent as explicit UTC (`…Z`) so every browser shows correct local time |

## 🏗️ Tech Stack

| Layer | Technology |
| :--- | :--- |
| Backend | FastAPI (Python 3.10+), Pydantic v2 |
| Database | SQLite via SQLAlchemy 2.0 (typed `Mapped` models, automatic safe migrations) |
| Auth | bcrypt + PyJWT |
| Frontend | Vanilla HTML5 / CSS3 / ES6 JavaScript, Chart.js |
| Tests | pytest + FastAPI TestClient |

```
Browser (static HTML/JS, :5500)  ──JSON + Bearer token──▶  FastAPI (:8000)  ──SQLAlchemy──▶  SQLite
```

## 📂 Project Structure

```text
FixMycampus/
├── main.py               # FastAPI app: models, auth, endpoints
├── run.py                # One-click launcher (API on :8000, frontend on :5500)
├── seed_demo.py          # Demo accounts + 16 sample issues (for presentations)
├── requirements.txt      # Runtime dependencies
├── requirements-dev.txt  # + pytest, httpx
├── tests/                # 16 automated API tests
│   ├── conftest.py
│   └── test_api.py
└── frontend/
    ├── config.js         # API address + login helpers (shared by every page)
    ├── index.html / script.js     # Public portal: report + browse issues
    ├── track.html / track.js      # Track an issue by ID, with timeline
    ├── login.html / login.js      # Log in / create student account
    ├── admin.html / admin.js      # Staff & admin dashboard + charts
    ├── admin-extras.js            # Profile, logout, assignment, timeline in modal
    └── style.css / admin.css
```

## 🚀 Quick Start

Requires **Python 3.10+** and Git.

```bash
git clone https://github.com/AdityaAdsul07/FixMycampus.git
cd FixMycampus

# Windows
python -m venv .venv
.\.venv\Scripts\activate
# macOS / Linux
# python3 -m venv .venv && source .venv/bin/activate

pip install -r requirements.txt
```

**Optional — load demo data** (recommended for a presentation):

```bash
python seed_demo.py --reset
```

| Role | Email | Password |
| :--- | :--- | :--- |
| Admin | `admin@fixmycampus.edu` | `Admin@1234` |
| Staff | `staff@fixmycampus.edu` | `Staff@1234` |
| Student | `student@fixmycampus.edu` | `Student@1234` |

> ⚠️ These are **demo-only** passwords created by `seed_demo.py`. Never use the demo script in production.

**Start the app:**

```bash
python run.py
```

- Public portal → http://127.0.0.1:5500/index.html
- Login → http://127.0.0.1:5500/login.html
- Admin dashboard → http://127.0.0.1:5500/admin.html (login required)
- API docs (Swagger) → http://127.0.0.1:8000/docs

Without the demo script, the **first run creates an admin** and prints its generated password once in the terminal. To choose your own, set `ADMIN_EMAIL` / `ADMIN_PASSWORD` before the first start.

### Run the tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

### Configuration (environment variables, all optional)

| Variable | Purpose | Default |
| :--- | :--- | :--- |
| `JWT_SECRET` | Token signing key | random, stored in `.jwt_secret` |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | First admin account | `admin@fixmycampus.edu` / generated |
| `DATABASE_URL` | Database location | `sqlite:///./fixmycampus.db` |
| `CORS_ORIGINS` | Allowed frontend origins (comma-separated) | `127.0.0.1:5500`, `localhost:5500` |

## 📡 REST API

Full interactive docs at `/docs`. **Auth** column: 🌐 public · 🔑 logged in · 🛠️ staff/admin · 👑 admin.

| Method | Endpoint | Auth | Description |
| :--- | :--- | :---: | :--- |
| `POST` | `/api/auth/register` | 🌐 | Create a student account |
| `POST` | `/api/auth/login` | 🌐 | Log in, receive a JWT |
| `GET` | `/api/auth/me` | 🔑 | Current user |
| `POST` | `/api/issues` | 🌐 | Report an issue (linked to you if logged in) |
| `GET` | `/api/issues` | 🌐 | List issues (`?my_reports=true` needs login). Reporter hidden for the public |
| `GET` | `/api/issues/{id}` | 🌐 | One issue by tracking ID |
| `GET` | `/api/issues/{id}/history` | 🌐 | Activity timeline |
| `PATCH` | `/api/issues/{id}/status` | 🛠️ | Change status (optional note) |
| `PATCH` | `/api/issues/{id}/assign` | 👑 | Assign to a staff member |
| `GET` | `/api/staff` | 🛠️ | List staff for assignment |
| `POST` | `/api/admin/staff` | 👑 | Create a staff account |
| `GET` | `/api/stats` | 🌐 | Totals by status / priority / category |

## 🎬 Suggested Demo Flow (5 minutes)

1. **Student:** open the portal → submit a report → copy the tracking ID.
2. **Track page:** paste the ID → show the timeline (“Submitted”).
3. **Admin login** → dashboard KPIs and charts → open the new report.
4. **Assign** it to the staff member with a note → change the status to *In Progress*, then *Resolved*.
5. Back on the **Track page**: refresh — the reporter sees the full timeline.
6. Show that `admin.html` redirects to login when logged out, and that a student account cannot open it.

## 🗺️ Roadmap

- [x] **Phase 1** — User model, bcrypt hashing, admin seeding
- [x] **Phase 2** — Auth endpoints (register / login / me), JWT, role dependencies
- [x] **Phase 3** — Login page, protected admin dashboard, role-based API access
- [x] **Phase 4** — Staff assignment, activity timeline, automated tests, demo data
- [ ] **Phase 5** — In-app notifications when a report's status changes
- [ ] **Phase 6** — Photo attachments, duplicate-report detection, PostgreSQL for deployment

## 👥 Team

Add your team members here (name · roll number · role).

* **Aditya Adsul** — [@AdityaAdsul07](https://github.com/AdityaAdsul07)

## 📄 License

MIT — see [LICENSE](LICENSE).
