-- =====================================================================
-- SMART CAMPUS - schema.sql  (MySQL 8.0, InnoDB)
-- Run with:  mysql -u root -p < schema.sql
-- WARNING: drops and recreates the smart_campus database.
-- =====================================================================
DROP DATABASE IF EXISTS smart_campus;
CREATE DATABASE smart_campus CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE smart_campus;

-- ---------------------------------------------------------------------
-- CORE: users, students, staff, settings
-- ---------------------------------------------------------------------
CREATE TABLE users (
  user_id       INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  email         VARCHAR(120) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,                 -- Werkzeug hash, never plain text
  full_name     VARCHAR(100) NOT NULL,
  phone         VARCHAR(15),
  role          ENUM('student','admin','warden','mess_manager','maintenance') NOT NULL,
  is_active     TINYINT(1) NOT NULL DEFAULT 1,
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT chk_users_email CHECK (email LIKE '%_@_%.__%')
) ENGINE=InnoDB;

CREATE TABLE students (
  student_id     INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id        INT UNSIGNED NOT NULL UNIQUE,         -- 1:1 with users
  roll_no        VARCHAR(20) NOT NULL UNIQUE,
  department     VARCHAR(60) NOT NULL,
  year_of_study  TINYINT UNSIGNED NOT NULL,
  gender         ENUM('male','female','other') NOT NULL,
  guardian_phone VARCHAR(15),
  CONSTRAINT chk_students_year CHECK (year_of_study BETWEEN 1 AND 6),
  CONSTRAINT fk_students_user FOREIGN KEY (user_id) REFERENCES users(user_id)
) ENGINE=InnoDB;

CREATE TABLE maintenance_staff (
  staff_id       INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id        INT UNSIGNED NOT NULL UNIQUE,
  specialization ENUM('Electricity','Water','Fan','Furniture','Cleaning','Internet','Other') NOT NULL,
  CONSTRAINT fk_staff_user FOREIGN KEY (user_id) REFERENCES users(user_id)
) ENGINE=InnoDB;

