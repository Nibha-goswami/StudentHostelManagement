# 🏛️ Smart Campus — Hostel Management System

A full-stack **Hostel Management System** built with **Python Flask** and **MySQL**, featuring role-based portals for Admin, Warden, Students, Maintenance Staff, and Mess Manager.

---

## ✨ Features

| Module | Features |
|--------|----------|
| **Authentication** | Login, Student self-registration, Role-based access, Gender-aware hostel assignment |
| **Admin Portal** | User management, Hostel occupancy, Complaint assignment, Financial ledger |
| **Student Portal** | Bed booking, Room transfers, Leave applications, Mess history, Fee payments |
| **Warden Portal** | Approve/reject applications, Leaves, Transfers, **Student checkout** (free beds for new students) |
| **Maintenance Portal** | View assigned complaints, Update status (In Progress / Resolved) |
| **Mess Manager Portal** | Attendance tracking, Scan logs, Monthly billing, Rebates |

---

## 🏠 Hostels

- **C.V Raman Boys Hostel** — Male students
- **Saraswati Girls Hostel** — Female students

Gender is detected at registration and only matching hostel beds are shown.

---

## 🛠️ Tech Stack

- **Backend:** Python 3, Flask, Flask-Login, Flask-MySQLdb
- **Database:** MySQL 8.0 (stored procedures, triggers, views)
- **Frontend:** Vanilla HTML/CSS/JS — Dark glassmorphism theme
- **Auth:** Werkzeug password hashing

---

## 🚀 Setup Instructions

### 1. Clone the repo
```bash
git clone https://github.com/Nibha-goswami/StudentHostelManagement.git
cd StudentHostelManagement
```

### 2. Install Python dependencies
```bash
pip install flask flask-login flask-mysqldb mysqlclient werkzeug python-dotenv
```

### 3. Set up MySQL database
```bash
mysql -u root -p < schema.sql
mysql -u root -p smart_campus < seed_data.sql
```

### 4. Configure environment
```bash
cp .env.example .env
# Edit .env and fill in your MySQL credentials
```

### 5. Run the app
```bash
python run.py
```

Open **http://127.0.0.1:5000** in your browser.

---

## 🔑 Demo Accounts

### Staff (password: `Demo@1234`)
| Email | Role |
|-------|------|
| admin@smartcampus.edu | Admin |
| warden@smartcampus.edu | Warden |
| mess@smartcampus.edu | Mess Manager |
| electrician@smartcampus.edu | Maintenance |

### Students (password: `FirstName@123`)
| Email | Password | Gender |
|-------|----------|--------|
| nibha.kumari@student.edu | Nibha@123 | Female |
| diya.verma@student.edu | Diya@123 | Female |
| rohan.gupta@student.edu | Rohan@123 | Male |
| ananya.singh@student.edu | Ananya@123 | Female |
| karan.mehta@student.edu | Karan@123 | Male |
| ishita.joshi@student.edu | Ishita@123 | Female |
| vivaan.patel@student.edu | Vivaan@123 | Male |
| meera.nair@student.edu | Meera@123 | Female |

---

## 📁 Project Structure

```
smart-campus/
├── run.py                    # App entry point
├── schema.sql                # Database schema
├── seed_data.sql             # Sample data
├── .env.example              # Environment template
├── app/
│   ├── __init__.py           # Flask factory
│   ├── models.py             # User model
│   ├── routes/
│   │   ├── auth.py           # Login & Registration
│   │   ├── admin.py          # Admin portal
│   │   ├── student.py        # Student portal
│   │   ├── warden.py         # Warden portal
│   │   ├── maintenance.py    # Maintenance portal
│   │   └── mess.py           # Mess manager portal
│   ├── static/
│   │   ├── css/main.css      # Dark theme stylesheet
│   │   └── js/main.js        # UI helpers
│   └── templates/
│       ├── base.html         # Base layout
│       ├── auth/             # Login & Register pages
│       ├── admin/            # Admin templates
│       ├── student/          # Student templates
│       ├── warden/           # Warden templates
│       ├── maintenance/      # Maintenance templates
│       └── mess/             # Mess manager templates
└── database_design.md        # ER diagram & schema notes
```

---

## 👩‍💻 Developed By

**Nibha Kumari** — Smart Campus Hostel Management System
