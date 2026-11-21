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
        selected_role = request.form.get('role', 'student').strip().lower()
        email         = request.form.get('email', '').strip().lower()
        password      = request.form.get('password', '')

        # Alias resolution for wardens
        lookup_email = email
        if email in ('warden@smartcampus.edu', 'vikram.sharma@smartcampus.edu'):
            lookup_email = 'boys.warden@smartcampus.edu'
        elif email == 'reena.verma@smartcampus.edu':
            lookup_email = 'girls.warden@smartcampus.edu'

        cur = mysql.connection.cursor()
        cur.execute(
            """SELECT u.user_id, u.email, u.full_name, u.role, u.password_hash, u.is_active,
                      COALESCE(ws.warden_type, h.gender_type) as warden_type,
                      h.hostel_id, h.name as hostel_name
               FROM users u
               LEFT JOIN warden_staff ws ON ws.user_id = u.user_id
               LEFT JOIN hostels h ON (h.warden_user_id = u.user_id OR h.hostel_id = ws.hostel_id)
               WHERE u.email=%s""", (lookup_email,))
        row = cur.fetchone()
        cur.close()

        if not row or not check_password_hash(row['password_hash'], password):
            flash('Invalid email or password. Please try again.', 'danger')
            return render_template('auth/login.html')

        if not row['is_active']:
            flash('Your account is currently deactivated. Please contact campus administration.', 'danger')
            return render_template('auth/login.html')

        # Role verification
        if selected_role == 'boys_warden':
            if row['role'] != 'warden' or row.get('warden_type') != 'boys':
                if row['role'] == 'warden' and row.get('warden_type') == 'girls':
                    flash("Role mismatch: Reena Verma is registered as 'Girls Warden'. Please select the Girls Warden tab.", 'danger')
                else:
                    flash("Role mismatch: This account is not registered as 'Boys Warden'.", 'danger')
                return render_template('auth/login.html')
        elif selected_role == 'girls_warden':
            if row['role'] != 'warden' or row.get('warden_type') != 'girls':
                if row['role'] == 'warden' and row.get('warden_type') == 'boys':
                    flash("Role mismatch: Vikram Sharma is registered as 'Boys Warden'. Please select the Boys Warden tab.", 'danger')
                else:
                    flash("Role mismatch: This account is not registered as 'Girls Warden'.", 'danger')
                return render_template('auth/login.html')
        elif selected_role == 'warden':
            if row['role'] != 'warden':
                flash("Role mismatch: This account does not have Warden privileges.", 'danger')
                return render_template('auth/login.html')
        else:
            if row['role'] != selected_role:
                role_name = selected_role.replace('_', ' ').title()
                actual_role = row['role'].replace('_', ' ').title()
                flash(f"Role mismatch: This account is registered as '{actual_role}', not '{role_name}'. Please select the {actual_role} tab to sign in.", 'danger')
                return render_template('auth/login.html')

        user = User(
            row['user_id'],
            row['email'],
            row['full_name'],
            row['role'],
            row['is_active'],
            warden_type=row.get('warden_type'),
            hostel_id=row.get('hostel_id'),
            hostel_name=row.get('hostel_name')
        )
        login_user(user)

        if user.role == 'warden':
            warden_type_label = 'Boys Warden' if user.warden_type == 'boys' else 'Girls Warden'
            flash(f"Welcome back, {user.full_name} ({warden_type_label})!", 'success')
        else:
            flash(f"Welcome back, {user.full_name}!", 'success')

        role_redirects = {
            'admin': 'admin.dashboard',
            'student': 'student.dashboard',
            'warden': 'warden.dashboard',
            'maintenance': 'maintenance.dashboard',
            'mess_manager': 'mess.dashboard',
        }
        return redirect(url_for(role_redirects.get(row['role'], 'auth.dashboard')))

    return render_template('auth/login.html')

# ─────────────────────────────────────────────
#  FORGOT / RESET PASSWORD
# ─────────────────────────────────────────────
@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('auth.dashboard'))

    if request.method == 'POST':
        email            = request.form.get('email', '').strip().lower()
        identifier       = request.form.get('identifier', '').strip()
        new_password     = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        errors = []
        if not email or '@' not in email:
            errors.append('Please provide a valid registered email address.')
        if not identifier:
            errors.append('Please provide your Roll Number (students) or Phone Number (staff).')
        if len(new_password) < 6:
            errors.append('New password must be at least 6 characters long.')
        if new_password != confirm_password:
            errors.append('Passwords do not match.')

        if errors:
            for err in errors:
                flash(err, 'danger')
            return render_template('auth/forgot_password.html', form=request.form)

        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT u.user_id, u.email, u.full_name, u.role, u.phone, u.is_active, s.roll_no
            FROM users u
            LEFT JOIN students s ON s.user_id = u.user_id
            WHERE u.email = %s
        """, (email,))
        user_row = cur.fetchone()

        if not user_row:
            cur.close()
            flash('No account registered with this email address.', 'danger')
            return render_template('auth/forgot_password.html', form=request.form)

        if not user_row['is_active']:
            cur.close()
            flash('This account is currently deactivated. Please contact the campus administrator or warden.', 'danger')
            return render_template('auth/forgot_password.html', form=request.form)

        # Verification check
        verified = False
        clean_id = identifier.replace(' ', '').upper()
        if user_row['role'] == 'student':
            student_roll = (user_row['roll_no'] or '').replace(' ', '').upper()
            student_phone = (user_row['phone'] or '').replace(' ', '').replace('-', '')
            clean_phone_input = identifier.replace(' ', '').replace('-', '')
            if (student_roll and clean_id == student_roll) or (student_phone and clean_phone_input == student_phone):
                verified = True
        else:
            staff_phone = (user_row['phone'] or '').replace(' ', '').replace('-', '')
            clean_phone_input = identifier.replace(' ', '').replace('-', '')
            if (staff_phone and clean_phone_input == staff_phone) or clean_id == user_row['full_name'].replace(' ', '').upper():
                verified = True

        if not verified:
            cur.close()
            flash('Verification failed: The Roll Number or Phone Number does not match our records for this account.', 'danger')
            return render_template('auth/forgot_password.html', form=request.form)

        try:
            hashed = generate_password_hash(new_password)
            cur.execute("UPDATE users SET password_hash = %s WHERE user_id = %s", (hashed, user_row['user_id']))
            mysql.connection.commit()
            flash(f"Password for {user_row['full_name']} has been reset successfully! Please sign in with your new password.", 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            mysql.connection.rollback()
            flash(f"Password reset failed: {str(e)}", 'danger')
            return render_template('auth/forgot_password.html', form=request.form)
        finally:
            cur.close()

    return render_template('auth/forgot_password.html', form={})

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
