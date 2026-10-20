"""Production-oriented Flask application intake and restricted admin dashboard."""
import os, re, sqlite3, secrets, smtplib, ssl, time, logging
from datetime import datetime, timezone, timedelta
from email.message import EmailMessage
from functools import wraps
from pathlib import Path
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, abort, make_response
from flask_cors import CORS
from werkzeug.security import check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix

ROOT=Path(__file__).resolve().parent
SERVICES={'strategy':'Стратегия и управление','analytics':'Продукты и бизнес-аналитика','human':'Бизнес-психоаналитическое консультирование','legal':'Корпоративное право','marketing':'Маркетинг и коммуникации','unsure':'Не определено'}
STATUSES={'new':'Новое','in_progress':'В работе','closed':'Закрыто'}

def create_app(test_config=None):
 app=Flask(__name__,template_folder='templates',static_folder='../',static_url_path='/site')
 app.config.update(SECRET_KEY=os.environ.get('SECRET_KEY',''),DATABASE=os.environ.get('DATABASE',str(ROOT/'data'/'requests.sqlite3')),ADMIN_USERNAME=os.environ.get('ADMIN_USERNAME','admin'),ADMIN_PASSWORD_HASH=os.environ.get('ADMIN_PASSWORD_HASH',''),API_ORIGIN=os.environ.get('API_ORIGIN',''),COOKIE_SECURE=os.environ.get('COOKIE_SECURE','1')!='0',SMTP_HOST=os.environ.get('SMTP_HOST',''),SMTP_PORT=int(os.environ.get('SMTP_PORT','587')),SMTP_USER=os.environ.get('SMTP_USER',''),SMTP_PASSWORD=os.environ.get('SMTP_PASSWORD',''),SMTP_FROM=os.environ.get('SMTP_FROM',''),NOTIFY_EMAIL=os.environ.get('NOTIFY_EMAIL',''),RATELIMIT_WINDOW=3600,RATELIMIT_MAX=5)
 if test_config:app.config.update(test_config)
 if not app.config['SECRET_KEY'] or not app.config['ADMIN_PASSWORD_HASH']:
  raise RuntimeError('Set SECRET_KEY and ADMIN_PASSWORD_HASH before starting the server')
 app.config.update(SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Lax',SESSION_COOKIE_SECURE=app.config['COOKIE_SECURE'],PERMANENT_SESSION_LIFETIME=timedelta(hours=8),MAX_CONTENT_LENGTH=12*1024)
 app.wsgi_app=ProxyFix(app.wsgi_app,x_for=1,x_proto=1,x_host=1)
 if app.config['API_ORIGIN']:
  CORS(app,resources={r'/api/applications':{'origins':[app.config['API_ORIGIN']]}},methods=['POST','OPTIONS'],allow_headers=['Content-Type'])
 db_path=Path(app.config['DATABASE']);db_path.parent.mkdir(parents=True,exist_ok=True)
 def db():
  conn=sqlite3.connect(db_path,timeout=15);conn.row_factory=sqlite3.Row;return conn
 with db() as conn:
  conn.execute('CREATE TABLE IF NOT EXISTS applications(id INTEGER PRIMARY KEY AUTOINCREMENT, reference TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL, name TEXT NOT NULL, email TEXT NOT NULL, service TEXT NOT NULL, message TEXT NOT NULL, status TEXT NOT NULL DEFAULT "new", notified INTEGER NOT NULL DEFAULT 0)')
  conn.execute('CREATE TABLE IF NOT EXISTS attempts(id INTEGER PRIMARY KEY AUTOINCREMENT, ip_hash TEXT NOT NULL, created_at INTEGER NOT NULL)')
  conn.execute('CREATE INDEX IF NOT EXISTS idx_attempts_ip_time ON attempts(ip_hash,created_at)')
 def no_store(resp):resp.headers['Cache-Control']='no-store';resp.headers['X-Content-Type-Options']='nosniff';resp.headers['X-Frame-Options']='DENY';return resp
 @app.after_request
 def security_headers(resp):
  resp=no_store(resp)
  if request.path.startswith('/admin'):
   resp.headers['Content-Security-Policy']="default-src 'self'; style-src 'self' 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; base-uri 'self'"
  return resp
 def csrf_token():
  if '_csrf' not in session:session['_csrf']=secrets.token_urlsafe(32)
  return session['_csrf']
 app.jinja_env.globals['csrf_token']=csrf_token
 def check_csrf():
  if not secrets.compare_digest(str(session.get('_csrf','')),str(request.form.get('csrf_token',''))) or not session.get('_csrf'):abort(400)
 def admin_required(fn):
  @wraps(fn)
  def wrapped(*args,**kwargs):
   if not session.get('admin'):return redirect(url_for('admin_login'))
   return fn(*args,**kwargs)
  return wrapped
 def send_notice(item):
  cfg=app.config
  if not all(cfg[x] for x in ('SMTP_HOST','SMTP_FROM','NOTIFY_EMAIL')):return False
  msg=EmailMessage();msg['Subject']=f'Новая заявка {item["reference"]} — Щербинины';msg['From']=cfg['SMTP_FROM'];msg['To']=cfg['NOTIFY_EMAIL'];msg['Reply-To']=item['email']
  msg.set_content(f'Заявка: {item["reference"]}\nИмя: {item["name"]}\nEmail: {item["email"]}\nНаправление: {SERVICES[item["service"]]}\n\n{item["message"]}\n\nПроверьте административную панель.')
  try:
   with smtplib.SMTP(cfg['SMTP_HOST'],cfg['SMTP_PORT'],timeout=12) as smtp:
    smtp.ehlo();smtp.starttls(context=ssl.create_default_context());smtp.ehlo()
    if cfg['SMTP_USER']:smtp.login(cfg['SMTP_USER'],cfg['SMTP_PASSWORD'])
    smtp.send_message(msg)
   return True
  except Exception:
   app.logger.exception('SMTP notification failed for %s',item['reference']);return False
 @app.post('/api/applications')
 def application_create():
  if request.mimetype!='application/json':return jsonify(error='Ожидается JSON'),415
  data=request.get_json(silent=True)
  if not isinstance(data,dict):return jsonify(error='Некорректный запрос'),400
  if data.get('website'):return jsonify(reference='ACCEPTED'),201 # honeypot
  name=str(data.get('name','')).strip();email=str(data.get('email','')).strip();service=str(data.get('service','unsure'));message=str(data.get('message','')).strip()
  if not (2<=len(name)<=100 and re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email) and len(email)<=150 and service in SERVICES and 15<=len(message)<=2500 and data.get('consent') in (True,'true','on')):
   return jsonify(error='Проверьте имя, email, направление, описание задачи и согласие'),400
  import hashlib
  iphash=hashlib.sha256((request.remote_addr or 'unknown').encode()+app.config['SECRET_KEY'].encode()).hexdigest();now=int(time.time())
  with db() as conn:
   conn.execute('DELETE FROM attempts WHERE created_at < ?',(now-86400,))
   count=conn.execute('SELECT COUNT(*) FROM attempts WHERE ip_hash=? AND created_at>=?',(iphash,now-app.config['RATELIMIT_WINDOW'])).fetchone()[0]
   if count>=app.config['RATELIMIT_MAX']:return jsonify(error='Слишком много обращений. Попробуйте позже.'),429
   conn.execute('INSERT INTO attempts(ip_hash,created_at) VALUES(?,?)',(iphash,now))
   ref='FCG-'+datetime.now(timezone.utc).strftime('%y%m%d')+'-'+secrets.token_hex(3).upper()
   item=dict(reference=ref,name=name,email=email,service=service,message=message)
   conn.execute('INSERT INTO applications(reference,created_at,name,email,service,message) VALUES(?,?,?,?,?,?)',(ref,datetime.now(timezone.utc).isoformat(),name,email,service,message))
  notified=send_notice(item)
  if notified:
   with db() as conn:conn.execute('UPDATE applications SET notified=1 WHERE reference=?',(ref,))
  return jsonify(reference=ref),201
 @app.get('/health')
 def health():return jsonify(status='ok')
 @app.route('/admin/login',methods=['GET','POST'])
 def admin_login():
  error=None
  if request.method=='POST':
   check_csrf()
   username=request.form.get('username','');password=request.form.get('password','')
   import hashlib
   login_key='login:'+hashlib.sha256(((request.remote_addr or 'unknown')+app.config['SECRET_KEY']).encode()).hexdigest()
   with db() as conn:
    now=int(time.time())
    failures=conn.execute('SELECT COUNT(*) FROM attempts WHERE ip_hash=? AND created_at>?',(login_key,now-900)).fetchone()[0]
    if failures>=10:abort(429)
    conn.execute('INSERT INTO attempts(ip_hash,created_at) VALUES(?,?)',(login_key,now))
   if secrets.compare_digest(username,app.config['ADMIN_USERNAME']) and check_password_hash(app.config['ADMIN_PASSWORD_HASH'],password):
    session.clear();session['admin']=True;session.permanent=True;csrf_token();return redirect(url_for('admin_dashboard'))
   time.sleep(.4);error='Неверные учётные данные'
  return render_template('login.html',error=error)
 @app.post('/admin/logout')
 @admin_required
 def admin_logout():check_csrf();session.clear();return redirect(url_for('admin_login'))
 @app.get('/admin')
 @admin_required
 def admin_dashboard():
  status=request.args.get('status','all');status=status if status in (*STATUSES,'all') else 'all'
  with db() as conn:
   items=conn.execute('SELECT id,reference,created_at,name,email,service,status,notified FROM applications '+('WHERE status=? ' if status!='all' else '')+'ORDER BY id DESC LIMIT 200',(status,) if status!='all' else ()).fetchall()
   counts={k:conn.execute('SELECT COUNT(*) FROM applications WHERE status=?',(k,)).fetchone()[0] for k in STATUSES}
  return render_template('dashboard.html',items=items,counts=counts,status=status,services=SERVICES,statuses=STATUSES)
 @app.get('/admin/applications/<int:app_id>')
 @admin_required
 def admin_detail(app_id):
  with db() as conn:item=conn.execute('SELECT * FROM applications WHERE id=?',(app_id,)).fetchone()
  if not item:abort(404)
  return render_template('detail.html',item=item,services=SERVICES,statuses=STATUSES)
 @app.post('/admin/applications/<int:app_id>/status')
 @admin_required
 def admin_status(app_id):
  check_csrf();status=request.form.get('status')
  if status not in STATUSES:abort(400)
  with db() as conn:
   cur=conn.execute('UPDATE applications SET status=? WHERE id=?',(status,app_id))
   if not cur.rowcount:abort(404)
  return redirect(url_for('admin_detail',app_id=app_id))
 return app

if __name__=='__main__':
 create_app().run(host='127.0.0.1',port=int(os.environ.get('PORT','8000')))
