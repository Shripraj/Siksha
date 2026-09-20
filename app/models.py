from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from . import db

class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class School(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(180), nullable=False)
    board = db.Column(db.String(100), default="State Board")
    academic_year = db.Column(db.String(30), default="2026–2027")

class User(UserMixin, TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    name = db.Column(db.String(160), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), nullable=False)  # school, teacher, student
    school_id = db.Column(db.Integer, db.ForeignKey("school.id"), nullable=True)
    active = db.Column(db.Boolean, default=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class TeacherProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), unique=True, nullable=False)
    employee_code = db.Column(db.String(80))
    subjects = db.Column(db.String(300))

class StudentProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), unique=True, nullable=False)
    class_name = db.Column(db.String(50))
    roll_no = db.Column(db.String(50))
    guardian_name = db.Column(db.String(160))

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("school.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)

class Topic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("subject.id"), nullable=False)
    chapter = db.Column(db.String(160), nullable=False)
    title = db.Column(db.String(180), nullable=False)
    order_index = db.Column(db.Integer, default=1)

class Progress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    topic_id = db.Column(db.Integer, db.ForeignKey("topic.id"), nullable=False)
    mastery = db.Column(db.Float, default=0)
    status = db.Column(db.String(40), default="locked")
    xp = db.Column(db.Integer, default=0)
    attempts = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Assessment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    topic_id = db.Column(db.Integer, db.ForeignKey("topic.id"), nullable=False)
    total_marks = db.Column(db.Integer, default=25)
    payload_json = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AssessmentAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey("assessment.id"), nullable=False)
    score = db.Column(db.Float, default=0)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

class IntegrityEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey("assessment.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    event_type = db.Column(db.String(80), nullable=False)
    detail = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class TeacherNote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    note = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CounsellingSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    scheduled_for = db.Column(db.String(100))
    reason = db.Column(db.String(300))
    notes = db.Column(db.Text, default="")
    status = db.Column(db.String(40), default="Scheduled")

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow)
    status = db.Column(db.String(30), default="Present")

class SyllabusDocument(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("school.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(40), default="Uploaded")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
