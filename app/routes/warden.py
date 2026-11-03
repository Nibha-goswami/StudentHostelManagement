from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from functools import wraps
from app import mysql

warden_bp = Blueprint('warden', __name__, url_prefix='/warden')

def warden_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role not in ('warden', 'admin'):
            flash('Access denied.', 'danger')
            return redirect(url_for('auth.dashboard'))
        return f(*args, **kwargs)
    return decorated

# ─────────────────────────────────────────────
#  DASHBOARD
# ─────────────────────────────────────────────
@warden_bp.route('/dashboard')
@login_required
@warden_required
def dashboard():
    cur = mysql.connection.cursor()
    cur.execute("SELECT hostel_name, total_beds, occupied_beds, available_beds, occupancy_percent FROM v_hostel_occupancy")
    occupancy = cur.fetchall()

    cur.execute("""SELECT ra.application_id, ra.status, ra.reserved_at, ra.reservation_expires_at,
                   u.full_name as student_name, s.roll_no, b.bed_label, r.room_number, h.name as hostel_name
                   FROM room_applications ra
                   JOIN students s ON s.student_id=ra.student_id
                   JOIN users u ON u.user_id=s.user_id
                   JOIN beds b ON b.bed_id=ra.bed_id
                   JOIN rooms r ON r.room_id=b.room_id
                   JOIN hostels h ON h.hostel_id=r.hostel_id
                   WHERE ra.status IN ('pending','reserved')
                   ORDER BY ra.reserved_at DESC""")
    pending_apps = cur.fetchall()

    cur.execute("SELECT COUNT(*) as cnt FROM leave_applications WHERE status='pending'")
    pending_leaves = cur.fetchone()['cnt']

    cur.execute("""SELECT la.leave_id, la.start_date, la.end_date, la.reason, la.status, la.applied_at,
                   u.full_name as student_name, s.roll_no
                   FROM leave_applications la
                   JOIN students s ON s.student_id=la.student_id
                   JOIN users u ON u.user_id=s.user_id
                   WHERE la.status='pending' ORDER BY la.applied_at""")
    leave_requests = cur.fetchall()

    cur.execute("""SELECT rt.transfer_id, rt.reason, rt.status, rt.requested_at,
                   u.full_name as student_name,
                   bf.bed_label as from_bed, rf.room_number as from_room,
                   bt.bed_label as to_bed, rt2.room_number as to_room
                   FROM room_transfers rt
                   JOIN students s ON s.student_id=rt.student_id
                   JOIN users u ON u.user_id=s.user_id
                   JOIN beds bf ON bf.bed_id=rt.from_bed_id JOIN rooms rf ON rf.room_id=bf.room_id
                   JOIN beds bt ON bt.bed_id=rt.to_bed_id JOIN rooms rt2 ON rt2.room_id=bt.room_id
                   WHERE rt.status='pending' ORDER BY rt.requested_at""")
    transfer_requests = cur.fetchall()
    cur.close()

    return render_template('warden/dashboard.html', occupancy=occupancy,
                           pending_apps=pending_apps, pending_leaves=pending_leaves,
                           leave_requests=leave_requests, transfer_requests=transfer_requests)

