import os
from datetime import date, datetime, timedelta
import io, csv, json
from flask import Flask, request, redirect, url_for, render_template_string, make_response, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY','presby-yaf-pro-2026')
db_url = os.environ.get('DATABASE_URL','')
if db_url.startswith('postgres://'): db_url=db_url.replace('postgres://','postgresql://',1)
app.config['SQLALCHEMY_DATABASE_URI']=db_url or 'sqlite:///yaf.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']=False
app.config['CONG_NAME']=os.environ.get('CONG_NAME','Presbyterian Church of Ghana - YAF')
app.config['CONG_MOTTO']=os.environ.get('CONG_MOTTO','Friendship, Fellowship & Impact')
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
 email=db.Column(db.String(100))
 zone=db.Column(db.String(50))
 birthday=db.Column(db.Date, nullable=True)
 anniversary=db.Column(db.Date, nullable=True)
 status=db.Column(db.String(20), default='Active')
 occupation=db.Column(db.String(80))
 date_joined=db.Column(db.DateTime, default=datetime.utcnow)
 photo_url=db.Column(db.String(300))

class Event(db.Model):
 id=db.Column(db.Integer, primary_key=True)
 title=db.Column(db.String(150), nullable=False)
 event_date=db.Column(db.DateTime, nullable=False)
 location=db.Column(db.String(120))
 description=db.Column(db.Text)
 type=db.Column(db.String(30), default='Meeting')

class Attendance(db.Model):
 id=db.Column(db.Integer, primary_key=True)
 event_id=db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
 member_id=db.Column(db.Integer, db.ForeignKey('member.id'), nullable=False)
 timestamp=db.Column(db.DateTime, default=datetime.utcnow)
 event=db.relationship('Event', backref='attendances')
 member=db.relationship('Member', backref='attendances')

class Executive(db.Model):
 id=db.Column(db.Integer, primary_key=True)
 position=db.Column(db.String(80), nullable=False)
 member_id=db.Column(db.Integer, db.ForeignKey('member.id'))
 year=db.Column(db.String(20), default='2025/2026')
 photo_url=db.Column(db.String(300))
 phone=db.Column(db.String(20))
 member=db.relationship('Member')

class Announcement(db.Model):
 id=db.Column(db.Integer, primary_key=True)
 title=db.Column(db.String(150), nullable=False)
 content=db.Column(db.Text, nullable=False)
 date_posted=db.Column(db.DateTime, default=datetime.utcnow)
 posted_by=db.Column(db.String(80))

class Contribution(db.Model):
 id=db.Column(db.Integer, primary_key=True)
 member_id=db.Column(db.Integer, db.ForeignKey('member.id'), nullable=False)
 amount=db.Column(db.Float, nullable=False)
 purpose=db.Column(db.String(80), default='Dues')
 date_paid=db.Column(db.Date, default=date.today)
 member=db.relationship('Member', backref='contributions')

class PrayerRequest(db.Model):
 id=db.Column(db.Integer, primary_key=True)
 member_id=db.Column(db.Integer, db.ForeignKey('member.id'))
 request_text=db.Column(db.Text, nullable=False)
 is_private=db.Column(db.Boolean, default=True)
 status=db.Column(db.String(20), default='Pending')
 date_submitted=db.Column(db.DateTime, default=datetime.utcnow)
 member=db.relationship('Member')

@login_manager.user_loader
def load_user(uid): return User.query.get(int(uid))

