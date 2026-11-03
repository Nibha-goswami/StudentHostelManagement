-- SMART CAMPUS - seed_data.sql   (run AFTER schema.sql)
-- Demo login for EVERY seeded user:  password  Demo@1234  (change before any real use)
USE smart_campus;

INSERT INTO system_settings VALUES
 ('mess_rate_per_day','120','Mess rebate per eligible leave day (Rs.)'),
 ('min_rebate_leave_days','3','Minimum leave length (days) to earn a rebate'),
 ('reservation_minutes','10','Bed reservation hold time'),
 ('qr_ttl_seconds','30','QR token lifetime'),
 ('antipassback_minutes','120','Minutes before another meal scan is allowed'),
 ('escalation_hours','48','Hours before an unresolved complaint is escalated');

INSERT INTO users (user_id,email,password_hash,full_name,phone,role) VALUES
 (1,'admin@smartcampus.edu','scrypt:32768:8:1$30cStnIxlQTTlGBp$4bfad1a7634453dbae8193f56e8d04161efa1fedc1e4d4c8d56f1173a3ead39eeab584c5f42782c42a341072c5618d071eebf7453e471da6de8cf7d5b052b930','Dr. Rajesh Kulkarni','9000000001','admin'),
 (2,'warden@smartcampus.edu','scrypt:32768:8:1$30cStnIxlQTTlGBp$4bfad1a7634453dbae8193f56e8d04161efa1fedc1e4d4c8d56f1173a3ead39eeab584c5f42782c42a341072c5618d071eebf7453e471da6de8cf7d5b052b930','Mrs. Sunita Deshmukh','9000000002','warden'),
 (3,'mess@smartcampus.edu','scrypt:32768:8:1$30cStnIxlQTTlGBp$4bfad1a7634453dbae8193f56e8d04161efa1fedc1e4d4c8d56f1173a3ead39eeab584c5f42782c42a341072c5618d071eebf7453e471da6de8cf7d5b052b930','Mr. Prakash Rao','9000000003','mess_manager'),
 (4,'electrician@smartcampus.edu','scrypt:32768:8:1$30cStnIxlQTTlGBp$4bfad1a7634453dbae8193f56e8d04161efa1fedc1e4d4c8d56f1173a3ead39eeab584c5f42782c42a341072c5618d071eebf7453e471da6de8cf7d5b052b930','Ramesh Yadav','9000000004','maintenance'),
 (5,'plumber@smartcampus.edu','scrypt:32768:8:1$30cStnIxlQTTlGBp$4bfad1a7634453dbae8193f56e8d04161efa1fedc1e4d4c8d56f1173a3ead39eeab584c5f42782c42a341072c5618d071eebf7453e471da6de8cf7d5b052b930','Suresh Pawar','9000000005','maintenance'),
 (6,'aarav.sharma@student.edu','scrypt:32768:8:1$30cStnIxlQTTlGBp$4bfad1a7634453dbae8193f56e8d04161efa1fedc1e4d4c8d56f1173a3ead39eeab584c5f42782c42a341072c5618d071eebf7453e471da6de8cf7d5b052b930','Aarav Sharma','9100000001','student'),
 (7,'diya.verma@student.edu','scrypt:32768:8:1$30cStnIxlQTTlGBp$4bfad1a7634453dbae8193f56e8d04161efa1fedc1e4d4c8d56f1173a3ead39eeab584c5f42782c42a341072c5618d071eebf7453e471da6de8cf7d5b052b930','Diya Verma','9100000002','student'),
 (8,'rohan.gupta@student.edu','scrypt:32768:8:1$30cStnIxlQTTlGBp$4bfad1a7634453dbae8193f56e8d04161efa1fedc1e4d4c8d56f1173a3ead39eeab584c5f42782c42a341072c5618d071eebf7453e471da6de8cf7d5b052b930','Rohan Gupta','9100000003','student'),
 (9,'ananya.singh@student.edu','scrypt:32768:8:1$30cStnIxlQTTlGBp$4bfad1a7634453dbae8193f56e8d04161efa1fedc1e4d4c8d56f1173a3ead39eeab584c5f42782c42a341072c5618d071eebf7453e471da6de8cf7d5b052b930','Ananya Singh','9100000004','student'),
 (10,'karan.mehta@student.edu','scrypt:32768:8:1$30cStnIxlQTTlGBp$4bfad1a7634453dbae8193f56e8d04161efa1fedc1e4d4c8d56f1173a3ead39eeab584c5f42782c42a341072c5618d071eebf7453e471da6de8cf7d5b052b930','Karan Mehta','9100000005','student'),
 (11,'ishita.joshi@student.edu','scrypt:32768:8:1$30cStnIxlQTTlGBp$4bfad1a7634453dbae8193f56e8d04161efa1fedc1e4d4c8d56f1173a3ead39eeab584c5f42782c42a341072c5618d071eebf7453e471da6de8cf7d5b052b930','Ishita Joshi','9100000006','student'),
 (12,'vivaan.patel@student.edu','scrypt:32768:8:1$30cStnIxlQTTlGBp$4bfad1a7634453dbae8193f56e8d04161efa1fedc1e4d4c8d56f1173a3ead39eeab584c5f42782c42a341072c5618d071eebf7453e471da6de8cf7d5b052b930','Vivaan Patel','9100000007','student'),
 (13,'meera.nair@student.edu','scrypt:32768:8:1$30cStnIxlQTTlGBp$4bfad1a7634453dbae8193f56e8d04161efa1fedc1e4d4c8d56f1173a3ead39eeab584c5f42782c42a341072c5618d071eebf7453e471da6de8cf7d5b052b930','Meera Nair','9100000008','student');

