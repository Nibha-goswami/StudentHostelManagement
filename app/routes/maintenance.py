from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from functools import wraps
from app import mysql

maintenance_bp = Blueprint('maintenance', __name__, url_prefix='/maintenance')

def maintenance_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role not in ('maintenance', 'admin'):
            flash('Access denied.', 'danger')
            return redirect(url_for('auth.dashboard'))
        return f(*args, **kwargs)
    return decorated

def get_staff_id():
    cur = mysql.connection.cursor()
    cur.execute("SELECT staff_id, specialization FROM maintenance_staff WHERE user_id=%s", (current_user.id,))
    row = cur.fetchone()
    cur.close()
    return row

@maintenance_bp.route('/dashboard')
@login_required
@maintenance_required
def dashboard():
    staff = get_staff_id()
    cur = mysql.connection.cursor()
    if staff:
        cur.execute("""SELECT c.complaint_id, c.ticket_no, c.title, c.category, c.status,
                       c.created_at, c.description, c.escalated_at,
                       u.full_name as student_name, r.room_number, h.name as hostel_name
                       FROM complaints c
                       JOIN complaint_assignments ca ON ca.complaint_id=c.complaint_id AND ca.is_current=1
                       JOIN students s ON s.student_id=c.student_id
                       JOIN users u ON u.user_id=s.user_id
                       JOIN rooms r ON r.room_id=c.room_id
                       JOIN hostels h ON h.hostel_id=r.hostel_id
                       WHERE ca.staff_id=%s
                       ORDER BY c.status='Escalated' DESC, c.created_at ASC""", (staff['staff_id'],))
        my_complaints = cur.fetchall()
        cur.execute("SELECT COUNT(*) as open FROM complaints c JOIN complaint_assignments ca ON ca.complaint_id=c.complaint_id AND ca.is_current=1 WHERE ca.staff_id=%s AND c.status IN ('Open','In_Progress')", (staff['staff_id'],))
        open_count = cur.fetchone()['open']
        cur.execute("SELECT COUNT(*) as resolved FROM complaints c JOIN complaint_assignments ca ON ca.complaint_id=c.complaint_id WHERE ca.staff_id=%s AND c.status='Resolved'", (staff['staff_id'],))
        resolved_count = cur.fetchone()['resolved']
    else:
        my_complaints = []
        open_count = 0
        resolved_count = 0
    cur.close()
    return render_template('maintenance/dashboard.html', staff=staff,
                           my_complaints=my_complaints, open_count=open_count,
                           resolved_count=resolved_count)

@maintenance_bp.route('/complaint/<int:cid>/update', methods=['POST'])
@login_required
@maintenance_required
def update_complaint(cid):
    new_status = request.form.get('status')
    note = request.form.get('resolution_note', '')
    cur = mysql.connection.cursor()
    cur.execute("SET @app_user_id = %s", (current_user.id,))
    if new_status == 'Resolved':
        cur.execute("""UPDATE complaints SET status='Resolved', resolved_at=NOW(), resolution_note=%s
                       WHERE complaint_id=%s""", (note, cid))
    elif new_status == 'In_Progress':
        cur.execute("UPDATE complaints SET status='In_Progress' WHERE complaint_id=%s", (cid,))
    mysql.connection.commit()
    cur.execute("SET @app_user_id = NULL")
    mysql.connection.commit()
    cur.close()
    flash('Complaint status updated.', 'success')
    return redirect(url_for('maintenance.dashboard'))