BASE='''<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><title>{{CONG}}</title>
<link href="https://cdn.jsdelivr.net/npm/fullcalendar@6.1.8/index.global.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
:root{--pcg-blue:#0a1931;--pcg-gold:#d4af37}
body{font-family:system-ui,Segoe UI,sans-serif;background:#f6f7fb;margin:0}
nav{background:var(--pcg-blue);color:#fff;padding:12px 16px;display:flex;gap:8px;flex-wrap:wrap;align-items:center;position:sticky;top:0;z-index:99}
nav b{color:var(--pcg-gold)} nav a{color:#fff;text-decoration:none;padding:6px 10px;border-radius:8px;font-size:13px}
nav a:hover{background:#1a2d50}.container{max-width:1200px;margin:16px auto;padding:0 12px}
.card{background:#fff;border-radius:14px;padding:16px;margin-bottom:14px;box-shadow:0 2px 12px rgba(0,0,0,.06)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px}
.btn{background:var(--pcg-blue);color:#fff;padding:8px 14px;border-radius:8px;text-decoration:none;border:none;cursor:pointer;font-size:13px;display:inline-block}
.btn-gold{background:var(--pcg-gold);color:#000}.btn-light{background:#eef2ff;color:#0a1931}
.badge{padding:3px 8px;border-radius:12px;font-size:11px;background:#eef2ff}
input,select,textarea{width:100%;padding:9px;border:1px solid #ddd;border-radius:8px;margin-top:4px;box-sizing:border-box}
table{width:100%;border-collapse:collapse}th,td{padding:8px;border-bottom:1px solid #eee;font-size:13px;text-align:left}
.alert{background:#fff3cd;border:1px solid #ffe69c;padding:10px;border-radius:8px;margin-bottom:12px}
</style></head><body>
<nav><b>{{CONG}}</b> <small style="opacity:.8">{{MOTTO}}</small>
<a href="/dashboard">Dash</a><a href="/members">Members</a><a href="/events">Events</a><a href="/calendar">Calendar</a><a href="/attendance">Attend</a><a href="/executives">Exec</a><a href="/announcements">News</a><a href="/contributions">Dues</a><a href="/prayers">Prayers</a><a href="/analytics">Analytics</a><a href="/zones">Zones</a>
{% if current_user.is_authenticated %}<span style="margin-left:auto;font-size:12px">{{ current_user.username }}</span> <a href="/settings">Settings</a> <a href="/logout">Logout</a>{% endif %}
</nav><div class="container">__CONTENT__</div>
<script src="https://cdn.jsdelivr.net/npm/fullcalendar@6.1.8/index.global.min.js"></script>
</body></html>'''

def page(content, **kwargs):
 cong = app.config['CONG_NAME']; motto=app.config['CONG_MOTTO']
 html = BASE.replace('__CONTENT__', content).replace('{{CONG}}', cong).replace('{{MOTTO}}', motto)
 return render_template_string(html, **kwargs)

@app.route('/', methods=['GET','POST'])
@app.route('/login', methods=['GET','POST'])
def login():
 if request.method=='POST':
  u=User.query.filter_by(username=request.form['username']).first()
  if u and u.check_password(request.form['password']):
   login_user(u); return redirect(url_for('dashboard'))
 return page('''<div class="card" style="max-width:380px;margin:60px auto;text-align:center"><h3 style="color:#0a1931">Presbyterian YAF</h3><p><small>Young Adults Fellowship</small></p>
<form method="POST"><input name="username" placeholder="Username" required><input name="password" type="password" placeholder="Password" required style="margin-top:8px"><div style="margin-top:12px"><button class="btn" style="width:100%">Login</button></div></form><p><small>Default: admin / admin123</small></p></div>''')

