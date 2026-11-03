from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from functools import wraps
from app import mysql
import uuid, secrets, string
from datetime import datetime, date

student_bp = Blueprint('student', __name__, url_prefix='/student')

def student_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role != 'student':
            flash('Access denied.', 'danger')
            return redirect(url_for('auth.dashboard'))
        return f(*args, **kwargs)
    return decorated

def get_student_id():
    cur = mysql.connection.cursor()
    cur.execute("SELECT student_id FROM students WHERE user_id=%s", (current_user.id,))
    row = cur.fetchone()
    cur.close()
    return row['student_id'] if row else None

@student_bp.route('/dashboard')
@login_required
@student_required
def dashboard():
    sid = get_student_id()
    cur = mysql.connection.cursor()
    cur.execute("""SELECT sl.roll_no, sl.hostel_fees, sl.mess_fees, sl.fines,
                   sl.approved_rebates, sl.payments_made, sl.outstanding_balance
                   FROM student_ledger sl WHERE sl.student_id=%s""", (sid,))
    ledger = cur.fetchone()

    cur.execute("""SELECT ra.status, b.bed_label, r.room_number, r.floor_no, h.name as hostel_name
                   FROM room_allocations ra
                   JOIN beds b ON b.bed_id=ra.bed_id
                   JOIN rooms r ON r.room_id=b.room_id
                   JOIN hostels h ON h.hostel_id=r.hostel_id
                   WHERE ra.student_id=%s AND ra.status='active'""", (sid,))
    allocation = cur.fetchone()

    cur.execute("""SELECT c.ticket_no, c.title, c.status, c.category, c.created_at
                   FROM complaints c WHERE c.student_id=%s ORDER BY c.created_at DESC LIMIT 5""", (sid,))
    complaints = cur.fetchall()

    cur.execute("""SELECT la.leave_id, la.start_date, la.end_date, la.status, la.reason
                   FROM leave_applications la WHERE la.student_id=%s ORDER BY la.applied_at DESC LIMIT 5""", (sid,))
    leaves = cur.fetchall()

    cur.execute("""SELECT ml.meal_type, ml.meal_date, ml.scan_status, ml.scan_timestamp
                   FROM mess_logs ml WHERE ml.student_id=%s ORDER BY ml.scan_timestamp DESC LIMIT 7""", (sid,))
    meal_logs = cur.fetchall()

    first_of_month = date.today().replace(day=1)
    cur.execute("""SELECT COUNT(*) as cnt FROM mess_logs
                   WHERE student_id=%s AND scan_status='success'
                   AND meal_date >= %s""", (sid, first_of_month))
    month_meals = cur.fetchone()['cnt']

    cur.close()
    return render_template('student/dashboard.html', ledger=ledger,
                           allocation=allocation, complaints=complaints,
                           leaves=leaves, meal_logs=meal_logs, month_meals=month_meals)

@student_bp.route('/hostel')
@login_required
@student_required
def hostel():
    sid = get_student_id()
    cur = mysql.connection.cursor()
    cur.execute("""SELECT ra.allocation_id, ra.status, ra.allocated_at,
                   b.bed_label, r.room_number, r.floor_no, h.name as hostel_name, h.gender_type
                   FROM room_allocations ra
                   JOIN beds b ON b.bed_id=ra.bed_id
                   JOIN rooms r ON r.room_id=b.room_id
                   JOIN hostels h ON h.hostel_id=r.hostel_id
                   WHERE ra.student_id=%s AND ra.status='active'""", (sid,))
    allocation = cur.fetchone()

    cur.execute("""SELECT app.application_id, app.status, app.reserved_at, app.reservation_expires_at,
                   b.bed_label, r.room_number, h.name as hostel_name
                   FROM room_applications app
                   JOIN beds b ON b.bed_id=app.bed_id
                   JOIN rooms r ON r.room_id=b.room_id
                   JOIN hostels h ON h.hostel_id=r.hostel_id
                   WHERE app.student_id=%s AND app.status IN ('reserved','pending')
                   ORDER BY app.reserved_at DESC LIMIT 1""", (sid,))
    pending_app = cur.fetchone()

    # Get student gender for filtering
    cur.execute("SELECT gender FROM students WHERE student_id=%s", (sid,))
    st = cur.fetchone()
    gender = st['gender']
    hostel_gender = 'boys' if gender == 'male' else 'girls'

    cur.execute("""SELECT vb.bed_id, vb.bed_label, vb.room_number, vb.floor_no,
                   vb.hostel_name, vb.hostel_id, vb.bed_status
                   FROM v_bed_status vb
                   WHERE vb.bed_status='available'
                   AND EXISTS (SELECT 1 FROM hostels hh WHERE hh.hostel_id=vb.hostel_id AND hh.gender_type=%s)
                   LIMIT 30""", (hostel_gender,))
    available_beds = cur.fetchall()

    cur.execute("""SELECT rt.transfer_id, rt.status, rt.requested_at, rt.reason,
                   bf.bed_label as from_bed, rf.room_number as from_room,
                   bt.bed_label as to_bed, rt2.room_number as to_room
                   FROM room_transfers rt
                   JOIN beds bf ON bf.bed_id=rt.from_bed_id
                   JOIN rooms rf ON rf.room_id=bf.room_id
                   JOIN beds bt ON bt.bed_id=rt.to_bed_id
                   JOIN rooms rt2 ON rt2.room_id=bt.room_id
                   WHERE rt.student_id=%s ORDER BY rt.requested_at DESC LIMIT 5""", (sid,))
    transfers = cur.fetchall()
    cur.close()
    return render_template('student/hostel.html', allocation=allocation,
                           pending_app=pending_app, available_beds=available_beds,
                           transfers=transfers)

