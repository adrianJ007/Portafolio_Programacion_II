import os
import json
import tempfile
import smtplib
import random
import secrets
from models import Company, Combo
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from sqlalchemy import func

from flask import Flask, render_template, request, redirect, url_for, flash
from config import Config
from models import db, Company, Combo, Order, ReplicaManager

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

# Inicializar bases de datos al arrancar la aplicación
with app.app_context():
        db.create_all()
        ReplicaManager.init_replica_db()

# ------------------------------------------------------------------
# Funciones auxiliares para enviar correos con JSON adjunto
# ------------------------------------------------------------------
def enviar_correo_con_json(destinatario, asunto, datos_json, tipo="pedido"):
    """
    Envía un correo con un archivo JSON adjunto y enlaces HTML.
    tipo: 'pedido' o 'pago'
    """
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = f"Chiriquí Eats <{app.config['MAIL_USERNAME']}>"
        msg['Reply-To'] = 'chiriquieatss.a.507@gmail.com'
        msg['To'] = destinatario
        msg['Subject'] = asunto
        
        # --- Parte HTML con enlaces ---
        if tipo == "pedido":
            html = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; }}
                    .container {{ max-width: 600px; margin: 20px auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px; }}
                    .btn-confirm {{ background: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 5px; }}
                    .btn-reject {{ background: #dc3545; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 5px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h2>🍽️ Nuevo Pedido en Chiriquí Eats</h2>
                    <p>Hola,</p>
                    <p>Se ha recibido un nuevo pedido en la plataforma. Por favor, confirma si puedes atenderlo:</p>
                    
                    <table>
                        <tr><td><strong>ID Pedido:</strong></td><td>#{datos_json.get('id')}</td></tr>
                        <tr><td><strong>Cliente:</strong></td><td>{datos_json.get('cliente')}</td></tr>
                        <tr><td><strong>Combo:</strong></td><td>{datos_json.get('combo')}</td></tr>
                        <tr><td><strong>Cantidad:</strong></td><td>{datos_json.get('cantidad')}</td></tr>
                        <tr><td><strong>Total:</strong></td><td>${datos_json.get('total')}</td></tr>
                        <tr><td><strong>Fecha:</strong></td><td>{datos_json.get('fecha')}</td></tr>
                    </table>
                    
                    <hr>
                    <p><strong>¿Deseas confirmar este pedido?</strong></p>
                    
                    <!-- ✅ AGREGADO target="_blank" para abrir en nueva pestaña -->
                    <a href="{datos_json.get('confirmar')}" target="_blank" class="btn-confirm">✅ Confirmar Pedido</a>
                    <a href="{datos_json.get('rechazar')}" target="_blank" class="btn-reject">❌ Rechazar Pedido</a>
                    
                    <hr>
                    <p style="color: #666; font-size: 12px;">Este enlace te llevará a la página de confirmación. No necesitas iniciar sesión.</p>
                    <p style="color: #666; font-size: 12px;">También adjuntamos el detalle en formato JSON.</p>
                </div>
            </body>
            </html>
            """
        else:  # tipo == "pago"
            html = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; }}
                    .container {{ max-width: 600px; margin: 20px auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px; background: #f8f9fa; }}
                    .success {{ color: #28a745; font-size: 24px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h2>💰 Pago Confirmado - Pedido #{datos_json.get('id')}</h2>
                    <p>Hola,</p>
                    <p>Se ha confirmado el pago del pedido:</p>
                    
                    <table>
                        <tr><td><strong>ID Pedido:</strong></td><td>#{datos_json.get('id')}</td></tr>
                        <tr><td><strong>Cliente:</strong></td><td>{datos_json.get('cliente')}</td></tr>
                        <tr><td><strong>Combo:</strong></td><td>{datos_json.get('combo')}</td></tr>
                        <tr><td><strong>Cantidad:</strong></td><td>{datos_json.get('cantidad')}</td></tr>
                        <tr><td><strong>Total pagado:</strong></td><td>${datos_json.get('total_pagado')}</td></tr>
                        <tr><td><strong>Transacción Yappy:</strong></td><td>{datos_json.get('transaccion_yappy', 'No registrada')}</td></tr>
                    </table>
                    
                    <p class="success">✅ PAGO COMPLETADO</p>
                    <p>Puedes proceder con la preparación del pedido.</p>
                    
                    <hr>
                    <p style="color: #666; font-size: 12px;">Adjuntamos el detalle en formato JSON para tus registros.</p>
                </div>
            </body>
            </html>
            """
        
        msg.attach(MIMEText(html, 'html'))
        
        # --- Crear archivo JSON adjunto ---
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as tmp:
            json.dump(datos_json, tmp, indent=4, ensure_ascii=False)
            tmp_path = tmp.name
        
        with open(tmp_path, 'rb') as adj:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(adj.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename=confirmacion_{tipo}_{datos_json.get("id", "tmp")}.json')
            msg.attach(part)
        
        # Enviar
        with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as server:
            if app.config['MAIL_PORT'] == 587:
                server.starttls()
            server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            server.send_message(msg)
        
        os.unlink(tmp_path)
        return True
    except Exception as e:
        print(f"Error enviando correo a {destinatario}: {e}")
        return False
# ------------------------------------------------------------------
# Rutas principales
# ------------------------------------------------------------------
@app.route('/')
def index():
    nombres_destacados = [
        'Combo Clásico de Hamburguesa',
        'Combo de Pollo Crujiente',
        'Combo Pizza Personal y Nudos de Ajo',
        'Combo Sushi Variado'
    ]
    
    combos = Combo.query.filter(Combo.name.in_(nombres_destacados)).all()
    
    if len(combos) < 4:
        combos = Combo.query.order_by(Combo.id.desc()).limit(4).all()
    
    imagen_por_nombre = {
        'Combo Clásico de Hamburguesa': 'hamburguesa.png',
        'Combo de Pollo Crujiente': 'pollo.png',
        'Combo Pizza Personal y Nudos de Ajo': 'pizza.png',
        'Combo Sushi Variado': 'sushi.png'
    }
    
    combo_con_pedidos = []
    for combo in combos:
        total_vendido = db.session.query(func.sum(Order.quantity)).filter(Order.combo_id == combo.id).scalar() or 0
        combo_con_pedidos.append((combo, imagen_por_nombre.get(combo.name, 'default.png'), total_vendido))
    
    return render_template('index.html', combos_con_imagen=combo_con_pedidos)

# --------------------- CRUD Empresas ----------------------------
@app.route('/companies')
def list_companies():
    companies = Company.query.all()
    return render_template('companies.html', companies=companies)

@app.route('/company/new', methods=['GET', 'POST'])
def create_company():
    if request.method == 'POST':
        try:
            name = request.form['name']
            email = request.form['email']
            phone = request.form.get('phone', '')
            address = request.form.get('address', '')
            
            company = Company(name=name, email=email, phone=phone, address=address)
            db.session.add(company)
            db.session.commit()
            ReplicaManager.replicate_company(company.to_dict())
            flash('Empresa creada exitosamente', 'success')
            return redirect(url_for('list_companies'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear empresa: {str(e)}', 'danger')
    return render_template('company_form.html', company=None)

@app.route('/company/edit/<int:id>', methods=['GET', 'POST'])
def edit_company(id):
    company = Company.query.get_or_404(id)
    if request.method == 'POST':
        try:
            company.name = request.form['name']
            company.email = request.form['email']
            company.phone = request.form.get('phone', '')
            company.address = request.form.get('address', '')
            db.session.commit()
            ReplicaManager.replicate_company(company.to_dict())
            flash('Empresa actualizada', 'success')
            return redirect(url_for('list_companies'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
    return render_template('company_form.html', company=company)

@app.route('/company/delete/<int:id>')
def delete_company(id):
    try:
        company = Company.query.get_or_404(id)
        ReplicaManager.replicate_company({'id': id}, delete=True)
        db.session.delete(company)
        db.session.commit()
        flash('Empresa eliminada', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar: {str(e)}', 'danger')
    return redirect(url_for('list_companies'))

# --------------------- CRUD Combos ------------------------------
@app.route('/combos')
def list_combos():
    combos = Combo.query.all()
    return render_template('combos.html', combos=combos)

@app.route('/combo/new', methods=['GET', 'POST'])
def create_combo():
    companies = Company.query.all()
    if request.method == 'POST':
        try:
            name = request.form['name']
            description = request.form.get('description', '')
            items = request.form.get('items', '')
            price = float(request.form['price'])
            company_id = int(request.form['company_id'])
            combo = Combo(name=name, description=description, items=items, price=price, company_id=company_id)
            db.session.add(combo)
            db.session.commit()
            ReplicaManager.replicate_combo(combo.to_dict())
            flash('Combo creado', 'success')
            return redirect(url_for('list_combos'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
    return render_template('combo_form.html', combo=None, companies=companies)

@app.route('/combo/edit/<int:id>', methods=['GET', 'POST'])
def edit_combo(id):
    combo = Combo.query.get_or_404(id)
    companies = Company.query.all()
    if request.method == 'POST':
        try:
            combo.name = request.form['name']
            combo.description = request.form.get('description', '')
            combo.items = request.form.get('items', '')
            combo.price = float(request.form['price'])
            combo.company_id = int(request.form['company_id'])
            db.session.commit()
            ReplicaManager.replicate_combo(combo.to_dict())
            flash('Combo actualizado', 'success')
            return redirect(url_for('list_combos'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
    return render_template('combo_form.html', combo=combo, companies=companies)

@app.route('/combo/delete/<int:id>')
def delete_combo(id):
    try:
        combo = Combo.query.get_or_404(id)
        ReplicaManager.replicate_combo({'id': id}, delete=True)
        db.session.delete(combo)
        db.session.commit()
        flash('Combo eliminado', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
    return redirect(url_for('list_combos'))

# --------------------- Pedidos (Orders) -------------------------
@app.route('/orders')
def list_orders():
    orders = Order.query.all()
    return render_template('orders.html', orders=orders)

@app.route('/order/new', methods=['GET', 'POST'])
def create_order():
    combos = Combo.query.all()
    selected_combo_id = request.args.get('combo_id', type=int)
    
    if request.method == 'POST':
        try:
            customer_name = request.form['customer_name']
            combo_id = int(request.form['combo_id'])
            quantity = int(request.form['quantity'])
            
            combo = Combo.query.get(combo_id)
            if not combo:
                raise ValueError("Combo no encontrado")
            
            total_price = combo.price * quantity
            
            order = Order(
                customer_name=customer_name,
                quantity=quantity,
                total_price=total_price,
                status='PENDIENTE',
                company_id=combo.company_id,
                combo_id=combo_id
            )
            db.session.add(order)
            db.session.commit()
            
            token = secrets.token_urlsafe(32)
            order.confirmation_token = token
            db.session.commit()
            
            confirm_url = url_for('confirm_order', token=token, _external=True)
            reject_url = url_for('reject_order', token=token, _external=True)
            
            company = Company.query.get(combo.company_id)
            datos_pedido = {
                'id': order.id,
                'cliente': customer_name,
                'combo': combo.name,
                'cantidad': quantity,
                'total': total_price,
                'fecha': order.created_at.isoformat(),
                'estado': 'PENDIENTE',
                'confirmar': confirm_url,
                'rechazar': reject_url,
                'mensaje': f'Para confirmar este pedido, haz clic en: {confirm_url}\nPara rechazarlo: {reject_url}'
            }
            
            exito = enviar_correo_con_json(
                destinatario=company.email,
                asunto=f"Confirmación de pedido #{order.id} - Chiriquí Eats",
                datos_json=datos_pedido,
                tipo="pedido"
            )
            
            if exito:
                flash('Pedido creado y correo enviado a la empresa', 'success')
            else:
                flash('Pedido creado, pero falló el envío del correo', 'warning')
                
            return redirect(url_for('list_orders'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear pedido: {str(e)}', 'danger')
    
    return render_template('order_form.html', combos=combos, selected_combo_id=selected_combo_id)

@app.route('/order/confirm/<token>')
def confirm_order(token):
    order = Order.query.filter_by(confirmation_token=token).first_or_404()
    
    if order.confirmed:
        flash('Este pedido ya fue confirmado', 'info')
        return render_template('confirmacion.html', order=order, estado='ya_confirmado')
    
    order.confirmed = True
    db.session.commit()
    
    # Actualizar réplica
    order_dict = order.to_dict()
    order_dict['created_at'] = order.created_at.isoformat()
    ReplicaManager.replicate_order(order_dict)
    
    return render_template('confirmacion.html', order=order, estado='confirmado')

@app.route('/order/reject/<token>')
def reject_order(token):
    order = Order.query.filter_by(confirmation_token=token).first_or_404()
    
    if order.status == 'RECHAZADO':
        flash('Este pedido ya fue rechazado', 'info')
        return render_template('confirmacion.html', order=order, estado='ya_rechazado')
    
    order.status = 'RECHAZADO'
    db.session.commit()
    
    return render_template('confirmacion.html', order=order, estado='rechazado')

@app.route('/order/pay/<int:id>')
def pay_order(id):
    try:
        order = Order.query.get_or_404(id)
        if order.status == 'PAGADO':
            flash('Este pedido ya fue pagado', 'info')
            return redirect(url_for('list_orders'))
        
        order.status = 'PAGADO'
        db.session.commit()
        
        order_dict = order.to_dict()
        order_dict['created_at'] = order.created_at.isoformat()
        ReplicaManager.replicate_order(order_dict)
        
        company = order.company
        datos_pago = {
            'id': order.id,
            'cliente': order.customer_name,
            'combo': order.combo.name,
            'cantidad': order.quantity,
            'total_pagado': order.total_price,
            'fecha_pago': datetime.now().isoformat(),
            'estado': 'PAGADO'
        }
        exito = enviar_correo_con_json(
            destinatario=company.email,
            asunto=f"Confirmación de pago - Pedido #{order.id}",
            datos_json=datos_pago,
            tipo="pago"
        )
        if exito:
            flash('Pago registrado. Correo de confirmación enviado a la empresa.', 'success')
        else:
            flash('Pago registrado, pero falló el envío del correo.', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al procesar pago: {str(e)}', 'danger')
    return redirect(url_for('list_orders'))

# --------------------- Simulación de N pedidos -------------------
@app.route('/simulate', methods=['GET', 'POST'])
def simulate():
    resultados = None
    if request.method == 'POST':
        try:
            n = int(request.form['n'])
            if n <= 0:
                flash('N debe ser mayor que 0', 'danger')
                return redirect(url_for('simulate'))
            
            combos = Combo.query.all()
            if not combos:
                flash('Debe existir al menos un combo para simular pedidos', 'danger')
                return redirect(url_for('simulate'))
            
            exitos = 0
            errores = 0
            detalles = []
            
            for i in range(n):
                try:
                    combo = random.choice(combos)
                    cantidad = random.randint(1, 5)
                    total = combo.price * cantidad
                    cliente = f"Simulación_{random.randint(1000, 9999)}"
                    
                    order = Order(
                        customer_name=cliente,
                        quantity=cantidad,
                        total_price=total,
                        status='PENDIENTE',
                        company_id=combo.company_id,
                        combo_id=combo.id
                    )
                    db.session.add(order)
                    db.session.commit()
                    
                    odict = order.to_dict()
                    odict['created_at'] = order.created_at.isoformat()
                    ReplicaManager.replicate_order(odict)
                    
                    exitos += 1
                    detalles.append(f"Pedido {order.id}: {cliente} - combo {combo.name} - OK")
                except Exception as e:
                    errores += 1
                    detalles.append(f"Error en iteración {i+1}: {str(e)}")
                    db.session.rollback()
            
            resultados = {
                'total': n,
                'exitos': exitos,
                'errores': errores,
                'detalles': detalles[:20]
            }
            flash(f'Simulación completada. Éxitos: {exitos}, Errores: {errores}', 'info')
        except Exception as e:
            flash(f'Error en la simulación: {str(e)}', 'danger')
    
    return render_template('simulate.html', resultados=resultados)

@app.route('/confirm-pay')
def confirm_pay():
    try:
        order_id = request.args.get('order_id', type=int)
        transaction_id = request.args.get('transaction_id', '')
        if not order_id or not transaction_id:
            flash('Datos de pago incompletos', 'danger')
            return redirect(url_for('list_orders'))
        
        order = Order.query.get_or_404(order_id)
        if order.status == 'PAGADO':
            flash('Este pedido ya fue pagado', 'info')
            return redirect(url_for('list_orders'))
        
        order.status = 'PAGADO'
        db.session.commit()
        
        order_dict = order.to_dict()
        order_dict['created_at'] = order.created_at.isoformat()
        ReplicaManager.replicate_order(order_dict)
        
        company = order.company
        datos_pago = {
            'id': order.id,
            'cliente': order.customer_name,
            'combo': order.combo.name,
            'cantidad': order.quantity,
            'total_pagado': order.total_price,
            'fecha_pago': datetime.now().isoformat(),
            'estado': 'PAGADO',
            'transaccion_yappy': transaction_id
        }
        exito = enviar_correo_con_json(
            destinatario=company.email,
            asunto=f"Confirmación de pago - Pedido #{order.id} (Yappy)",
            datos_json=datos_pago,
            tipo="pago"
        )
        if exito:
            flash(f'Pago registrado con Yappy (Transacción: {transaction_id}). Correo enviado a la empresa.', 'success')
        else:
            flash('Pago registrado, pero falló el envío del correo.', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al procesar pago: {str(e)}', 'danger')
    return redirect(url_for('list_orders'))

@app.route('/order/delete/<int:id>')
def delete_order(id):
    try:
        order = Order.query.get_or_404(id)
        if order.status != 'PAGADO':
            flash('Solo se pueden eliminar pedidos que ya hayan sido pagados.', 'warning')
            return redirect(url_for('list_orders'))
        
        ReplicaManager.replicate_order({'id': order.id}, delete=True)
        db.session.delete(order)
        db.session.commit()
        flash('Pedido eliminado correctamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar pedido: {str(e)}', 'danger')
    return redirect(url_for('list_orders'))

# ------------------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)