@app.route('/logout')
def logout(): logout_user(); return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
 today=date.today(); week_later=today+timedelta(days=7)
 all_members=Member.query.all()
 birthdays=[]
 for m in all_members:
  if m.birthday:
   try:
    b_this_year = m.birthday.replace(year=today.year)
    if b_this_year < today: b_this_year = b_this_year.replace(year=today.year+1)
    if today <= b_this_year <= week_later: birthdays.append(m)
   except: pass
 total=Member.query.count(); active=Member.query.filter_by(status='Active').count()
 events=Event.query.count(); total_dues=db.session.query(db.func.sum(Contribution.amount)).scalar() or 0
 anns=Announcement.query.order_by(Announcement.date_posted.desc()).limit(3).all()
 ann_html=''.join([f"<div class='card'><b>{a.title}</b> <small>{a.date_posted.strftime('%Y-%m-%d')}</small><p>{a.content[:120]}</p><a href='https://wa.me/?text={a.title} - {a.content[:100]}' target='_blank' class='btn btn-light'>Share WhatsApp</a></div>" for a in anns])
 bday_html=''.join([f"<tr><td>{m.full_name}</td><td>{m.birthday.strftime('%d %b')}</td><td>{m.phone or ''}</td></tr>" for m in birthdays]) or "<tr><td colspan=3>No birthdays this week</td></tr>"
 return page(f'''<div class="grid">
<div class="card"><h4>Members</h4><h2>{total}</h2><small>Active: {active}</small></div>
<div class="card"><h4>Events</h4><h2>{events}</h2><a class="btn btn-light" href="/calendar">Calendar</a></div>
<div class="card"><h4>Total Dues</h4><h2>GHS {total_dues:.2f}</h2><a class="btn btn-light" href="/contributions">View</a></div>
<div class="card"><h4>Quick</h4><a class="btn" href="/members/new">+ Member</a> <a class="btn btn-gold" href="/announcements/new">+ News</a></div>
</div>
<div class="grid">
<div class="card"><h3>🎂 Birthdays This Week</h3><table><tr><th>Name</th><th>Date</th><th>Phone</th></tr>{bday_html}</table></div>
<div class="card"><h3>📢 Latest Announcements</h3>{ann_html if ann_html else '<p>No announcements</p>'}<br><a class="btn btn-light" href="/announcements">All News</a></div>
</div>
<div class="card"><h3>Zone Summary</h3><a class="btn btn-light" href="/zones">View Zones</a> <a class="btn btn-light" href="/analytics">Analytics</a> <a class="btn btn-light" href="/members/export.csv">Export CSV</a></div>''')
@app.route('/members')
@login_required
def members_list():
 q=request.args.get('q',''); zone=request.args.get('zone','')
 qry=Member.query
 if q: qry=qry.filter(Member.full_name.ilike(f"%{q}%"))
 if zone: qry=qry.filter_by(zone=zone)
 all_m=qry.order_by(Member.full_name).all()
 zones=db.session.query(Member.zone).distinct().all()
 zone_opts=''.join([f"<option value='{z[0]}' {'selected' if z[0]==zone else ''}>{z[0]}</option>" for z in zones if z[0]])
 rows=''.join([f"<tr><td>{m.full_name}</td><td>{m.phone or ''}</td><td><span class='badge'>{m.zone or ''}</span></td><td>{m.status}</td><td><a href='/members/{m.id}/edit'>Edit</a> | <a href='/members/{m.id}/delete'>Del</a> | <a href='/contributions?member={m.id}'>Dues</a></td></tr>" for m in all_m])
 return page(f'''<div class="card"><h3>Members ({len(all_m)})</h3>
<form method="GET" style="display:flex;gap:6px;flex-wrap:wrap"><input name="q" value="{q}" placeholder="Search name" style="flex:2"><select name="zone" style="flex:1"><option value="">All Zones</option>{zone_opts}</select><button class="btn">Filter</button></form>
<br><a class="btn" href="/members/new">+ Add Member</a> <a class="btn btn-light" href="/members/import">Import Excel</a> <a class="btn btn-light" href="/members/export.csv">Export CSV</a>
<table><tr><th>Name</th><th>Phone</th><th>Zone</th><th>Status</th><th>Action</th></tr>{rows}</table></div>''')

