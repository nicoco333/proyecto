from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

# CONFIGURACIÓN DE LA BASE DE DATOS
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gastos.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializamos la base de datos
db = SQLAlchemy(app)

# MODELO
# Tabla de'Gasto'
class Gasto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, default=datetime.utcnow)
    descripcion = db.Column(db.String(100), nullable=False)
    monto = db.Column(db.Float, nullable=False)
    categoria = db.Column(db.String(50), nullable=False)

@app.route('/')
def home():
    # 1. Consultamos TODOS los gastos de la base de datos
    todos_los_gastos = Gasto.query.order_by(Gasto.fecha.desc()).all()
    # 2. Se los enviamos al HTML en la variable 'gastos'
    return render_template('index.html', gastos=todos_los_gastos)

@app.route('/agregar', methods=['POST'])
def agregar():
    # 1. Obtenemos los datos del formulario HTML
    descripcion = request.form['descripcion']
    monto = request.form['monto']
    categoria = request.form['categoria']

    # 2. Creamos un nuevo objeto Gasto (preparamos la fila para la DB)
    nuevo_gasto = Gasto(descripcion=descripcion, monto=float(monto), categoria=categoria)

    # 3. Guardamos en la Base de Datos
    db.session.add(nuevo_gasto)
    db.session.commit()  # ¡Importante! Sin commit no se guardan los cambios

    # 4. Volvemos a la página principal
    return redirect(url_for('home'))

@app.route('/delete/<int:id>')
def delete(id):
    # 1. Buscamos el gasto por su ID. Si no existe, da error 404
    gasto_a_borrar = Gasto.query.get_or_404(id)
    
    # 2. Lo borramos de la DB
    db.session.delete(gasto_a_borrar)
    db.session.commit()
    
    # 3. Volvemos a la lista
    return redirect(url_for('home'))

with app.app_context():
        db.create_all()
if __name__ == '__main__':
    app.run(debug=True)