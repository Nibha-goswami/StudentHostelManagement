from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from app import mysql
from app.models import User

auth_bp = Blueprint('auth', __name__)

DEPARTMENTS = [
    'Computer Science', 'Information Technology', 'Electronics',
    'Electrical', 'Mechanical', 'Civil', 'Chemical', 'Biotechnology', 'Other'
]

@auth_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('auth.dashboard'))
    return redirect(url_for('auth.login'))

# ─────────────────────────────────────────────
#  LOGIN
# ─────────────────────────────────────────────
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('auth.dashboard'))
    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        cur = mysql.connection.cursor()
        cur.execute(
            "SELECT user_id, email, full_name, role, password_hash, is_active "
            "FROM users WHERE email=%s", (email,))
        row = cur.fetchone()
        cur.close()
        if row and row['is_active'] and check_password_hash(row['password_hash'], password):
            user = User(row['user_id'], row['email'], row['full_name'],
                        row['role'], row['is_active'])
            login_user(user)
            flash(f"Welcome back, {user.full_name}!", 'success')
            return redirect(url_for('auth.dashboard'))
        flash('Invalid email or password. Please try again.', 'danger')
    return render_template('auth/login.html')

# ─────────────────────────────────────────────
#  REGISTER  (students only)
# ─────────────────────────────────────────────
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('auth.dashboard'))

    if request.method == 'POST':
        full_name      = request.form.get('full_name', '').strip()
        email          = request.form.get('email', '').strip().lower()
        phone          = request.form.get('phone', '').strip()
        password       = request.form.get('password', '')
        confirm_pass   = request.form.get('confirm_password', '')
        roll_no        = request.form.get('roll_no', '').strip().upper()
        department     = request.form.get('department', '').strip()
        year_of_study  = request.form.get('year_of_study', '1')
        gender         = request.form.get('gender', '')
        guardian_phone = request.form.get('guardian_phone', '').strip()

        # ── Client-side validation ──
        errors = []
        if not full_name:
            errors.append('Full name is required.')
        if not email or '@' not in email:
            errors.append('A valid email address is required.')
        if not roll_no:
            errors.append('Roll number is required.')
        if not department:
            errors.append('Please select your department.')
        if gender not in ('male', 'female', 'other'):
            errors.append('Please select your gender.')
        if len(password) < 6:
            errors.append('Password must be at least 6 characters.')
        if password != confirm_pass:
            errors.append('Passwords do not match.')

        # ── Uniqueness checks ──
        if not errors:
            cur = mysql.connection.cursor()
            cur.execute("SELECT 1 FROM users WHERE email=%s", (email,))
            if cur.fetchone():
                errors.append('This email is already registered. Please log in.')
            cur.execute("SELECT 1 FROM students WHERE roll_no=%s", (roll_no,))
            if cur.fetchone():
                errors.append('This roll number is already registered.')
            cur.close()

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('auth/register.html',
                                   departments=DEPARTMENTS, form=request.form)

        # ── Create user + student rows ──
        hashed = generate_password_hash(password)
        cur = mysql.connection.cursor()
        try:
            cur.execute(
                "INSERT INTO users (email, password_hash, full_name, phone, role) "
                "VALUES (%s, %s, %s, %s, 'student')",
                (email, hashed, full_name, phone or None))
            new_user_id = cur.lastrowid

            cur.execute(
                "INSERT INTO students "
                "(user_id, roll_no, department, year_of_study, gender, guardian_phone) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (new_user_id, roll_no, department,
                 int(year_of_study), gender, guardian_phone or None))
            mysql.connection.commit()

            # Auto-login after registration
            new_user = User(new_user_id, email, full_name, 'student', True)
            login_user(new_user)
            flash(f"Welcome to Smart Campus, {full_name}! "
                  f"Your account has been created successfully.", 'success')
            return redirect(url_for('student.dashboard'))

        except Exception as e:
            mysql.connection.rollback()
            flash(f'Registration failed: {str(e)}', 'danger')
            return render_template('auth/register.html',
                                   departments=DEPARTMENTS, form=request.form)
        finally:
            cur.close()

    return render_template('auth/register.html', departments=DEPARTMENTS, form={})

# ─────────────────────────────────────────────
#  ROLE-BASED DASHBOARD REDIRECT
# ─────────────────────────────────────────────
@auth_bp.route('/dashboard')
@login_required
def dashboard():
    role = current_user.role
    if role == 'admin':
        return redirect(url_for('admin.dashboard'))
    elif role == 'student':
        return redirect(url_for('student.dashboard'))
    elif role == 'warden':
        return redirect(url_for('warden.dashboard'))
    elif role == 'maintenance':
        return redirect(url_for('maintenance.dashboard'))
    elif role == 'mess_manager':
        return redirect(url_for('mess.dashboard'))
    return redirect(url_for('auth.login'))

# ─────────────────────────────────────────────
#  LOGOUT
# ─────────────────────────────────────────────
@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))