@app.route('/members/new', methods=['GET','POST'])
@app.route('/members/<int:id>/edit', methods=['GET','POST'])
@login_required
def member_form(id=None):
 m=Member.query.get(id) if id else None
 if request.method=='POST':
  if not m: m=Member(); db.session.add(m)
  m.full_name=request.form['full_name']; m.gender=request.form['gender']; m.phone=request.form['phone']; m.email=request.form['email']; m.zone=request.form['zone']; m.status=request.form['status']; m.occupation=request.form['occupation']; m.photo_url=request.form['photo_url']
  b=request.form.get('birthday'); a=request.form.get('anniversary')
  try: m.birthday=date.fromisoformat(b) if b else None
  except: m.birthday=None
  try: m.anniversary=date.fromisoformat(a) if a else None
  except: m.anniversary=None
  db.session.commit(); return redirect(url_for('members_list'))
 fn=m.full_name if m else ''; ph=m.phone if m else ''; em=m.email if m else ''; zn=m.zone if m else ''; oc=m.occupation if m else ''; bd=m.birthday.isoformat() if m and m.birthday else ''; an=m.anniversary.isoformat() if m and m.anniversary else ''; pu=m.photo_url if m else ''
 return page(f'''<div class="card"><h3>{'Edit' if m else 'New'} Member</h3><form method="POST" class="grid">
<div><label>Full Name</label><input name="full_name" value="{fn}" required></div>
<div><label>Gender</label><select name="gender"><option>Male</option><option {'selected' if m and m.gender=='Female' else ''}>Female</option></select></div>
<div><label>Phone</label><input name="phone" value="{ph}"></div>
<div><label>Email</label><input name="email" value="{em}"></div>
<div><label>Zone</label><input name="zone" value="{zn}" placeholder="e.g. Nkawkaw North"></div>
<div><label>Birthday</label><input type="date" name="birthday" value="{bd}"></div>
<div><label>Wedding Anniversary</label><input type="date" name="anniversary" value="{an}"></div>
<div><label>Occupation</label><input name="occupation" value="{oc}"></div>
<div><label>Status</label><select name="status"><option>Active</option><option {'selected' if m and m.status=='Inactive' else ''}>Inactive</option></select></div>
<div><label>Photo URL (optional)</label><input name="photo_url" value="{pu}" placeholder="https://"></div>
<div style="grid-column:1/-1"><button class="btn">Save Member</button> <a class="btn btn-light" href="/members">Cancel</a></div></form></div>''')

@app.route('/members/<int:id>/delete')
@login_required
def member_delete(id): db.session.delete(Member.query.get_or_404(id)); db.session.commit(); return redirect(url_for('members_list'))

@app.route('/members/import', methods=['GET','POST'])
@login_required
def members_import():
 if request.method=='POST':
  f=request.files.get('file')
  if not f: return page('<div class="card">No file</div>')
  import pandas as pd
  df=pd.read_csv(f) if f.filename.endswith('.csv') else pd.read_excel(f)
  count=0
  for _, row in df.iterrows():
   try:
    m=Member(full_name=str(row.get('full_name') or row.get('Name') or ''), phone=str(row.get('phone') or ''), zone=str(row.get('zone') or ''))
    if m.full_name: db.session.add(m); count+=1
   except: pass
  db.session.commit()
  return redirect(url_for('members_list'))
 return page('''<div class="card"><h3>Import Members</h3><p>Upload CSV or Excel with columns: full_name, phone, zone</p><form method="POST" enctype="multipart/form-data"><input type="file" name="file" required><br><br><button class="btn">Import</button></form></div>''')

@app.route('/zones')
@login_required
def zones_view():
 data=db.session.query(Member.zone, db.func.count(Member.id)).group_by(Member.zone).all()
 rows=''.join([f"<tr><td>{z or 'No Zone'}</td><td>{c}</td><td><a href='/members?zone={z}'>View</a></td></tr>" for z,c in data])
 return page(f'''<div class="card"><h3>Zones</h3><table><tr><th>Zone</th><th>Count</th><th>Action</th></tr>{rows}</table></div>''')

@app.route('/events')
@login_required
def events_list():
 ev=Event.query.order_by(Event.event_date.desc()).all()
 rows=''.join([f"<tr><td>{e.title}</td><td>{e.event_date.strftime('%Y-%m-%d %H:%M')}</td><td>{e.type}</td><td>{e.location or ''}</td><td>{len(e.attendances)}</td><td><a href='/attendance?event={e.id}'>Take</a> | <a href='/events/{e.id}/delete'>Del</a></td></tr>" for e in ev])
 return page(f'''<div class="card"><h3>Events</h3><a class="btn" href="/events/new">+ New Event</a> <a class="btn btn-light" href="/calendar">Calendar View</a><table><tr><th>Title</th><th>Date</th><th>Type</th><th>Loc</th><th>Att</th><th>Action</th></tr>{rows}</table></div>''')

