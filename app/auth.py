from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user
from sqlalchemy import func
from . import db
from .models import User, School, TeacherProfile, StudentProfile

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "").strip().lower()
        user = User.query.filter(func.lower(User.email) == email).first()
        if not user or not user.check_password(password):
            flash("Invalid email or password.", "error")
            return render_template("auth/login.html", selected_role=role)
        if role and user.role != role:
            flash("This account is registered under a different portal.", "error")
            return render_template("auth/login.html", selected_role=role)
        login_user(user, remember=True)
        return redirect(url_for("main.dashboard"))
    selected_role = request.args.get("role", "student")
    if selected_role not in {"school", "teacher", "student"}:
        selected_role = "student"
    return render_template("auth/login.html", selected_role=selected_role)

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        role = request.form.get("role", "student").strip().lower()
        school_name = request.form.get("school_name", "").strip()
        class_name = request.form.get("class_name", "").strip()
        roll_no = request.form.get("roll_no", "").strip()
        employee_code = request.form.get("employee_code", "").strip()
        subjects = request.form.get("subjects", "").strip()

        if not name or not email or not password:
            flash("Please fill all required fields.", "error")
            return render_template("auth/register.html")
        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template("auth/register.html")
        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return render_template("auth/register.html")
        if role not in {"school", "teacher", "student"}:
            flash("Choose a valid portal.", "error")
            return render_template("auth/register.html")
        if User.query.filter(func.lower(User.email) == email).first():
            flash("An account with this email already exists. Please log in.", "error")
            return render_template("auth/register.html")

        school = None
        if role == "school":
            school = School(name=school_name or f"{name}'s School")
            db.session.add(school)
            db.session.flush()
        else:
            school = School.query.first()
            if not school:
                school = School(name="My School", board="State Board")
                db.session.add(school)
                db.session.flush()

        user = User(email=email, name=name, role=role, school_id=school.id)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        if role == "teacher":
            db.session.add(TeacherProfile(user_id=user.id, employee_code=employee_code, subjects=subjects))
        elif role == "student":
            db.session.add(StudentProfile(
                user_id=user.id,
                class_name=class_name or "10A",
                roll_no=roll_no,
                guardian_name=""
            ))
        db.session.commit()

        # Seed quest map for new students
        if role == "student":
            from . import seed_student_topics
            seed_student_topics(user.id, school.id)

        login_user(user, remember=True)
        flash("Account created successfully. Your quest begins!", "success")
        return redirect(url_for("main.dashboard"))
    return render_template("auth/register.html")

@auth_bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("main.home"))
