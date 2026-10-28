# 🏫 FixMyCampus — Campus Facility & Grievance Management System

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.13+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-D71F00.svg?style=flat&logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org)
[![Chart.js](https://img.shields.io/badge/Chart.js-4.0+-FF6384.svg?style=flat&logo=chart.js&logoColor=white)](https://www.chartjs.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> A modern full-stack web platform for reporting, tracking, and resolving campus facility issues and maintenance requests in real time.

---

## 🌟 Overview

**FixMyCampus** streamlines communication between students, faculty, and campus facility management. When infrastructure breaks down (broken fans, water leaks, electrical faults, damaged benches), students can submit a detailed report within seconds and track resolution progress using a unique tracking ID—without requiring complex sign-up hurdles.

Facility administrators have a dedicated management workspace featuring KPI counters, inline status updates, ticket inspection modals, and live visual analytics.

---

## ✨ Features

### 👨‍🎓 Student & Public Portal
- **Instant Reporting**: Submit reports with title, category, location, priority level, reporter name, and description.
- **Unique Tracking Code**: Generates human-readable IDs (`FMC-XXXXXXXX`) with one-click clipboard copying.
- **Standalone Issue Tracker (`track.html`)**: Search any ticket by ID to check current status, priority, and updates in real time.
- **Live Search & Filter**: Instant client-side search across all reports by keyword, category, or status with XSS sanitization.
- **Live Campus Metrics**: Real-time counter displaying Total, Open, and Resolved campus grievances.

### 🛠️ Administrator Workspace (`admin.html`)
- **Metric KPI Cards**: Live cards tracking *Total*, *Submitted*, *In Progress*, and *Resolved* issues.
- **Inline Status Triage**: Update tickets through standard workflows (`Submitted` ➔ `Under Review` ➔ `Assigned` ➔ `In Progress` ➔ `Resolved` ➔ `Closed` / `Rejected`).
- **Interactive Report Modal**: Click any issue title or tracking ID to inspect full ticket history and timestamps.
- **Live Analytics Dashboard (Chart.js)**:
  - 🍩 **Report Status** (Doughnut Chart)
  - 🍩 **Priority Distribution** (Doughnut Chart)
  - 📊 **Issue Categories** (Horizontal Bar Chart)
  - 📈 **Reporting Trends Over Time** (Smooth Area Line Chart)

### 🔐 Security & Database Architecture
- **Modern ORM**: Powered by SQLAlchemy 2.0 with type-annotated `Mapped` models.
- **Password Security**: Salted 12-round password hashing using `bcrypt`.
- **Token Ready**: Integrated `pyjwt` infrastructure for role-based authentication.
- **Three-Tier Roles**: Built-in support for `student`, `staff`, and `admin` roles.
- **Safe Migrations**: Backward-compatible schema evolution preserving all existing reports.

---

## 🏗️ Tech Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Backend** | [FastAPI](https://fastapi.tiangolo.com/) | High-performance asynchronous REST API |
| **Language** | [Python 3.13+](https://www.python.org/) | Core backend programming language |
| **ORM / Database** | [SQLAlchemy 2.0](https://www.sqlalchemy.org/) + [SQLite](https://www.sqlite.org/) | Relational database modeling and persistence |
| **Security** | [Bcrypt](https://pypi.org/project/bcrypt/) + [PyJWT](https://pyjwt.readthedocs.io/) | Salted password hashing & JWT tokens |
| **Frontend** | Vanilla HTML5, CSS3, JavaScript (ES6+) | Lightweight, dependency-free responsive client |
| **Data Visualization** | [Chart.js](https://www.chartjs.org/) | Interactive visual dashboard charts |

---

## 📂 Project Structure

```text
FixMycampus/
├── frontend/
│   ├── index.html        # Public reporting & recent issues portal
│   ├── script.js         # Public portal logic & XSS sanitizer
│   ├── style.css         # Main modern design system
│   ├── track.html        # Dedicated issue tracking page
│   ├── track.js          # Direct tracking lookup handler
│   ├── admin.html        # Admin management & analytics workspace
│   ├── admin.js          # Admin triage, filtering, modal & Chart.js charts
│   └── admin.css         # Admin workspace stylesheet
├── fixmycampus.db        # SQLite database
├── main.py               # FastAPI backend & database models
├── requirements.txt      # Python dependencies
├── run.py                # 1-click launcher for backend & frontend
├── README.md             # Project documentation
└── .gitignore            # Git exclusions (.venv, caches, etc.)
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.10+ installed
- Git installed

### 2. Clone the Repository
```bash
git clone https://github.com/AdityaAdsul07/FixMycampus.git
cd FixMycampus
```

### 3. Create & Activate Virtual Environment
```bash
# Windows
python -m venv .venv
.\.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Launch the Application

**Option A — Using the 1-Click Launcher:**
```bash
python run.py
```
*This starts the FastAPI backend at port `8000`, the frontend server at port `5500`, and opens both pages in your browser automatically.*

**Option B — Starting the Backend Manually:**
```bash
uvicorn main:app --reload --port 8000
```
Then open `frontend/index.html` or `frontend/admin.html` with VS Code Live Server or directly in your browser.

---

## 🔑 Default Administrator Credentials

On first run, the database automatically seeds a default administrator account:
- **Email:** `admin@fixmycampus.edu`
- **Password:** `Admin@123`
- **Role:** `admin`

---

## 📡 REST API Reference

Interactive Swagger documentation is available at:  
👉 **`http://127.0.0.1:8000/docs`**

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Server health check |
| `POST` | `/api/issues` | Submit a new campus report |
| `GET` | `/api/issues` | List all campus issues (newest first) |
| `GET` | `/api/issues/{tracking_id}` | Retrieve details of a specific issue |
| `PATCH`| `/api/issues/{tracking_id}/status` | Update issue progress status |
| `GET` | `/api/stats` | Retrieve aggregate statistics by status |

---

## 🗺️ Roadmap

- [x] **Phase 1**: Database User Model, Bcrypt Password Security, & Admin Seed
- [ ] **Phase 2**: Authentication Endpoints (`/register`, `/login`, JWT Tokens)
- [ ] **Phase 3**: Frontend Login Gateway & Admin Route Protection
- [ ] **Phase 4**: Issue Assignment to Staff & Maintenance Departments
- [ ] **Phase 5**: Real-Time In-App Notifications

---

## 👤 Author

* **Aditya Adsul** — [@AdityaAdsul07](https://github.com/AdityaAdsul07)

---

## 📄 License

This project is open-source under the [MIT License](LICENSE).
