from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import extract

app = Flask(__name__)

# CONFIGURACIÓN DE LA BASE DE DATOS
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///finanzas_estudiante.db' 
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializamos la base de datos
db = SQLAlchemy(app)

# MODELO
# Tabla de'Transaccion'
class Transaccion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, default=datetime.utcnow)
    descripcion = db.Column(db.String(100), nullable=False)
    monto = db.Column(db.Float, nullable=False)
    categoria = db.Column(db.String(50), nullable=False)
    tipo = db.Column(db.String(10), nullable=False) 

@app.route('/')
def home():
    # Obtenemos fecha actual para filtrar el mes
    hoy = datetime.today()
    
    # Filtramos las transacciones de ESTE mes y ESTE año
    transacciones = Transaccion.query.filter(
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
                           mes=nombre_mes)

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
        tipo=tipo
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