INSERT INTO students (student_id,user_id,roll_no,department,year_of_study,gender,guardian_phone) VALUES
 (1,6,'CS2201','Computer Science',3,'male','9200000001'),
 (2,7,'CS2202','Computer Science',3,'female','9200000002'),
 (3,8,'EC2203','Electronics',2,'male','9200000003'),
 (4,9,'ME2204','Mechanical',2,'female','9200000004'),
 (5,10,'CS2305','Computer Science',1,'male','9200000005'),
 (6,11,'IT2306','Information Technology',1,'female','9200000006'),
 (7,12,'CE2307','Civil',1,'male','9200000007'),
 (8,13,'CS2308','Computer Science',1,'female','9200000008');

INSERT INTO maintenance_staff (staff_id,user_id,specialization) VALUES (1,4,'Electricity'),(2,5,'Water');

INSERT INTO hostels (hostel_id,name,gender_type,warden_user_id) VALUES
 (1,'Himalaya Boys Hostel','boys',2),(2,'Ganga Girls Hostel','girls',2);

-- 2 hostels x 2 floors x 2 rooms = 8 rooms (101,102,201,202), 3 beds each = 24 beds
INSERT INTO rooms (hostel_id,room_number,floor_no,capacity)
SELECT h.hostel_id, CONCAT(f.n, '0', r.n), f.n, 3
FROM hostels h CROSS JOIN (SELECT 1 n UNION SELECT 2) f CROSS JOIN (SELECT 1 n UNION SELECT 2) r
ORDER BY h.hostel_id, f.n, r.n;

INSERT INTO beds (room_id,bed_label)
SELECT r.room_id, l.lbl FROM rooms r CROSS JOIN (SELECT 'A' lbl UNION SELECT 'B' UNION SELECT 'C') l
ORDER BY r.room_id, l.lbl;

-- Applications: students 1-4 approved (allocated), 5 pending, 6 holds a live 10-minute reservation
INSERT INTO room_applications (student_id,bed_id,status,reservation_expires_at,reviewed_by,reviewed_at) VALUES
 (1,1,'approved',NOW(),2,NOW()),(3,2,'approved',NOW(),2,NOW()),
 (2,13,'approved',NOW(),2,NOW()),(4,14,'approved',NOW(),2,NOW());
INSERT INTO room_applications (student_id,bed_id,status,reservation_expires_at) VALUES
 (5,3,'pending',NOW() + INTERVAL 1 DAY);
INSERT INTO room_applications (student_id,bed_id,status,reservation_expires_at) VALUES
 (6,15,'reserved',NOW() + INTERVAL 10 MINUTE);
INSERT INTO room_allocations (application_id,student_id,bed_id) VALUES (1,1,1),(2,3,2),(3,2,13),(4,4,14);

-- Mess
INSERT INTO mess_meals (meal_type,start_time,end_time,cost_per_portion) VALUES
 ('breakfast','07:30:00','09:30:00',30),('lunch','12:30:00','14:30:00',55),('dinner','19:30:00','21:30:00',45);
