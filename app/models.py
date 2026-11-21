from flask_login import UserMixin
from app import mysql, login_manager

class User(UserMixin):
    def __init__(self, user_id, email, full_name, role, is_active=True, warden_type=None, hostel_id=None, hostel_name=None):
        self.id = user_id
        self.email = email
        self.full_name = full_name
        self.role = role
        self._is_active = is_active
        self.warden_type = warden_type
        self.hostel_id = hostel_id
        self.hostel_name = hostel_name

    @property
    def is_active(self):
        return bool(self._is_active)

    def get_id(self):
        return str(self.id)

    @property
    def display_role(self):
        if self.role == 'warden':
            if self.warden_type == 'boys':
                return 'Boys Warden'
            elif self.warden_type == 'girls':
                return 'Girls Warden'
            return 'Warden'
        return self.role.replace('_', ' ').title()

@login_manager.user_loader
def load_user(user_id):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT u.user_id, u.email, u.full_name, u.role, u.is_active,
               COALESCE(ws.warden_type, h.gender_type) as warden_type,
               h.hostel_id, h.name as hostel_name
        FROM users u
        LEFT JOIN warden_staff ws ON ws.user_id = u.user_id
        LEFT JOIN hostels h ON (h.warden_user_id = u.user_id OR h.hostel_id = ws.hostel_id)
        WHERE u.user_id = %s
    """, (user_id,))
    row = cur.fetchone()
    cur.close()
    if row:
        return User(
            row['user_id'],
            row['email'],
            row['full_name'],
            row['role'],
            row['is_active'],
            warden_type=row.get('warden_type'),
            hostel_id=row.get('hostel_id'),
            hostel_name=row.get('hostel_name')
        )
    return None
