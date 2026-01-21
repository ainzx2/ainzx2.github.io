from flask import Flask, render_template, request, redirect, flash, Response, send_file
from flask_mail import Mail, Message
from dotenv import load_dotenv
import psycopg2
import os
from functools import wraps
import openpyxl
from io import BytesIO

# Cargar variables de entorno (.env)
load_dotenv()

app = Flask(__name__)

# Clave secreta
app.secret_key = os.getenv('FLASK_SECRET_KEY', '123@h')

# Configuración Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = "bcaparchados4@gmail.com"
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = app.config['MAIL_USERNAME']

mail = Mail(app)

# ============================
# CONEXIÓN A POSTGRESQL
# ============================
DATABASE_URL = os.getenv('DATABASE_URL')

def get_connection():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL no está configurada")
    return psycopg2.connect(DATABASE_URL)

# ============================
# INICIALIZAR BASE DE DATOS
# ============================
def init_db():
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS inscripciones (
                id SERIAL PRIMARY KEY,
                tipo_doc TEXT,
                num_doc TEXT,
                nombres TEXT,
                apellidos TEXT,
                edad INTEGER,
                genero TEXT,
                categoria TEXT,
                barrio TEXT,
                num_inscripcion TEXT
            )
        """)
        conn.commit()
        conn.close()
        print("Base de datos inicializada correctamente.")
    except Exception as e:
        print("⚠️ No se pudo inicializar la base de datos:", e)

# ============================
# AUTENTICACIÓN BÁSICA
# ============================
USUARIO_ADMIN = "organizador"
CLAVE_ADMIN = "CarreraParchada_2025#"

def requiere_login(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not (auth.username == USUARIO_ADMIN and auth.password == CLAVE_ADMIN):
            return Response(
                'Debe iniciar sesión.',
                401,
                {'WWW-Authenticate': 'Basic realm="Login"'}
            )
        return f(*args, **kwargs)
    return decorated

# ============================
# RUTAS
# ============================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/send_email', methods=['POST'])
def send_email():
    try:
        nombre = request.form['nombre']
        correo = request.form['correo']
        mensaje = request.form['mensaje']

        msg = Message(
            'Nuevo mensaje de contacto',
            sender=app.config['MAIL_USERNAME'],
            recipients=[app.config['MAIL_USERNAME']]
        )
        msg.body = f"Nombre: {nombre}\nCorreo: {correo}\nMensaje: {mensaje}"

        mail.send(msg)
        flash("Mensaje enviado correctamente.", "success")
    except Exception as e:
        print("Error al enviar correo:", e)
        flash("Ocurrió un error al enviar el mensaje.", "danger")

    return redirect('/')

@app.route('/inscribir', methods=['POST'])
def inscribir():
    try:
        campos = [
            'tipo_doc', 'num_doc', 'nombres', 'apellidos',
            'edad', 'genero', 'categoria', 'barrio', 'num_inscripcion'
        ]
        datos = {campo: request.form.get(campo, '').strip() for campo in campos}

        if '' in datos.values():
            flash("Por favor, completa todos los campos.", "danger")
            return redirect('/')

        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            INSERT INTO inscripciones
            (tipo_doc, num_doc, nombres, apellidos, edad, genero, categoria, barrio, num_inscripcion)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, tuple(datos.values()))
        conn.commit()
        conn.close()

        flash("¡Inscripción enviada correctamente!", "success")

    except Exception as e:
        print("Error al inscribir:", e)
        flash("Ocurrió un error al guardar la inscripción.", "danger")

    return redirect('/')

@app.route('/inscritos')
@requiere_login
def ver_inscritos():
    try:
        init_db()  # asegura que la tabla exista
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM inscripciones ORDER BY id DESC")
        inscritos = c.fetchall()
        conn.close()
        return render_template('inscritos.html', inscritos=inscritos)
    except Exception as e:
        print("Error al obtener inscritos:", e)
        flash("No se pudo obtener la lista de inscritos.", "danger")
        return redirect('/')

@app.route('/descargar_inscritos')
@requiere_login
def descargar_inscritos():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM inscripciones")
    inscritos = c.fetchall()
    conn.close()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Inscritos"

    encabezados = [
        "ID", "Tipo Doc", "Número Doc", "Nombres", "Apellidos",
        "Edad", "Género", "Categoría", "Barrio", "N° Inscripción"
    ]
    ws.append(encabezados)

    for col in ws.columns:
        col[0].font = openpyxl.styles.Font(bold=True)

    for row in inscritos:
        ws.append(row)

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    return send_file(
        output,
        download_name="inscritos.xlsx",
        as_attachment=True,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@app.route('/reiniciar_inscritos')
@requiere_login
def reiniciar_inscritos():
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM inscripciones")
        conn.commit()
        conn.close()
        flash("✅ Lista de inscritos reiniciada correctamente.", "success")
    except Exception as e:
        print("Error al reiniciar:", e)
        flash("⚠️ Error al reiniciar la lista.", "danger")
    return redirect('/inscritos')

@app.route('/reiniciar_id', methods=['POST'])
@requiere_login
def reiniciar_id():
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM inscripciones")
        c.execute("ALTER SEQUENCE inscripciones_id_seq RESTART WITH 1")
        conn.commit()
        conn.close()
        flash("✅ Lista e ID reiniciados correctamente.", "success")
    except Exception as e:
        print("Error al reiniciar ID:", e)
        flash("⚠️ Error al reiniciar el ID.", "danger")
    return redirect('/inscritos')

# ============================
# ARRANQUE
# ============================
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
