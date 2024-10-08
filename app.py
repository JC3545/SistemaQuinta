from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta'  # Cambia esto por una clave más segura

# Conexión a la base de datos SQLite
def get_db_connection():
    conn = sqlite3.connect('reservas.db')
    conn.row_factory = sqlite3.Row
    return conn

# Inicializar la base de datos
def init_db():
    conn = get_db_connection()
    conn.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, role TEXT)')
    
    # Agregar el usuario administrador por defecto (ID 1 será siempre el administrador)
    conn.execute('INSERT OR IGNORE INTO users (id, username, password, role) VALUES (?, ?, ?, ?)', (1, 'admin', 'admin_password', 'administrador'))
    
    conn.execute('CREATE TABLE IF NOT EXISTS reservas (id INTEGER PRIMARY KEY, fecha TEXT, nombre TEXT, telefono TEXT, tipo_evento TEXT, total REAL, seña REAL, fecha_seña TEXT, metodo_pago TEXT, dirigido_a TEXT, resto REAL, observaciones TEXT)')
    conn.commit()
    conn.close()

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    
    if user is None:
        flash('Usuario no encontrado. Por favor, regístrate.')
        return redirect(url_for('register'))  # Redirige a la página de registro
    
    # Verifica la contraseña
    if user['password'] != password:
        flash('Contraseña incorrecta.')
        return redirect(url_for('home'))  # Redirige al login

    # Lógica de inicio de sesión exitoso
    session['username'] = username
    session['role'] = user['role'].lower()  # Guardar el rol del usuario en la sesión

    # Redirigir a la página de reservas directamente después del login
    return redirect(url_for('reservar'))

@app.route('/admin_usuarios')
def admin_usuarios():
    if session.get('role') != 'administrador':
        flash('Acceso restringido. Solo administradores pueden acceder a esta sección.')
        return redirect(url_for('reservar'))

    # Obtener todos los usuarios de la base de datos
    conn = get_db_connection()
    usuarios = conn.execute('SELECT username, password, role FROM users').fetchall()
    conn.close()

    return render_template('admin_usuarios.html', usuarios=usuarios)

