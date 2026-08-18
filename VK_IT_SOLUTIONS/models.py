from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, index=True)
    phone = db.Column(db.String(30), nullable=True)
    department = db.Column(db.String(100), nullable=True)
    designation = db.Column(db.String(100), nullable=True)
    manager_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    manager = db.relationship(
        "User",
        remote_side=[id],
        backref=db.backref("employees", lazy=True),
        foreign_keys=[manager_id]
    )

    tasks = db.relationship(
        "Task",
        back_populates="employee",
        foreign_keys="Task.employee_id",
        cascade="all, delete-orphan"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(30), default="pending", nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    manager_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    due_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    employee = db.relationship("User", foreign_keys=[employee_id], back_populates="tasks")
    manager = db.relationship("User", foreign_keys=[manager_id])


class Announcement(db.Model):
    __tablename__ = "announcements"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    creator = db.relationship("User", foreign_keys=[created_by])


class Attendance(db.Model):
    id=db.Column(db.Integer,primary_key=True); employee_id=db.Column(db.Integer,db.ForeignKey('users.id'),nullable=False); date=db.Column(db.Date,nullable=False); status=db.Column(db.String(30),nullable=False,default='present'); check_in=db.Column(db.String(10)); check_out=db.Column(db.String(10)); notes=db.Column(db.String(500)); employee=db.relationship('User',foreign_keys=[employee_id])

class LeaveRequest(db.Model):
    id=db.Column(db.Integer,primary_key=True); employee_id=db.Column(db.Integer,db.ForeignKey('users.id'),nullable=False); leave_type=db.Column(db.String(50),nullable=False); start_date=db.Column(db.Date,nullable=False); end_date=db.Column(db.Date,nullable=False); reason=db.Column(db.Text,nullable=False); status=db.Column(db.String(30),default='pending',nullable=False); comment=db.Column(db.String(500)); employee=db.relationship('User',foreign_keys=[employee_id])

class Payroll(db.Model):
    id=db.Column(db.Integer,primary_key=True); employee_id=db.Column(db.Integer,db.ForeignKey('users.id'),nullable=False); month=db.Column(db.String(7),nullable=False); basic_salary=db.Column(db.Float,default=0); allowances=db.Column(db.Float,default=0); deductions=db.Column(db.Float,default=0); net_salary=db.Column(db.Float,default=0); payment_status=db.Column(db.String(30),default='pending'); employee=db.relationship('User',foreign_keys=[employee_id])

class Notification(db.Model):
    id=db.Column(db.Integer,primary_key=True); user_id=db.Column(db.Integer,db.ForeignKey('users.id'),nullable=False); title=db.Column(db.String(200),nullable=False); message=db.Column(db.Text,nullable=False); is_read=db.Column(db.Boolean,default=False); created_at=db.Column(db.DateTime,default=datetime.utcnow); user=db.relationship('User',foreign_keys=[user_id])