@app.route('/events/new', methods=['GET','POST'])
@login_required
def event_new():
 if request.method=='POST':
  e=Event(title=request.form['title'], event_date=datetime.fromisoformat(request.form['event_date']), location=request.form['location'], description=request.form['description'], type=request.form['type'])
  db.session.add(e); db.session.commit(); return redirect(url_for('events_list'))
 return page('''<div class="card"><h3>New Event</h3><form method="POST" class="grid">
<div><label>Title</label><input name="title" required></div>
<div><label>Type</label><select name="type"><option>Meeting</option><option>Sunday Service</option><option>Revival</option><option>Outreach</option><option>Welfare</option><option>Other</option></select></div>
<div><label>Date & Time</label><input type="datetime-local" name="event_date" required></div>
<div><label>Location</label><input name="location"></div>
<div style="grid-column:1/-1"><label>Description</label><textarea name="description"></textarea></div>
<div><button class="btn">Create</button></div></form></div>''')

@app.route('/events/<int:id>/delete')
@login_required
def event_delete(id): db.session.delete(Event.query.get_or_404(id)); db.session.commit(); return redirect(url_for('events_list'))

@app.route('/calendar')
@login_required
def calendar_view():
 ev=Event.query.all()
 events_json=json.dumps([{"title": e.title, "start": e.event_date.isoformat(), "description": e.location} for e in ev])
 return page(f'''<div class="card"><h3>YAF Calendar</h3><div id="calendar"></div></div>
<script>document.addEventListener('DOMContentLoaded', function(){{ var calEl=document.getElementById('calendar'); var cal=new FullCalendar.Calendar(calEl,{{initialView:'dayGridMonth', events:{events_json}}}); cal.render(); }});</script>''')

@app.route('/attendance')
@login_required
def attendance_page():
 eid=request.args.get('event', type=int); ev=Event.query.get(eid) if eid else Event.query.order_by(Event.event_date.desc()).first()
 if not ev: return page('<div class="card"><h3>No events</h3><a class="btn" href="/events/new">+ Event</a></div>')
 all_ev=Event.query.order_by(Event.event_date.desc()).all(); members=Member.query.filter_by(status='Active').order_by(Member.full_name).all()
 attended=set([a.member_id for a in ev.attendances]); opts=''.join([f"<option value='{e.id}' {'selected' if e.id==ev.id else ''}>{e.title} - {e.event_date.strftime('%d %b')}</option>" for e in all_ev])
 rows=''.join([f"<tr><td>{m.full_name}</td><td><span class='badge'>{m.zone or ''}</span></td><td><input type='checkbox' name='member_{m.id}' {'checked' if m.id in attended else ''}></td></tr>" for m in members])
 return page(f'''<div class="card"><h3>Attendance - {ev.title} ({ev.event_date.strftime('%Y-%m-%d')})</h3>
<form method="GET"><select name="event" onchange="this.form.submit()">{opts}</select></form>
<form method="POST" action="/attendance/mark"><input type="hidden" name="event_id" value="{ev.id}"><table><tr><th>Member</th><th>Zone</th><th>Present</th></tr>{rows}</table><br><button class="btn">Save Attendance</button> <a class="btn btn-light" href="/attendance/export?event={ev.id}">Export CSV</a></form></div>''')

@app.route('/attendance/mark', methods=['POST'])
@login_required
def mark_attendance():
 eid=int(request.form['event_id']); Attendance.query.filter_by(event_id=eid).delete()
 for m in Member.query.all():
  if request.form.get(f'member_{m.id}'): db.session.add(Attendance(event_id=eid, member_id=m.id))
 db.session.commit(); return redirect(url_for('attendance_page', event=eid))

