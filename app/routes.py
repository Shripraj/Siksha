import json
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, abort
from flask_login import login_required, current_user
from . import db
from .models import User, School, Subject, Topic, Progress, Assessment, AssessmentAttempt, IntegrityEvent, TeacherNote, CounsellingSession, SyllabusDocument
from services.ai import generate_assessment, generate_recommendation

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
def home():
    return render_template("landing.html")

@main_bp.route("/dashboard")
@login_required
def dashboard():
    return redirect(url_for(f"main.{current_user.role}_dashboard"))

@main_bp.route("/school")
@login_required
def school_dashboard():
    if current_user.role != "school": abort(403)
    school = db.session.get(School, current_user.school_id)
    students = User.query.filter_by(role="student", school_id=current_user.school_id).all()
    teacher_count = User.query.filter_by(role="teacher", school_id=current_user.school_id).count()
    class_count = 36  # placeholder; replace with real class model when available
    progress = Progress.query.filter(Progress.student_id.in_([s.id for s in students])).all() if students else []
    avg = round(sum(p.mastery for p in progress) / len(progress), 1) if progress else 0
    attention = [s for s in students if _student_average(s.id) < 40]
    return render_template("school/dashboard.html",
                           students=students, teacher_count=teacher_count,
                           class_count=class_count, avg=avg,
                           attention=attention, school=school)

@main_bp.route("/school/syllabus", methods=["GET"])
@login_required
def syllabus():
    if current_user.role != "school": abort(403)
    docs = SyllabusDocument.query.filter_by(school_id=current_user.school_id).order_by(SyllabusDocument.created_at.desc()).all()
    # Build subject → topics map for display
    subjects = Subject.query.filter_by(school_id=current_user.school_id).all()
    subject_topics = {}
    for s in subjects:
        topics = Topic.query.filter_by(subject_id=s.id).order_by(Topic.order_index).all()
        if topics:
            subject_topics[s.name] = topics
    return render_template("school/syllabus.html", docs=docs, subject_topics=subject_topics)

@main_bp.route("/teacher")
@login_required
def teacher_dashboard():
    if current_user.role != "teacher": abort(403)
    students = User.query.filter_by(role="student", school_id=current_user.school_id).all()
    rows = []
    for s in students:
        avg = _student_average(s.id)
        rows.append({"student": s, "avg": avg})
    weak = [r for r in rows if r["avg"] < 40]
    integrity = IntegrityEvent.query.order_by(IntegrityEvent.created_at.desc()).limit(8).all()
    return render_template("teacher/dashboard.html", rows=rows, weak=weak, integrity=integrity)

@main_bp.route("/student")
@login_required
def student_dashboard():
    if current_user.role != "student": abort(403)
    progress = Progress.query.filter_by(student_id=current_user.id).all()
    topic_ids = [p.topic_id for p in progress]
    topics = Topic.query.filter(Topic.id.in_(topic_ids)).order_by(Topic.order_index).all() if topic_ids else []
    pmap = {p.topic_id: p for p in progress}
    total_xp = sum(p.xp for p in progress)
    completed = sum(1 for p in progress if p.status == "completed")
    avg = round(sum(p.mastery for p in progress) / len(progress), 1) if progress else 0
    streak = 12  # placeholder; replace with real streak logic
    return render_template("student/dashboard.html",
                           topics=topics, pmap=pmap, total_xp=total_xp,
                           completed=completed, avg=avg, streak=streak)

@main_bp.route("/student/topic/<int:topic_id>")
@login_required
def topic(topic_id):
    if current_user.role != "student": abort(403)
    t = db.session.get(Topic, topic_id)
    if not t: abort(404)
    progress = Progress.query.filter_by(student_id=current_user.id, topic_id=t.id).first()
    if not progress: abort(403)
    return render_template("student/topic.html", topic=t, progress=progress)

@main_bp.route("/student/assessment/<int:topic_id>", methods=["GET", "POST"])
@login_required
def assessment(topic_id):
    if current_user.role != "student": abort(403)
    t = db.session.get(Topic, topic_id)
    if not t: abort(404)
    progress = Progress.query.filter_by(student_id=current_user.id, topic_id=t.id).first()
    if not progress: abort(403)
    if progress.status == "locked": abort(403)

    if request.method == "POST":
        assessment_id = int(request.form.get("assessment_id", 0))
        a = Assessment.query.filter_by(id=assessment_id, student_id=current_user.id, topic_id=t.id).first_or_404()
        payload = json.loads(a.payload_json or "{}")
        score = 0
        for q in payload.get("questions", []):
            if "answer_index" in q:
                chosen = request.form.get(f"q{q.get('id')}")
                if chosen is not None and str(chosen).isdigit() and int(chosen) == int(q["answer_index"]):
                    score += int(q.get("marks", 0))
        score = max(0, min(a.total_marks, score))
        db.session.add(AssessmentAttempt(assessment_id=a.id, score=score))
        progress.attempts += 1
        progress.mastery = round(score / a.total_marks * 100, 1)
        if score >= a.total_marks * 0.40:
            progress.status = "completed"
            progress.xp += int(score * 10)
            # Unlock next topic in sequence
            next_topic = Topic.query.filter_by(subject_id=t.subject_id).filter(
                Topic.order_index == t.order_index + 1).first()
            if next_topic:
                next_progress = Progress.query.filter_by(
                    student_id=current_user.id, topic_id=next_topic.id).first()
                if next_progress and next_progress.status == "locked":
                    next_progress.status = "in_progress"
        else:
            progress.status = "needs_revision"
        db.session.commit()
        return render_template("student/result.html", topic=t, score=score, progress=progress)

    payload = generate_assessment(t.title, t.chapter, 25)
    a = Assessment(student_id=current_user.id, topic_id=t.id, total_marks=25, payload_json=json.dumps(payload))
    db.session.add(a)
    db.session.commit()
    return render_template("student/assessment.html", topic=t, assessment=a, questions=payload.get("questions", []))

