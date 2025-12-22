from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import extract
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt

app = Flask(__name__)

# CONFIGURACIÓN DE LA BASE DE DATOS
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///finanzas_estudiante.db' 
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'una_clave_secreta_muy_dificil'

# Inicializamos la base de datos
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# MODELOS
# --- MODELO DE USUARIO (NUEVO) ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=False)
    # Relación: Un usuario tiene muchas transacciones
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
        password = request.form['password']
        
        # Encriptamos la contraseña
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        # Creamos el usuario
        nuevo_usuario = User(username=username, password=hashed_password)
        try:
            db.session.add(nuevo_usuario)
            db.session.commit()
            return redirect(url_for('login'))
        except:
            return "El nombre de usuario ya existe"
            
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and bcrypt.check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('home'))
        else:
            return "Usuario o contraseña incorrectos"
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def home():
    # Obtenemos fecha actual para filtrar el mes
    hoy = datetime.today()
    
    # Filtramos las transacciones de ESTE mes y ESTE año
    transacciones = Transaccion.query.filter(
        Transaccion.user_id == current_user.id,
        extract('month', Transaccion.fecha) == hoy.month,
        extract('year', Transaccion.fecha) == hoy.year
    ).order_by(Transaccion.fecha.desc()).all()

    # Calculamos los totales matemáticamente
    total_ingresos = sum(t.monto for t in transacciones if t.tipo == 'ingreso')
    total_gastos = sum(t.monto for t in transacciones if t.tipo == 'gasto')
    saldo = total_ingresos - total_gastos

    # Formateamos el nombre del mes (truco rápido)
    nombres_meses = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    nombre_mes = names_meses = nombres_meses[hoy.month]

    return render_template('index.html', 
                           transacciones=transacciones, 
                           ingresos=total_ingresos, 
                           gastos=total_gastos, 
                           saldo=saldo,
                           mes=nombre_mes,
                           usuario=current_user.username)

@app.route('/agregar', methods=['POST'])
def agregar():
    descripcion = request.form['descripcion']
    monto = float(request.form['monto'])
    categoria = request.form['categoria']
    tipo = request.form['tipo'] 

    nova_transaccion = Transaccion(
        descripcion=descripcion, 
        monto=monto, 
        categoria=categoria, 
        tipo=tipo,
        user_id=current_user.id
    )

    db.session.add(nova_transaccion)
    db.session.commit()
    return redirect(url_for('home'))

@app.route('/delete/<int:id>')
def delete(id):
    item = Transaccion.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    return redirect(url_for('home'))

with app.app_context():
        db.create_all()
if __name__ == '__main__':
    app.run(debug=True)