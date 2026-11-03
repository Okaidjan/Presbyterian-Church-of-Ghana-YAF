import os
from datetime import date, datetime
import io, csv
from flask import Flask, request, redirect
from flask import url_for, render_template_string
from flask import make_response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin
from flask_login import login_user, logout_user
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get(
    'SECRET_KEY', 'presby-yaf-2026')
db_url = os.environ.get('DATABASE_URL', '')
if db_url.startswith('postgres://'):
    db_url = db_url.replace(
        'postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url or 'sqlite:///yaf.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(
        db.String(80), unique=True, nullable=False)
    password_hash = db.Column(
        db.String(200), nullable=False)
    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)
    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    gender = db.Column(db.String(10))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    zone = db.Column(db.String(50))
    birthday = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), default='Active')
    date_joined = db.Column(
        db.DateTime, default=datetime.utcnow)
    occupation = db.Column(db.String(80))

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    event_date = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(120))
    description = db.Column(db.Text)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(
        db.Integer, db.ForeignKey('event.id'), nullable=False)
    member_id = db.Column(
        db.Integer, db.ForeignKey('member.id'), nullable=False)
    timestamp = db.Column(
        db.DateTime, default=datetime.utcnow)
    event = db.relationship('Event', backref='attendances')
    member = db.relationship('Member', backref='attendances')