INSERT INTO mess_counters (name) VALUES ('Main Entrance'),('Side Entrance');
INSERT INTO mess_daily_plan (plan_date,meal_id,prepared_portions)
SELECT d.dt, m.meal_id, 10 FROM mess_meals m CROSS JOIN (SELECT CURDATE() dt UNION SELECT CURDATE() - INTERVAL 1 DAY) d;
INSERT INTO mess_logs (student_id,meal_type,meal_date,scan_timestamp,scan_status,mess_counter_id) VALUES
 (1,'breakfast',CURDATE(),TIMESTAMP(CURDATE(),'08:05:00'),'success',1),
 (2,'breakfast',CURDATE(),TIMESTAMP(CURDATE(),'08:12:00'),'success',1),
 (3,'breakfast',CURDATE(),TIMESTAMP(CURDATE(),'08:30:00'),'success',2),
 (1,'lunch',CURDATE(),TIMESTAMP(CURDATE(),'13:00:00'),'success',1),
 (3,'lunch',CURDATE(),TIMESTAMP(CURDATE(),'13:10:00'),'success',1),
 (3,'lunch',CURDATE(),TIMESTAMP(CURDATE(),'13:25:00'),'antipassback',2),
 (NULL,'lunch',CURDATE(),TIMESTAMP(CURDATE(),'13:40:00'),'invalid',1),
 (1,'dinner',CURDATE() - INTERVAL 1 DAY,TIMESTAMP(CURDATE() - INTERVAL 1 DAY,'20:00:00'),'success',1),
 (2,'dinner',CURDATE() - INTERVAL 1 DAY,TIMESTAMP(CURDATE() - INTERVAL 1 DAY,'20:10:00'),'success',1);

-- Billing
INSERT INTO hostel_fees (student_id,academic_year,semester,amount,due_date)
SELECT student_id,'2026-2027',1,20000,CURDATE() + INTERVAL 30 DAY FROM students;
INSERT INTO mess_billing (student_id,billing_month,gross_amount)
SELECT student_id, DATE_FORMAT(CURDATE(),'%Y-%m-01'), 5000 FROM students;
INSERT INTO fines (student_id,reason,description,amount,imposed_by) VALUES
 (1,'damage','Broken window latch',500,2);
INSERT INTO payments (student_id,amount,method,status,reference_no) VALUES
 (1,24900,'demo_upi','successful','DEMO-0001'),
 (2,10000,'demo_card','successful','DEMO-0002'),
 (2,5000,'demo_card','failed','DEMO-0003');

-- Leave: approving fires the trigger -> rebate Rs. 600 (5 days x Rs. 120) for student 1
INSERT INTO leave_applications (student_id,start_date,end_date,reason) VALUES
 (1,DATE_FORMAT(CURDATE(),'%Y-%m-01'),DATE_FORMAT(CURDATE(),'%Y-%m-01') + INTERVAL 4 DAY,'Family function'),
 (2,CURDATE() + INTERVAL 10 DAY,CURDATE() + INTERVAL 14 DAY,'Sister wedding'),
 (3,CURDATE() + INTERVAL 20 DAY,CURDATE() + INTERVAL 21 DAY,'Short trip');
UPDATE leave_applications SET status='approved', reviewed_by=2, reviewed_at=NOW() WHERE leave_id=1;
UPDATE leave_applications SET status='rejected', reviewed_by=2, reviewed_at=NOW(), remarks='Exams that week' WHERE leave_id=3;

-- Complaints
SET @app_user_id = 6;
CALL sp_create_complaint(1, 1, 'Internet', 'Wi-Fi drops every evening', 'Router on floor 1 keeps disconnecting', NULL, @t1);
SET @app_user_id = 8;
CALL sp_create_complaint(3, 1, 'Fan', 'Ceiling fan not working', 'Fan makes noise and stops', NULL, @t2);
SET @app_user_id = 9;
CALL sp_create_complaint(4, 5, 'Water', 'No water in bathroom tap', 'Tap dry since yesterday', NULL, @t3);
SET @app_user_id = 7;
CALL sp_create_complaint(2, 5, 'Electricity', 'Socket sparking', 'Socket near bed sparks', NULL, @t4);
SET @app_user_id = 2;
INSERT INTO complaint_assignments (complaint_id,staff_id,assigned_by) VALUES (1,1,2),(3,2,2),(4,1,2);
SET @app_user_id = 4;
UPDATE complaints SET status='In_Progress' WHERE ticket_no=@t1;
UPDATE complaints SET status='Resolved', resolved_at=NOW(), resolution_note='Socket replaced' WHERE ticket_no=@t4;
UPDATE complaints SET created_at = NOW() - INTERVAL 50 HOUR WHERE ticket_no=@t3;   -- make it overdue
CALL sp_escalate_overdue_complaints(@escalated);
SET @app_user_id = NULL;
