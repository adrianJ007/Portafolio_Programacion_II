from datetime import datetime
from pathlib import Path
from uuid import uuid4

from flask import Blueprint, current_app, flash, redirect, render_template, request, send_file, session, url_for

from app.services.email_service import send_email
from app.services.json_export_service import export_json
from app.services.mock_replication_service import replicate
from app.services.pdf_service import build_guide_profile_pdf, build_invoice_pdf
from app.services.storage_service import create, read, update
from app.services.upload_service import save_upload
from app.utils.decorators import roles_required

bp = Blueprint("payments", __name__, url_prefix="/payments")


def notify_copies(subject, body, attachments, email_type, related_id):
    recipients = [current_app.config.get("MAIL_ADMIN_RECEIVER")] + [x.get("email") for x in read("operators")]
    for recipient in dict.fromkeys(x for x in recipients if x):
        send_email(recipient, subject, body, attachments=attachments, email_type=email_type, related_id=related_id, payment_id=related_id)


def _payment_html(subject, body, reservation=None, payment=None, worker=None):
    services = reservation.get("services", []) if reservation else []
    providers = reservation.get("providers", []) if reservation else []
    service_rows = "".join(
        f"<tr><td style='padding:9px;border-bottom:1px solid #24434a'>{s.get('name','')}</td><td style='padding:9px;border-bottom:1px solid #24434a'>{s.get('provider_name','Turismo Chiriquí')}</td><td style='padding:9px;border-bottom:1px solid #24434a;text-align:right'>${s.get('price',0)}</td></tr>"
        for s in services
    ) or "<tr><td colspan='3' style='padding:9px;color:#91a8ad'>Sin servicios adicionales.</td></tr>"
    provider_text = "".join(f"<li>{p.get('name')} · {p.get('service')} · {p.get('status')}</li>" for p in providers) or "<li>No aplica</li>"
    guide = "Por asignar"
    if worker:
        guide = f"{worker.get('name')} · {worker.get('phone','')} · {worker.get('languages','')} · {worker.get('specialty','')}"
    total = payment.get("amount") if payment else reservation.get("total", 0) if reservation else 0
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"></head>
<body style="margin:0;background:#06131b;font-family:Arial,'Segoe UI',sans-serif;color:#d5e5e4">
<table width="100%" cellpadding="0" cellspacing="0" style="padding:28px 10px;background:linear-gradient(135deg,#02080d,#082934)"><tr><td align="center">
<table width="680" cellpadding="0" cellspacing="0" style="max-width:680px;background:#0d2731;border:1px solid #29454d;border-radius:24px;overflow:hidden;box-shadow:0 28px 80px rgba(0,0,0,.35)">
<tr><td style="padding:30px;background:linear-gradient(135deg,#123b45,#071923)"><div style="color:#39dec7;font-size:12px;letter-spacing:2px;text-transform:uppercase;font-weight:bold">Turismo Chiriquí</div><h1 style="color:#fff;font-size:28px;margin:10px 0 0">{subject}</h1></td></tr>
<tr><td style="padding:26px"><p style="line-height:1.7">{str(body).replace(chr(10),'<br>')}</p>
<table width="100%" cellpadding="0" cellspacing="0" style="margin:18px 0;border:1px solid #24434a;border-radius:16px;overflow:hidden"><tr><td style="padding:14px;background:#102f38"><b>Resumen de reserva</b></td></tr><tr><td style="padding:16px;line-height:1.7">
Cliente: {reservation.get('client','') if reservation else ''}<br>Reserva: #{reservation.get('id','') if reservation else ''}<br>Tour: {reservation.get('tour_name','') if reservation else ''}<br>Ruta: {reservation.get('route_name','') if reservation else ''}<br>Fecha: {reservation.get('date','') if reservation else ''}<br>Personas: {reservation.get('people','') if reservation else ''}<br>Guía: {guide}<br>Total: <b style="color:#39dec7">${total}</b>
</td></tr></table>
<h3 style="color:#39dec7">Servicios adicionales</h3><table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse">{service_rows}</table>
<h3 style="color:#39dec7">Empresas proveedoras</h3><ul>{provider_text}</ul>
<p style="margin-top:24px"><a href="http://127.0.0.1:5000/login" style="padding:13px 22px;border-radius:999px;background:#39dec7;color:#03201c;text-decoration:none;font-weight:bold">Abrir Turismo Chiriquí</a></p>
</td></tr><tr><td style="padding:18px 26px;border-top:1px solid #29454d;color:#91a8ad;font-size:12px">Turismo Chiriquí · David, Chiriquí · +507 6000-2026 · info@turismochiriqui.com</td></tr>
</table></td></tr></table></body></html>"""


def _active_payment_for(reservation_id):
    blocked = {"received", "validated", "pending cash", "cash received", "requires review"}
    return next((p for p in read("payments") if int(p.get("reservation_id", 0)) == int(reservation_id) and p.get("status") in blocked), None)


@bp.route("/upload", methods=["GET", "POST"])
@roles_required("client")
def upload():
    paid_ids = {int(p.get("reservation_id", 0)) for p in read("payments") if p.get("status") in ("received", "validated", "pending cash", "cash received")}
    reservations = [
        x for x in read("reservations")
        if int(x.get("user_id", 0)) == int(session["user"])
        and x.get("status") in ("pre-reservation", "payment rejected", "payment received", "pending cash payment")
        and int(x.get("id", 0)) not in paid_ids
    ]
    if request.method == "POST":
        try:
            # --- OBTENCIÓN SEGURA DEL ID DE RESERVA (soporta form y JSON) ---
            reservation_id = request.form.get("reservation_id")
            if not reservation_id:
                # Intenta obtenerlo de una petición JSON
                data = request.get_json(silent=True)
                if data:
                    reservation_id = data.get("reservation_id")
            if not reservation_id:
                raise ValueError("Falta el ID de la reserva (reservation_id). Asegúrate de incluir el campo en el formulario o en el JSON.")

            reservation = next(
                (x for x in read("reservations")
                 if int(x["id"]) == int(reservation_id) and int(x.get("user_id", 0)) == int(session["user"])),
                None
            )
            if reservation is None:
                raise ValueError("Reserva no encontrada o no pertenece a tu usuario.")

            existing = _active_payment_for(reservation["id"])
            if existing:
                flash("Ya existe un pago o comprobante pendiente para esta reserva. Espera validación o solicita revisión.", "error")
                return redirect(url_for("payments.upload"))

            # Obtención segura del resto de campos requeridos
            method = request.form.get("method")
            if not method:
                raise ValueError("Debes seleccionar un método de pago.")

            email = request.form.get("email")
            if not email:
                raise ValueError("El correo electrónico es obligatorio.")
            phone = request.form.get("phone", "")

            capture = ""
            reference = ""
            if method == "Yappy":
                capture = save_upload(request.files.get("capture"), "payments")
                state = "received"
                reservation_state = "payment received"
            elif method == "Tarjeta simulada":
                reference = f"SIM-{uuid4().hex[:10].upper()}"
                state = "validated"
                reservation_state = "payment validated"
            else:
                reference = f"EFE-{uuid4().hex[:8].upper()}"
                state = "pending cash"
                reservation_state = "pending cash payment"

            item = create("payments", {
                "reservation_id": reservation["id"], "client": reservation["client"], "tour": reservation["tour_name"],
                "route": reservation.get("route_name"), "tour_date": reservation["date"], "subtotal": reservation["subtotal"],
                "itbms": reservation["itbms"], "discount": reservation["discount"], "guide_cost": reservation["guide_cost"],
                "service_charge": reservation["service_charge"], "amount": reservation["total"], "method": method,
                "merchant": "Turismo Chiriquí", "yappy": "+507 6000-2026" if method == "Yappy" else "",
                "reference": reference, "email": email, "phone": phone,
                "capture": capture, "status": state, "rejection_reason": "", "date": datetime.now().isoformat(timespec="seconds"),
                "validated_by": "", "history": [{"date": datetime.now().isoformat(timespec="seconds"), "status": state, "actor": session["name"]}],
            })
            update("reservations", reservation["id"], {"status": reservation_state})
            receipt = export_json("payments", item)
            update("payments", item["id"], {"receipt_path": str(receipt)})
            replicate("payment", item["id"])
            body = f"Pago #{item['id']}\nReserva: #{reservation['id']}\nTour: {reservation['tour_name']}\nMétodo: {method}\nMonto: ${item['amount']}\nEstado: {state}"
            attachments = [receipt] + ([current_app.config["UPLOAD_DIR"] / capture] if capture else [])
            send_email(item["email"], "Pago registrado", body, attachments=attachments, email_type="captura recibida" if capture else "pago registrado", related_id=item["id"], reservation_id=reservation["id"], payment_id=item["id"])
            notify_copies("Nuevo pago recibido", body, attachments, "notificación de pago", item["id"])
            flash("Pago registrado y comprobante enviado", "success")
            return redirect(url_for("client.dashboard"))
        except (ValueError, StopIteration) as exc:
            flash(str(exc), "error")
    return render_template("client/payment_upload.html", reservations=reservations)


@bp.post("/<int:item_id>/<action>")
@roles_required("admin", "operator")
def status(item_id, action):
    allowed = {"validate": "validated", "reject": "rejected", "retry": "requires new capture", "cash": "cash received"}
    state = allowed.get(action, "pending")
    reason = request.form.get("reason", "")
    item = next((p for p in read("payments") if int(p.get("id", 0)) == int(item_id)), None)
    if not item:
        return "Pago no encontrado", 404
    history = list(item.get("history") or [])
    history.append({"date": datetime.now().isoformat(timespec="seconds"), "status": state, "actor": session.get("name"), "reason": reason})
    item = update("payments", item_id, {"status": state, "validated_by": session.get("name"), "rejection_reason": reason, "history": history})
    reservation_state = {"validated": "payment validated", "rejected": "payment rejected", "requires new capture": "payment rejected", "cash received": "payment validated"}[state]
    reservation = update("reservations", item["reservation_id"], {"status": reservation_state, "tracking_status": "confirmada" if state in ("validated", "cash received") else "pago rechazado"})
    replicate("payment", item_id, "STATUS")
    receipt = export_json("payments", item)
    attachments = [receipt]
    if item.get("capture"):
        capture_path = Path(current_app.config["UPLOAD_DIR"]) / item["capture"]
        if capture_path.is_file():
            attachments.append(capture_path)
    worker = None
    if state in ("validated", "cash received"):
        worker = next((w for w in read("workers") if str(w.get("id")) == str((reservation or {}).get("worker_id"))), None)
        invoice = build_invoice_pdf(item, reservation, worker)
        update("payments", item_id, {"invoice_pdf": str(invoice)})
        attachments.append(invoice)
        if reservation and reservation.get("itinerary_pdf") and Path(str(reservation["itinerary_pdf"])).is_file():
            attachments.append(reservation["itinerary_pdf"])
        if worker:
            guide_pdf = build_guide_profile_pdf(worker, reservation)
            attachments.append(guide_pdf)
    body = f"Pago #{item_id}\nReserva: #{item['reservation_id']}\nMonto: ${item['amount']}\nMétodo: {item['method']}\nEstado: {state}\nMotivo: {reason or 'No aplica'}\nRevisado por: {session.get('name')}"
    html_body = _payment_html("Estado de tu pago", body, reservation, item, worker if state in ("validated", "cash received") else None)
    send_email(item["email"], "Estado de tu pago", body, html_body=html_body, attachments=attachments, email_type=f"pago {state}", related_id=item_id, reservation_id=item["reservation_id"], payment_id=item_id)
    notify_copies("Pago actualizado", body, attachments, f"pago {state}", item_id)
    flash("Pago actualizado, factura generada cuando aplica y notificaciones procesadas", "success")
    return redirect(url_for("admin.crud", module="payments"))


@bp.get("/invoice/<int:item_id>")
@roles_required("admin", "operator", "client")
def invoice(item_id):
    payment = next((p for p in read("payments") if int(p.get("id", 0)) == int(item_id)), None)
    if not payment:
        return "Pago no encontrado", 404
    if session.get("role") == "client":
        reservation = next((r for r in read("reservations") if int(r.get("id", 0)) == int(payment.get("reservation_id", 0))), None)
        if not reservation or int(reservation.get("user_id", 0)) != int(session["user"]):
            return "No autorizado", 403
    return send_file(payment["invoice_pdf"], as_attachment=True) if payment.get("invoice_pdf") else ("Factura no disponible", 404)