class Executive(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    position = db.Column(db.String(80), nullable=False)
    member_id = db.Column(
        db.Integer, db.ForeignKey('member.id'))
    year = db.Column(db.String(10), default='2025/2026')
    member = db.relationship('Member')

class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(
        db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

BASE = '''<!DOCTYPE html><html><head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>YAF</title>
<style>
body{font-family:system-ui;background:#f6f7fb;margin:0}
nav{background:#0a1931;color:#fff;padding:14px;display:flex;gap:10px;flex-wrap:wrap}
nav a{color:#fff;text-decoration:none;padding:6px 10px}
.container{max-width:1100px;margin:20px auto;padding:0 16px}
.card{background:#fff;border-radius:14px;padding:18px;margin-bottom:16px;box-shadow:0 2px 12px rgba(0,0,0,.06)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px}
.btn{background:#0a1931;color:#fff;padding:8px 14px;border-radius:8px;text-decoration:none;display:inline-block;border:none}
.btn-light{background:#eef2ff;color:#0a1931}
input,select,textarea{width:100%;padding:10px;border:1px solid #ddd;border-radius:8px;margin-top:6px}
table{width:100%;border-collapse:collapse}th,td{padding:10px;border-bottom:1px solid #eee}
</style></head><body>
<nav><b>YAF</b>
<a href="/dashboard">Dashboard</a>
<a href="/members">Members</a>
<a href="/events">Events</a>
<a href="/attendance">Attendance</a>
<a href="/executives">Exec</a>
<a href="/announcements">News</a>
<a href="/analytics">Analytics</a>
{% if current_user.is_authenticated %}
<span style="margin-left:auto">{{ current_user.username }}</span>
<a href="/logout">Logout</a>
{% endif %}</nav>
<div class="container">__CONTENT__</div></body></html>'''

def page(c):
    h = BASE.replace('__CONTENT__', c)
    return render_template_string(h)

@app.route('/')
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        u = User.query.filter_by(
            username=request.form['username']).first()
        if u and u.check_password(request.form['password']):
            login_user(u)
            return redirect(url_for('dashboard'))
    return page('''<div class="card" style="max-width:400px;margin:60px auto">
<h2>YAF Login</h2>
<form method="POST">
<label>Username</label><input name="username" required>
<label>Password</label><input name="password" type="password" required>
<div style="margin-top:12px"><button class="btn">Login</button></div>
</form><p><small>admin / admin123</small></p></div>''')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    total = Member.query.count()
    active = Member.query.filter_by(status='Active').count()
    events = Event.query.count()
    return page(f'''<div class="card"><h2>Dashboard</h2></div>
<div class="grid">
<div class="card"><h3>Total Members</h3><h2>{total}</h2></div>
<div class="card"><h3>Active</h3><h2>{active}</h2></div>
<div class="card"><h3>Events</h3><h2>{events}</h2></div>
<div class="card"><a class="btn" href="/members/new">+ Member</a>
<a class="btn btn-light" href="/events/new">+ Event</a></div></div>''')

@app.route('/members')
@login_required
def members_list():
    q = request.args.get('q','')
    query = Member.query
    if q:
        query = query.filter(Member.full_name.ilike(f"%{q}%"))
    all_m = query.order_by(Member.full_name).all()
    rows = ''
    for m in all_m:
        rows += f"<tr><td>{m.full_name}</td><td>{m.phone or ''}</td><td>{m.zone or ''}</td><td>{m.status}</td><td><a href='/members/{m.id}/edit'>Edit</a> | <a href='/members/{m.id}/delete'>Del</a></td></tr>"
    return page(f'''<div class="card"><h2>Members ({len(all_m)})</h2>
<form method="GET" style="display:flex;gap:8px"><input name="q" value="{q}" placeholder="Search"><button class="btn">Go</button></form>
<div style="margin-top:10px"><a class="btn" href="/members/new">+ Add</a> <a class="btn btn-light" href="/members/export.csv">CSV</a></div>
<table><tr><th>Name</th><th>Phone</th><th>Zone</th><th>Status</th><th>Action</th></tr>{rows}</table></div>''')

@app.route('/members/new', methods=['GET','POST'])
@app.route('/members/<int:id>/edit', methods=['GET','POST'])
@login_required
def member_form(id=None):
    m = Member.query.get(id) if id else None
    if request.method == 'POST':
        if not m:
            m = Member()
            db.session.add(m)
        m.full_name = request.form['full_name']
        m.gender = request.form['gender']
        m.phone = request.form['phone']
        m.email = request.form['email']
        m.zone = request.form['zone']
        m.status = request.form['status']
        m.occupation = request.form['occupation']
        bday = request.form.get('birthday')
        try:
            m.birthday = date.fromisoformat(bday) if bday else None
        except:
            m.birthday = None
        db.session.commit()
        return redirect(url_for('members_list'))
    fn = m.full_name if m else ''
    ph = m.phone if m else ''
    em = m.email if m else ''
    zn = m.zone if m else ''
    oc = m.occupation if m else ''
    bd = m.birthday.isoformat() if m and m.birthday else ''
    sel_f = 'selected' if m and m.gender=='Female' else ''
    sel_i = 'selected' if m and m.status=='Inactive' else ''
    ttl = 'Edit' if m else 'New'
    return page(f'''<div class="card"><h2>{ttl} Member</h2>
<form method="POST" class="grid">
<div><label>Full Name</label><input name="full_name" value="{fn}" required></div>
<div><label>Gender</label><select name="gender"><option>Male</option><option {sel_f}>Female</option></select></div>
<div><label>Phone</label><input name="phone" value="{ph}"></div>
<div><label>Email</label><input name="email" value="{em}"></div>
<div><label>Zone</label><input name="zone" value="{zn}"></div>
<div><label>Birthday</label><input type="date" name="birthday" value="{bd}"></div>
<div><label>Occupation</label><input name="occupation" value="{oc}"></div>
<div><label>Status</label><select name="status"><option>Active</option><option {sel_i}>Inactive</option></select></div>
<div style="grid-column:1/-1"><button class="btn">Save</button></div></form></div>''')

@app.route('/members/<int:id>/delete')
@login_required
def member_delete(id):
    db.session.delete(Member.query.get_or_404(id))
    db.session.commit()
    return redirect(url_for('members_list'))

@app.route('/events')
@login_required
def events_list():
    ev = Event.query.order_by(Event.event_date.desc()).all()
    rows = ''
    for e in ev:
        rows += f"<tr><td>{e.title}</td><td>{e.event_date.strftime('%Y-%m-%d')}</td><td>{e.location or ''}</td><td>{len(e.attendances)}</td><td><a href='/attendance?event={e.id}'>Take</a> | <a href='/events/{e.id}/delete'>Del</a></td></tr>"
    return page(f'''<div class="card"><h2>Events</h2><a class="btn" href="/events/new">+ New</a>
<table><tr><th>Title</th><th>Date</th><th>Loc</th><th>Count</th><th>Action</th></tr>{rows}</table></div>''')

@app.route('/events/new', methods=['GET','POST'])
@login_required
def event_new():
    if request.method == 'POST':
        e = Event(title=request.form['title'], event_date=datetime.fromisoformat(request.form['event_date']), location=request.form['location'], description=request.form['description'])
        db.session.add(e)
        db.session.commit()
        return redirect(url_for('events_list'))
    return page('''<div class="card"><h2>New Event</h2>
<form method="POST" class="grid">
<div><label>Title</label><input name="title" required></div>
<div><label>Date</label><input type="datetime-local" name="event_date" required></div>
<div><label>Location</label><input name="location"></div>
<div style="grid-column:1/-1"><label>Desc</label><textarea name="description"></textarea></div>
<div><button class="btn">Create</button></div></form></div>''')

@app.route('/events/<int:id>/delete')
@login_required
def event_delete(id):
    db.session.delete(Event.query.get_or_404(id))
    db.session.commit()
    return redirect(url_for('events_list'))

@app.route('/attendance')
@login_required
def attendance_page():
    eid = request.args.get('event', type=int)
    ev = Event.query.get(eid) if eid else Event.query.order_by(Event.event_date.desc()).first()
    all_ev = Event.query.order_by(Event.event_date.desc()).all()
    members = Member.query.filter_by(status='Active').order_by(Member.full_name).all()
    if
