from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import extract, desc
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
import csv
from io import StringIO
from flask import make_response
import os
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

# CONFIGURACIÓN DE LA BASE DE DATOS
database_url = os.environ.get('DATABASE_URL') 

if database_url:
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///finanzas_estudiante.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'clave_secreta_super_segura'
app.config['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID')
app.config['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET')

oauth = OAuth(app)

google = oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),     
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# Inicializamos la base de datos
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# MODELOS
# --- MODELO DE USUARIO (NUEVO) ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    email = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=True)
    transacciones = db.relationship('Transaccion', backref='dueno', lazy=True)

# --- MODELO DE TRANSACCIÓN (MODIFICADO) ---
class Transaccion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, default=datetime.utcnow)
    descripcion = db.Column(db.String(100), nullable=False)
    monto = db.Column(db.Float, nullable=False)
    categoria = db.Column(db.String(50), nullable=False)
    tipo = db.Column(db.String(10), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


# Función para cargar usuario
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email'] 
        password = request.form['password']
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        if User.query.filter_by(username=username).first():
            return render_template('register.html', error="⚠️ El usuario ya existe.")

        if User.query.filter_by(email=email).first():
            return render_template('register.html', error="⚠️ Ese email ya está registrado.")

        nuevo_usuario = User(username=username, email=email, password=hashed_password)
        db.session.add(nuevo_usuario)
        db.session.commit()
        return redirect(url_for('login'))
            
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and bcrypt.check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('home'))
        else:
            return render_template('login.html', error="Usuario o contraseña incorrectos")
    return render_template('login.html')

@app.route('/login/google')
def google_login():
    redirect_uri = url_for('authorize', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/authorize')
def authorize():
    token = google.authorize_access_token()
    resp = google.get('https://www.googleapis.com/oauth2/v3/userinfo')
    user_info = resp.json()
    
    email_google = user_info['email']
    nombre_google = user_info.get('name', email_google)

    user = User.query.filter_by(email=email_google).first()

    if not user:
        import secrets
        password_dummy = secrets.token_hex(16) 
        
        user = User(username=email_google, email=email_google, password=password_dummy)
        
        db.session.add(user)
        db.session.commit()

    login_user(user)
    return redirect(url_for('home'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def home():
    hoy = datetime.today()
    
    anio_seleccionado = request.args.get('anio', type=int, default=hoy.year)
    mes_seleccionado = request.args.get('mes', type=int, default=hoy.month)

    fechas_disponibles = db.session.query(
        extract('year', Transaccion.fecha).label('anio'),
        extract('month', Transaccion.fecha).label('mes')
    ).filter(Transaccion.user_id == current_user.id)\
     .group_by('anio', 'mes')\
     .order_by(desc('anio'), desc('mes'))\
     .all()

    transacciones = Transaccion.query.filter(
        Transaccion.user_id == current_user.id, 
        extract('month', Transaccion.fecha) == mes_seleccionado,
        extract('year', Transaccion.fecha) == anio_seleccionado
    ).order_by(Transaccion.fecha.desc()).all()

    total_ingresos = sum(t.monto for t in transacciones if t.tipo == 'ingreso')
    total_gastos = sum(t.monto for t in transacciones if t.tipo == 'gasto')
    saldo = total_ingresos - total_gastos

    datos_gastos = {} 
    for t in transacciones:
        if t.tipo == 'gasto':
            if t.categoria in datos_gastos:
                datos_gastos[t.categoria] += t.monto
            else:
                datos_gastos[t.categoria] = t.monto
    
    labels_grafico = list(datos_gastos.keys())
    values_grafico = list(datos_gastos.values())

    nombres_meses = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

    return render_template('index.html', 
                           transacciones=transacciones, 
                           ingresos=total_ingresos, 
                           gastos=total_gastos, 
                           saldo=saldo,
                           mes_nombre=nombres_meses[mes_seleccionado], 
                           anio_actual=anio_seleccionado,
                           mes_actual=mes_seleccionado,
                           fechas_menu=fechas_disponibles,
                           nombres_meses=nombres_meses,
                           usuario=current_user.username,
                           labels_grafico=labels_grafico,
                           values_grafico=values_grafico)


@app.route('/agregar', methods=['POST'])
@login_required
def agregar():
    # ... (Igual que antes) ...
    descripcion = request.form['descripcion']
    monto = float(request.form['monto'])
    categoria = request.form['categoria']
    tipo = request.form['tipo']

    nova_transaccion = Transaccion(
        descripcion=descripcion, monto=monto, categoria=categoria, tipo=tipo, user_id=current_user.id
    )
    db.session.add(nova_transaccion)
    db.session.commit()
    return redirect(url_for('home'))

@app.route('/delete/<int:id>')
@login_required
def delete(id):
    item = Transaccion.query.get_or_404(id)
    if item.user_id == current_user.id:
        db.session.delete(item)
        db.session.commit()
    return redirect(url_for('home'))

@app.route('/descargar_reporte')
@login_required
def descargar_reporte():
    hoy = datetime.today()
    anio = request.args.get('anio', type=int, default=hoy.year)
    mes = request.args.get('mes', type=int, default=hoy.month)

    transacciones = Transaccion.query.filter(
        Transaccion.user_id == current_user.id, 
        extract('month', Transaccion.fecha) == mes,
        extract('year', Transaccion.fecha) == anio
    ).order_by(Transaccion.fecha.desc()).all()

    si = StringIO()
    cw = csv.writer(si)
        
    cw.writerow(['Fecha', 'Tipo', 'Categoria', 'Descripcion', 'Monto'])

    for t in transacciones:
        cw.writerow([
            t.fecha.strftime('%d/%m/%Y'),
            t.tipo,
            t.categoria,
            t.descripcion,
            t.monto
        ])

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename=reporte_{mes}_{anio}.csv"
    output.headers["Content-type"] = "text/csv"
    
    return output

with app.app_context():
        db.create_all()
if __name__ == '__main__':
    app.run(debug=True)