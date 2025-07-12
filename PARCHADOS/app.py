from flask import Flask, render_template, request, redirect, flash, Response, send_file
from flask_mail import Mail, Message
from dotenv import load_dotenv
import sqlite3
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

# Inicializar base de datos
def init_db():
    conn = sqlite3.connect('inscripciones.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS inscripciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    ''')
    conn.commit()
    conn.close()

init_db()


# Autenticación
USUARIO_ADMIN = "organizador"
CLAVE_ADMIN = "CarreraParchada_2025#"

def requiere_login(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not (auth.username == USUARIO_ADMIN and auth.password == CLAVE_ADMIN):
            return Response('Debe iniciar sesión.', 401, {'WWW-Authenticate': 'Basic realm="Login"'})
        return f(*args, **kwargs)
    return decorated

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/send_email', methods=['POST'])
def send_email():
    try:
        nombre = request.form['nombre']
        correo = request.form['correo']
        mensaje = request.form['mensaje']

        msg = Message('Nuevo mensaje de contacto',
                      sender=app.config['MAIL_USERNAME'],
                      recipients=[app.config['MAIL_USERNAME']])
        msg.body = f"Nombre: {nombre}\nCorreo: {correo}\nMensaje: {mensaje}"

        mail.send(msg)
        flash("Mensaje enviado correctamente.", "success")
    except Exception as e:
        print(f"Error: {e}")
        flash("Ocurrió un error al enviar el mensaje.", "danger")

    return redirect('/')

@app.route('/inscribir', methods=['POST'])
def inscribir():
    try:
        campos = ['tipo_doc', 'num_doc', 'nombres', 'apellidos', 'edad', 'genero', 'categoria', 'barrio', 'num_inscripcion']
        datos = {campo: request.form.get(campo, '').strip() for campo in campos}

        # Validación de campos vacíos para evitar inscripciones incompletas
        if '' in datos.values():
            flash("Por favor, completa todos los campos antes de enviar la inscripción.", "danger")
            return redirect('/')

        conn = sqlite3.connect('inscripciones.db')
        c = conn.cursor()
        c.execute('''
            INSERT INTO inscripciones 
            (tipo_doc, num_doc, nombres, apellidos, edad, genero, categoria, barrio, num_inscripcion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', tuple(datos.values()))
        conn.commit()
        conn.close()

        flash("¡Inscripción enviada correctamente!", "success")

    except Exception as e:
        print(f"Error al inscribir: {e}")
        flash("Ocurrió un error al guardar la inscripción.", "danger")

    return redirect('/')

@app.route('/inscritos')
@requiere_login
def ver_inscritos():
    try:
        conn = sqlite3.connect('inscripciones.db')
        c = conn.cursor()
        c.execute('SELECT * FROM inscripciones ORDER BY id DESC')
        inscritos = c.fetchall()
        conn.close()
        return render_template('inscritos.html', inscritos=inscritos)
    except Exception as e:
        print(f"Error al obtener inscritos: {e}")
        flash("No se pudo obtener la lista de inscritos.", "danger")
        return redirect('/')

@app.route('/descargar_inscritos')
@requiere_login
def descargar_inscritos():
    conn = sqlite3.connect('inscripciones.db')
    c = conn.cursor()
    c.execute('SELECT * FROM inscripciones')
    inscritos = c.fetchall()
    conn.close()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Inscritos"

    encabezados = ["ID", "Tipo Doc", "Número Doc", "Nombres", "Apellidos",
                   "Edad", "Género", "Categoría", "Barrio", "N° Inscripción"]
    ws.append(encabezados)

    for col in ws.columns:
        col[0].font = openpyxl.styles.Font(bold=True)

    for row in inscritos:
        ws.append(row)

    for column_cells in ws.columns:
        length = max(len(str(cell.value)) for cell in column_cells)
        ws.column_dimensions[column_cells[0].column_letter].width = length + 2

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    return send_file(output,
                     download_name="inscritos.xlsx",
                     as_attachment=True,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/reiniciar_inscritos')
@requiere_login
def reiniciar_inscritos():
    try:
        conn = sqlite3.connect('inscripciones.db')
        c = conn.cursor()
        c.execute('DELETE FROM inscripciones')
        conn.commit()
        conn.close()
        flash("✅ Lista de inscritos reiniciada correctamente.", "success")
    except Exception as e:
        print(f"Error al reiniciar: {e}")
        flash("⚠️ Error al reiniciar la lista.", "danger")
    return redirect('/inscritos')

@app.route('/reiniciar_id', methods=['POST'])
@requiere_login
def reiniciar_id():
    try:
        conn = sqlite3.connect('inscripciones.db')
        c = conn.cursor()
        c.execute('DELETE FROM inscripciones')
        conn.commit()
        c.execute('DELETE FROM sqlite_sequence WHERE name="inscripciones"')
        conn.commit()
        conn.close()
        flash("✅ Lista de inscritos e ID reiniciados correctamente.", "success")
    except Exception as e:
        print(f"Error al reiniciar ID: {e}")
        flash("⚠️ Error al reiniciar el ID de la lista.", "danger")
    return redirect('/inscritos')
if __name__ == "__main__":
    app.run(debug=True)


   

