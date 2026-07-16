import os
from werkzeug.utils import secure_filename
import json
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import pymysql
from pymysql.cursors import DictCursor
from PIL import Image, ImageDraw, ImageFont
import random
import requests
import base64
from io import BytesIO
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Configuración para subir imágenes
UPLOAD_FOLDER = 'static/img/pizzas'
REFRESCO_UPLOAD_FOLDER = 'static/img/refrescos'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['REFRESCO_UPLOAD_FOLDER'] = REFRESCO_UPLOAD_FOLDER
app.secret_key = 'Clavesecreta123'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REFRESCO_UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ==================== CONFIGURACIÓN DE CORREOS ====================
EMAIL_EMPRESA = "chinoscafesa@gmail.com"
URL_BASE = "http://localhost:5000"

# ==================== CONFIGURACIÓN CLOUDFLARE ====================
CLOUDFLARE_ACCOUNT_ID = "api-removida"
CLOUDFLARE_API_TOKEN = "api-removida"

# ==================== FUNCIONES DE GENERACIÓN DE IMÁGENES ====================
def generar_imagen_con_ia(prompt, nombre_archivo=None):
    try:
        url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/@cf/stabilityai/stable-diffusion-xl-base-1.0"
        headers = {"Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}", "Content-Type": "application/json"}
        payload = {"prompt": prompt, "negative_prompt": "blurry, ugly, low quality, bad composition, deformed", "num_steps": 20}
        print(f"🎨 Generando imagen con Cloudflare: {prompt[:50]}...")
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '')
            if 'image' in content_type:
                if not nombre_archivo:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    nombre_archivo = f"cloudflare_{timestamp}.png"
                nombre_limpio = nombre_archivo.lower().replace(' ', '_')
                nombre_limpio = ''.join(c for c in nombre_limpio if c.isalnum() or c == '_')
                if not nombre_limpio.endswith('.png'):
                    nombre_limpio += '.png'
                ruta_completa = os.path.join(app.config['UPLOAD_FOLDER'], nombre_limpio)
                with open(ruta_completa, 'wb') as f:
                    f.write(response.content)
                print(f"✅ Imagen guardada: {nombre_limpio}")
                return nombre_limpio
            else:
                data = response.json()
                if data.get('success'):
                    image_data = base64.b64decode(data['result']['image'])
                    if not nombre_archivo:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        nombre_archivo = f"cloudflare_{timestamp}.png"
                    nombre_limpio = nombre_archivo.lower().replace(' ', '_')
                    nombre_limpio = ''.join(c for c in nombre_limpio if c.isalnum() or c == '_')
                    if not nombre_limpio.endswith('.png'):
                        nombre_limpio += '.png'
                    ruta_completa = os.path.join(app.config['UPLOAD_FOLDER'], nombre_limpio)
                    with open(ruta_completa, 'wb') as f:
                        f.write(image_data)
                    print(f"✅ Imagen guardada: {nombre_limpio}")
                    return nombre_limpio
                else:
                    print(f"❌ Error de Cloudflare: {data.get('errors', 'Unknown error')}")
                    return None
        else:
            print(f"❌ Error HTTP: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error generando imagen: {e}")
        return None

def generar_imagen_refresco(nombre):
    prompt = f"Can of {nombre} soda, cold beverage, product photography, white background, professional, 4k"
    return generar_imagen_con_ia(prompt, nombre)

def generar_imagen_local(nombre, ingredientes=""):
    colores = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#FF8A65', '#A8D8EA']
    color = random.choice(colores)
    nombre_limpio = nombre.lower().replace(' ', '_').replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
    nombre_archivo = f"{nombre_limpio}.png"
    ruta_completa = os.path.join(app.config['UPLOAD_FOLDER'], nombre_archivo)
    img = Image.new('RGB', (400, 300), color=color)
    draw = ImageDraw.Draw(img)
    draw.rectangle([10, 10, 390, 290], outline='white', width=3)
    try:
        font = ImageFont.truetype("arial.ttf", 36)
        font_small = ImageFont.truetype("arial.ttf", 18)
    except:
        font = ImageFont.load_default()
        font_small = ImageFont.load_default()
    draw.text((200, 100), "🍕", fill='white', anchor='mm', font=font)
    draw.text((200, 160), nombre[:20], fill='white', anchor='mm', font=font)
    if ingredientes:
        draw.text((200, 210), ingredientes[:30], fill='white', anchor='mm', font=font_small)
    img.save(ruta_completa)
    print(f"✅ Imagen local generada: {nombre_archivo}")
    return nombre_archivo