@student_bp.route('/hostel/book', methods=['POST'])
@login_required
@student_required
def book_bed():
    sid = get_student_id()
    bed_id = request.form.get('bed_id')
    cur = mysql.connection.cursor()
    # Expire stale reservations first
    cur.execute("CALL sp_expire_stale_reservations()")
    # Check student doesn't already have active allocation
    cur.execute("SELECT 1 FROM room_allocations WHERE student_id=%s AND status='active'", (sid,))
    if cur.fetchone():
        flash('You already have an active room allocation.', 'warning')
        cur.close()
        return redirect(url_for('student.hostel'))
    try:
        from datetime import datetime, timedelta
        expires = datetime.now() + timedelta(minutes=10)
        cur.execute("""INSERT INTO room_applications (student_id, bed_id, status, reservation_expires_at)
                       VALUES (%s, %s, 'reserved', %s)""", (sid, bed_id, expires))
        mysql.connection.commit()
        flash('Bed reserved for 10 minutes! Please confirm with the warden.', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash(f'Booking failed: {str(e)}', 'danger')
    cur.close()
    return redirect(url_for('student.hostel'))

@student_bp.route('/hostel/transfer', methods=['POST'])
@login_required
@student_required
def request_transfer():
    sid = get_student_id()
    to_bed_id = request.form.get('to_bed_id')
    reason = request.form.get('reason', '')
    cur = mysql.connection.cursor()
    cur.execute("SELECT bed_id FROM room_allocations WHERE student_id=%s AND status='active'", (sid,))
    alloc = cur.fetchone()
    if not alloc:
        flash('You do not have an active allocation to transfer from.', 'warning')
        cur.close()
        return redirect(url_for('student.hostel'))
    try:
        cur.execute("""INSERT INTO room_transfers (student_id, from_bed_id, to_bed_id, reason)
                       VALUES (%s, %s, %s, %s)""", (sid, alloc['bed_id'], to_bed_id, reason))
        mysql.connection.commit()
        flash('Transfer request submitted successfully.', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash(f'Transfer request failed: {str(e)}', 'danger')
    cur.close()
    return redirect(url_for('student.hostel'))

@student_bp.route('/mess')
@login_required
@student_required
def mess():
    sid = get_student_id()
    cur = mysql.connection.cursor()
    cur.execute("""SELECT ml.meal_type, ml.meal_date, ml.scan_status, ml.scan_timestamp
                   FROM mess_logs ml WHERE ml.student_id=%s
                   ORDER BY ml.scan_timestamp DESC LIMIT 30""", (sid,))
    meal_logs = cur.fetchall()
    cur.execute("SELECT meal_type, start_time, end_time, cost_per_portion FROM mess_meals ORDER BY meal_id")
    meals = cur.fetchall()
    cur.execute("""SELECT SUM(gross_amount) as total, MAX(billing_month) as last_month
                   FROM mess_billing WHERE student_id=%s""", (sid,))
    billing = cur.fetchone()
    cur.execute("""SELECT SUM(rebate_amount) as total_rebate FROM mess_rebates
                   WHERE student_id=%s AND status='applied'""", (sid,))
    rebate = cur.fetchone()
    cur.close()
    return render_template('student/mess.html', meal_logs=meal_logs, meals=meals,
                           billing=billing, rebate=rebate)

@student_bp.route('/leaves')
@login_required
@student_required
def leaves():
    sid = get_student_id()
    cur = mysql.connection.cursor()
    cur.execute("""SELECT la.leave_id, la.start_date, la.end_date, la.reason, la.status,
                   la.applied_at, la.remarks, u.full_name as reviewed_by
                   FROM leave_applications la
                   LEFT JOIN users u ON u.user_id=la.reviewed_by
                   WHERE la.student_id=%s ORDER BY la.applied_at DESC""", (sid,))
    leaves = cur.fetchall()
    cur.execute("""SELECT mr.rebate_days, mr.rebate_amount, mr.status as rebate_status
                   FROM mess_rebates mr WHERE mr.student_id=%s ORDER BY mr.created_at DESC""", (sid,))
    rebates = cur.fetchall()
    cur.close()
    return render_template('student/leaves.html', leaves=leaves, rebates=rebates)

@student_bp.route('/leaves/apply', methods=['POST'])
@login_required
@student_required
def apply_leave():
    sid = get_student_id()
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    reason = request.form.get('reason', '').strip()
    if not all([start_date, end_date, reason]):
        flash('All fields are required.', 'warning')
        return redirect(url_for('student.leaves'))
    cur = mysql.connection.cursor()
    try:
        cur.execute("""INSERT INTO leave_applications (student_id, start_date, end_date, reason)
                       VALUES (%s, %s, %s, %s)""", (sid, start_date, end_date, reason))
        mysql.connection.commit()
        flash('Leave application submitted successfully.', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash(f'Application failed: {str(e)}', 'danger')
    cur.close()
    return redirect(url_for('student.leaves'))

@student_bp.route('/complaints')
@login_required
@student_required
def complaints():
    sid = get_student_id()
    cur = mysql.connection.cursor()
    cur.execute("""SELECT c.complaint_id, c.ticket_no, c.title, c.category, c.status,
                   c.created_at, c.description, c.resolution_note, c.escalated_at
                   FROM complaints c WHERE c.student_id=%s ORDER BY c.created_at DESC""", (sid,))
    complaints = cur.fetchall()
    # Get room for this student
    cur.execute("""SELECT ra.bed_id, r.room_id, r.room_number, h.name as hostel_name
                   FROM room_allocations ra
                   JOIN beds b ON b.bed_id=ra.bed_id
                   JOIN rooms r ON r.room_id=b.room_id
                   JOIN hostels h ON h.hostel_id=r.hostel_id
                   WHERE ra.student_id=%s AND ra.status='active'""", (sid,))
    room = cur.fetchone()
    cur.close()
    return render_template('student/complaints.html', complaints=complaints, room=room)

@student_bp.route('/complaints/raise', methods=['POST'])
@login_required
@student_required
def raise_complaint():
    sid = get_student_id()
    room_id = request.form.get('room_id')
    category = request.form.get('category')
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    if not all([room_id, category, title]):
        flash('Please fill all required fields.', 'warning')
        return redirect(url_for('student.complaints'))
    cur = mysql.connection.cursor()
    try:
        cur.execute("SET @app_user_id = %s", (current_user.id,))
        ticket_var = cur.callproc('sp_create_complaint',
                                  (sid, int(room_id), category, title, description, None, ''))
        mysql.connection.commit()
        flash('Complaint raised successfully!', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash(f'Failed to raise complaint: {str(e)}', 'danger')
    cur.close()
    return redirect(url_for('student.complaints'))

@student_bp.route('/fees')
@login_required
@student_required
def fees():
    sid = get_student_id()
    cur = mysql.connection.cursor()
    cur.execute("""SELECT sl.hostel_fees, sl.mess_fees, sl.fines,
                   sl.approved_rebates, sl.payments_made, sl.outstanding_balance
                   FROM student_ledger sl WHERE sl.student_id=%s""", (sid,))
    ledger = cur.fetchone()
    cur.execute("""SELECT hf.fee_id, hf.academic_year, hf.semester, hf.amount, hf.due_date
                   FROM hostel_fees hf WHERE hf.student_id=%s ORDER BY hf.due_date""", (sid,))
    hostel_fees = cur.fetchall()
    cur.execute("""SELECT mb.billing_month, mb.gross_amount, mb.rebate_total, mb.net_amount
                   FROM mess_billing mb WHERE mb.student_id=%s ORDER BY mb.billing_month DESC""", (sid,))
    mess_bills = cur.fetchall()
    cur.execute("""SELECT f.fine_id, f.reason, f.description, f.amount, f.status, f.imposed_at
                   FROM fines f WHERE f.student_id=%s ORDER BY f.imposed_at DESC""", (sid,))
    fines = cur.fetchall()
    cur.execute("""SELECT p.payment_id, p.amount, p.method, p.status, p.reference_no, p.created_at
                   FROM payments p WHERE p.student_id=%s ORDER BY p.created_at DESC""", (sid,))
    payments = cur.fetchall()
    cur.close()
    return render_template('student/fees.html', ledger=ledger, hostel_fees=hostel_fees,
                           mess_bills=mess_bills, fines=fines, payments=payments)

@student_bp.route('/fees/pay', methods=['POST'])
@login_required
@student_required
def pay_fees():
    sid = get_student_id()
    amount = request.form.get('amount')
    method = request.form.get('method', 'demo_upi')
    ref = 'DEMO-' + ''.join(secrets.choice(string.digits) for _ in range(8))
    cur = mysql.connection.cursor()
    try:
        cur.execute("""INSERT INTO payments (student_id, amount, method, status, reference_no)
                       VALUES (%s, %s, %s, 'successful', %s)""", (sid, amount, method, ref))
        mysql.connection.commit()
        flash(f'Payment of ₹{amount} successful! Ref: {ref}', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash(f'Payment failed: {str(e)}', 'danger')
    cur.close()
    return redirect(url_for('student.fees'))
