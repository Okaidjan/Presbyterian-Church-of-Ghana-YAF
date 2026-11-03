import os
from datetime import date, datetime
import io, csv
from flask import Flask, request, redirect, url_for, render_template_string, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY','yaf-2026')
db_url = os.environ.get('DATABASE_URL','')
if db_url.startswith('postgres://'): db_url=db_url.replace('postgres://','postgresql://',1)
app.config['SQLALCHEMY_DATABASE_URI']=db_url or 'sqlite:///yaf.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']=False
db=SQLAlchemy(app)
login_manager=LoginManager(app)
login_manager.login_view='login'

class User(UserMixin, db.Model):
 id=db.Column(db.Integer, primary_key=True)
 username=db.Column(db.String(80), unique=True, nullable=False)
 password_hash=db.Column(db.String(200), nullable=False)
 def set_password(self,p): self.password_hash=generate_password_hash(p)
 def check_password(self,p): return check_password_hash(self.password_hash,p)

class Member(db.Model):
 id=db.Column(db.Integer, primary_key=True)
 full_name=db.Column(db.String(120), nullable=False)
 gender=db.Column(db.String(10))
 phone=db.Column(db.String(20))
 zone=db.Column(db.String(50))
 birthday=db.Column(db.Date, nullable=True)
 status=db.Column(db.String(20), default='Active')
 date_joined=db.Column(db.DateTime, default=datetime.utcnow)

class Event(db.Model):
 id=db.Column(db.Integer, primary_key=True)
 title=db.Column(db.String(150), nullable=False)
 event_date=db.Column(db.DateTime, nullable=False)
 location=db.Column(db.String(120))

class Attendance(db.Model):
 id=db.Column(db.Integer, primary_key=True)
 event_id=db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
 member_id=db.Column(db.Integer, db.ForeignKey('member.id'), nullable=False)
 event=db.relationship('Event', backref='attendances')
 member=db.relationship('Member', backref='attendances')

@login_manager.user_loader
def load_user(uid): return User.query.get(int(uid))

BASE='''<meta name="viewport" content="width=device-width, initial-scale=1"><style>
body{font-family:system-ui;background:#f6f7fb;margin:0}nav{background:#0a1931;color:#fff;padding:14px;display:flex;gap:8px;flex-wrap:wrap}
nav a{color:#fff;text-decoration:none}.container{max-width:1000px;margin:16px auto;padding:0 12px}.card{background:#fff;border-radius:12px;padding:14px;margin-bottom:12px;box-shadow:0 1px 8px rgba(0,0,0,.06)}
.btn{background:#0a1931;color:#fff;padding:8px 12px;border-radius:8px;text-decoration:none;border:none}input,select{width:100%;padding:8px;border:1px solid #ddd;border-radius:6px;margin-top:4px}
table{width:100%;border-collapse:collapse}th,td{padding:8px;border-bottom:1px solid #eee;font-size:13px}
</style><nav><b>YAF</b> <a href="/dashboard">Dash</a> <a href="/members">Members</a> <a href="/events">Events</a> <a href="/attendance">Attend</a> {% if current_user.is_authenticated %}<span style="margin-left:auto">{{ current_user.username }}</span> <a href="/logout">Logout</a>{% endif %}</nav><div class="container">__CONTENT__</div>'''
def page(c): return render_template_string(BASE.replace('__CONTENT__',c))

@app.route('/', methods=['GET','POST'])
@app.route('/login', methods=['GET','POST'])
def login():
 if request.method=='POST':
  u=User.query.filter_by(username=request.form['username']).first()
  if u and u.check_password(request.form['password']):
   login_user(u); return redirect(url_for('dashboard'))
 return page('<div class="card" style="max-width:360px;margin:50px auto"><h3>YAF Login</h3><form method="POST"><input name="username" placeholder="Username" required><input name="password" type="password" placeholder="Password" required style="margin-top:8px"><div style="margin-top:10px"><button class="btn">Login</button></div></form><p><small>admin / admin123</small></p></div>')

@app.route('/logout')
def logout(): logout_user(); return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
 return page(f'<div class="card"><h3>Dashboard</h3></div><div class="card">Members: {Member.query.count()} | Active: {Member.query.filter_by(status="Active").count()} | Events: {Event.query.count()}<br><br><a class="btn" href="/members/new">+ Member</a> <a class="btn" href="/events/new">+ Event</a></div>')

@app.route('/members')
@login_required
def members_list():
 q=request.args.get('q',''); qry=Member.query.filter(Member.full_name.ilike(f"%{q}%")) if q else Member.query
 all_m=qry.order_by(Member.full_name).all(); rows=''.join([f"<tr><td>{m.full_name}</td><td>{m.phone or ''}</td><td>{m.zone or ''}</td><td><a href='/members/{m.id}/edit'>Edit</a> | <a href='/members/{m.id}/delete'>Del</a></td></tr>" for m in all_m])
 return page(f'<div class="card"><h3>Members ({len(all_m)})</h3><form method="GET"><input name="q" value="{q}" placeholder="Search"><button class="btn">Go</button></form><br><a class="btn" href="/members/new">+ Add</a><table><tr><th>Name</th><th>Phone</th><th>Zone</th><th>Act</th></tr>{rows}</table></div>')

