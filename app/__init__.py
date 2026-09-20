import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-only-change-me")
    db_url = os.getenv("DATABASE_URL", "sqlite:///siksha.db")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    login_manager.init_app(app)

    from .models import User
    from .auth import auth_bp
    from .routes import main_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    with app.app_context():
        db.create_all()
        seed_demo_data()

    return app

@login_manager.user_loader
def load_user(user_id):
    from .models import User
    return db.session.get(User, int(user_id))

def seed_demo_data():
    from .models import User, School, TeacherProfile, StudentProfile, Subject, Topic, Progress
    if User.query.filter_by(email="admin@siksha.demo").first():
        return

    school = School(name="Springfield High", board="State Board", academic_year="2026–2027")
    db.session.add(school)
    db.session.flush()

    admin = User(email="admin@siksha.demo", name="School Admin", role="school", school_id=school.id)
    admin.set_password("admin123")
    teacher = User(email="teacher@siksha.demo", name="Priya Sharma", role="teacher", school_id=school.id)
    teacher.set_password("teacher123")
    student = User(email="student@siksha.demo", name="Aarav Sharma", role="student", school_id=school.id)
    student.set_password("student123")
    db.session.add_all([admin, teacher, student])
    db.session.flush()

    db.session.add(TeacherProfile(user_id=teacher.id, employee_code="T-104", subjects="Mathematics, Science"))
    db.session.add(StudentProfile(user_id=student.id, class_name="10A", roll_no="17", guardian_name="Raj Sharma"))

    # Seed topics (shared across the school)
    topic_data = [
        ("Mathematics", "Algebra", "Introduction to Variables", 1),
        ("Mathematics", "Algebra", "Linear Equations", 2),
        ("Mathematics", "Algebra", "Word Problems", 3),
        ("Mathematics", "Algebra", "Inequalities", 4),
        ("Mathematics", "Algebra", "Functions", 5),
        ("Science", "Chemical Reactions", "Types of Reactions", 1),
        ("English", "Reading", "Comprehension", 1),
    ]
    # Progress for the demo student
    student_progress = [
        ("Introduction to Variables", 100, "completed"),
        ("Linear Equations", 68, "in_progress"),
        ("Word Problems", 0, "locked"),
        ("Inequalities", 0, "locked"),
        ("Functions", 0, "locked"),
        ("Types of Reactions", 36, "in_progress"),
        ("Comprehension", 82, "completed"),
    ]
    progress_map = {title: (mastery, status) for title, mastery, status in student_progress}

    created_topics = {}
    for subject_name, chapter, title, order_index in topic_data:
        subject = Subject.query.filter_by(name=subject_name, school_id=school.id).first()
        if not subject:
            subject = Subject(name=subject_name, school_id=school.id)
            db.session.add(subject)
            db.session.flush()
        topic = Topic(subject_id=subject.id, chapter=chapter, title=title, order_index=order_index)
        db.session.add(topic)
        db.session.flush()
        created_topics[title] = topic

    for title, topic in created_topics.items():
        mastery, status = progress_map.get(title, (0, "locked"))
        db.session.add(Progress(
            student_id=student.id, topic_id=topic.id,
            mastery=mastery, status=status, xp=int(mastery * 2)
        ))

    db.session.commit()

def seed_student_topics(student_id, school_id):
    """Called after a new student registers to give them their quest map."""
    from .models import Topic, Subject, Progress
    subjects = Subject.query.filter_by(school_id=school_id).all()
    subject_ids = [s.id for s in subjects]
    if not subject_ids:
        return
    topics = Topic.query.filter(Topic.subject_id.in_(subject_ids)).order_by(
        Topic.subject_id, Topic.order_index).all()
    existing = {p.topic_id for p in Progress.query.filter_by(student_id=student_id).all()}
    for i, topic in enumerate(topics):
        if topic.id in existing:
            continue
        # First topic of each subject is in_progress; rest are locked
        is_first = (i == 0) or (topics[i - 1].subject_id != topic.subject_id)
        status = "in_progress" if is_first else "locked"
        db.session.add(Progress(student_id=student_id, topic_id=topic.id,
                                mastery=0, status=status, xp=0))
    db.session.commit()