CREATE TABLE system_settings (
  setting_key   VARCHAR(50) PRIMARY KEY,
  setting_value VARCHAR(50) NOT NULL,
  description   VARCHAR(200)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- MODULE 1: hostel, rooms, beds, applications, allocations
-- ---------------------------------------------------------------------
CREATE TABLE hostels (
  hostel_id      INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  name           VARCHAR(80) NOT NULL UNIQUE,
  gender_type    ENUM('boys','girls') NOT NULL,
  warden_user_id INT UNSIGNED NULL,
  CONSTRAINT fk_hostels_warden FOREIGN KEY (warden_user_id) REFERENCES users(user_id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE rooms (
  room_id     INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  hostel_id   INT UNSIGNED NOT NULL,
  room_number VARCHAR(10) NOT NULL,
  floor_no    TINYINT UNSIGNED NOT NULL,
  capacity    TINYINT UNSIGNED NOT NULL,
  UNIQUE KEY uq_room_in_hostel (hostel_id, room_number),
  CONSTRAINT chk_rooms_capacity CHECK (capacity > 0),
  CONSTRAINT fk_rooms_hostel FOREIGN KEY (hostel_id) REFERENCES hostels(hostel_id)
) ENGINE=InnoDB;

CREATE TABLE beds (
  bed_id    INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  room_id   INT UNSIGNED NOT NULL,
  bed_label VARCHAR(5) NOT NULL,
  is_usable TINYINT(1) NOT NULL DEFAULT 1,             -- 0 = broken / under repair
  UNIQUE KEY uq_bed_in_room (room_id, bed_label),
  CONSTRAINT fk_beds_room FOREIGN KEY (room_id) REFERENCES rooms(room_id)
) ENGINE=InnoDB;

-- A "live" application (reserved or pending) holds a bed.
-- The two generated columns are bed_id / student_id while live and NULL otherwise.
-- UNIQUE indexes ignore NULLs, so only live rows compete: MySQL itself blocks double-booking.
CREATE TABLE room_applications (
  application_id         INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  student_id             INT UNSIGNED NOT NULL,
  bed_id                 INT UNSIGNED NOT NULL,
  status                 ENUM('reserved','pending','approved','rejected','cancelled','expired') NOT NULL DEFAULT 'reserved',
  reserved_at            DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  reservation_expires_at DATETIME NOT NULL,
  reviewed_by            INT UNSIGNED NULL,
  reviewed_at            DATETIME NULL,
  remarks                VARCHAR(255),
  live_bed_key     INT UNSIGNED GENERATED ALWAYS AS (IF(status IN ('reserved','pending'), bed_id, NULL)) STORED,
  live_student_key INT UNSIGNED GENERATED ALWAYS AS (IF(status IN ('reserved','pending'), student_id, NULL)) STORED,
  UNIQUE KEY uq_one_live_app_per_bed (live_bed_key),
  UNIQUE KEY uq_one_live_app_per_student (live_student_key),
  KEY idx_app_expiry (status, reservation_expires_at),
  CONSTRAINT fk_app_student  FOREIGN KEY (student_id)  REFERENCES students(student_id),
  CONSTRAINT fk_app_bed      FOREIGN KEY (bed_id)      REFERENCES beds(bed_id),
  CONSTRAINT fk_app_reviewer FOREIGN KEY (reviewed_by) REFERENCES users(user_id)
) ENGINE=InnoDB;

CREATE TABLE room_allocations (
  allocation_id  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  application_id INT UNSIGNED NOT NULL UNIQUE,
  student_id     INT UNSIGNED NOT NULL,
  bed_id         INT UNSIGNED NOT NULL,
  status         ENUM('active','vacated') NOT NULL DEFAULT 'active',
  allocated_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  vacated_at     DATETIME NULL,
  active_bed_key     INT UNSIGNED GENERATED ALWAYS AS (IF(status='active', bed_id, NULL)) STORED,
  active_student_key INT UNSIGNED GENERATED ALWAYS AS (IF(status='active', student_id, NULL)) STORED,
  UNIQUE KEY uq_one_active_alloc_per_bed (active_bed_key),
  UNIQUE KEY uq_one_active_alloc_per_student (active_student_key),
  CONSTRAINT chk_alloc_vacated CHECK ((status='active' AND vacated_at IS NULL) OR status='vacated'),
  CONSTRAINT fk_alloc_app     FOREIGN KEY (application_id) REFERENCES room_applications(application_id),
  CONSTRAINT fk_alloc_student FOREIGN KEY (student_id)     REFERENCES students(student_id),
  CONSTRAINT fk_alloc_bed     FOREIGN KEY (bed_id)         REFERENCES beds(bed_id)
) ENGINE=InnoDB;

CREATE TABLE room_transfers (
  transfer_id  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  student_id   INT UNSIGNED NOT NULL,
  from_bed_id  INT UNSIGNED NOT NULL,
  to_bed_id    INT UNSIGNED NOT NULL,
  reason       VARCHAR(255),
  status       ENUM('pending','approved','rejected','completed') NOT NULL DEFAULT 'pending',
  requested_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  reviewed_by  INT UNSIGNED NULL,
  reviewed_at  DATETIME NULL,
  CONSTRAINT chk_transfer_diff CHECK (from_bed_id <> to_bed_id),
  CONSTRAINT fk_tr_student  FOREIGN KEY (student_id)  REFERENCES students(student_id),
  CONSTRAINT fk_tr_from     FOREIGN KEY (from_bed_id) REFERENCES beds(bed_id),
  CONSTRAINT fk_tr_to       FOREIGN KEY (to_bed_id)   REFERENCES beds(bed_id),
  CONSTRAINT fk_tr_reviewer FOREIGN KEY (reviewed_by) REFERENCES users(user_id)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- MODULE 2: mess meals, QR tokens, scan logs
-- ---------------------------------------------------------------------
CREATE TABLE mess_meals (
  meal_id          TINYINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  meal_type        ENUM('breakfast','lunch','dinner') NOT NULL UNIQUE,
  start_time       TIME NOT NULL,
  end_time         TIME NOT NULL,
  cost_per_portion DECIMAL(8,2) NOT NULL,
  CONSTRAINT chk_meal_time CHECK (end_time > start_time)
) ENGINE=InnoDB;

CREATE TABLE mess_counters (
  counter_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  name       VARCHAR(50) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE mess_daily_plan (                         -- how much food the kitchen prepared
  plan_date         DATE NOT NULL,
  meal_id           TINYINT UNSIGNED NOT NULL,
  prepared_portions INT UNSIGNED NOT NULL,
  PRIMARY KEY (plan_date, meal_id),
  CONSTRAINT fk_plan_meal FOREIGN KEY (meal_id) REFERENCES mess_meals(meal_id)
) ENGINE=InnoDB;

CREATE TABLE qr_token_records (                        -- only an ID is stored, never student details
  token_jti  CHAR(32) PRIMARY KEY,
  student_id INT UNSIGNED NOT NULL,
  issued_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  expires_at DATETIME NOT NULL,
  used_at    DATETIME NULL,                            -- set once on first scan: replay prevention
  KEY idx_qr_student (student_id, issued_at),
  CONSTRAINT fk_qr_student FOREIGN KEY (student_id) REFERENCES students(student_id)
) ENGINE=InnoDB;

CREATE TABLE mess_logs (
  log_id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  student_id      INT UNSIGNED NULL,                   -- NULL when the token was invalid
  meal_type       ENUM('breakfast','lunch','dinner') NOT NULL,
  meal_date       DATE NOT NULL,
  scan_timestamp  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  scan_status     ENUM('success','expired','invalid','duplicate','antipassback') NOT NULL,
  mess_counter_id INT UNSIGNED NOT NULL,
  token_jti       CHAR(32) NULL,
  success_student_id INT UNSIGNED GENERATED ALWAYS AS (IF(scan_status='success', student_id, NULL)) STORED,
  UNIQUE KEY uq_one_meal_per_day (success_student_id, meal_date, meal_type),   -- no duplicate meal
  KEY idx_logs_student_time (student_id, scan_timestamp),
  KEY idx_logs_day_meal (meal_date, meal_type),
  CONSTRAINT fk_logs_student FOREIGN KEY (student_id) REFERENCES students(student_id),
  CONSTRAINT fk_logs_counter FOREIGN KEY (mess_counter_id) REFERENCES mess_counters(counter_id)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- MODULE 3: leave, billing, rebates
-- ---------------------------------------------------------------------
CREATE TABLE leave_applications (
  leave_id    INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  student_id  INT UNSIGNED NOT NULL,
  start_date  DATE NOT NULL,
  end_date    DATE NOT NULL,
  reason      VARCHAR(255) NOT NULL,
  status      ENUM('pending','approved','rejected','cancelled') NOT NULL DEFAULT 'pending',
  applied_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  reviewed_by INT UNSIGNED NULL,
  reviewed_at DATETIME NULL,
  remarks     VARCHAR(255),
  KEY idx_leave_student (student_id, status),
  CONSTRAINT chk_leave_dates CHECK (end_date >= start_date),
  CONSTRAINT fk_leave_student  FOREIGN KEY (student_id)  REFERENCES students(student_id),
  CONSTRAINT fk_leave_reviewer FOREIGN KEY (reviewed_by) REFERENCES users(user_id)
) ENGINE=InnoDB;

CREATE TABLE mess_billing (
  billing_id    INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  student_id    INT UNSIGNED NOT NULL,
  billing_month DATE NOT NULL,                         -- always the 1st of the month
  gross_amount  DECIMAL(10,2) NOT NULL,
  rebate_total  DECIMAL(10,2) NOT NULL DEFAULT 0,      -- kept in sync by sp_sync_billing_rebate
  net_amount    DECIMAL(10,2) GENERATED ALWAYS AS (gross_amount - rebate_total) STORED,
  UNIQUE KEY uq_bill_month (student_id, billing_month),
  CONSTRAINT chk_bill_first_day CHECK (DAY(billing_month) = 1),
  CONSTRAINT chk_bill_amounts CHECK (gross_amount >= 0 AND rebate_total >= 0),
  CONSTRAINT fk_bill_student FOREIGN KEY (student_id) REFERENCES students(student_id)
) ENGINE=InnoDB;

CREATE TABLE mess_rebates (
  rebate_id     INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  leave_id      INT UNSIGNED NOT NULL UNIQUE,          -- UNIQUE = one rebate per leave, ever
  student_id    INT UNSIGNED NOT NULL,
  billing_id    INT UNSIGNED NULL,
  rebate_days   INT UNSIGNED NOT NULL,
  rate_per_day  DECIMAL(8,2) NOT NULL,
  rebate_amount DECIMAL(10,2) NOT NULL,
  status        ENUM('applied','reversed') NOT NULL DEFAULT 'applied',
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_rebate_student (student_id, status),
  CONSTRAINT chk_rebate_days CHECK (rebate_days > 0),
  CONSTRAINT fk_rebate_leave   FOREIGN KEY (leave_id)   REFERENCES leave_applications(leave_id),
  CONSTRAINT fk_rebate_student FOREIGN KEY (student_id) REFERENCES students(student_id),
  CONSTRAINT fk_rebate_bill    FOREIGN KEY (billing_id) REFERENCES mess_billing(billing_id)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- MODULE 4: maintenance complaints
-- ---------------------------------------------------------------------
CREATE TABLE complaints (
  complaint_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  ticket_no    VARCHAR(20) NULL UNIQUE,                -- set by sp_create_complaint
  student_id   INT UNSIGNED NOT NULL,
  room_id      INT UNSIGNED NOT NULL,
  category     ENUM('Electricity','Water','Fan','Furniture','Cleaning','Internet','Other') NOT NULL,
  title        VARCHAR(120) NOT NULL,
  description  TEXT,
  photo_path   VARCHAR(255),
  status       ENUM('Open','In_Progress','Resolved','Escalated') NOT NULL DEFAULT 'Open',
  created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  escalated_at DATETIME NULL,
  resolved_at  DATETIME NULL,
  resolution_note VARCHAR(255),
  KEY idx_complaint_status_time (status, created_at),
  KEY idx_complaint_student (student_id),
  CONSTRAINT chk_resolved_time CHECK (status <> 'Resolved' OR resolved_at IS NOT NULL),
  CONSTRAINT fk_complaint_student FOREIGN KEY (student_id) REFERENCES students(student_id),
  CONSTRAINT fk_complaint_room    FOREIGN KEY (room_id)    REFERENCES rooms(room_id)
) ENGINE=InnoDB;

CREATE TABLE complaint_assignments (
  assignment_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  complaint_id  INT UNSIGNED NOT NULL,
  staff_id      INT UNSIGNED NOT NULL,
  assigned_by   INT UNSIGNED NOT NULL,
  assigned_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  is_current    TINYINT(1) NOT NULL DEFAULT 1,
  current_key   INT UNSIGNED GENERATED ALWAYS AS (IF(is_current=1, complaint_id, NULL)) STORED,
  UNIQUE KEY uq_one_current_assignee (current_key),
  KEY idx_assign_staff (staff_id, is_current),
  CONSTRAINT fk_assign_complaint FOREIGN KEY (complaint_id) REFERENCES complaints(complaint_id),
  CONSTRAINT fk_assign_staff     FOREIGN KEY (staff_id)     REFERENCES maintenance_staff(staff_id),
  CONSTRAINT fk_assign_by        FOREIGN KEY (assigned_by)  REFERENCES users(user_id)
) ENGINE=InnoDB;

CREATE TABLE complaint_history (
  history_id   BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  complaint_id INT UNSIGNED NOT NULL,
  old_status   ENUM('Open','In_Progress','Resolved','Escalated') NULL,
  new_status   ENUM('Open','In_Progress','Resolved','Escalated') NOT NULL,
  changed_by   INT UNSIGNED NULL,                      -- NULL = changed by the system
  changed_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_hist_complaint (complaint_id, changed_at),
  CONSTRAINT fk_hist_complaint FOREIGN KEY (complaint_id) REFERENCES complaints(complaint_id),
  CONSTRAINT fk_hist_user      FOREIGN KEY (changed_by)   REFERENCES users(user_id)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- MODULE 5: fees, fines, payments, No-Dues
-- ---------------------------------------------------------------------
CREATE TABLE hostel_fees (
  fee_id        INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  student_id    INT UNSIGNED NOT NULL,
  academic_year VARCHAR(9) NOT NULL,
  semester      TINYINT UNSIGNED NOT NULL,
  amount        DECIMAL(10,2) NOT NULL,
  due_date      DATE NOT NULL,
  UNIQUE KEY uq_fee_term (student_id, academic_year, semester),
  CONSTRAINT chk_fee_amount CHECK (amount >= 0),
  CONSTRAINT fk_fee_student FOREIGN KEY (student_id) REFERENCES students(student_id)
) ENGINE=InnoDB;

CREATE TABLE fines (
  fine_id     INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  student_id  INT UNSIGNED NOT NULL,
  reason      ENUM('damage','late_entry','rule_violation','other') NOT NULL,
  description VARCHAR(255),
  amount      DECIMAL(10,2) NOT NULL,
  status      ENUM('active','waived') NOT NULL DEFAULT 'active',
  imposed_by  INT UNSIGNED NOT NULL,
  imposed_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_fine_student (student_id, status),
  CONSTRAINT chk_fine_amount CHECK (amount > 0),
  CONSTRAINT fk_fine_student FOREIGN KEY (student_id) REFERENCES students(student_id),
  CONSTRAINT fk_fine_by      FOREIGN KEY (imposed_by) REFERENCES users(user_id)
) ENGINE=InnoDB;

CREATE TABLE payments (
  payment_id   INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  student_id   INT UNSIGNED NOT NULL,
  amount       DECIMAL(10,2) NOT NULL,
  method       ENUM('demo_upi','demo_card','counter_cash') NOT NULL,
  status       ENUM('initiated','successful','failed') NOT NULL DEFAULT 'initiated',
  is_demo      TINYINT(1) NOT NULL DEFAULT 1,          -- simulated: no real gateway involved
  reference_no VARCHAR(30) NOT NULL UNIQUE,
  created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_pay_student (student_id, status),
  CONSTRAINT chk_pay_amount CHECK (amount > 0),
  CONSTRAINT fk_pay_student FOREIGN KEY (student_id) REFERENCES students(student_id)
) ENGINE=InnoDB;

CREATE TABLE no_dues_certificates (
  cert_id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  student_id       INT UNSIGNED NOT NULL UNIQUE,
  verification_id  CHAR(36) NOT NULL UNIQUE,
  balance_at_issue DECIMAL(12,2) NOT NULL,
  issued_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT chk_cert_balance CHECK (balance_at_issue <= 0),
  CONSTRAINT fk_cert_student FOREIGN KEY (student_id) REFERENCES students(student_id)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- VIEWS
-- ---------------------------------------------------------------------
-- Each money source is summed in its OWN subquery first, then joined 1:1 per student.
-- Joining the raw tables directly would multiply rows and inflate every total.
CREATE VIEW student_ledger AS
SELECT s.student_id, s.roll_no, u.full_name,
       COALESCE(h.total,0) AS hostel_fees,
       COALESCE(m.total,0) AS mess_fees,
       COALESCE(f.total,0) AS fines,
       COALESCE(r.total,0) AS approved_rebates,
       COALESCE(p.total,0) AS payments_made,
       (COALESCE(h.total,0) + COALESCE(m.total,0) + COALESCE(f.total,0))
         - (COALESCE(r.total,0) + COALESCE(p.total,0)) AS outstanding_balance
FROM students s
JOIN users u ON u.user_id = s.user_id
LEFT JOIN (SELECT student_id, SUM(amount) total FROM hostel_fees GROUP BY student_id) h ON h.student_id = s.student_id
LEFT JOIN (SELECT student_id, SUM(gross_amount) total FROM mess_billing GROUP BY student_id) m ON m.student_id = s.student_id
LEFT JOIN (SELECT student_id, SUM(amount) total FROM fines WHERE status='active' GROUP BY student_id) f ON f.student_id = s.student_id
LEFT JOIN (SELECT student_id, SUM(rebate_amount) total FROM mess_rebates WHERE status='applied' GROUP BY student_id) r ON r.student_id = s.student_id
LEFT JOIN (SELECT student_id, SUM(amount) total FROM payments WHERE status='successful' GROUP BY student_id) p ON p.student_id = s.student_id;

CREATE VIEW v_bed_status AS
SELECT b.bed_id, b.bed_label, r.room_id, r.room_number, r.floor_no, h.hostel_id, h.name AS hostel_name,
       CASE WHEN b.is_usable = 0 THEN 'unavailable'
            WHEN ra.allocation_id IS NOT NULL THEN 'occupied'
            WHEN ap.application_id IS NOT NULL THEN 'reserved'
            ELSE 'available' END AS bed_status
FROM beds b
JOIN rooms r ON r.room_id = b.room_id
JOIN hostels h ON h.hostel_id = r.hostel_id
LEFT JOIN room_allocations ra ON ra.bed_id = b.bed_id AND ra.status = 'active'
LEFT JOIN room_applications ap ON ap.bed_id = b.bed_id
       AND (ap.status = 'pending' OR (ap.status = 'reserved' AND ap.reservation_expires_at > NOW()));

CREATE VIEW v_hostel_occupancy AS
SELECT hostel_id, hostel_name, COUNT(*) AS total_beds,
       SUM(bed_status = 'occupied') AS occupied_beds,
       SUM(bed_status = 'available') AS available_beds,
       ROUND(100 * SUM(bed_status = 'occupied') / COUNT(*), 1) AS occupancy_percent
FROM v_bed_status GROUP BY hostel_id, hostel_name;

CREATE VIEW v_daily_meal_attendance AS
SELECT meal_date, meal_type, COUNT(*) AS students_attended
FROM mess_logs WHERE scan_status = 'success' GROUP BY meal_date, meal_type;

-- ---------------------------------------------------------------------
-- TRIGGERS and STORED PROCEDURES  (DELIMITER is a mysql CLI command)
-- ---------------------------------------------------------------------
DELIMITER $$

-- A student who already has a live application or an active bed cannot apply again.
CREATE TRIGGER trg_app_no_double_booking BEFORE INSERT ON room_applications
FOR EACH ROW
BEGIN
  IF EXISTS (SELECT 1 FROM room_allocations WHERE student_id = NEW.student_id AND status = 'active') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Student already has an active hostel allocation';
  END IF;
END$$

-- Frees beds whose 10-minute reservation ran out. Called by the scheduler and before each booking.
CREATE PROCEDURE sp_expire_stale_reservations()
BEGIN
  UPDATE room_applications SET status = 'expired'
  WHERE status = 'reserved' AND reservation_expires_at <= NOW();
END$$

-- Stops the same student having overlapping leave requests (which would double the rebate).
CREATE TRIGGER trg_leave_no_overlap BEFORE INSERT ON leave_applications
FOR EACH ROW
BEGIN
  IF EXISTS (SELECT 1 FROM leave_applications
             WHERE student_id = NEW.student_id AND status IN ('pending','approved')
               AND NEW.start_date <= end_date AND NEW.end_date >= start_date) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Overlapping leave application already exists';
  END IF;
END$$

CREATE PROCEDURE sp_sync_billing_rebate(IN p_student_id INT UNSIGNED)
BEGIN
  UPDATE mess_billing b
  SET b.rebate_total = COALESCE((SELECT SUM(r.rebate_amount) FROM mess_rebates r
                                 WHERE r.billing_id = b.billing_id AND r.status = 'applied'), 0)
  WHERE b.student_id = p_student_id;
END$$

CREATE PROCEDURE sp_apply_rebate(IN p_leave_id INT UNSIGNED, IN p_student_id INT UNSIGNED,
                                 IN p_start DATE, IN p_end DATE)
BEGIN
  DECLARE v_days INT;
  DECLARE v_rate DECIMAL(8,2);
  DECLARE v_min  INT;
  DECLARE v_bill INT UNSIGNED;
  SET v_rate = (SELECT CAST(setting_value AS DECIMAL(8,2)) FROM system_settings WHERE setting_key = 'mess_rate_per_day');
  SET v_min  = (SELECT CAST(setting_value AS UNSIGNED)     FROM system_settings WHERE setting_key = 'min_rebate_leave_days');
  SET v_days = DATEDIFF(p_end, p_start) + 1;
  IF v_days >= v_min THEN
    SET v_bill = (SELECT billing_id FROM mess_billing
                  WHERE student_id = p_student_id AND billing_month = DATE_FORMAT(p_start, '%Y-%m-01') LIMIT 1);
    -- UNIQUE(leave_id) means re-approving updates the same row instead of creating a duplicate
    INSERT INTO mess_rebates (leave_id, student_id, billing_id, rebate_days, rate_per_day, rebate_amount, status)
    VALUES (p_leave_id, p_student_id, v_bill, v_days, v_rate, v_days * v_rate, 'applied') AS new_row
    ON DUPLICATE KEY UPDATE billing_id = new_row.billing_id, rebate_days = new_row.rebate_days,
        rate_per_day = new_row.rate_per_day, rebate_amount = new_row.rebate_amount, status = 'applied';
    CALL sp_sync_billing_rebate(p_student_id);
  END IF;
END$$

CREATE PROCEDURE sp_reverse_rebate(IN p_leave_id INT UNSIGNED, IN p_student_id INT UNSIGNED)
BEGIN
  UPDATE mess_rebates SET status = 'reversed' WHERE leave_id = p_leave_id AND status = 'applied';
  CALL sp_sync_billing_rebate(p_student_id);
END$$

-- The automation: the warden only changes the status; the database does the rest, atomically.
CREATE TRIGGER trg_leave_after_update AFTER UPDATE ON leave_applications
FOR EACH ROW
BEGIN
  IF NEW.status = 'approved' AND OLD.status <> 'approved' THEN
    CALL sp_apply_rebate(NEW.leave_id, NEW.student_id, NEW.start_date, NEW.end_date);
  ELSEIF OLD.status = 'approved' AND NEW.status <> 'approved' THEN
    CALL sp_reverse_rebate(NEW.leave_id, NEW.student_id);
  ELSEIF OLD.status = 'approved' AND NEW.status = 'approved'
         AND (NEW.start_date <> OLD.start_date OR NEW.end_date <> OLD.end_date) THEN
    CALL sp_apply_rebate(NEW.leave_id, NEW.student_id, NEW.start_date, NEW.end_date);
  END IF;
END$$

-- Complaint history is written by triggers, so no code path can forget it.
-- The app sets  SET @app_user_id = <id>;  on its connection first; NULL means "system".
CREATE TRIGGER trg_complaint_after_insert AFTER INSERT ON complaints
FOR EACH ROW
BEGIN
  INSERT INTO complaint_history (complaint_id, old_status, new_status, changed_by)
  VALUES (NEW.complaint_id, NULL, NEW.status, @app_user_id);
END$$

CREATE TRIGGER trg_complaint_after_update AFTER UPDATE ON complaints
FOR EACH ROW
BEGIN
  IF NEW.status <> OLD.status THEN
    INSERT INTO complaint_history (complaint_id, old_status, new_status, changed_by)
    VALUES (NEW.complaint_id, OLD.status, NEW.status, @app_user_id);
  END IF;
END$$

CREATE PROCEDURE sp_create_complaint(IN p_student INT UNSIGNED, IN p_room INT UNSIGNED, IN p_category VARCHAR(20),
                                     IN p_title VARCHAR(120), IN p_desc TEXT, IN p_photo VARCHAR(255),
                                     OUT p_ticket VARCHAR(20))
BEGIN
  DECLARE v_id INT UNSIGNED;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
  START TRANSACTION;
  INSERT INTO complaints (student_id, room_id, category, title, description, photo_path)
  VALUES (p_student, p_room, p_category, p_title, p_desc, p_photo);
  SET v_id = LAST_INSERT_ID();
  SET p_ticket = CONCAT('TKT-', LPAD(v_id, 6, '0'));
  UPDATE complaints SET ticket_no = p_ticket WHERE complaint_id = v_id;
  COMMIT;
END$$

-- Called by the scheduler every few minutes. p_count = how many tickets were escalated.
CREATE PROCEDURE sp_escalate_overdue_complaints(OUT p_count INT)
BEGIN
  DECLARE v_hours INT;
  SET v_hours = (SELECT CAST(setting_value AS UNSIGNED) FROM system_settings WHERE setting_key = 'escalation_hours');
  SET @app_user_id = NULL;
  UPDATE complaints SET status = 'Escalated', escalated_at = NOW()
  WHERE status IN ('Open','In_Progress') AND created_at <= NOW() - INTERVAL v_hours HOUR;
  SET p_count = ROW_COUNT();
END$$

-- No-Dues: refuses unless the ledger balance is cleared. Safe to call repeatedly.
CREATE PROCEDURE sp_generate_no_dues(IN p_student INT UNSIGNED, OUT p_verification CHAR(36))
BEGIN
  DECLARE v_balance DECIMAL(12,2);
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
  START TRANSACTION;
  IF NOT EXISTS (SELECT 1 FROM students WHERE student_id = p_student FOR UPDATE) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Student not found';
  END IF;
  SET v_balance = (SELECT outstanding_balance FROM student_ledger WHERE student_id = p_student);
  IF v_balance > 0 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Outstanding dues exist: No-Dues cannot be generated';
  END IF;
  SET p_verification = (SELECT verification_id FROM no_dues_certificates WHERE student_id = p_student);
  IF p_verification IS NULL THEN
    SET p_verification = UUID();
    INSERT INTO no_dues_certificates (student_id, verification_id, balance_at_issue)
    VALUES (p_student, p_verification, v_balance);
  END IF;
  COMMIT;
END$$

DELIMITER ;
