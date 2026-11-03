from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from functools import wraps
from app import mysql

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role != 'admin':
            flash('Access denied.', 'danger')
            return redirect(url_for('auth.dashboard'))
        return f(*args, **kwargs)
    return decorated

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    cur = mysql.connection.cursor()
    cur.execute("SELECT COUNT(*) as cnt FROM users WHERE is_active=1")
    total_users = cur.fetchone()['cnt']
    cur.execute("SELECT COUNT(*) as cnt FROM students")
    total_students = cur.fetchone()['cnt']
    cur.execute("SELECT COUNT(*) as cnt FROM complaints WHERE status='Open'")
    open_complaints = cur.fetchone()['cnt']
    cur.execute("SELECT COUNT(*) as cnt FROM complaints WHERE status='Escalated'")
    escalated = cur.fetchone()['cnt']
    cur.execute("SELECT SUM(outstanding_balance) as total FROM student_ledger WHERE outstanding_balance>0")
    row = cur.fetchone()
    total_dues = row['total'] if row['total'] else 0
    cur.execute("SELECT COUNT(*) as cnt FROM room_applications WHERE status='pending'")
    pending_apps = cur.fetchone()['cnt']

    cur.execute("""SELECT u.full_name, u.email, u.role, u.created_at, u.is_active
                   FROM users u ORDER BY u.created_at DESC LIMIT 8""")
    recent_users = cur.fetchall()

    cur.execute("""SELECT c.ticket_no, c.title, c.status, c.created_at, u.full_name as student_name, c.category
                   FROM complaints c JOIN students s ON s.student_id=c.student_id
                   JOIN users u ON u.user_id=s.user_id
                   ORDER BY c.created_at DESC LIMIT 6""")
    recent_complaints = cur.fetchall()

    cur.execute("SELECT hostel_name, total_beds, occupied_beds, available_beds, occupancy_percent FROM v_hostel_occupancy")
    occupancy = cur.fetchall()

    cur.execute("""SELECT meal_date, meal_type, students_attended FROM v_daily_meal_attendance
                   ORDER BY meal_date DESC, meal_type LIMIT 10""")
    meal_attendance = cur.fetchall()

    cur.execute("SELECT COUNT(*) as cnt FROM leave_applications WHERE status='pending'")
    pending_leaves = cur.fetchone()['cnt']

    cur.close()
    return render_template('admin/dashboard.html',
        total_users=total_users, total_students=total_students,
        open_complaints=open_complaints, escalated=escalated,
        total_dues=total_dues, pending_apps=pending_apps,
        recent_users=recent_users, recent_complaints=recent_complaints,
        occupancy=occupancy, meal_attendance=meal_attendance,
        pending_leaves=pending_leaves)

@admin_bp.route('/users')
@login_required
@admin_required
def users():
    cur = mysql.connection.cursor()
    cur.execute("""SELECT u.user_id, u.email, u.full_name, u.phone, u.role, u.is_active, u.created_at
                   FROM users u ORDER BY u.created_at DESC""")
    users = cur.fetchall()
    cur.close()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/toggle/<int:uid>', methods=['POST'])
@login_required
@admin_required
def toggle_user(uid):
    if uid == current_user.id:
        flash('Cannot deactivate yourself.', 'warning')
        return redirect(url_for('admin.users'))
    cur = mysql.connection.cursor()
    cur.execute("UPDATE users SET is_active = 1 - is_active WHERE user_id=%s", (uid,))
    mysql.connection.commit()
    cur.close()
    flash('User status updated.', 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/hostels')
@login_required
@admin_required
def hostels():
    cur = mysql.connection.cursor()
    cur.execute("""SELECT h.hostel_id, h.name, h.gender_type, u.full_name as warden_name,
                   COUNT(r.room_id) as room_count
                   FROM hostels h LEFT JOIN users u ON u.user_id=h.warden_user_id
                   LEFT JOIN rooms r ON r.hostel_id=h.hostel_id
                   GROUP BY h.hostel_id""")
    hostels = cur.fetchall()
    cur.execute("""SELECT hostel_name, total_beds, occupied_beds, available_beds, occupancy_percent
                   FROM v_hostel_occupancy""")
    occupancy = cur.fetchall()
    cur.close()
    return render_template('admin/hostels.html', hostels=hostels, occupancy=occupancy)

@admin_bp.route('/complaints')
@login_required
@admin_required
def complaints():
    cur = mysql.connection.cursor()
    cur.execute("""SELECT c.complaint_id, c.ticket_no, c.title, c.category, c.status,
                   c.created_at, c.escalated_at, c.resolved_at,
                   u.full_name as student_name, r.room_number,
                   h.name as hostel_name
                   FROM complaints c
                   JOIN students s ON s.student_id=c.student_id
                   JOIN users u ON u.user_id=s.user_id
                   JOIN rooms r ON r.room_id=c.room_id
                   JOIN hostels h ON h.hostel_id=r.hostel_id
                   ORDER BY c.created_at DESC""")
    complaints = cur.fetchall()

    cur.execute("""SELECT ms.staff_id, u.full_name, ms.specialization
                   FROM maintenance_staff ms JOIN users u ON u.user_id=ms.user_id""")
    staff = cur.fetchall()
    cur.close()
    return render_template('admin/complaints.html', complaints=complaints, staff=staff)

@admin_bp.route('/complaints/assign', methods=['POST'])
@login_required
@admin_required
def assign_complaint():
    complaint_id = request.form.get('complaint_id')
    staff_id = request.form.get('staff_id')
    cur = mysql.connection.cursor()
    # Mark old assignments as not current
    cur.execute("UPDATE complaint_assignments SET is_current=0 WHERE complaint_id=%s", (complaint_id,))
    cur.execute("INSERT INTO complaint_assignments (complaint_id, staff_id, assigned_by) VALUES (%s,%s,%s)",
                (complaint_id, staff_id, current_user.id))
    cur.execute("UPDATE complaints SET status='In_Progress' WHERE complaint_id=%s AND status='Open'", (complaint_id,))
    mysql.connection.commit()
    cur.close()
    flash('Staff assigned successfully.', 'success')
    return redirect(url_for('admin.complaints'))

@admin_bp.route('/finance')
@login_required
@admin_required
def finance():
    cur = mysql.connection.cursor()
    cur.execute("""SELECT sl.student_id, sl.roll_no, sl.full_name,
                   sl.hostel_fees, sl.mess_fees, sl.fines,
                   sl.approved_rebates, sl.payments_made, sl.outstanding_balance
                   FROM student_ledger sl ORDER BY sl.outstanding_balance DESC""")
    ledger = cur.fetchall()

    cur.execute("SELECT SUM(outstanding_balance) as total FROM student_ledger WHERE outstanding_balance>0")
    row = cur.fetchone()
    total_dues = row['total'] if row['total'] else 0

    cur.execute("SELECT SUM(amount) as total FROM payments WHERE status='successful'")
    row = cur.fetchone()
    total_collected = row['total'] if row['total'] else 0

    cur.execute("""SELECT p.payment_id, p.amount, p.method, p.status, p.reference_no, p.created_at,
                   u.full_name as student_name
                   FROM payments p JOIN students s ON s.student_id=p.student_id
                   JOIN users u ON u.user_id=s.user_id
                   ORDER BY p.created_at DESC LIMIT 20""")
    payments = cur.fetchall()
    cur.close()
    return render_template('admin/finance.html', ledger=ledger,
                           total_dues=total_dues, total_collected=total_collected,
                           payments=payments)
