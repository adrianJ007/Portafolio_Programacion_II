from flask import Flask, render_template, request, jsonify
import json
import os
from datetime import datetime

app = Flask(__name__)

# Asegurar que existe la carpeta data
if not os.path.exists('data'):
    os.makedirs('data')

# Archivo donde se guardan las noticias
NOTICIAS_FILE = 'data/noticias.json'

def cargar_noticias():
    """Carga las noticias desde el archivo JSON"""
    try:
        with open(NOTICIAS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Noticias por defecto
        noticias_default = [
            {
                "id": 1,
                "titulo": "🎉 ¡Bienvenidos a SUCESOS y MÁS!",
                "contenido": "Iniciamos operaciones con el objetivo de transformar tus eventos en experiencias inolvidables. Contamos con el mejor equipo de profesionales.",
                "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "enlace": "#"
            },
            {
                "id": 2,
                "titulo": "🍽️ Nuevo servicio de catering exclusivo",
                "contenido": "Ahora ofrecemos servicio de catering gourmet para todo tipo de eventos. ¡Pregunta por nuestros paquetes especiales!",
                "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "enlace": "#"
            },
            {
                "id": 3,
                "titulo": "🎊 Descuento especial por lanzamiento",
                "contenido": "Contrata nuestros servicios antes del 30 de mayo y obtén un 15% de descuento en paquetes seleccionados.",
                "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "enlace": "/servicios"
            }
        ]
        guardar_noticias(noticias_default)
        return noticias_default

def guardar_noticias(noticias):
    """Guarda las noticias en el archivo JSON"""
    with open(NOTICIAS_FILE, 'w', encoding='utf-8') as f:
        json.dump(noticias, f, ensure_ascii=False, indent=2)

# ===== RUTAS DEL MENÚ PRINCIPAL =====
@app.route('/')
def index():
    """Página principal"""
    noticias = cargar_noticias()
    # Mostrar solo las últimas 3 noticias
    ultimas_noticias = noticias[-3:] if len(noticias) >= 3 else noticias
    return render_template('index.html', noticias=ultimas_noticias)

@app.route('/clientes')
def clientes():
    """Página de clientes - Collage"""
    return render_template('clientes.html')

@app.route('/servicios')
def servicios():
    """Página de servicios"""
    return render_template('servicios.html')

@app.route('/contacto')
def contacto():
    """Página de contacto con redes sociales"""
    return render_template('contacto.html')

@app.route('/ubicacion')
def ubicacion():
    """Página de ubicación del local"""
    return render_template('ubicacion.html')

@app.route('/noticias')
def noticias():
    """Página de noticias con panel ADMIN"""
    todas_noticias = cargar_noticias()
    # Invertir para mostrar las más recientes primero
    todas_noticias.reverse()
    return render_template('noticias.html', noticias=todas_noticias)

@app.route('/factura')
def factura():
    """Página de factura"""
    return render_template('factura.html')

# ===== API PARA ADMIN (Agregar noticias en tiempo real) =====
@app.route('/api/agregar_noticia', methods=['POST'])
def agregar_noticia():
    """Endpoint para agregar noticias desde el panel ADMIN"""
    try:
        data = request.get_json()
        titulo = data.get('titulo')
        contenido = data.get('contenido')
        enlace = data.get('enlace', '#')
        
        if not titulo or not contenido:
            return jsonify({'success': False, 'error': 'Faltan datos'}), 400
        
        noticias = cargar_noticias()
        nueva_noticia = {
            "id": len(noticias) + 1,
            "titulo": titulo,
            "contenido": contenido,
            "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "enlace": enlace
        }
        noticias.append(nueva_noticia)
        guardar_noticias(noticias)
        
        return jsonify({'success': True, 'noticia': nueva_noticia})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ===== API PARA OBTENER NOTICIAS =====
@app.route('/api/noticias')
def api_noticias():
    """Endpoint para obtener todas las noticias (para JavaScript)"""
    noticias = cargar_noticias()
    noticias.reverse()  # Más recientes primero
    return jsonify(noticias)
# Agrega esto DESPUÉS de la función agregar_noticia() y ANTES de if __name__ == '__main__':

# ===== API PARA ELIMINAR NOTICIAS =====
@app.route('/api/eliminar_noticia/<int:id>', methods=['DELETE'])
def eliminar_noticia(id):
    """Endpoint para eliminar una noticia por ID"""
    try:
        noticias = cargar_noticias()
        # Filtrar la noticia que queremos eliminar
        noticias_actualizadas = [n for n in noticias if n.get('id') != id]
        
        if len(noticias_actualizadas) == len(noticias):
            return jsonify({'success': False, 'error': 'Noticia no encontrada'}), 404
        
        # Reasignar IDs para mantener orden
        for i, noticia in enumerate(noticias_actualizadas, 1):
            noticia['id'] = i
        
        guardar_noticias(noticias_actualizadas)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
# ===== ARCHIVO PARA GUARDAR MENSAJES DE CONTACTO =====
MENSAJES_FILE = 'data/mensajes.json'

def cargar_mensajes():
    """Carga los mensajes desde el archivo JSON"""
    try:
        with open(MENSAJES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def guardar_mensajes(mensajes):
    """Guarda los mensajes en el archivo JSON"""
    with open(MENSAJES_FILE, 'w', encoding='utf-8') as f:
        json.dump(mensajes, f, ensure_ascii=False, indent=2)

# ===== API PARA GUARDAR MENSAJES DE CONTACTO =====
@app.route('/api/enviar_mensaje', methods=['POST'])
def enviar_mensaje():
    """Endpoint para guardar mensajes del formulario de contacto"""
    try:
        data = request.get_json()
        mensaje = {
            "id": len(cargar_mensajes()) + 1,
            "nombre": data.get('nombre'),
            "email": data.get('email'),
            "telefono": data.get('telefono'),
            "servicio": data.get('servicio'),
            "mensaje": data.get('mensaje'),
            "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "leido": False
        }
        
        mensajes = cargar_mensajes()
        mensajes.append(mensaje)
        guardar_mensajes(mensajes)
        
        return jsonify({'success': True, 'mensaje': 'Mensaje guardado correctamente'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ===== API PARA OBTENER MENSAJES (ADMIN) =====
@app.route('/api/mensajes')
def api_mensajes():
    """Endpoint para obtener todos los mensajes (solo admin)"""
    mensajes = cargar_mensajes()
    mensajes.reverse()  # Más recientes primero
    return jsonify(mensajes)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)