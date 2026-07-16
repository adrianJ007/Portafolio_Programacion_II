from html import escape
from pathlib import Path

from flask import Blueprint, current_app, flash, redirect, render_template, request, send_from_directory, url_for
from werkzeug.security import generate_password_hash

from app.services.email_service import send_email
from app.services.mock_replication_service import replicate
from app.services.pdf_service import build_guide_profile_pdf
from app.services.settings_service import get_settings, update_settings
from app.services.storage_service import create, delete, read, update
from app.services.upload_service import save_upload
from app.utils.decorators import roles_required

bp = Blueprint("admin", __name__, url_prefix="/admin")


def _assignable_workers():
    hidden = {"inactive", "inactivo", "suspended", "suspendido", "rejected", "rechazado", "pending confirmation", "pendiente de confirmación"}
    unavailable = {"no disponible", "ocupado en gira", "suspendido"}
    rows = []
    for worker in read("workers"):
        status = str(worker.get("status", "active")).strip().lower()
        availability = str(worker.get("availability", "Disponible")).strip().lower()
        if status in hidden or availability in unavailable:
            continue
        rows.append(worker)
    return sorted(rows, key=lambda item: str(item.get("name", "")).lower())


def _guide_assignment_html(reservation, worker, meeting, code):
    photo = worker.get("profile_photo") or worker.get("photo") or ""
    photo_block = f"<p style='margin:0 0 12px;color:#5d6f73'>Foto registrada en expediente: <b>{escape(photo)}</b></p>" if photo else ""
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"></head>
<body style="margin:0;background:#edf6f5;font-family:Arial,'Segoe UI',sans-serif;color:#123">
<table width="100%" cellpadding="0" cellspacing="0" style="padding:28px 10px;background:#edf6f5"><tr><td align="center">
<table width="680" cellpadding="0" cellspacing="0" style="max-width:680px;background:#ffffff;border:1px solid #d9e8e6;border-radius:24px;overflow:hidden;box-shadow:0 20px 60px rgba(5,38,45,.12)">
<tr><td style="padding:30px;background:#06313a;color:#fff"><div style="font-size:12px;letter-spacing:2px;text-transform:uppercase;color:#62ead9;font-weight:bold">Turismo Chiriquí</div><h1 style="margin:10px 0 0;font-size:28px">Tu guía fue asignado</h1></td></tr>
<tr><td style="padding:26px">
<p style="font-size:16px;line-height:1.7">Tu experiencia <b>{escape(str(reservation.get('tour_name','')))}</b> ya tiene guía confirmado.</p>
<table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #d9e8e6;border-radius:18px;overflow:hidden;margin:18px 0">
<tr><td style="padding:18px;background:#f7fbfb"><b style="font-size:18px;color:#06313a">{escape(str(worker.get('name','Guía asignado')))}</b><br>{escape(str(worker.get('specialty','Turismo')))}</td></tr>
<tr><td style="padding:18px;line-height:1.8">
{photo_block}
<b>Teléfono:</b> {escape(str(worker.get('phone','Por confirmar')))}<br>
<b>Correo:</b> {escape(str(worker.get('email','Por confirmar')))}<br>
<b>Idiomas:</b> {escape(str(worker.get('languages','Español')))}<br>
<b>Experiencia:</b> {escape(str(worker.get('experience','Experiencia verificada')))}<br>
<b>Certificación:</b> {escape(str(worker.get('certification','Validada por Turismo Chiriquí')))}
</td></tr></table>
<table width="100%" cellpadding="0" cellspacing="0"><tr>
<td style="padding:14px;border:1px solid #d9e8e6;border-radius:14px"><b>Punto de encuentro</b><br>{escape(str(meeting))}</td>
<td width="14"></td>
<td style="padding:14px;border:1px solid #d9e8e6;border-radius:14px"><b>Código</b><br>{escape(str(code))}</td>
</tr></table>
<p style="color:#5d6f73;line-height:1.7">Llega 15 minutos antes, lleva documento de identidad, agua y calzado cómodo. Si tienes dudas, responde este correo o contacta soporte.</p>
</td></tr>
<tr><td style="padding:18px 26px;background:#f7fbfb;color:#5d6f73;font-size:12px">Turismo Chiriquí · David, Chiriquí · +507 6000-2026 · info@turismochiriqui.com</td></tr>
</table></td></tr></table></body></html>"""

MODULES = {
    "clients": "clients",
    "workers": "workers",
    "operators": "operators",
    "tours": "tours",
    "services": "services",
    "promotions": "promotions",
    "providers": "providers",
    "provider_services": "provider_services",
    "provider_tracking": "provider_tracking",
    "reservations": "reservations",
    "payments": "payments",
    "complaints": "complaints",
    "emails": "emails",
}

LABELS = {
    "clients": "Clientes",
    "workers": "Guías y trabajadores",
    "operators": "Operarios",
    "tours": "Giras",
    "services": "Servicios adicionales",
    "promotions": "Promociones",
    "providers": "Empresas proveedoras",
    "provider_services": "Servicios de empresas",
    "provider_tracking": "Seguimiento de proveedores",
    "reservations": "Reservas",
    "payments": "Pagos",
    "complaints": "Quejas",
    "emails": "Correos",
}

FIELDS = {
    "clients": [("name", "Nombre"), ("email", "Correo"), ("phone", "Teléfono"), ("status", "Estado")],
    "workers": [
        ("name", "Nombre completo"), ("email", "Correo"), ("phone", "Teléfono"), ("identity", "Cédula"),
        ("type", "Tipo"), ("specialty", "Especialidad"), ("languages", "Idiomas"),
        ("recommended_capacity", "Capacidad máxima recomendada"), ("experience", "Experiencia"),
        ("availability", "Disponibilidad"), ("documents_verified", "Estado de documentos"),
        ("internal_notes", "Observaciones internas"), ("status", "Estado"), ("profile_photo", "Foto de perfil"),
        ("identity_front", "Cédula frontal"), ("identity_back", "Cédula reverso"), ("certification", "Certificación"),
    ],
    "operators": [("name", "Nombre"), ("email", "Correo"), ("phone", "Teléfono"), ("position", "Cargo"), ("shift", "Turno"), ("area", "Área"), ("status", "Estado"), ("image", "Foto")],
    "tours": [
        ("name", "Nombre"), ("destination", "Destino"), ("description", "Descripción"), ("price_base", "Precio base"),
        ("suggested_duration", "Duración"), ("capacity", "Cupos máximos"), ("minimum_people", "Mínimo de personas"),
        ("maximum_people", "Máximo de personas"), ("guide_capacity", "Personas por guía"),
        ("extra_guide_price", "Precio de guía adicional"), ("difficulty", "Dificultad"), ("provider", "Proveedor"),
        ("promotion", "Promoción"), ("status", "Estado"), ("image", "Imagen"),
    ],
    "services": [
        ("name", "Nombre"), ("provider_name", "Empresa proveedora"), ("description", "Descripción"), ("price", "Precio"),
        ("applies_itbms", "Aplica ITBMS"), ("profit_percent", "Ganancia %"), ("capacity_daily", "Capacidad diaria"),
        ("coverage_zone", "Zona de cobertura"), ("availability", "Disponibilidad"), ("policy", "Política del servicio"),
        ("status", "Estado"), ("image", "Imagen"),
    ],
    "promotions": [("code", "Código"), ("name", "Nombre"), ("description", "Descripción"), ("discount_percent", "Descuento %"), ("start_date", "Fecha inicio"), ("end_date", "Fecha fin"), ("usage_limit", "Límite de uso"), ("used_count", "Usos"), ("status", "Estado")],
    "providers": [
        ("name", "Nombre comercial"), ("ruc", "RUC o identificación fiscal"), ("legal_representative", "Representante legal"),
        ("email", "Correo"), ("phone", "Teléfono"), ("address", "Dirección"), ("service_type", "Tipo de servicio"),
        ("description", "Descripción"), ("website", "Sitio web"), ("social", "Redes sociales"),
        ("message", "Mensaje de presentación"), ("status", "Estado"), ("logo", "Logo o foto"), ("validation_document", "Documento"),
    ],
    "provider_services": [
        ("provider_name", "Empresa"), ("name", "Servicio"), ("type", "Tipo"), ("description", "Descripción"),
        ("price", "Precio"), ("applies_itbms", "Aplica ITBMS"), ("profit_percent", "Ganancia %"),
        ("capacity_daily", "Capacidad diaria"), ("coverage_zone", "Zona"), ("availability", "Disponibilidad"),
        ("policy", "Política"), ("status", "Estado"), ("image", "Imagen"),
    ],
    "provider_tracking": [
        ("reservation_id", "Reserva"), ("tour", "Tour"), ("client", "Cliente"), ("service", "Servicio"),
        ("provider_name", "Empresa"), ("contact", "Contacto"), ("required_time", "Hora requerida"),
        ("status", "Estado"), ("observations", "Observaciones"),
    ],
    "reservations": [("client", "Cliente"), ("tour_name", "Gira"), ("date", "Fecha"), ("people", "Personas"), ("total", "Total"), ("status", "Estado")],
    "payments": [("reservation_id", "Reserva"), ("amount", "Monto"), ("email", "Correo"), ("capture", "Captura"), ("date", "Fecha"), ("status", "Estado")],
    "complaints": [("subject", "Asunto"), ("message", "Mensaje"), ("priority", "Prioridad"), ("status", "Estado"), ("response", "Respuesta")],
    "emails": [("to", "Destinatario"), ("subject", "Asunto"), ("type", "Tipo"), ("status", "Estado"), ("smtp_error", "Error SMTP")],
}


@bp.get("/")
@roles_required("admin")
def dashboard():
    data = {key: read(source) for key, source in MODULES.items()}
    metrics = {LABELS[key]: len(value) for key, value in data.items() if key not in {"emails", "provider_tracking"}}
    metrics["Ingresos simulados"] = sum(float(x.get("total", 0)) for x in data["reservations"] if x.get("status") in ("paid", "pagada", "completed", "completada", "payment validated"))
    return render_template("admin/dashboard.html", metrics=metrics, logs=read("logs")[:10], providers=read("providers"), provider_services=read("provider_services"), settings=get_settings())


@bp.post("/settings/guides")
@roles_required("admin")
def guide_settings():
    update_settings(request.form)
    flash("Reglas de guías actualizadas correctamente.", "success")
    return redirect(url_for("admin.dashboard"))


@bp.route("/crud/<module>", methods=["GET", "POST"])
@roles_required("admin")
def crud(module):
    if module not in MODULES:
        return "Módulo inválido", 404
    if request.method == "POST":
        payload = request.form.to_dict()
        item_id = payload.pop("id", None)
        image = request.files.get("image_file")
        if image and image.filename:
            try:
                payload["image"] = save_upload(image, "tours" if module == "tours" else "profiles")
            except ValueError as exc:
                flash(str(exc), "error")
                return redirect(url_for("admin.crud", module=module))
        item = update(module, item_id, payload) if item_id else create(module, payload)
        replicate(module, item["id"], "UPDATE" if item_id else "INSERT")
        flash("Cambios guardados correctamente", "success")
        return redirect(url_for("admin.crud", module=module))

    q = request.args.get("q", "").lower()
    rows = [x for x in read(module) if q in str(x).lower()]
    if module == "reservations":
        return render_template("admin/reservations.html", rows=rows, workers=_assignable_workers(), settings=get_settings())
    if module == "payments":
        return render_template("admin/payments_manage.html", rows=rows)
    return render_template("admin/crud.html", module=module, module_label=LABELS[module], fields=FIELDS[module], rows=rows)


@bp.post("/crud/<module>/<int:item_id>/delete")
@roles_required("admin")
def remove(module, item_id):
    delete(module, item_id)
    replicate(module, item_id, "DELETE")
    flash("Registro eliminado", "success")
    return redirect(url_for("admin.crud", module=module))


@bp.route("/media", methods=["GET", "POST"])
@roles_required("admin")
def media():
    if request.method == "POST":
        try:
            path = save_upload(request.files.get("image"), request.form.get("category", "profiles"))
            flash(f"Imagen guardada: {path}", "success")
        except ValueError as exc:
            flash(str(exc), "error")
    return render_template("admin/media.html")


@bp.get("/uploads/<path:filename>")
@roles_required("admin", "operator", "worker", "client", "provider")
def uploaded_file(filename):
    return send_from_directory(current_app.config["UPLOAD_DIR"], filename)


@bp.get("/tour-proposals")
@roles_required("admin")
def proposals():
    return render_template("admin/proposals.html", rows=read("tour_proposals"))


@bp.post("/tour-proposals/<int:item_id>/<action>")
@roles_required("admin")
def proposal_action(item_id, action):
    states = {"approve": "approved", "reject": "rejected", "changes": "requires changes", "review": "in review"}
    proposal = update("tour_proposals", item_id, {"status": states.get(action, "in review"), "admin_comment": request.form.get("comment", "")})
    replicate("tour proposal", item_id, "STATUS")
    if action == "approve" and proposal:
        existing = next((tour for tour in read("tours") if str(tour.get("source_proposal_id", "")) == str(proposal.get("id"))), None)
        tour_payload = {
            "name": proposal["name"], "destination": proposal["destination"], "description": proposal["description"],
            "price_base": proposal["suggested_price"], "suggested_duration": proposal["duration"],
            "capacity": proposal["suggested_capacity"], "minimum_people": 1, "maximum_people": proposal["suggested_capacity"],
            "guide_capacity": 8, "extra_guide_price": 45, "difficulty": proposal["difficulty"],
            "includes_transport": proposal.get("includes_transport", False), "includes_food": proposal.get("includes_food", False),
            "provider_id": proposal.get("provider_id"), "provider": proposal.get("provider_name", proposal.get("guide_name", "")),
            "provider_email": proposal.get("provider_email", ""), "source_proposal_id": proposal.get("id"), "route_options": proposal.get("route_options", ""),
            "requirements": proposal.get("requirements", ""), "policy": proposal.get("policy", ""), "status": "published", "image": proposal.get("image", ""),
        }
        if existing:
            update("tours", existing["id"], tour_payload)
        else:
            create("tours", tour_payload)
        if proposal.get("provider_email"):
            send_email(proposal["provider_email"], "Gira aprobada y publicada", f"Tu gira {proposal['name']} fue aprobada y ya puede ser reservada por clientes.", email_type="gira de empresa", related_id=item_id)
    elif proposal and proposal.get("provider_email"):
        send_email(proposal["provider_email"], f"Estado de gira: {proposal['status']}", f"Tu propuesta {proposal['name']} quedó en estado: {proposal['status']}. {proposal.get('admin_comment','')}", email_type="gira de empresa", related_id=item_id)
    flash("Propuesta actualizada", "success")
    return redirect(url_for("admin.proposals"))


@bp.post("/providers/<int:item_id>/<action>")
@roles_required("admin")
def provider_action(item_id, action):
    states = {"approve": "aprobada", "reject": "rechazada", "info": "requiere información", "suspend": "suspendida"}
    provider = update("providers", item_id, {"status": states.get(action, "pendiente de revisión"), "admin_comment": request.form.get("comment", "")})
    if provider:
        subject = f"Estado de empresa aliada: {provider['status']}"
        send_email(provider["email"], subject, f"Hola {provider['name']}, tu solicitud en Turismo Chiriquí ahora está: {provider['status']}. {provider.get('admin_comment','')}", email_type="empresa aliada", related_id=item_id)
        replicate("provider", item_id, "STATUS")
    flash("Empresa actualizada", "success")
    return redirect(url_for("admin.crud", module="providers"))


@bp.post("/provider-services/<int:item_id>/<action>")
@roles_required("admin")
def provider_service_action(item_id, action):
    states = {"approve": "aprobado", "reject": "rechazado", "info": "requiere información", "suspend": "suspendido"}
    service = update("provider_services", item_id, {"status": states.get(action, "pendiente de revisión"), "admin_comment": request.form.get("comment", "")})
    if service:
        if action == "approve":
            create("services", {
                "name": service["name"],
                "provider_id": service.get("provider_id"),
                "provider_name": service.get("provider_name"),
                "description": service["description"],
                "price": service["price"],
                "applies_itbms": service.get("applies_itbms", "Sí"),
                "profit_percent": service.get("profit_percent", 15),
                "capacity_daily": service.get("capacity_daily", ""),
                "coverage_zone": service.get("coverage_zone", ""),
                "availability": service.get("availability", "Disponible"),
                "policy": service.get("policy", ""),
                "status": "approved",
                "image": service.get("image", ""),
            })
        send_email(service.get("provider_email", ""), f"Servicio {service['status']}", f"El servicio {service['name']} quedó en estado: {service['status']}.", email_type="servicio de empresa", related_id=item_id)
        replicate("provider service", item_id, "STATUS")
    flash("Servicio de empresa actualizado", "success")
    return redirect(url_for("admin.crud", module="provider_services"))


@bp.post("/reservations/<int:item_id>/assign")
@roles_required("admin")
def assign_reservation(item_id):
    reservation = next((x for x in read("reservations") if int(x["id"]) == item_id), None)
    if not reservation or reservation.get("status") not in ("payment validated", "confirmed", "guide assigned", "itinerary confirmed"):
        flash("Primero debes validar el pago.", "error")
    else:
        worker = next((x for x in read("workers") if int(x["id"]) == int(request.form["worker_id"])), None)
        code = f"TC-RES-{item_id:06d}"
        meeting = request.form["meeting_point"]
        guide_snapshot = {}
        if worker:
            guide_snapshot = {
                "guide_name": worker.get("name", ""),
                "guide_email": worker.get("email", ""),
                "guide_phone": worker.get("phone", ""),
                "guide_languages": worker.get("languages", ""),
                "guide_experience": worker.get("experience", ""),
                "guide_specialty": worker.get("specialty", ""),
                "guide_certification": worker.get("certification", ""),
                "guide_profile_photo": worker.get("profile_photo") or worker.get("photo") or "",
            }
        updated_reservation = update("reservations", item_id, {
            "worker_id": int(request.form["worker_id"]), "meeting_point": meeting, "status": "guide assigned",
            "itinerary_status": reservation.get("itinerary_status", "pendiente de propuesta"),
            "assignment_status": "pending acceptance", "verification_code": code, "check_in_status": "pending check-in",
            "tracking_status": "guía asignado",
            **guide_snapshot,
        })
        create("tracking_events", {"reservation_id": item_id, "status": "guía asignado", "note": f"Guía asignado: {worker['name'] if worker else 'Pendiente'}", "actor": "Administración", "created_at": __import__("datetime").datetime.now().isoformat(timespec="seconds")})
        replicate("reservation", item_id, "ASSIGN")
        if worker:
            body_client = f"Tu guía fue asignado correctamente.\n\nGuía: {worker['name']}\nTeléfono: {worker.get('phone','Por confirmar')}\nCorreo: {worker.get('email','Por confirmar')}\nEspecialidad: {worker.get('specialty','Turismo')}\nIdiomas: {worker.get('languages','Español')}\nExperiencia: {worker.get('experience','Experiencia turística verificada')}\nCertificación: {worker.get('certification','Verificada por Turismo Chiriquí')}\n\nPunto de encuentro: {meeting}\nCódigo de verificación: {code}\n\nLlega 15 minutos antes y presenta este código."
            attachments = [build_guide_profile_pdf(worker, updated_reservation or reservation)]
            for rel_path in [worker.get("profile_photo"), worker.get("certification_document"), worker.get("experience_document")]:
                if rel_path and (Path(current_app.config["UPLOAD_DIR"]) / rel_path).is_file():
                    attachments.append(Path(current_app.config["UPLOAD_DIR"]) / rel_path)
            if get_settings().get("allow_sensitive_guide_documents_email"):
                for rel_path in [worker.get("identity_front"), worker.get("identity_back"), worker.get("license_document")]:
                    if rel_path and (Path(current_app.config["UPLOAD_DIR"]) / rel_path).is_file():
                        attachments.append(Path(current_app.config["UPLOAD_DIR"]) / rel_path)
            send_email(reservation["notification_email"], "Guía asignado a tu gira", body_client, html_body=_guide_assignment_html(updated_reservation or reservation, worker, meeting, code), attachments=attachments, email_type="guía asignado", related_id=item_id, reservation_id=item_id)
            send_email(worker["email"], "Nueva gira asignada", f"Cliente: {reservation['client']}\nPersonas: {reservation['people']}\nGira: {reservation['tour_name']}\nRuta: {reservation['route_name']}\nFecha: {reservation['date']}\nPunto de encuentro: {meeting}\nCódigo: {code}\nObservaciones: {reservation.get('preferences','Sin observaciones')}", email_type="gira asignada", related_id=item_id, reservation_id=item_id)
        flash("Asignación enviada y partes notificadas.", "success")
    return redirect(url_for("admin.crud", module="reservations"))


@bp.post("/reservations/<int:item_id>/itinerary")
@roles_required("admin")
def confirm_itinerary(item_id):
    reservation = next((x for x in read("reservations") if int(x["id"]) == item_id), None)
    if not reservation or reservation.get("status") not in ("payment validated", "confirmed", "guide assigned", "itinerary confirmed"):
        flash("No puedes confirmar el itinerario hasta validar el pago.", "error")
    else:
        update("reservations", item_id, {"status": "itinerary confirmed", "itinerary_status": "confirmado por cliente"})
        replicate("reservation", item_id, "STATUS")
        flash("Itinerario confirmado", "success")
    return redirect(url_for("admin.crud", module="reservations"))


@bp.post("/reminders/test")
@roles_required("admin")
def test_reminders():
    sent = 0
    workers = {int(x["id"]): x for x in read("workers")}
    for reservation in read("reservations"):
        if reservation.get("status") not in ("payment validated", "guide assigned", "itinerary confirmed"):
            continue
        body = f"Recordatorio de gira\nTour: {reservation['tour_name']}\nFecha: {reservation['date']}\nPunto de encuentro: {reservation.get('meeting_point','Por confirmar')}\nCódigo: {reservation.get('verification_code','Pendiente')}\nRecomendación: llega 15 minutos antes."
        send_email(reservation["notification_email"], "Recordatorio de tu próxima gira", body, email_type="recordatorio de gira", related_id=reservation["id"], reservation_id=reservation["id"])
        sent += 1
        worker = workers.get(int(reservation.get("worker_id") or 0))
        if worker:
            send_email(worker["email"], "Recordatorio de gira asignada", body, email_type="recordatorio de guía", related_id=reservation["id"], reservation_id=reservation["id"])
            sent += 1
    flash(f"Recordatorios de prueba procesados: {sent}", "success")
    return redirect(url_for("admin.dashboard"))


@bp.get("/guide-applications")
@roles_required("admin")
def guide_applications():
    return render_template("admin/guide_applications.html", rows=read("guide_applications"))


@bp.post("/guide-applications/<int:item_id>/<action>")
@roles_required("admin")
def guide_application_action(item_id, action):
    states = {"approve": "approved", "reject": "rejected", "info": "more information required"}
    item = update("guide_applications", item_id, {"status": states[action], "admin_comment": request.form.get("comment", "")})
    if action == "approve" and item:
        create("workers", {"user_id": None, "name": item["name"], "email": item["email"], "phone": item["phone"], "image": item["photo"], "type": "guía turístico", "specialty": item["specialty"], "languages": item["languages"], "experience": item["experience"], "recommended_capacity": 8, "availability": "Disponible", "status": "active"})
    if item:
        send_email(item["email"], "Estado de tu solicitud", f"Tu solicitud cambió a: {states[action]}. {item.get('admin_comment','')}", email_type="solicitud de guía", related_id=item_id)
    replicate("guide application", item_id, "STATUS")
    flash("Solicitud actualizada", "success")
    return redirect(url_for("admin.guide_applications"))


@bp.post("/providers/<int:item_id>/approve-account")
@roles_required("admin")
def provider_approve_account(item_id):
    provider = update("providers", item_id, {"status": "aprobada", "admin_comment": request.form.get("comment", "")})
    if not provider:
        return "Empresa no encontrada", 404
    username = provider["email"]
    password = f"Proveedor{provider['id']}2026"
    if not any(u.get("username") == username for u in read("users")):
        create("users", {"username": username, "name": provider["name"], "email": provider["email"], "phone": provider.get("phone", ""), "password_hash": generate_password_hash(password), "role": "provider", "status": "active"})
    create("provider_accounts", {"provider_id": provider["id"], "provider_name": provider["name"], "email": provider["email"], "username": username, "created_at": __import__("datetime").datetime.now().isoformat(timespec="seconds")})
    send_email(provider["email"], "Empresa aprobada en Turismo Chiriquí", f"Tu empresa fue aprobada.\nUsuario: {username}\nContraseña temporal: {password}\nYa puedes entrar al portal de proveedores.", email_type="cuenta proveedor", related_id=item_id)
    replicate("provider", item_id, "APPROVE")
    flash(f"Empresa aprobada. Usuario proveedor creado: {username}", "success")
    return redirect(url_for("admin.crud", module="providers"))


@bp.post("/guide-applications/<int:item_id>/approve-account")
@roles_required("admin")
def guide_application_approve_account(item_id):
    item = update("guide_applications", item_id, {"status": "approved", "admin_comment": request.form.get("comment", "")})
    if not item:
        return "Solicitud no encontrada", 404
    username = item["email"].split("@")[0].replace(".", "_")[:20]
    password = f"Guia{item_id}2026"
    user = next((u for u in read("users") if u.get("username") == username), None)
    if not user:
        user = create("users", {"username": username, "name": item["name"], "email": item["email"], "phone": item["phone"], "password_hash": generate_password_hash(password), "role": "worker", "status": "active"})
    worker_payload = {
        "user_id": user["id"], "name": item["name"], "email": item["email"], "phone": item["phone"], "profile_photo": item.get("photo", ""),
        "identity": item.get("identity", ""), "identity_front": item.get("identity_front", ""), "identity_back": item.get("identity_back", ""),
        "certification": item.get("certificate", ""), "experience_document": item.get("resume", ""),
        "type": "guía turístico", "specialty": item.get("specialty", "Turismo"), "languages": item.get("languages", "Español"),
        "experience": item.get("experience", ""), "recommended_capacity": 8, "availability": "Disponible",
        "documents_verified": "Verificados", "status": "active",
    }
    existing_worker = next((w for w in read("workers") if (w.get("user_id") not in (None, "") and int(w.get("user_id")) == int(user["id"])) or str(w.get("email", "")).strip().lower() == item["email"].strip().lower()), None)
    worker = update("workers", existing_worker["id"], worker_payload) if existing_worker else create("workers", worker_payload)
    send_email(item["email"], "Cuenta de guía aprobada", f"Tu solicitud fue aprobada.\nUsuario: {username}\nContraseña temporal: {password}\nCambia esta contraseña después de entrar.", email_type="cuenta guía", related_id=item_id)
    replicate("guide application", item_id, "APPROVE")
    flash(f"Guía aprobado. Usuario creado: {username}", "success")
    return redirect(url_for("admin.guide_applications"))
