import os
from datetime import date, datetime, timedelta
from collections import defaultdict
import io, csv
from flask import Flask, request, redirect, url_for, render_template_string, make_response, flash
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
    id=db.Column(db.Integer, primary_key=True); username=db.Column(db.String(80), unique=True, nullable=False)
    password_hash=db.Column(db.String(200), nullable=False); role=db.Column(db.String(20), default='admin')
    def set_password(self, pw): self.password_hash=generate_password_hash(pw)
    def check_password(self, pw): return check_password_hash(self.password_hash, pw)

class Member(db.Model):
    id=db.Column(db.Integer, primary_key=True); full_name=db.Column(db.String(120), nullable=False); gender=db.Column(db.String(10))
    phone=db.Column(db.String(20)); email=db.Column(db.String(100)); zone=db.Column(db.String(50)); birthday=db.Column(db.Date, nullable=True)
    status=db.Column(db.String(20), default='Active'); date_joined=db.Column(db.DateTime, default=datetime.utcnow); occupation=db.Column(db.String(80))

class Event(db.Model):
    id=db.Column(db.Integer, primary_key=True); title=db.Column(db.String(150), nullable=False); event_date=db.Column(db.DateTime, nullable=False)
    location=db.Column(db.String(120)); description=db.Column(db.Text)

class Attendance(db.Model):
    id=db.Column(db.Integer, primary_key=True); event_id=db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    member_id=db.Column(db.Integer, db.ForeignKey('member.id'), nullable=False); timestamp=db.Column(db.DateTime, default=datetime.utcnow)
    event=db.relationship('Event', backref='attendances'); member=db.relationship('Member', backref='attendances')

class Executive(db.Model):
    id=db.Column(db.Integer, primary_key=True); position=db.Column(db.String(80), nullable=False)
    member_id=db.Column(db.Integer, db.ForeignKey('member.id')); year=db.Column(db.String(10), default='2025/2026')
    member=db.relationship('Member')

class Announcement(db.Model):
    id=db.Column(db.Integer, primary_key=True); title=db.Column(db.String(150), nullable=False)
    content=db.Column(db.Text, nullable=False); date_posted=db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id): return User.query.get(int(user_id))

def page_template(content, title="Presbyterian YAF"):
    return render_template_string("""<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><title>{{ title }}</title>
<style>body{font-family:system-ui,sans-serif;background:#f6f7fb;margin:0}nav{background:#0a1931;color:white;padding:14px 20px;display:flex;gap:12px;flex-wrap:wrap}nav a{color:white;text-decoration:none;padding:6px 10px;border-radius:6px}nav a:hover{background:#1a2d50}.container{max-width:1100px;margin:20px auto;padding:0 16px}.card{background:white;border-radius:14px;padding:18px;box-shadow:0 2px 12px rgba(0,0,0,0.06);margin-bottom:16px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}.btn{background:#0a1931;color:white;padding:8px 14px;border-radius:8px;text-decoration:none;display:inline-block}.btn-light{background:#eef2ff;color:#0a1931}input,select,textarea{width:100%;padding:10px;border:1px solid #ddd;border-radius:8px;margin-top:6px}table{width:100%;border-collapse:collapse}th,td{padding:10px;border-bottom:1px solid #eee;font-size:14px}</style>
</head><body><nav><b>⛪ PRESBY YAF</b><a href="/dashboard">Dashboard</a><a href="/members">Members</a><a href="/events">Events</a><a href="/attendance">Attendance</a><a href="/executives">Executives</a><a href="/announcements">Announcements</a><a href="/analytics">Analytics</a><span style="margin-left:auto"></span>{% if current_user.is_authenticated %}<span>{{ current_user.username }}</span><a href="/logout">Logout</a>{% endif %}</nav><div class="container">{{ content|safe }}</div></body></html>""", content=content, title=title)