@app.route('/logout')
def logout():
    session.clear()
    flash('Has cerrado sesión exitosamente.')
    return redirect(url_for('home'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        try:
            # Todos los nuevos usuarios son colaboradores por defecto
            conn.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)', (username, password, 'colaborador'))
            conn.commit()
            flash('Usuario registrado con éxito')
            return redirect(url_for('home'))
        except sqlite3.IntegrityError:
            flash('El usuario ya existe')
        finally:
            conn.close()
    
    return render_template('register.html')

@app.route('/reservar')
def reservar():
    fechas_reservadas = ["2024-09-25", "2024-09-28", "2024-09-30"]
    username = session.get('username')  # Obtener el nombre de usuario de la sesión
    role = session.get('role')  # Obtener el rol de la sesión

    return render_template('reservar.html', fechas_reservadas=fechas_reservadas, username=username, role=role)

def actualizar_roles():
    conn = get_db_connection()
    conn.execute("UPDATE users SET role = 'colaborador' WHERE role IS NULL OR role = '';")
    conn.commit()
    conn.close()

@app.route('/check_fecha', methods=['POST'])
def check_fecha():
    fecha = request.form['fecha']
    conn = get_db_connection()
    reserva = conn.execute('SELECT * FROM reservas WHERE fecha = ?', (fecha,)).fetchone()
    conn.close()
    
    if reserva:
        flash('No disponible')
        return redirect(url_for('reservar'))
    else:
        return render_template('ingresar_cliente.html', fecha=fecha)

@app.route('/reservas')
def reservas():
    conn = get_db_connection()
    reservas = conn.execute('SELECT * FROM reservas ORDER BY fecha ASC').fetchall()
    conn.close()

    reservas_format = []
    for reserva in reservas:
        fecha = datetime.strptime(reserva['fecha'], '%Y-%m-%d').strftime('%d/%m/%Y')
        fecha_seña = datetime.strptime(reserva['fecha_seña'], '%Y-%m-%d').strftime('%d/%m/%Y') if reserva['fecha_seña'] else None
        reservas_format.append({
            'id': reserva['id'],
            'fecha': fecha,
            'nombre': reserva['nombre'],
            'telefono': reserva['telefono'],
            'tipo_evento': reserva['tipo_evento'],
            'total': reserva['total'],
            'seña': reserva['seña'],
            'fecha_seña': fecha_seña,
            'metodo_pago': reserva['metodo_pago'],
            'dirigido_a': reserva['dirigido_a'],
            'resto': reserva['resto'],
            'observaciones': reserva['observaciones']
        })
    
    return render_template('ver_reservas.html', reservas=reservas_format)

@app.route('/ver/<int:id>')
def ver_reserva(id):
    conn = get_db_connection()
    reserva = conn.execute('SELECT * FROM reservas WHERE id = ?', (id,)).fetchone()
    conn.close()
    
    if reserva:
        reserva_dict = dict(reserva)
        reserva_dict['fecha'] = datetime.strptime(reserva['fecha'], '%Y-%m-%d').strftime('%d/%m/%Y')
        if reserva['fecha_seña']:
            reserva_dict['fecha_seña'] = datetime.strptime(reserva['fecha_seña'], '%Y-%m-%d').strftime('%d/%m/%Y')

        return render_template('detalles_reserva.html', reserva=reserva_dict)
    else:
        flash('Reserva no encontrada.')
        return redirect(url_for('reservar'))

@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar_reserva(id):
    conn = get_db_connection()
    reserva = conn.execute('SELECT * FROM reservas WHERE id = ?', (id,)).fetchone()
    
    if request.method == 'POST':
        nombre = request.form['nombre']
        telefono = request.form['telefono']
        tipo_evento = request.form['tipo_evento']
        total = request.form['total']
        seña = request.form['seña']
        fecha_seña = request.form['fecha_seña']
        metodo_pago = request.form['metodo_pago']
        dirigido_a = request.form['dirigido_a']
        resto = request.form['resto']
        observaciones = request.form['observaciones']

        conn.execute('''UPDATE reservas 
                        SET nombre = ?, telefono = ?, tipo_evento = ?, total = ?, seña = ?, fecha_seña = ?, 
                            metodo_pago = ?, dirigido_a = ?, resto = ?, observaciones = ?
                        WHERE id = ?''', 
                     (nombre, telefono, tipo_evento, total, seña, fecha_seña, metodo_pago, dirigido_a, resto, observaciones, id))
        conn.commit()
        conn.close()

        flash('Reserva actualizada con éxito.')
        return redirect(url_for('reservas'))
    
    reserva_dict = dict(reserva)  # Convertimos el objeto a diccionario para que sea modificable
    return render_template('editar_reserva.html', reserva=reserva_dict)

@app.route('/eliminar/<int:id>', methods=['POST'])
def eliminar_reserva(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM reservas WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Reserva eliminada con éxito')
    return redirect(url_for('reservas'))

@app.route('/ingresar_cliente', methods=['POST'])
def ingresar_cliente():
    fecha = request.form['fecha']
    nombre = request.form['nombre']
    telefono = request.form['telefono']
    tipo_evento = request.form['tipo_evento']
    total = request.form['total']
    seña = request.form['seña']
    fecha_seña = request.form['fecha_seña']
    metodo_pago = request.form['metodo_pago']
    dirigido_a = request.form['dirigido_a']
    resto = request.form['resto']
    observaciones = request.form['observaciones']
    
    conn = get_db_connection()
    conn.execute('INSERT INTO reservas (fecha, nombre, telefono, tipo_evento, total, seña, fecha_seña, metodo_pago, dirigido_a, resto, observaciones) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', 
                 (fecha, nombre, telefono, tipo_evento, total, seña, fecha_seña, metodo_pago, dirigido_a, resto, observaciones))
    conn.commit()
    conn.close()
    
    flash('Cliente ingresado correctamente')
    return redirect(url_for('reservar'))

if __name__ == '__main__':
    init_db()
    app.run(debug=False)
