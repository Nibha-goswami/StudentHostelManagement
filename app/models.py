from flask_login import UserMixin
from app import mysql, login_manager

class User(UserMixin):
    def __init__(self, user_id, email, full_name, role, is_active=True):
        self.id = user_id
        self.email = email
        self.full_name = full_name
        self.role = role
        self._is_active = is_active

    @property
    def is_active(self):
        return bool(self._is_active)

    def get_id(self):
        return str(self.id)

@login_manager.user_loader
def load_user(user_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT user_id, email, full_name, role, is_active FROM users WHERE user_id = %s", (user_id,))
    row = cur.fetchone()
    cur.close()
    if row:
        return User(row['user_id'], row['email'], row['full_name'], row['role'], row['is_active'])
    return None