@app.route("/")
@app.route("/login", methods=['GET','POST'])
def login():
    if request.method=='POST':
        u=User.query.filter_by(username=request.form['username']).first()
        if u and u.check_password(request.form['password']): login_user(u); return redirect(url_for('dashboard'))
    return page_template('<div class="card" style="max-width:400px;margin:60px auto"><h2>YAF Login</h2><form method="POST"><label>Username</label><input name="username" required><label>Password</label><input name="password" type="password" required><div style="margin-top:12px"><button class="btn" type="submit">Login</button></div></form><small>Default: admin / admin123</small></div>')

@app.route("/logout")
def logout(): logout_user(); return redirect(url_for('login'))

@app.route("/dashboard")
@login_required
def dashboard():
    total_members=Member.query.count(); active_members=Member.query.filter_by(status='Active').count(); total_events=Event.query.count(); upcoming=Event.query.filter(Event.event_date >= datetime.utcnow()).count()
    content=render_template_string("""<div class="card"><h2>Dashboard — Presbyterian Church of Ghana YAF</h2></div><div class="grid"><div class="card"><h3>Total Members</h3><h2>{{ total_members }}</h2></div><div class="card"><h3>Active</h3><h2>{{ active_members }}</h2></div><div class="card"><h3>Events</h3><h2>{{ total_events }}</h2></div><div class="card"><h3>Upcoming</h3><h2>{{ upcoming }}</h2></div></div><div class="grid"><div class="card"><h3>Quick Actions</h3><a class="btn" href="/members/new">+ Add Member</a> <a class="btn" href="/events/new">+ New Event</a></div><div class="card"><h3>Latest Members</h3><table>{% for m in latest %}<tr><td>{{ m.full_name }}</td><td>{{ m.zone }}</td></tr>{% endfor %}</table></div></div>""", total_members=total_members, active_members=active_members, total_events=total_events, upcoming=upcoming, latest=Member.query.order_by(Member.id.desc()).limit(5).all())
    return page_template(content)

@app.route("/members")
@login_required
def members():
    q=request.args.get('q',''); query=Member.query; 
    if q: query=query.filter(Member.full_name.ilike(f"%{q}%"))
    all_members=query.order_by(Member.full_name).all()
    content=render_template_string("""<div class="card"><h2>Members ({{ all_members|length }})</h2><form method="GET" style="display:flex;gap:8px"><input name="q" placeholder="Search" value="{{ q }}"><button class="btn">Search</button></form><div style="margin-top:10px"><a class="btn" href="/members/new">+ Add Member</a> <a class="btn btn-light" href="/members/export.csv">Export CSV</a></div><table><tr><th>Name</th><th>Phone</th><th>Zone</th><th>Status</th><th>Action</th></tr>{% for m in all_members %}<tr><td>{{ m.full_name }}</td><td>{{ m.phone }}</td><td>{{ m.zone }}</td><td>{{ m.status }}</td><td><a href="/members/{{ m.id }}/edit">Edit</a> | <a href="/members/{{ m.id }}/delete" onclick="return confirm('Delete?')">Del</a></td></tr>{% endfor %}</table></div>""", all_members=all_members, q=q)
    return page_template(content)

@app.route("/members/new", methods=['GET','POST'])
@app.route("/members/<int:id>/edit", methods=['GET','POST'])
@login_required
def member_form(id=None):
    m=Member.query.get(id) if id else None
    if request.method=='POST':
        if not m: m=Member(); db.session.add(m)
        m.full_name=request.form['full_name']; m.gender=request.form['gender']; m.phone=request.form['phone']; m.email=request.form['email']; m.zone=request.form['zone']; m.status=request.form['status']; m.occupation=request.form['occupation']
        try: m.birthday=date.fromisoformat(request.form.get('birthday')) if request.form.get('birthday') else None
        except: m.birthday=None
        db.session.commit(); return redirect(url_for('members'))
    content=render_template_string("""<div class="card"><h2>{{ 'Edit' if m else 'New' }} Member</h2><form method="POST" class="grid"><div><label>Full Name</label><input name="full_name" value="{{ m.full_name if m else '' }}" required></div><div><label>Gender</label><select name="gender"><option>Male</option><option {% if m and m.gender=='Female' %}selected{% endif %}>Female</option></