def generar_imagen_refresco_local(nombre):
    colores = ['#4A90D9', '#E74C3C', '#2ECC71', '#F1C40F', '#9B59B6', '#1ABC9C', '#FF6B6B', '#45B7D1', '#F39C12', '#1A237E']
    color = random.choice(colores)
    import unicodedata
    nombre_limpio = nombre.lower().replace(' ', '_')
    nombre_limpio = ''.join(c for c in unicodedata.normalize('NFD', nombre_limpio) if unicodedata.category(c) != 'Mn')
    nombre_limpio = ''.join(c for c in nombre_limpio if c.isalnum() or c == '_')
    nombre_archivo = f"{nombre_limpio}.png"
    ruta_completa = os.path.join(app.config['REFRESCO_UPLOAD_FOLDER'], nombre_archivo)
    img = Image.new('RGB', (400, 300), color=color)
    draw = ImageDraw.Draw(img)
    draw.rectangle([10, 10, 390, 290], outline='white', width=4)
    draw.rectangle([15, 15, 385, 285], outline='white', width=1)
    try:
        font_grande = ImageFont.truetype("arial.ttf", 60)
        font_pequena = ImageFont.truetype("arial.ttf", 28)
    except:
        font_grande = ImageFont.load_default()
        font_pequena = ImageFont.load_default()
    draw.text((200, 110), "🥤", fill='white', anchor='mm', font=font_grande)
    draw.text((200, 180), nombre.upper()[:20], fill='white', anchor='mm', font=font_pequena)
    img.save(ruta_completa)
    print(f"✅ Imagen local generada para refresco: {nombre_archivo}")
    return nombre_archivo

# ==================== FUNCIONES DE CORREO (GMAIL) ====================
def enviar_email(destinatario, asunto, cuerpo, adjunto_path=None, imagenes=None):
    try:
        if adjunto_path or imagenes:
            msg = MIMEMultipart()
            msg.attach(MIMEText(cuerpo, 'html', 'utf-8'))
            if adjunto_path:
                with open(adjunto_path, 'rb') as f:
                    part = MIMEApplication(f.read(), Name=os.path.basename(adjunto_path))
                    part['Content-Disposition'] = f'attachment; filename="{os.path.basename(adjunto_path)}"'
                    msg.attach(part)
            if imagenes:
                for img_path in imagenes:
                    if os.path.exists(img_path):
                        with open(img_path, 'rb') as f:
                            img_part = MIMEImage(f.read(), Name=os.path.basename(img_path))
                            img_part['Content-Disposition'] = f'attachment; filename="{os.path.basename(img_path)}"'
                            msg.attach(img_part)
        else:
            msg = MIMEText(cuerpo, 'html', 'utf-8')
        msg['Subject'] = asunto
        msg['From'] = app.config['MAIL_USERNAME']
        msg['To'] = destinatario
        with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as server:
            server.starttls()
            server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            server.send_message(msg)
        print(f"✅ Correo enviado a {destinatario}")
        return True
    except Exception as e:
        print(f"❌ Error enviando correo: {e}")
        return False

# ------------------------------------------------------------
# Funciones auxiliares
# ------------------------------------------------------------
def get_db():
    return pymysql.connect(
        host=app.config['DB_HOST'],
        user=app.config['DB_USER'],
        password=app.config['DB_PASSWORD'],
        database=app.config['DB_NAME'],
        port=app.config['DB_PORT'],
        cursorclass=DictCursor,
        autocommit=False
    )