@app.route('/attendance/export')
@login_required
def attendance_export():
 eid=request.args.get('event', type=int); ev=Event.query.get_or_404(eid)
 output=io.StringIO(); w=csv.writer(output); w.writerow(['Event', ev.title, ev.event_date.strftime('%Y-%m-%d')]); w.writerow(['Name','Zone','Phone','Present'])
 members=Member.query.all(); attended=set([a.member_id for a in ev.attendances])
 for m in members: w.writerow([m.full_name, m.zone, m.phone, 'Yes' if m.id in attended else 'No'])
 resp=make_response(output.getvalue()); resp.headers['Content-Disposition']=f'attachment; filename=attendance_{eid}.csv'; resp.headers['Content-Type']='text/csv'; return resp
 @app.route('/executives', methods=['GET','POST'])
@login_required
def executives_page():
 if request.method=='POST':
  ex=Executive(position=request.form['position'], member_id=int(request.form['member_id']) if request.form['member_id'] else None, year=request.form['year'], photo_url=request.form['photo_url'], phone=request.form['phone'])
  db.session.add(ex); db.session.commit(); return redirect(url_for('executives_page'))
 exs=Executive.query.all(); mems=Member.query.all()
 opts=''.join([f"<option value='{m.id}'>{m.full_name}</option>" for m in mems])
 rows=''.join([f"<tr><td>{e.position}</td><td>{e.member.full_name if e.member else ''}</td><td>{e.year}</td><td>{e.phone or ''}</td><td><a href='/executives/{e.id}/delete'>Del</a></td></tr>" for e in exs])
 return page(f'''<div class="card"><h3>YAF Executives</h3>
<form method="POST" class="grid"><div><label>Position</label><input name="position" placeholder="e.g. President" required></div>
<div><label>Member</label><select name="member_id"><option value="">-- Select --</option>{opts}</select></div>
<div><label>Year</label><input name="year" value="2025/2026"></div>
<div><label>Phone</label><input name="phone"></div>
<div><label>Photo URL</label><input name="photo_url" placeholder="https://"></div>
<div><button class="btn">Add Executive</button></div></form>
<table><tr><th>Position</th><th>Name</th><th>Year</th><th>Phone</th><th>Action</th></tr>{rows}</table></div>''')

@app.route('/executives/<int:id>/delete')
@login_required
def exec_delete(id): db.session.delete(Executive.query.get_or_404(id)); db.session.commit(); return redirect(url_for('executives_page'))

@app.route('/announcements')
@login_required
def announcements_page():
 anns=Announcement.query.order_by(Announcement.date_posted.desc()).all()
 cards=''.join([f"<div class='card'><h3>{a.title}</h3><small>{a.date_posted.strftime('%Y-%m-%d')} by {a.posted_by or 'Admin'}</small><p>{a.content}</p><a href='https://wa.me/?text=*{a.title}*%0A{a.content}%0A%0AFrom YAF' target='_blank' class='btn btn-gold'>Share to WhatsApp</a> <a href='/announcements/{a.id}/delete' class='btn btn-light'>Delete</a></div>" for a in anns])
 return page(f'''<div class="card"><h3>Announcements</h3><a class="btn" href="/announcements/new">+ New Announcement</a></div>{cards}''')

@app.route('/announcements/new', methods=['GET','POST'])
@login_required
def ann_new():
 if request.method=='POST':
  db.session.add(Announcement(title=request.form['title'], content=request.form['content'], posted_by=current_user.username)); db.session.commit(); return redirect(url_for('announcements_page'))
 return page('''<div class="card"><h3>New Announcement</h3><form method="POST"><label>Title</label><input name="title" required><label>Content</label><textarea name="content" rows="6" required></textarea><br><button class="btn">Post & Enable WhatsApp Share</button></form></div>''')

@app.route('/announcements/<int:id>/delete')
@login_required
def ann_delete(id): db.session.delete(Announcement.query.get_or_404(id)); db.session.commit(); return redirect(url_for('announcements_page'))

