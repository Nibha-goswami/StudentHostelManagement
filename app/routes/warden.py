from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from functools import wraps
from werkzeug.security import generate_password_hash
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

def get_warden_info():
    """
    Returns (warden_type, hostel_id, hostel_name).
    If current_user is admin, returns (None, None, None).
    """
    if current_user.role == 'admin':
        return None, None, None

    warden_type = getattr(current_user, 'warden_type', None)
    hostel_id = getattr(current_user, 'hostel_id', None)
    hostel_name = getattr(current_user, 'hostel_name', None)

    if not warden_type:
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT ws.warden_type, h.hostel_id, h.name as hostel_name
            FROM warden_staff ws
            LEFT JOIN hostels h ON (h.hostel_id = ws.hostel_id OR h.warden_user_id = ws.user_id)
            WHERE ws.user_id = %s
        """, (current_user.id,))
        row = cur.fetchone()
        cur.close()
        if row:
            warden_type = row['warden_type']
            hostel_id = row['hostel_id']
            hostel_name = row['hostel_name']
            current_user.warden_type = warden_type
            current_user.hostel_id = hostel_id
            current_user.hostel_name = hostel_name

    return warden_type, hostel_id, hostel_name

# ─────────────────────────────────────────────
#  DASHBOARD
# ─────────────────────────────────────────────
@warden_bp.route('/dashboard')
@login_required
@warden_required
def dashboard():
    warden_type, hostel_id, hostel_name = get_warden_info()
    cur = mysql.connection.cursor()

    # 1. Occupancy view
    if warden_type:
        gender_keyword = 'Boys' if warden_type == 'boys' else 'Girls'
        cur.execute("""SELECT hostel_name, total_beds, occupied_beds, available_beds, occupancy_percent
                       FROM v_hostel_occupancy WHERE hostel_name LIKE %s""", (f"%{gender_keyword}%",))
    else:
        cur.execute("SELECT hostel_name, total_beds, occupied_beds, available_beds, occupancy_percent FROM v_hostel_occupancy")
    occupancy = cur.fetchall()

    # 2. Room applications
    if warden_type:
        cur.execute("""SELECT ra.application_id, ra.status, ra.reserved_at, ra.reservation_expires_at,
                              u.full_name as student_name, s.roll_no, b.bed_label, r.room_number, h.name as hostel_name
                       FROM room_applications ra
                       JOIN students s ON s.student_id=ra.student_id
                       JOIN users u ON u.user_id=s.user_id
                       JOIN beds b ON b.bed_id=ra.bed_id
                       JOIN rooms r ON r.room_id=b.room_id
                       JOIN hostels h ON h.hostel_id=r.hostel_id
                       WHERE ra.status IN ('pending','reserved') AND h.gender_type=%s
                       ORDER BY ra.reserved_at DESC""", (warden_type,))
    else:
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

    # 3. Leave applications
    student_gender = ('male' if warden_type == 'boys' else 'female') if warden_type else None
    if student_gender:
        cur.execute("""SELECT COUNT(*) as cnt
                       FROM leave_applications la
                       JOIN students s ON s.student_id=la.student_id
                       WHERE la.status='pending' AND s.gender=%s""", (student_gender,))
        pending_leaves = cur.fetchone()['cnt']

        cur.execute("""SELECT la.leave_id, la.start_date, la.end_date, la.reason, la.status, la.applied_at,
                              u.full_name as student_name, s.roll_no
                       FROM leave_applications la
                       JOIN students s ON s.student_id=la.student_id
                       JOIN users u ON u.user_id=s.user_id
                       WHERE la.status='pending' AND s.gender=%s ORDER BY la.applied_at""", (student_gender,))
        leave_requests = cur.fetchall()
    else:
        cur.execute("SELECT COUNT(*) as cnt FROM leave_applications WHERE status='pending'")
        pending_leaves = cur.fetchone()['cnt']

        cur.execute("""SELECT la.leave_id, la.start_date, la.end_date, la.reason, la.status, la.applied_at,
                              u.full_name as student_name, s.roll_no
                       FROM leave_applications la
                       JOIN students s ON s.student_id=la.student_id
                       JOIN users u ON u.user_id=s.user_id
                       WHERE la.status='pending' ORDER BY la.applied_at""")
        leave_requests = cur.fetchall()

    # 4. Room transfers
    if student_gender:
        cur.execute("""SELECT rt.transfer_id, rt.reason, rt.status, rt.requested_at,
                              u.full_name as student_name,
                              bf.bed_label as from_bed, rf.room_number as from_room,
                              bt.bed_label as to_bed, rt2.room_number as to_room
                       FROM room_transfers rt
                       JOIN students s ON s.student_id=rt.student_id
                       JOIN users u ON u.user_id=s.user_id
                       JOIN beds bf ON bf.bed_id=rt.from_bed_id JOIN rooms rf ON rf.room_id=bf.room_id
                       JOIN beds bt ON bt.bed_id=rt.to_bed_id JOIN rooms rt2 ON rt2.room_id=bt.room_id
                       WHERE rt.status='pending' AND s.gender=%s ORDER BY rt.requested_at""", (student_gender,))
    else:
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
                           leave_requests=leave_requests, transfer_requests=transfer_requests,
                           warden_type=warden_type)

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
#  RESET STUDENT PASSWORD (WARDEN)
# ─────────────────────────────────────────────
@warden_bp.route('/student/<int:user_id>/reset-password', methods=['POST'])
@login_required
@warden_required
def reset_student_password(user_id):
    new_password = request.form.get('new_password', '').strip()
    if len(new_password) < 6:
        flash('Password must be at least 6 characters long.', 'danger')
        return redirect(request.referrer or url_for('warden.rooms'))

    cur = mysql.connection.cursor()
    cur.execute("""SELECT u.user_id, u.full_name, u.email, s.roll_no
                   FROM users u
                   JOIN students s ON s.user_id=u.user_id
                   WHERE u.user_id=%s AND u.role='student'""", (user_id,))
    student_user = cur.fetchone()
    if not student_user:
        flash('Student record not found.', 'danger')
        cur.close()
        return redirect(request.referrer or url_for('warden.rooms'))

    try:
        hashed = generate_password_hash(new_password)
        cur.execute("UPDATE users SET password_hash=%s WHERE user_id=%s AND role='student'", (hashed, user_id))
        mysql.connection.commit()
        flash(f"Password for {student_user['full_name']} (Roll: {student_user['roll_no']}) has been reset successfully.", 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash(f"Password reset failed: {str(e)}", 'danger')
    finally:
        cur.close()

    return redirect(request.referrer or url_for('warden.rooms'))

# ─────────────────────────────────────────────
#  STUDENT RECORDS (WARDEN)
# ─────────────────────────────────────────────
@warden_bp.route('/students')
@login_required
@warden_required
def students():
    warden_type, hostel_id, hostel_name = get_warden_info()
    cur = mysql.connection.cursor()

    if warden_type:
        student_gender = 'male' if warden_type == 'boys' else 'female'
        cur.execute("""SELECT s.student_id, s.user_id, s.roll_no, s.department, s.year_of_study, s.gender, s.guardian_phone,
                              u.full_name, u.email, u.phone, u.is_active, u.created_at,
                              COALESCE(sl.outstanding_balance, 0) as outstanding_balance,
                              h.name as hostel_name, r.room_number, b.bed_label
                       FROM students s
                       JOIN users u ON u.user_id=s.user_id
                       LEFT JOIN student_ledger sl ON sl.student_id=s.student_id
                       LEFT JOIN room_allocations ra ON ra.student_id=s.student_id AND ra.status='active'
                       LEFT JOIN beds b ON b.bed_id=ra.bed_id
                       LEFT JOIN rooms r ON r.room_id=b.room_id
                       LEFT JOIN hostels h ON h.hostel_id=r.hostel_id
                       WHERE s.gender=%s
                       ORDER BY s.roll_no ASC""", (student_gender,))
    else:
        cur.execute("""SELECT s.student_id, s.user_id, s.roll_no, s.department, s.year_of_study, s.gender, s.guardian_phone,
                              u.full_name, u.email, u.phone, u.is_active, u.created_at,
                              COALESCE(sl.outstanding_balance, 0) as outstanding_balance,
                              h.name as hostel_name, r.room_number, b.bed_label
                       FROM students s
                       JOIN users u ON u.user_id=s.user_id
                       LEFT JOIN student_ledger sl ON sl.student_id=s.student_id
                       LEFT JOIN room_allocations ra ON ra.student_id=s.student_id AND ra.status='active'
                       LEFT JOIN beds b ON b.bed_id=ra.bed_id
                       LEFT JOIN rooms r ON r.room_id=b.room_id
                       LEFT JOIN hostels h ON h.hostel_id=r.hostel_id
                       ORDER BY s.roll_no ASC""")
    students_list = cur.fetchall()
    cur.close()
    return render_template('warden/students.html', students=students_list, warden_type=warden_type)

# ─────────────────────────────────────────────
#  ROOMS OVERVIEW
# ─────────────────────────────────────────────
@warden_bp.route('/rooms')
@login_required
@warden_required
def rooms():
    warden_type, hostel_id, hostel_name = get_warden_info()
    cur = mysql.connection.cursor()

    if warden_type:
        cur.execute("""SELECT vb.bed_id, vb.bed_label, vb.room_number, vb.floor_no,
                              vb.hostel_name, vb.hostel_id, vb.bed_status
                       FROM v_bed_status vb
                       JOIN hostels h ON h.hostel_id=vb.hostel_id
                       WHERE h.gender_type=%s
                       ORDER BY vb.floor_no, vb.room_number, vb.bed_label""", (warden_type,))
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
                       WHERE ra.status='active' AND h.gender_type=%s
                       ORDER BY r.room_number, b.bed_label""", (warden_type,))
        allocations = cur.fetchall()

        student_gender = 'male' if warden_type == 'boys' else 'female'
        cur.execute("""SELECT u.user_id, u.full_name, u.email, u.is_active,
                              s.student_id, s.roll_no, s.department, s.gender,
                              MAX(ra.vacated_at) as last_vacated
                       FROM users u
                       JOIN students s ON s.user_id=u.user_id
                       LEFT JOIN room_allocations ra ON ra.student_id=s.student_id
                       WHERE u.is_active=0 AND u.role='student' AND s.gender=%s
                       GROUP BY u.user_id, u.full_name, u.email, u.is_active,
                                s.student_id, s.roll_no, s.department, s.gender""", (student_gender,))
        inactive_students = cur.fetchall()
    else:
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
                           inactive_students=inactive_students,
                           warden_type=warden_type)