# ─────────────────────────────────────────────
#  ROOM APPLICATIONS
# ─────────────────────────────────────────────
@warden_bp.route('/application/<int:app_id>/approve', methods=['POST'])
@login_required
@warden_required
def approve_application(app_id):
    cur = mysql.connection.cursor()
    try:
        cur.execute("""SELECT student_id, bed_id FROM room_applications
                       WHERE application_id=%s AND status IN ('pending','reserved')""", (app_id,))
        app = cur.fetchone()
        if not app:
            flash('Application not found or already processed.', 'warning')
            cur.close()
            return redirect(url_for('warden.dashboard'))
        cur.execute("""UPDATE room_applications SET status='approved', reviewed_by=%s, reviewed_at=NOW()
                       WHERE application_id=%s""", (current_user.id, app_id))
        cur.execute("""INSERT INTO room_allocations (application_id, student_id, bed_id)
                       VALUES (%s, %s, %s)""", (app_id, app['student_id'], app['bed_id']))
        mysql.connection.commit()
        flash('Application approved and room allocated!', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash(f'Error: {str(e)}', 'danger')
    cur.close()
    return redirect(url_for('warden.dashboard'))

@warden_bp.route('/application/<int:app_id>/reject', methods=['POST'])
@login_required
@warden_required
def reject_application(app_id):
    remarks = request.form.get('remarks', 'Rejected by warden')
    cur = mysql.connection.cursor()
    cur.execute("""UPDATE room_applications SET status='rejected', reviewed_by=%s, reviewed_at=NOW(), remarks=%s
                   WHERE application_id=%s""", (current_user.id, remarks, app_id))
    mysql.connection.commit()
    cur.close()
    flash('Application rejected.', 'info')
    return redirect(url_for('warden.dashboard'))

# ─────────────────────────────────────────────
#  LEAVE APPLICATIONS
# ─────────────────────────────────────────────
@warden_bp.route('/leave/<int:leave_id>/approve', methods=['POST'])
@login_required
@warden_required
def approve_leave(leave_id):
    cur = mysql.connection.cursor()
    cur.execute("""UPDATE leave_applications SET status='approved', reviewed_by=%s, reviewed_at=NOW()
                   WHERE leave_id=%s AND status='pending'""", (current_user.id, leave_id))
    mysql.connection.commit()
    cur.close()
    flash('Leave approved. Rebate will be applied automatically.', 'success')
    return redirect(url_for('warden.dashboard'))

@warden_bp.route('/leave/<int:leave_id>/reject', methods=['POST'])
@login_required
@warden_required
def reject_leave(leave_id):
    remarks = request.form.get('remarks', '')
    cur = mysql.connection.cursor()
    cur.execute("""UPDATE leave_applications SET status='rejected', reviewed_by=%s, reviewed_at=NOW(), remarks=%s
                   WHERE leave_id=%s AND status='pending'""", (current_user.id, remarks, leave_id))
    mysql.connection.commit()
    cur.close()
    flash('Leave application rejected.', 'info')
    return redirect(url_for('warden.dashboard'))

# ─────────────────────────────────────────────
#  ROOM TRANSFERS
# ─────────────────────────────────────────────
@warden_bp.route('/transfer/<int:tid>/approve', methods=['POST'])
@login_required
@warden_required
def approve_transfer(tid):
    cur = mysql.connection.cursor()
    try:
        cur.execute("SELECT student_id, from_bed_id, to_bed_id FROM room_transfers WHERE transfer_id=%s", (tid,))
        tr = cur.fetchone()
        if tr:
            cur.execute("""UPDATE room_allocations SET bed_id=%s WHERE student_id=%s AND status='active'""",
                        (tr['to_bed_id'], tr['student_id']))
            cur.execute("""UPDATE room_transfers SET status='completed', reviewed_by=%s, reviewed_at=NOW()
                           WHERE transfer_id=%s""", (current_user.id, tid))
            mysql.connection.commit()
            flash('Transfer approved and completed.', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash(f'Error: {str(e)}', 'danger')
    cur.close()
    return redirect(url_for('warden.dashboard'))

# ─────────────────────────────────────────────
#  CHECKOUT STUDENT  (free bed for new student)
# ─────────────────────────────────────────────
@warden_bp.route('/student/<int:student_id>/checkout', methods=['POST'])
@login_required
@warden_required
def checkout_student(student_id):
    reason     = request.form.get('reason', 'Checked out by warden')
    deactivate = request.form.get('deactivate_account') == '1'
    cur = mysql.connection.cursor()
    try:
        cur.execute("SELECT user_id FROM students WHERE student_id=%s", (student_id,))
        stu = cur.fetchone()
        if not stu:
            flash('Student not found.', 'danger')
            cur.close()
            return redirect(url_for('warden.rooms'))

        user_id = stu['user_id']

        # Vacate active bed allocation
        cur.execute("""UPDATE room_allocations SET status='vacated', vacated_at=NOW()
                       WHERE student_id=%s AND status='active'""", (student_id,))
        vacated = cur.rowcount

        # Cancel any pending/reserved applications
        cur.execute("""UPDATE room_applications SET status='cancelled'
                       WHERE student_id=%s AND status IN ('pending','reserved')""", (student_id,))

        # Optionally deactivate login
        if deactivate:
            cur.execute("UPDATE users SET is_active=0 WHERE user_id=%s", (user_id,))

        mysql.connection.commit()

        if vacated:
            msg = 'Student checked out. Bed is now free for new incoming students.'
            if deactivate:
                msg += ' Login account deactivated.'
            flash(msg, 'success')
        else:
            flash('No active allocation found for this student.', 'warning')

    except Exception as e:
        mysql.connection.rollback()
        flash(f'Checkout failed: {str(e)}', 'danger')
    finally:
        cur.close()

    return redirect(url_for('warden.rooms'))

# ─────────────────────────────────────────────
#  RE-ACTIVATE STUDENT ACCOUNT
# ─────────────────────────────────────────────
@warden_bp.route('/student/<int:user_id>/reactivate', methods=['POST'])
@login_required
@warden_required
def reactivate_student(user_id):
    cur = mysql.connection.cursor()
    cur.execute("UPDATE users SET is_active=1 WHERE user_id=%s AND role='student'", (user_id,))
    mysql.connection.commit()
    cur.close()
    flash('Student account reactivated. They can now log in and book a new bed.', 'success')
    return redirect(url_for('warden.rooms'))

# ─────────────────────────────────────────────
#  ROOMS OVERVIEW
# ─────────────────────────────────────────────
@warden_bp.route('/rooms')
@login_required
@warden_required
def rooms():
    cur = mysql.connection.cursor()

    cur.execute("""SELECT vb.bed_id, vb.bed_label, vb.room_number, vb.floor_no,
                   vb.hostel_name, vb.hostel_id, vb.bed_status
                   FROM v_bed_status vb
                   ORDER BY vb.hostel_name, vb.floor_no, vb.room_number, vb.bed_label""")
    beds = cur.fetchall()

    cur.execute("""SELECT ra.allocation_id, ra.student_id, ra.allocated_at,
                   u.user_id, u.full_name as student_name, u.email, u.is_active,
                   s.roll_no, s.department, s.year_of_study, s.gender,
                   b.bed_label, r.room_number, r.floor_no,
                   h.name as hostel_name, h.gender_type
                   FROM room_allocations ra
                   JOIN students s ON s.student_id=ra.student_id
                   JOIN users u ON u.user_id=s.user_id
                   JOIN beds b ON b.bed_id=ra.bed_id
                   JOIN rooms r ON r.room_id=b.room_id
                   JOIN hostels h ON h.hostel_id=r.hostel_id
                   WHERE ra.status='active'
                   ORDER BY h.name, r.room_number, b.bed_label""")
    allocations = cur.fetchall()

    cur.execute("""SELECT u.user_id, u.full_name, u.email, u.is_active,
                   s.student_id, s.roll_no, s.department, s.gender,
                   MAX(ra.vacated_at) as last_vacated
                   FROM users u
                   JOIN students s ON s.user_id=u.user_id
                   LEFT JOIN room_allocations ra ON ra.student_id=s.student_id
                   WHERE u.is_active=0 AND u.role='student'
                   GROUP BY u.user_id, u.full_name, u.email, u.is_active,
                            s.student_id, s.roll_no, s.department, s.gender""")
    inactive_students = cur.fetchall()

    cur.close()
    return render_template('warden/rooms.html', beds=beds,
                           allocations=allocations,
                           inactive_students=inactive_students)