@app.route('/contributions')
@login_required
def contributions_page():
 member_id=request.args.get('member', type=int)
 qry=Contribution.query
 if member_id: qry=qry.filter_by(member_id=member_id)
 all_c=qry.order_by(Contribution.date_paid.desc()).all()
 members=Member.query.all(); m_opts=''.join([f"<option value='{m.id}' {'selected' if m.id==member_id else ''}>{m.full_name}</option>" for m in members])
 rows=''.join([f"<tr><td>{c.member.full_name if c.member else ''}</td><td>{c.purpose}</td><td>GHS {c.amount:.2f}</td><td>{c.date_paid}</td><td><a href='/contributions/{c.id}/delete'>Del</a></td></tr>" for c in all_c])
 total=db.session.query(db.func.sum(Contribution.amount)).scalar() or 0
 return page(f'''<div class="card"><h3>Dues & Contributions - Total: GHS {total:.2f}</h3>
<form method="POST" action="/contributions/add" class="grid"><div><label>Member</label><select name="member_id" required>{m_opts}</select></div>
<div><label>Amount (GHS)</label><input type="number" step="0.01" name="amount" required></div>
<div><label>Purpose</label><select name="purpose"><option>Dues</option><option>Welfare</option><option>Special Offering</option><option>Project</option></select></div>
<div><label>Date</label><input type="date" name="date_paid" value="{date.today().isoformat()}"></div>
<div><button class="btn">Add Payment</button></div></form></div>
<div class="card"><form method="GET"><select name="member"><option value="">All Members</option>{m_opts}</select> <button class="btn btn-light">Filter</button></form>
<table><tr><th>Member</th><th>Purpose</th><th>Amount</th><th>Date</th><th>Action</th></tr>{rows}</table></div>''')

@app.route('/contributions/add', methods=['POST'])
@login_required
def contrib_add():
 c=Contribution(member_id=int(request.form['member_id']), amount=float(request.form['amount']), purpose=request.form['purpose'], date_paid=date.fromisoformat(request.form['date_paid']) if request.form['date_paid'] else date.today())
 db.session.add(c); db.session.commit(); return redirect(url_for('contributions_page'))

@app.route('/contributions/<int:id>/delete')
@login_required
def contrib_delete(id): db.session.delete(Contribution.query.get_or_404(id)); db.session.commit(); return redirect(url_for('contributions_page'))

@app.route('/prayers', methods=['GET','POST'])
@login_required
def prayers_page():
 if request.method=='POST':
  p=PrayerRequest(member_id=int(request.form['member_id']) if request.form['member_id'] else None, request_text=request.form['request_text'], is_private=bool(request.form.get('is_private')))
  db.session.add(p); db.session.commit(); return redirect(url_for('prayers_page'))
 prs=PrayerRequest.query.order_by(PrayerRequest.date_submitted.desc()).all()
 mems=Member.query.all(); opts=''.join([f"<option value='{m.id}'>{m.full_name}</option>" for m in mems])
 rows=''.join([f"<tr><td>{p.member.full_name if p.member else 'Anonymous'}</td><td>{p.request_text[:80]}</td><td>{'Private' if p.is_private else 'Public'}</td><td>{p.status}</td><td>{p.date_submitted.strftime('%Y-%m-%d')}</td><td><a href='/prayers/{p.id}/done'>Mark Done</a> | <a href='/prayers/{p.id}/delete'>Del</a></td></tr>" for p in prs])
 return page(f'''<div class="card"><h3>Prayer Requests & Welfare Needs</h3>
<form method="POST" class="grid"><div><label>Member (optional)</label><select name="member_id"><option value="">Anonymous</option>{opts}</select></div>
<div style="grid-column:1/-1"><label>Request</label><textarea name="request_text" required placeholder="e.g. Pray for healing, welfare support needed"></textarea></div>
<div><label><input type="checkbox" name="is_private" checked> Private (executives only)</label></div><div><button class="btn">Submit Request</button></div></form></div>
<div class="card"><table><tr><th>Member</th><th>Request</th><th>Type</th><th>Status</th><th>Date</th><th>Action</th></tr>{rows}</table></div>''')

@app.route('/prayers/<int:id>/done')
@login_required
def prayer_done(id): p=PrayerRequest.query.get_or_404(id); p.status='Done'; db.session.commit(); return redirect(url_for('prayers_page'))

