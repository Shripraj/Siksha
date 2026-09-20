# SIKSHA — Warrior Learning Platform

A Flask + PostgreSQL-ready school learning platform based on the supplied SIKSHA visual reference.

## Included
- Dark fantasy / warrior landing page
- School Admin, Teacher and Student roles
- Email + password registration and login
- Password hashing with Werkzeug
- Role-aware redirects
- SQLite by default; PostgreSQL through `DATABASE_URL`
- School dashboard with performance and attention metrics
- Teacher dashboard with weak-student workflow, counselling notes and AI recommendations
- Student RPG quest map with XP, streak, mastery and topic progression
- Fullscreen assessment mode with integrity-event logging
- 25-mark assessment workflow
- Groq integration with a safe fallback when no API key is configured
- Syllabus upload endpoint and RAG service scaffold

## Run on Windows
```powershell
cd SIKSHA-Warrior-Learning-Platform
py -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python run.py
```
Open http://127.0.0.1:5000

## Demo accounts
- School Admin: admin@siksha.demo / admin123
- Teacher: teacher@siksha.demo / teacher123
- Student: student@siksha.demo / student123

You can also register a completely new account from the registration page.

## PostgreSQL
Set `DATABASE_URL` in `.env`, for example:
`postgresql+psycopg://username:password@localhost:5432/siksha`

If using PostgreSQL, add `psycopg[binary]` to requirements.

## Render
Build:
`pip install -r requirements.txt`

Start:
`gunicorn run:app`

Set `SECRET_KEY` and `DATABASE_URL` in Render environment variables.
