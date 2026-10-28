# 🏫 FixMyCampus

### Smart Campus Issue Reporting and Resolution System

FixMyCampus is a web-based application designed to make campus issue reporting and resolution easier, faster, and more transparent. It provides a centralized platform where campus-related problems can be reported, tracked, and managed efficiently.

The project aims to improve communication between students and campus administrators while helping institutions organize maintenance requests and monitor their resolution.

## 🎯 Problem Statement

Campus issues such as broken fans, electrical faults, damaged furniture, and cleanliness problems are often reported through informal channels. This can make it difficult to track complaints, monitor progress, and ensure timely resolution.

**FixMyCampus addresses this problem by providing a centralized digital system for reporting, tracking, and managing campus issues.**

## ✨ Features

- 📝 **Issue Reporting:** Submit campus-related problems through an online form.
- 🔎 **Unique Tracking ID:** Identify and track each reported issue using its tracking ID.
- 📋 **Issue Management:** View submitted reports in a centralized admin dashboard.
- 🔄 **Status Updates:** Update issue statuses to monitor resolution progress.
- 📊 **Dashboard Statistics:** View total reports and status-wise counts.
- 📈 **Analytics Dashboard:** Visualize reports by status, priority, category, and trends.
- 🔍 **Search and Filtering:** Find reports using available search and filter options.
- 🏢 **Centralized Issue Tracking:** Keep campus complaints organized in one place.

## 🛠️ Technology Stack

| Technology | Purpose |
|---|---|
| Python | Backend development |
| FastAPI | REST API development |
| SQLAlchemy | Database interaction |
| HTML5 | Web page structure |
| CSS3 | Styling and layout |
| JavaScript | Frontend functionality and API integration |
| Chart.js | Analytics and data visualization |
| Git and GitHub | Version control and collaboration |

## 🏗️ Project Structure

```text
FixMycampus/
├── main.py
├── frontend/
│   ├── index.html
│   ├── admin.html
│   ├── track.html
│   ├── style.css
│   ├── script.js
│   ├── admin.js
│   └── admin.css
├── README.md
└── ...
```

*Note: This is a representative structure. Your repository may contain additional files or use slightly different filenames.*

## ⚙️ Installation and Setup

### Prerequisites

- Python 3.10 or later
- pip
- Git
- A code editor such as Visual Studio Code

### 1. Clone the repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd FixMycampus
```

Replace `YOUR_GITHUB_REPOSITORY_URL` with your repository's actual URL.

### 2. Create a virtual environment

```bash
python -m venv .venv
```

### 3. Activate the virtual environment

For Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 4. Install the required dependencies

If a `requirements.txt` file is available:

```bash
pip install -r requirements.txt
```

Otherwise, install the dependencies specified by your project. The backend uses FastAPI, SQLAlchemy, and Uvicorn.

### 5. Run the backend

From the project root, run:

```bash
python -m uvicorn main:app --reload
```

Backend URL: http://127.0.0.1:8000

API documentation: http://127.0.0.1:8000/docs

### 6. Run the frontend

Open a second terminal in the project root and run:

```bash
python -m http.server 5173 --directory frontend
```

Open these pages in your browser:

- **Issue Reporting:** http://127.0.0.1:5173/
- **Admin Dashboard:** http://127.0.0.1:5173/admin.html
- **Issue Tracking:** http://127.0.0.1:5173/track.html

Keep both the backend and frontend terminals running while testing the application.

## 🔄 Application Workflow

1. A user submits an issue through the reporting form.
2. The backend processes the submitted information and creates an issue record.
3. The issue receives a unique tracking ID.
4. The user can use the tracking page to check its status.
5. Administrators view and manage reports through the dashboard.
6. Issue statuses are updated as work progresses.
7. Dashboard statistics and analytics help monitor reported issues.

## 🚀 Future Enhancements

The following features are potential improvements for future versions:

- 🔐 Secure user registration and login
- 👥 Role-based access for students, administrators, and staff
- 🏢 Assignment of issues to departments and responsible staff
- 🔔 In-app notifications for issue status changes
- 🖼️ Image attachments for reporting problems
- 📜 Issue history and resolution records
- 📱 Improved mobile responsiveness
- ☁️ Deployment for use across a college campus

*These enhancements are planned and may not yet be implemented in the current version.*

## 🎓 Project Objective

The objective of FixMyCampus is to simplify campus issue reporting, improve transparency, and help institutions manage maintenance and other campus-related problems through a centralized digital platform.

## 🤝 Contributing

Contributions and suggestions are welcome.

1. Fork the repository.
2. Create a new branch for your changes.
3. Make your changes and test them.
4. Commit and push your changes.
5. Open a pull request describing your improvements.

## 🔒 Security

- Do not commit passwords, API keys, or secret tokens.
- Keep virtual environments and sensitive local data out of version control.
- Use a `.gitignore` file to exclude unnecessary and sensitive files.
- Implement authentication and backend authorization before exposing administrative functionality publicly.

## 📄 License

A license has not yet been specified. Add an appropriate open-source license if you want to define how others may use, modify, and distribute this project.

---

### 💙 FixMyCampus

**Making campus issue reporting and resolution simpler, smarter, and more transparent.**