@app.route('/prayers/<int:id>/delete')
@login_required
def prayer_delete(id): db.session.delete(PrayerRequest.query.get_or_404(id)); db.session.commit(); return redirect(url_for('prayers_page'))

@app.route('/analytics')
@login_required
def analytics_page():
 total=Member.query.count(); active=Member.query.filter_by(status='Active').count(); male=Member.query.filter_by(gender='Male').count(); female=Member.query.filter_by(gender='Female').count()
 zone_data=db.session.query(Member.zone, db.func.count(Member.id)).group_by(Member.zone).all()
 zone_labels=json.dumps([z[0] or 'No Zone' for z in zone_data]); zone_counts=json.dumps([z[1] for z in zone_data])
 attendance_data=db.session.query(Event.title, db.func.count(Attendance.id)).outerjoin(Attendance).group_by(Event.id).all()
 att_labels=json.dumps([a[0] for a in attendance_data]); att_counts=json.dumps([a[1] for a in attendance_data])
 return page(f'''<div class="card"><h3>YAF Analytics Dashboard</h3></div>
<div class="grid">
<div class="card"><h4>Members Overview</h4><canvas id="genderChart"></canvas></div>
<div class="card"><h4>Zone Distribution</h4><canvas id="zoneChart"></canvas></div>
<div class="card"><h4>Event Attendance</h4><canvas id="attChart"></canvas></div>
<div class="card"><h4>Stats</h4><p>Total: {total}<br>Active: {active}<br>Male: {male}<br>Female: {female}</p><a class="btn" href="/members/export.csv">Export Members CSV</a> <a class="btn btn-light" href="/attendance">Attendance Report</a></div>
</div>
<script>
new Chart(document.getElementById('genderChart'), {{type:'doughnut', data:{{labels:['Male','Female'], datasets:[{{data:[{male},{female}], backgroundColor:['#0a1931','#d4af37']}}]}}}});
new Chart(document.getElementById('zoneChart'), {{type:'bar', data:{{labels:{zone_labels}, datasets:[{{label:'Members', data:{zone_counts}, backgroundColor:'#0a1931'}}]}}}});
new Chart(document.getElementById('attChart'), {{type:'bar', data:{{labels:{att_labels}, datasets:[{{label:'Attendance', data:{att_counts}, backgroundColor:'#d4af37'}}]}}}});
</script>''')

@app.route('/members/export.csv')
@login_required
def export_csv():
 output=io.StringIO(); w=csv.writer(output); w.writerow(['Full Name','Gender','Phone','Email','Zone','Birthday','Status','Occupation','Date Joined'])
 for m in Member.query.all(): w.writerow([m.full_name, m.gender, m.phone, m.email, m.zone, m.birthday, m.status, m.occupation, m.date_joined])
 resp=make_response(output.getvalue()); resp.headers['Content-Disposition']='attachment; filename=yaf_members.csv'; resp.headers['Content-Type']='text/csv'; return resp

@app.route('/settings', methods=['GET','POST'])
@login_required
def settings_page():
 if request.method=='POST':
  if request.form.get('new_password'):
   current_user.set_password(request.form['new_password']); db.session.commit()
  if request.form.get('cong_name'):
   app.config['CONG_NAME']=request.form['cong_name']; app.config['CONG_MOTTO']=request.form['motto']
 return page(f'''<div class="card"><h3>Settings</h3>
<form method="POST"><h4>Change Password</h4><input name="new_password" type="password" placeholder="New password" required><br><br><button class="btn">Change Password</button></form>
<hr><form method="POST"><h4>Branding</h4><label>Congregation Name</label><input name="cong_name" value="{app.config['CONG_NAME']}"><label>Motto</label><input name="motto" value="{app.config['CONG_MOTTO']}"><br><br><button class="btn btn-light">Update Branding</button></form>
<p><small>To make permanent, go to Render dashboard > Environment > Add CONG_NAME and CONG_MOTTO</small></p></div>''')

with app.app_context():
 db.create_all()
 if not User.query.first():
  admin=User(username='admin'); admin.set_password('admin123'); db.session.add(admin); db.session.commit()

if __name__=='__main__':
 app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)))