@main_bp.post("/api/assessment/<int:assessment_id>/integrity")
@login_required
def integrity(assessment_id):
    if current_user.role != "student": abort(403)
    a = db.session.get(Assessment, assessment_id)
    if not a: abort(404)
    if a.student_id != current_user.id: abort(403)
    data = request.get_json(silent=True) or {}
    event = IntegrityEvent(assessment_id=a.id, student_id=current_user.id,
                           event_type=data.get("event_type", "unknown"),
                           detail=data.get("detail", ""))
    db.session.add(event)
    db.session.commit()
    return jsonify({"ok": True})

@main_bp.post("/api/teacher/note")
@login_required
def teacher_note():
    if current_user.role != "teacher": abort(403)
    data = request.get_json(silent=True) or {}
    student_id = data.get("student_id")
    if not student_id: abort(400)
    student = db.session.get(User, int(student_id))
    if not student: abort(404)
    if student.school_id != current_user.school_id: abort(403)
    db.session.add(TeacherNote(teacher_id=current_user.id, student_id=student.id,
                               note=data.get("note", "")))
    db.session.commit()
    return jsonify({"ok": True})

@main_bp.post("/api/teacher/counselling")
@login_required
def counselling():
    if current_user.role != "teacher": abort(403)
    data = request.get_json(silent=True) or {}
    student_id = data.get("student_id")
    if not student_id: abort(400)
    student = db.session.get(User, int(student_id))
    if not student: abort(404)
    if student.school_id != current_user.school_id: abort(403)
    db.session.add(CounsellingSession(teacher_id=current_user.id, student_id=student.id,
                                     scheduled_for=data.get("scheduled_for", ""),
                                     reason=data.get("reason", "Low score")))
    db.session.commit()
    return jsonify({"ok": True})

@main_bp.get("/api/teacher/recommendation/<int:student_id>")
@login_required
def recommendation(student_id):
    if current_user.role != "teacher": abort(403)
    student = db.session.get(User, student_id)
    if not student: abort(404)
    if student.school_id != current_user.school_id: abort(403)
    avg = _student_average(student.id)
    note = TeacherNote.query.filter_by(student_id=student.id).order_by(TeacherNote.created_at.desc()).first()
    return jsonify(generate_recommendation(student.name, avg, note.note if note else ""))

def _student_average(student_id):
    ps = Progress.query.filter_by(student_id=student_id).all()
    return round(sum(p.mastery for p in ps) / len(ps), 1) if ps else 0


@main_bp.route("/school/syllabus/upload", methods=["POST"])
@login_required
def syllabus_upload():
    if current_user.role != "school": abort(403)
    f = request.files.get("syllabus")
    if not f or not f.filename.endswith(".json"):
        flash("Please upload a valid .json syllabus file.", "error")
        return redirect(url_for("main.syllabus"))

    try:
        import json as _json
        data = _json.loads(f.read().decode("utf-8"))
    except Exception:
        flash("Could not read the file. Make sure it is a valid JSON.", "error")
        return redirect(url_for("main.syllabus"))

    subjects_data = data.get("subjects", [])
    if not subjects_data:
        flash("No subjects found in the JSON file.", "error")
        return redirect(url_for("main.syllabus"))

    total_topics = 0
    for subj_data in subjects_data:
        subj_name = subj_data.get("name", "").strip()
        if not subj_name:
            continue
        subject = Subject.query.filter_by(name=subj_name, school_id=current_user.school_id).first()
        if not subject:
            subject = Subject(name=subj_name, school_id=current_user.school_id)
            db.session.add(subject)
            db.session.flush()

        order_counter = Topic.query.filter_by(subject_id=subject.id).count() + 1
        for chapter_data in subj_data.get("chapters", []):
            chapter_name = chapter_data.get("chapter", "").strip()
            for topic_title in chapter_data.get("topics", []):
                topic_title = topic_title.strip()
                exists = Topic.query.filter_by(
                    subject_id=subject.id, chapter=chapter_name, title=topic_title).first()
                if not exists:
                    topic = Topic(subject_id=subject.id, chapter=chapter_name,
                                  title=topic_title, order_index=order_counter)
                    db.session.add(topic)
                    db.session.flush()
                    order_counter += 1
                    total_topics += 1

    db.session.commit()

    # Assign progress to all students in the school
    from . import seed_student_topics
    students = User.query.filter_by(role="student", school_id=current_user.school_id).all()
    for student in students:
        seed_student_topics(student.id, current_user.school_id)

    # Log the upload
    doc = SyllabusDocument(school_id=current_user.school_id,
                           filename=f.filename,
                           status=f"✓ Seeded — {total_topics} new topics added")
    db.session.add(doc)
    db.session.commit()

    flash(f"Success! {total_topics} new topics seeded and assigned to {len(students)} student(s).", "success")
    return redirect(url_for("main.syllabus"))