@app.route('/members/new', methods=['GET','POST'])
@app.route('/members/<int:id>/edit', methods=['GET','POST'])
@login_required
def member_form(id=None):
 m=Member.query.get(id) if id else None
 if request.method=='POST':
  if not m: m=Member(); db.session.add(m)
  m.full_name=request.form['full_name']; m.gender=request.form['gender']; m.phone=request.form['phone']; m.zone=request.form['zone']; m.status=request.form['status']
  b=request.form.get('birthday'); 
  try: m.birthday=date.fromisoformat(b) if b else None
  except: m.birthday=None
  db.session.commit(); return redirect(url_for('members_list'))
 fn=m.full_name if m else ''; ph=m.phone if m else ''; zn=m.zone if m else ''; bd=m.birthday.isoformat() if m and m.birthday else ''
 return page(f'<div class="card"><h3>Member</h3><form method="POST"><label>Name</label><input name="full_name" value="{fn}" required><label>Gender</label><select name="gender"><option>Male</option><option>Female</option></select><label>Phone</label><input name="phone" value="{ph}"><label>Zone</label><input name="zone" value="{zn}"><label>Birthday</label><input type="date" name="birthday" value="{bd}"><label>Status</label><select name="status"><option>Active</option><option>Inactive</option></select><br><br><button class="btn">Save</button></form></div>')

@app.route('/members/<int:id>/delete')
@login_required
def member_delete(id): db.session.delete(Member.query.get_or_404(id)); db.session.commit(); return redirect(url_for('members_list'))

@app.route('/events')
@login_required
def events_list():
 ev=Event.query.order_by(Event.event_date.desc()).all(); rows=''.join([f"<tr><td>{e.title}</td><td>{e.event_date.strftime('%Y-%m-%d')}</td><td><a href='/attendance?event={e.id}'>Take</a> | <a href='/events/{e.id}/delete'>Del</a></td></tr>" for e in ev])
 return page(f'<div class="card"><h3>Events</h3><a class="btn" href="/events/new">+ New</a><table><tr><th>Title</th><th>Date</th><th>Act</th></tr>{rows}</table></div>')

@app.route('/events/new', methods=['GET','POST'])
@login_required
def event_new():
 if request.method=='POST':
  e=Event(title=request.form['title'], event_date=datetime.fromisoformat(request.form['event_date']), location=request.form['location']); db.session.add(e); db.session.commit(); return redirect(url_for('events_list'))
 return page('<div class="card"><h3>New Event</h3><form method="POST"><label>Title</label><input name="title" required><label>Date</label><input type="datetime-local" name="event_date" required><label>Location</label><input name="location"><br><br><button class="btn">Create</button></form></div>')

@app.route('/events/<int:id>/delete')
@login_required
def event_delete(id): db.session.delete(Event.query.get_or_404(id)); db.session.commit(); return redirect(url_for('events_list'))

@app.route('/attendance')
@login_required
def attendance_page():
 eid=request.args.get('event', type=int); ev=Event.query.get(eid) if eid else Event.query.order_by(Event.event_date.desc()).first()
 if not ev: return page('<div class="card"><h3>No events</h3><a class="btn" href="/events/new">+ Event</a></div>')
 all_ev=Event.query.order_by(Event.event_date.desc()).all(); members=Member.query.filter_by(status='Active').order_by(Member.full_name).all()
 attended=set([a.member_id for a in ev.attendances]); opts=''.join([f"<option value='{e.id}' {'selected' if e.id==ev.id else ''}>{e.title}</option>" for e in all_ev])
 rows=''.join([f"<tr><td>{m.full_name}</td><td><input type='checkbox' name='member_{m.id}' {'checked' if m.id in attended else ''}></td></tr>" for m in members])
 return page(f'<div class="card"><h3>Attendance - {ev.title}</h3><form method="GET"><select name="event" onchange="this.form.submit()">{opts}</select></form><form method="POST" action="/attendance/mark"><input type="hidden" name="event_id" value="{ev.id}"><table><tr><th>Member</th><th>Present</th></tr>{rows}</table><br><button class="btn">Save</button></form></div>')

@app.route('/attendance/mark', methods=['POST'])
@login_required
def mark_attendance():
 eid=int(request.form['event_id']); Attendance.query.filter_by(event_id=eid).delete()
 for m in Member.query.all():
  if request.form.get(f'member_{m.id}'): db.session.add(Attendance(event_id=eid, member_id=m.id))
 db.session.commit(); return redirect(url_for('attendance_page', event=eid))

with app.app_context():
 db.create_all()
 if not User.query.first():
  admin=User(username='admin'); admin.set_password('admin123'); db.session.add(admin); db.session.commit()

if __name__=='__main__':
 app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