# ==================== AUTENTICACIÓN ====================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM usuario WHERE email = %s", (email,))
        usuario = cur.fetchone()
        cur.close()
        conn.close()
        if usuario and usuario['contraseña'] == password:
            session['usuario_id'] = usuario['id']
            session['usuario_nombre'] = usuario['nombre']
            session['usuario_email'] = usuario['email']  # ✅ GUARDAR EMAIL
            session['usuario_rol'] = usuario['rol']
            flash(f'✅ Bienvenido {usuario["nombre"]}', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('❌ Correo o contraseña incorrectos', 'danger')
    return render_template('login.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        password = request.form['password']
        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO usuario (nombre, email, contraseña, rol) VALUES (%s, %s, %s, 'cliente')", (nombre, email, password))
            conn.commit()
            flash('✅ Cuenta creada exitosamente. Ahora inicia sesión.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'❌ Error: {e}', 'danger')
        finally:
            cur.close()
            conn.close()
    return render_template('registro.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('✅ Sesión cerrada', 'info')
    return redirect(url_for('login'))

# ==================== RUTAS PRINCIPALES ====================
@app.route('/')
def index():
    if 'usuario_id' in session:
        if session.get('usuario_rol') == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('index_cliente'))
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'usuario_id' not in session:
        flash('❌ Debes iniciar sesión primero', 'warning')
        return redirect(url_for('login'))
    if session.get('usuario_rol') == 'admin':
        return redirect(url_for('admin_dashboard'))
    else:
        return redirect(url_for('index_cliente'))

@app.route('/cliente')
def index_cliente():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    return render_template('index_cliente.html')

@app.route('/admin')
def admin_dashboard():
    if session.get('usuario_rol') != 'admin':
        flash('❌ No tienes permisos de administrador', 'danger')
        return redirect(url_for('login'))
    return render_template('admin_dashboard.html')

# ==================== ADMIN PEDIDOS ====================
@app.route('/admin/pedidos')
def admin_pedidos():
    if session.get('usuario_rol') != 'admin':
        flash('❌ No tienes permisos para ver esto', 'danger')
        return redirect(url_for('login'))
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM pedido ORDER BY id DESC")
    pedidos = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('admin_pedidos.html', pedidos=pedidos)

@app.route('/ver-pedido/<int:pedido_id>')
def ver_pedido(pedido_id):
    if session.get('usuario_rol') != 'admin':
        flash('❌ No tienes permisos', 'danger')
        return redirect(url_for('login'))
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM pedido WHERE id = %s", (pedido_id,))
    pedido = cur.fetchone()
    cur.execute("SELECT * FROM pedido_linea WHERE pedido_id = %s", (pedido_id,))
    lineas = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('ver_pedido.html', pedido=pedido, lineas=lineas)

# ==================== CRUD DE PIZZAS ====================
@app.route('/pizzas')
def listar_pizzas():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM pizza ORDER BY id")
    pizzas = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('pizzas.html', pizzas=pizzas)

@app.route('/pizza/nueva', methods=['GET', 'POST'])
def crear_pizza():
    if request.method == 'POST':
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        precio = request.form['precio']
        ingredientes = request.form['ingredientes']
        prompt = f"Delicious {nombre} pizza with {ingredientes}, professional food photography, restaurant quality, 4k"
        imagen_generada = generar_imagen_con_ia(prompt, nombre)
        if not imagen_generada:
            print("⚠️ Usando generación local como respaldo")
            imagen_generada = generar_imagen_local(nombre, ingredientes)
        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO pizza (nombre, descripcion, precio, ingredientes, imagen) VALUES (%s, %s, %s, %s, %s)",
                (nombre, descripcion, precio, ingredientes, imagen_generada)
            )
            conn.commit()
            flash('🍕 Pizza creada con imagen generada', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error al crear: {e}', 'danger')
        finally:
            cur.close()
            conn.close()
        return redirect(url_for('listar_pizzas'))
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM ingrediente ORDER BY nombre")
    ingredientes = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('create_pizza.html', ingredientes=ingredientes)

@app.route('/pizza/editar/<int:id>', methods=['GET', 'POST'])
def editar_pizza(id):
    conn = get_db()
    cur = conn.cursor()
    if request.method == 'POST':
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        precio = request.form['precio']
        ingredientes = request.form['ingredientes']
        imagen = request.form.get('imagen_actual')
        if 'imagen' in request.files:
            file = request.files['imagen']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                nombre_archivo = f"{nombre.replace(' ', '_')}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], nombre_archivo))
                imagen = nombre_archivo
        try:
            cur.execute(
                "UPDATE pizza SET nombre=%s, descripcion=%s, precio=%s, ingredientes=%s, imagen=%s WHERE id=%s",
                (nombre, descripcion, precio, ingredientes, imagen, id)
            )
            conn.commit()
            flash('Pizza actualizada', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error: {e}', 'danger')
        finally:
            cur.close()
            conn.close()
        return redirect(url_for('listar_pizzas'))
    cur.execute("SELECT * FROM pizza WHERE id=%s", (id,))
    pizza = cur.fetchone()
    cur.close()
    conn.close()
    return render_template('edit_pizza.html', pizza=pizza)

@app.route('/pizza/eliminar/<int:id>')
def eliminar_pizza(id):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM pizza WHERE id=%s", (id,))
        conn.commit()
        flash('Pizza eliminada', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error: {e}', 'danger')
    finally:
        cur.close()
        conn.close()
    return redirect(url_for('listar_pizzas'))

@app.route('/crear-pizza-personalizada')
def crear_pizza_personalizada():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM ingrediente ORDER BY nombre")
    ingredientes = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('create_pizza.html', ingredientes=ingredientes)

@app.route('/guardar-pizza-personalizada', methods=['POST'])
def guardar_pizza_personalizada():
    nombre_pizza = request.form.get('nombre_pizza', 'Pizza Personalizada')
    ingredientes_extra = request.form.getlist('ingredientes_extra')
    ingredientes_extra_texto = request.form.get('ingredientes_extra_texto', '').strip()
    
    # Procesar imágenes subidas
    imagenes_guardadas = []
    if 'imagenes' in request.files:
        files = request.files.getlist('imagenes')
        for file in files:
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                nombre_archivo = f"personalizada_{timestamp}_{filename}"
                ruta_completa = os.path.join(app.config['UPLOAD_FOLDER'], nombre_archivo)
                file.save(ruta_completa)
                imagenes_guardadas.append(nombre_archivo)
    
    precio_base = 7.00
    precio_extras = 0.00
    ingredientes_nombres = []
    
    conn = get_db()
    cur = conn.cursor()
    for ing_id in ingredientes_extra:
        cur.execute("SELECT nombre, precio_extra FROM ingrediente WHERE id = %s", (ing_id,))
        ing = cur.fetchone()
        if ing:
            ingredientes_nombres.append(ing['nombre'])
            precio_extras += float(ing['precio_extra'])
    
    if ingredientes_extra_texto:
        items = [item.strip() for item in ingredientes_extra_texto.split(',') if item.strip()]
        items = items[:10]
        if items:
            ingredientes_nombres.extend(items)
            precio_extras += len(items) * 0.50
    
    cur.close()
    conn.close()
    
    total_pizza = precio_base + precio_extras
    
    if 'carrito_personalizado' not in session:
        session['carrito_personalizado'] = []
    
    session['carrito_personalizado'].append({
        'nombre': nombre_pizza,
        'ingredientes': ', '.join(ingredientes_nombres) if ingredientes_nombres else 'Solo base',
        'precio': total_pizza,
        'imagenes': imagenes_guardadas  # Guardar nombres de imágenes
    })
    session.modified = True
    
    flash(f'🍕 {nombre_pizza} agregada al carrito - ${total_pizza:.2f}', 'success')
    return redirect(url_for('realizar_pedido'))

@app.route('/regenerar-imagen-pizza/<int:id>', methods=['POST'])
def regenerar_imagen_pizza(id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT nombre, ingredientes FROM pizza WHERE id = %s", (id,))
    pizza = cur.fetchone()
    if not pizza:
        return jsonify({'error': 'Pizza no encontrada'}), 404
    prompt = f"Delicious {pizza['nombre']} pizza with {pizza['ingredientes']}, professional food photography"
    nueva_imagen = generar_imagen_con_ia(prompt, pizza['nombre'])
    if not nueva_imagen:
        nueva_imagen = generar_imagen_local(pizza['nombre'], pizza['ingredientes'])
    if nueva_imagen:
        cur.execute("UPDATE pizza SET imagen = %s WHERE id = %s", (nueva_imagen, id))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'imagen': nueva_imagen})
    cur.close()
    conn.close()
    return jsonify({'error': 'No se pudo generar la imagen'}), 500

@app.route('/pizza-personalizada')
def pizza_personalizada():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM ingrediente ORDER BY nombre")
    ingredientes = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('pizza_personalizada.html', ingredientes=ingredientes)

# ==================== CRUD DE COMBOS ====================
@app.route('/combos')
def listar_combos():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM combo ORDER BY id")
    combos = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('combos.html', combos=combos)

@app.route('/combo/nuevo', methods=['GET', 'POST'])
def crear_combo():
    if request.method == 'POST':
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        precio = request.form['precio']
        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO combo (nombre, descripcion, precio) VALUES (%s, %s, %s)", (nombre, descripcion, precio))
            conn.commit()
            flash('Combo creado', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error: {e}', 'danger')
        finally:
            cur.close()
            conn.close()
        return redirect(url_for('listar_combos'))
    return render_template('create_combo.html')

@app.route('/combo/editar/<int:id>', methods=['GET', 'POST'])
def editar_combo(id):
    conn = get_db()
    cur = conn.cursor()
    if request.method == 'POST':
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        precio = request.form['precio']
        try:
            cur.execute("UPDATE combo SET nombre=%s, descripcion=%s, precio=%s WHERE id=%s", (nombre, descripcion, precio, id))
            conn.commit()
            flash('Combo actualizado', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error: {e}', 'danger')
        finally:
            cur.close()
            conn.close()
        return redirect(url_for('listar_combos'))
    cur.execute("SELECT * FROM combo WHERE id=%s", (id,))
    combo = cur.fetchone()
    cur.close()
    conn.close()
    return render_template('edit_combo.html', combo=combo)

@app.route('/combo/eliminar/<int:id>')
def eliminar_combo(id):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM combo WHERE id=%s", (id,))
        conn.commit()
        flash('Combo eliminado', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error: {e}', 'danger')
    finally:
        cur.close()
        conn.close()
    return redirect(url_for('listar_combos'))

# ==================== CRUD DE REFRESCOS ====================
@app.route('/refrescos')
def listar_refrescos():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM refresco ORDER BY id")
    refrescos = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('listar_refrescos.html', refrescos=refrescos)

@app.route('/refresco/nuevo', methods=['GET', 'POST'])
def crear_refresco():
    if request.method == 'POST':
        nombre = request.form['nombre']
        precio = request.form['precio']
        imagen_generada = generar_imagen_refresco_local(nombre)
        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO refresco (nombre, precio, imagen) VALUES (%s, %s, %s)", (nombre, precio, imagen_generada))
            conn.commit()
            flash('Refresco creado exitosamente', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error: {e}', 'danger')
        finally:
            cur.close()
            conn.close()
        return redirect(url_for('listar_refrescos'))
    return render_template('crear_refresco.html')

@app.route('/refresco/editar/<int:id>', methods=['GET', 'POST'])
def editar_refresco(id):
    conn = get_db()
    cur = conn.cursor()
    if request.method == 'POST':
        nombre = request.form['nombre']
        precio = request.form['precio']
        imagen = request.form.get('imagen_actual')
        if 'imagen' in request.files:
            file = request.files['imagen']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                nombre_archivo = f"{nombre.replace(' ', '_')}_{filename}"
                file.save(os.path.join(app.config['REFRESCO_UPLOAD_FOLDER'], nombre_archivo))
                imagen = nombre_archivo
        try:
            cur.execute("UPDATE refresco SET nombre=%s, precio=%s, imagen=%s WHERE id=%s", (nombre, precio, imagen, id))
            conn.commit()
            flash('Refresco actualizado', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error: {e}', 'danger')
        finally:
            cur.close()
            conn.close()
        return redirect(url_for('listar_refrescos'))
    cur.execute("SELECT * FROM refresco WHERE id=%s", (id,))
    refresco = cur.fetchone()
    cur.close()
    conn.close()
    return render_template('editar_refresco.html', refresco=refresco)

@app.route('/refresco/eliminar/<int:id>')
def eliminar_refresco(id):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM refresco WHERE id=%s", (id,))
        conn.commit()
        flash('Refresco eliminado', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error: {e}', 'danger')
    finally:
        cur.close()
        conn.close()
    return redirect(url_for('listar_refrescos'))

@app.route('/seleccionar-refrescos')
def seleccionar_refrescos():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM refresco ORDER BY nombre")
    refrescos = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('refrescos_selector.html', refrescos=refrescos)

@app.route('/agregar-refrescos-al-pedido', methods=['POST'])
def agregar_refrescos_al_pedido():
    conn = get_db()
    cur = conn.cursor()
    refrescos_agregados = []
    for key, value in request.form.items():
        if key.startswith('cantidad_') and int(value) > 0:
            ref_id = key.replace('cantidad_', '')
            cantidad = int(value)
            cur.execute("SELECT nombre, precio FROM refresco WHERE id = %s", (ref_id,))
            ref = cur.fetchone()
            if ref:
                refrescos_agregados.append(f"{cantidad} x {ref['nombre']}")
    cur.close()
    conn.close()
    if refrescos_agregados:
        flash(f'Refrescos agregados: {", ".join(refrescos_agregados)}', 'success')
    else:
        flash('No seleccionaste ningún refresco', 'warning')
    return redirect(url_for('realizar_pedido'))

# ==================== PÁGINA DE PEDIDO ====================
@app.route('/pedido', methods=['GET', 'POST'])
def realizar_pedido():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM pizza")
    pizzas = cur.fetchall()
    cur.execute("SELECT * FROM refresco")
    refrescos = cur.fetchall()
    cur.execute("SELECT * FROM extra")
    extras = cur.fetchall()
    cur.execute("SELECT * FROM combo")
    combos = cur.fetchall()
    cur.close()
    conn.close()

    # Restaurar selecciones si existen
    selecciones = session.pop('selecciones_temp', {}) if request.method == 'GET' else {}

    if request.method == 'POST':
        cliente_nombre = request.form['nombre']
        cliente_email = request.form['email']
        cliente_direccion = request.form.get('direccion', '')
        metodo_pago = request.form['metodo_pago']
        tipo_envio = request.form['tipo_envio']
        costo_envio = app.config.get('ENVIO_COSTO', 3.00) if tipo_envio == 'domicilio' else 0.0

        total = 0.0
        lineas = []
        detalle_pedido = []

        print("=" * 50)
        print("📋 PROCESANDO PEDIDO")
        print("=" * 50)

        # Procesar combos
        for cid in request.form.getlist('combos'):
            conn2 = get_db()
            cur2 = conn2.cursor()
            cur2.execute("SELECT nombre, precio FROM combo WHERE id=%s", (cid,))
            combo = cur2.fetchone()
            if combo:
                total += float(combo['precio'])
                lineas.append(('combo', cid, 1, combo['precio']))
                detalle_pedido.append(f"1x {combo['nombre']} - ${combo['precio']:.2f}")
            cur2.close()
            conn2.close()

        # Procesar pizzas
        for pid in request.form.getlist('pizzas'):
            conn2 = get_db()
            cur2 = conn2.cursor()
            cur2.execute("SELECT nombre, precio FROM pizza WHERE id=%s", (pid,))
            pizza = cur2.fetchone()
            if pizza:
                total += float(pizza['precio'])
                lineas.append(('pizza', pid, 1, pizza['precio']))
                detalle_pedido.append(f"1x {pizza['nombre']} - ${pizza['precio']:.2f}")
            cur2.close()
            conn2.close()

        # Procesar refrescos
        for rid in request.form.getlist('refrescos'):
            conn2 = get_db()
            cur2 = conn2.cursor()
            cur2.execute("SELECT nombre, precio FROM refresco WHERE id=%s", (rid,))
            ref = cur2.fetchone()
            if ref:
                total += float(ref['precio'])
                lineas.append(('refresco', rid, 1, ref['precio']))
                detalle_pedido.append(f"1x {ref['nombre']} - ${ref['precio']:.2f}")
            cur2.close()
            conn2.close()

        # Procesar extras
        for eid in request.form.getlist('extras'):
            conn2 = get_db()
            cur2 = conn2.cursor()
            cur2.execute("SELECT nombre, precio FROM extra WHERE id=%s", (eid,))
            extra = cur2.fetchone()
            if extra:
                total += float(extra['precio'])
                lineas.append(('extra', eid, 1, extra['precio']))
                detalle_pedido.append(f"1x {extra['nombre']} - ${extra['precio']:.2f}")
            cur2.close()
            conn2.close()

        # Procesar pizza personalizada
        if 'carrito_personalizado' in session:
            for item in session['carrito_personalizado']:
                total += float(item['precio'])
                lineas.append(('pizza_personalizada', 0, 1, item['precio']))
                detalle_pedido.append(f"1x {item['nombre']} (Personalizada) - ${item['precio']:.2f}")
            session.pop('carrito_personalizado', None)
            session.modified = True

        total += costo_envio
        if costo_envio > 0:
            detalle_pedido.append(f"🚚 Envío - ${costo_envio:.2f}")

        print(f"💰 Total final: ${total:.2f}")
        print("=" * 50)

        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute(
                """INSERT INTO pedido (cliente_nombre, cliente_email, cliente_direccion, total, metodo_pago, costo_envio, estado) 
                    VALUES (%s, %s, %s, %s, %s, %s, 'pendiente')""",
                (cliente_nombre, cliente_email, cliente_direccion, total, metodo_pago, costo_envio)
            )
            pedido_id = cur.lastrowid

            for linea in lineas:
                tipo, item_id, cant, precio_unit = linea
                cur.execute(
                    "INSERT INTO pedido_linea (pedido_id, tipo_item, item_id, cantidad, precio_unitario) VALUES (%s, %s, %s, %s, %s)",
                    (pedido_id, tipo, item_id, cant, precio_unit)
                )
            conn.commit()

            os.makedirs(app.config.get('JSON_ORDERS_DIR', 'json_orders'), exist_ok=True)
            orden_data = {
                'pedido_id': pedido_id,
                'cliente': cliente_nombre,
                'email': cliente_email,
                'direccion': cliente_direccion,
                'total': float(total),
                'costo_envio': float(costo_envio),
                'fecha': datetime.now().isoformat(),
                'lineas': [[tipo, item_id, cant, float(precio)] for tipo, item_id, cant, precio in lineas]
            }
            json_path = os.path.join(app.config.get('JSON_ORDERS_DIR', 'json_orders'), f'orden_{pedido_id}.json')
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(orden_data, f, indent=4, ensure_ascii=False)

            cur.execute("UPDATE pedido SET archivo_json_orden=%s WHERE id=%s", (json_path, pedido_id))
            conn.commit()

            # ==================== CORREO AL CLIENTE (SOLO CONFIRMACIÓN, SIN IMÁGENES) ====================
            asunto_cliente = f"Confirmación de pedido #{pedido_id} - Chinos Café"
            cuerpo_cliente = f"""
            <h2>🍕 ¡Pedido #{pedido_id} confirmado!</h2>
            <p>Hola <strong>{cliente_nombre}</strong>,</p>
            <p>Tu pedido ha sido registrado exitosamente.</p>
            <p><strong>Total:</strong> ${total:.2f}</p>
            <h3>📋 Detalle del pedido:</h3>
            <ul>
            """
            for item in detalle_pedido:
                cuerpo_cliente += f"<li>{item}</li>\n"
            cuerpo_cliente += """
            </ul>
            <p>Tu pedido está en espera de aprobación por la empresa.</p>
            <p>Recibirás un correo con el JSON y las imágenes cuando sea aprobado.</p>
            <p>¡Gracias por tu compra!</p>
            """
            # SOLO JSON, SIN IMÁGENES
            enviar_email(cliente_email, asunto_cliente, cuerpo_cliente, json_path)

            # ==================== CORREO A LA EMPRESA (CON JSON) ====================
            asunto_empresa = f"📋 NUEVO PEDIDO #{pedido_id} - Chinos Café"
            cuerpo_empresa = f"""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px;">
                <h2 style="color: #1B5E20;">🍕 Nuevo Pedido #{pedido_id}</h2>
                <p><strong>Cliente:</strong> {cliente_nombre}</p>
                <p><strong>Email:</strong> {cliente_email}</p>
                <p><strong>Total:</strong> ${total:.2f}</p>
                <p><strong>Fecha:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
                <hr>
                <h3>📋 Detalle:</h3>
                <ul>
            """
            for item in detalle_pedido:
                cuerpo_empresa += f"<li>{item}</li>\n"
            cuerpo_empresa += f"""
                </ul>
                <hr>
                <h3>📌 Acciones</h3>
                <a href="{URL_BASE}/aprobar-pedido/{pedido_id}" 
                    style="display: inline-block; padding: 12px 30px; background: #4CAF50; color: white; text-decoration: none; border-radius: 5px;">
                    ✅ Aprobar Pedido #{pedido_id}
                </a>
                <br><br>
                <a href="{URL_BASE}/rechazar-pedido/{pedido_id}" 
                    style="display: inline-block; padding: 12px 30px; background: #f44336; color: white; text-decoration: none; border-radius: 5px;">
                    ❌ Rechazar Pedido #{pedido_id}
                </a>
                <hr>
                <p>Pedido en formato JSON adjunto.</p>
            </body>
            </html>
            """
            enviar_email(EMAIL_EMPRESA, asunto_empresa, cuerpo_empresa, json_path)

            flash('Pedido realizado con éxito. Espera la confirmación de la empresa.', 'success')
            return redirect(url_for('index_cliente'))

        except Exception as e:
            conn.rollback()
            flash(f'Error al guardar el pedido: {e}', 'danger')
            return redirect(url_for('realizar_pedido'))
        finally:
            cur.close()
            conn.close()

    return render_template('order.html',
        pizzas=pizzas,
        refrescos=refrescos,
        extras=extras,
        combos=combos,
        selecciones=selecciones
    )

@app.route('/guardar-selecciones', methods=['POST'])
def guardar_selecciones():
    # Guardar selecciones en sesión
    session['selecciones_temp'] = {
        'combos': request.form.getlist('combos'),
        'pizzas': request.form.getlist('pizzas'),
        'refrescos': request.form.getlist('refrescos'),
        'extras': request.form.getlist('extras'),
        'direccion': request.form.get('direccion_temp', ''),
        'tipo_envio': request.form.get('tipo_envio_temp', 'retiro')
    }
    session.modified = True
    return redirect(url_for('pizza_personalizada'))

# ==================== PAGO YAPPY ====================
@app.route('/pagar/<int:pedido_id>', methods=['GET', 'POST'])
def pagar_pedido(pedido_id):
    if request.method == 'POST':
        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute("SELECT * FROM pedido WHERE id = %s", (pedido_id,))
            pedido = cur.fetchone()
            if not pedido:
                flash('Pedido no encontrado', 'danger')
                return redirect(url_for('index_cliente'))
            
            if pedido['estado'] != 'aprobado':
                flash('Este pedido debe ser aprobado por la empresa primero', 'warning')
                return redirect(url_for('index_cliente'))
            
            # Generar JSON de pago
            os.makedirs(app.config.get('JSON_PAYMENTS_DIR', 'json_payments'), exist_ok=True)
            pago_data = {
                'pedido_id': pedido_id,
                'monto': float(pedido['total']),
                'metodo': 'YAPPY',
                'fecha_pago': datetime.now().isoformat(),
                'estado': 'confirmado'
            }
            json_path = os.path.join(app.config.get('JSON_PAYMENTS_DIR', 'json_payments'), f'pago_{pedido_id}.json')
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(pago_data, f, indent=4)
            
            cur.execute("UPDATE pedido SET estado='pagado', archivo_json_pago=%s WHERE id=%s", (json_path, pedido_id))
            conn.commit()
            
            # Correo a la empresa
            asunto_pago = f"💳 Pago confirmado - Pedido #{pedido_id}"
            cuerpo_pago = f"""
            <h2>💳 Pago confirmado - Pedido #{pedido_id}</h2>
            <p><strong>Cliente:</strong> {pedido['cliente_nombre']}</p>
            <p><strong>Monto:</strong> ${pedido['total']:.2f}</p>
            <p><strong>Método:</strong> YAPPY Comercial</p>
            <p><strong>Fecha:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
            <br>
            <p>Proceder con el despacho del pedido.</p>
            """
            enviar_email(EMAIL_EMPRESA, asunto_pago, cuerpo_pago)
            
            flash('✅ Pago confirmado. Pedido procesado.', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error en el pago: {e}', 'danger')
        finally:
            cur.close()
            conn.close()
        return redirect(url_for('index_cliente'))
    
    return render_template('pago_yappy.html', pedido_id=pedido_id)

# ==================== APROBACIÓN/RECHAZO DE PEDIDOS ====================
@app.route('/aprobar-pedido/<int:pedido_id>')
def aprobar_pedido(pedido_id):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM pedido WHERE id = %s", (pedido_id,))
        pedido = cur.fetchone()
        if not pedido:
            flash('Pedido no encontrado', 'danger')
            return redirect(url_for('index_cliente'))
        
        if pedido['estado'] == 'aprobado':
            flash('Este pedido ya fue aprobado', 'warning')
            return redirect(url_for('index_cliente'))
        
        # Actualizar estado
        cur.execute("UPDATE pedido SET estado = 'aprobado' WHERE id = %s", (pedido_id,))
        conn.commit()
        
        # ===== OBTENER LÍNEAS DEL PEDIDO =====
        cur.execute("SELECT * FROM pedido_linea WHERE pedido_id = %s", (pedido_id,))
        lineas = cur.fetchall()
        
        # ===== RECOPILAR IMÁGENES DE LOS PRODUCTOS =====
        imagenes_adjuntas = []
        for linea in lineas:
            tipo = linea['tipo_item']
            item_id = linea['item_id']
            
            if tipo == 'pizza':
                cur.execute("SELECT imagen FROM pizza WHERE id = %s", (item_id,))
                item = cur.fetchone()
                if item and item['imagen']:
                    ruta = os.path.join(app.config['UPLOAD_FOLDER'], item['imagen'])
                    if os.path.exists(ruta):
                        imagenes_adjuntas.append(ruta)
            
            elif tipo == 'refresco':
                cur.execute("SELECT imagen FROM refresco WHERE id = %s", (item_id,))
                item = cur.fetchone()
                if item and item['imagen']:
                    ruta = os.path.join(app.config['REFRESCO_UPLOAD_FOLDER'], item['imagen'])
                    if os.path.exists(ruta):
                        imagenes_adjuntas.append(ruta)
            
            elif tipo == 'pizza_personalizada':
                # Buscar el JSON del pedido para obtener las imágenes
                json_path = pedido.get('archivo_json_orden')
                if json_path and os.path.exists(json_path):
                    with open(json_path, 'r') as f:
                        orden_data = json.load(f)
                        # Buscar imágenes en los datos del pedido
                        pass
        
        # Buscar imágenes de pizzas personalizadas en la sesión (si existe)
        if 'carrito_personalizado' in session:
            for item in session['carrito_personalizado']:
                if 'imagenes' in item:
                    for img in item['imagenes']:
                        ruta = os.path.join(app.config['UPLOAD_FOLDER'], img)
                        if os.path.exists(ruta):
                            imagenes_adjuntas.append(ruta)
        
        # Obtener el JSON del pedido
        json_path = pedido.get('archivo_json_orden')
        
        # ===== CORREO AL CLIENTE CON JSON + IMÁGENES =====
        asunto = f"✅ Pedido #{pedido_id} confirmado - Chinos Café"
        cuerpo = f"""
        <h2>✅ ¡Tu pedido #{pedido_id} ha sido confirmado!</h2>
        <p>Hola <strong>{pedido['cliente_nombre']}</strong>,</p>
        <p>Tu pedido ha sido aprobado por la empresa.</p>
        <p><strong>Total:</strong> ${pedido['total']:.2f}</p>
        <p>📎 <strong>Adjunto encontrarás el JSON de tu pedido y las imágenes de tus productos.</strong></p>
        <p>Tu pedido está siendo procesado y será despachado próximamente.</p>
        <br>
        <p>¡Gracias por tu compra!</p>
        """
        
        # Enviar correo con JSON e imágenes (si existen)
        enviar_email(pedido['cliente_email'], asunto, cuerpo, json_path if json_path and os.path.exists(json_path) else None, imagenes_adjuntas if imagenes_adjuntas else None)
        
        flash(f'✅ Pedido #{pedido_id} aprobado. Cliente notificado con JSON e imágenes.', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error: {e}', 'danger')
    finally:
        cur.close()
        conn.close()
    return redirect(url_for('index_cliente'))

@app.route('/rechazar-pedido/<int:pedido_id>')
def rechazar_pedido(pedido_id):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM pedido WHERE id = %s", (pedido_id,))
        pedido = cur.fetchone()
        if not pedido:
            flash('Pedido no encontrado', 'danger')
            return redirect(url_for('index_cliente'))
        cur.execute("UPDATE pedido SET estado = 'rechazado' WHERE id = %s", (pedido_id,))
        conn.commit()
        asunto = f"❌ Pedido #{pedido_id} rechazado - Chinos Café"
        cuerpo = f"""
        <h2>❌ Pedido #{pedido_id} rechazado</h2>
        <p>Hola <strong>{pedido['cliente_nombre']}</strong>,</p>
        <p>Lamentamos informarte que tu pedido ha sido rechazado por la empresa.</p>
        <p>Por favor, contacta con nosotros para más información.</p>
        """
        enviar_email(pedido['cliente_email'], asunto, cuerpo)
        flash(f'❌ Pedido #{pedido_id} rechazado', 'warning')
    except Exception as e:
        conn.rollback()
        flash(f'Error: {e}', 'danger')
    finally:
        cur.close()
        conn.close()
    return redirect(url_for('index_cliente'))

# ------------------------------------------------------------
# Punto de entrada
# ------------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)