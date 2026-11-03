from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from functools import wraps
from app import mysql
from datetime import date

mess_bp = Blueprint('mess', __name__, url_prefix='/mess')

def mess_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role not in ('mess_manager', 'admin'):
            flash('Access denied.', 'danger')
            return redirect(url_for('auth.dashboard'))
        return f(*args, **kwargs)
    return decorated

@mess_bp.route('/dashboard')
@login_required
@mess_required
def dashboard():
    cur = mysql.connection.cursor()
    cur.execute("SELECT meal_date, meal_type, students_attended FROM v_daily_meal_attendance ORDER BY meal_date DESC, meal_type LIMIT 15")
    attendance = cur.fetchall()
    cur.execute("SELECT meal_type, start_time, end_time, cost_per_portion FROM mess_meals ORDER BY meal_id")
    meals = cur.fetchall()
    cur.execute("""SELECT ml.log_id, ml.meal_type, ml.meal_date, ml.scan_status, ml.scan_timestamp,
                   u.full_name as student_name, s.roll_no
                   FROM mess_logs ml
                   LEFT JOIN students s ON s.student_id=ml.student_id
                   LEFT JOIN users u ON u.user_id=s.user_id
                   ORDER BY ml.scan_timestamp DESC LIMIT 20""")
    recent_logs = cur.fetchall()
    first_of_month = date.today().replace(day=1)
    today = date.today()
    cur.execute("""SELECT SUM(gross_amount) as total_billed, COUNT(DISTINCT student_id) as billed_students
                   FROM mess_billing WHERE billing_month=%s""", (first_of_month,))
    billing_summary = cur.fetchone()
    cur.execute("""SELECT SUM(rebate_amount) as total_rebates FROM mess_rebates WHERE status='applied'""")
    rebate_summary = cur.fetchone()
    cur.execute("""SELECT COUNT(*) as today_success FROM mess_logs
                   WHERE scan_status='success' AND meal_date=%s""", (today,))
    today_meals = cur.fetchone()['today_success']
    cur.close()
    return render_template('mess/dashboard.html', attendance=attendance, meals=meals,
                           recent_logs=recent_logs, billing_summary=billing_summary,
                           rebate_summary=rebate_summary, today_meals=today_meals)

@mess_bp.route('/billing')
@login_required
@mess_required
def billing():
    cur = mysql.connection.cursor()
    cur.execute("""SELECT mb.billing_id, mb.billing_month, mb.gross_amount, mb.rebate_total, mb.net_amount,
                   u.full_name as student_name, s.roll_no
                   FROM mess_billing mb
                   JOIN students s ON s.student_id=mb.student_id
                   JOIN users u ON u.user_id=s.user_id
                   ORDER BY mb.billing_month DESC, u.full_name""")
    bills = cur.fetchall()
    cur.close()
    return render_template('mess/billing.html', bills=bills)
