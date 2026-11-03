import os
from datetime import date, datetime
import io, csv
from flask import Flask, request, redirect, url_for, render_template_string, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'presby-yaf-secret-2026')
db_url = os.environ.get('DATABASE_URL', '')
if db_url.startswith('postgres://'): db_url = db_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url or 'sqlite:///yaf.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id=db.Column(db.Integer, primary_key=True); username=db.Column(db.String(80), unique=True, nullable=False); password_hash=db.Column(db.String(200), nullable=False)
    def set_password(self, pw): self.password_hash=generate_password_hash(pw)
    def check_password(self, pw): return check_password_hash(self.password_hash, pw)
class Member(db.Model):
    id=db.Column(db.Integer, primary_key=True); full_name=db.Column(db.String(120), nullable=False); gender=db.Column(db.String(10)); phone=db.Column(db.String(20)); email=db.Column(db.String(100)); zone=db.Column(db.String(50)); birthday=db.Column(db.Date, nullable=True); status=db.Column(db.String(20), default='Active'); date_joined=db.Column(db.DateTime, default=datetime.utcnow); occupation=db.Column(db.String(80))
class Event(db.Model):
    id=db.Column(db.Integer, primary_key=True); title=db.Column(db.String(150), nullable=False); event_date=db.Column(db.DateTime, nullable=False); location=db.Column(db.String(120)); description=db.Column(db.Text)
class Attendance(db.Model):
    id=db.Column(db.Integer, primary_key=True); event_id=db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False); member_id=db.Column(db.Integer, db.ForeignKey('member.id'), nullable=False); timestamp=db.Column(db.DateTime, default=datetime.utcnow); event=db.relationship('Event', backref='attendances'); member=db.relationship('Member', backref='attendances')
class Executive(db.Model):
    id=db.Column(db.Integer, primary_key=True); position=db.Column(db.String(80), nullable=False); member_id=db.Column(db.Integer, db.ForeignKey('member.id')); year=db.Column(db.String(10), default='2025/2026'); member=db.relationship('Member')
class Announcement(db.Model):
    id=db.Column(db.Integer, primary_key=True); title=db.Column(db.String(150), nullable=False); content=db.Column(db.Text, nullable=False); date_posted=db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id): return User.query.get(int(user_id))

BASE_HTML = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><title>YAF</title><style>body{font-family:system-ui,sans-serif;background:#f6f7fb;margin:0}nav{background:#0a1931;color:white;padding:14px 20px;display:flex;gap:12px;flex-wrap:wrap}nav a{color:white;text-decoration:none;padding:6px 10px;border-radius:6px}nav a:hover{background:#1a2d50}.container{max-width:1100px;margin:20px auto;padding:0 16px}.card{background:white;border-radius:14px;padding:18px;box-shadow:0 2px 12px rgba(0,0,0,0.06);margin-bottom:16px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}.btn{background:#0a1931;color:white;padding:8px 14px;border-radius:8px;text-decoration:none;display:inline-block;border:none}.btn-light{background:#eef2ff;color:#0a1931}input,select,textarea{width:100%;padding:10px;border:1px solid #ddd;border-radius:8px;margin-top:6px}table{width:100%;border-collapse:collapse}th,td{padding:10px;border-bottom:1px solid #eee;font-size:14px}</style></head><body><nav><b>PREBSY YAF</b><a href="/dashboard">Dashboard</a><a href="/members">Members</a><a href="/events">Events</a><a href="/attendance">Attendance</a><a href="/executives">Executives</a><a href="/announcements">Announcements</a><a href="/analytics">Analytics</a><span style="margin-left:auto"></span>{% if current_user.is_authenticated %}<span>{{ current_user.username }}</span><a href="/logout">Logout</a>{% endif %}</nav><div class="container">__CONTENT__</div></body></html>"""
def page(content): return render_template_string(BASE_HTML.replace("__CONTENT__", content))
