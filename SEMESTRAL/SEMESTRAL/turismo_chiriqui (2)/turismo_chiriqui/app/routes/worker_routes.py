from datetime import datetime
from flask import Blueprint, render_template, session, redirect, url_for, request, flash, current_app
from app.utils.decorators import roles_required
from app.services.storage_service import read, update, create, worker_for_user
from app.services.mock_replication_service import replicate
from app.services.upload_service import save_upload
from app.services.email_service import send_email

bp = Blueprint("worker", __name__, url_prefix="/worker")


def _current_worker():
    user = next((x for x in read("users") if int(x.get("id", 0)) == int(session["user"])), None)
    return worker_for_user(user)


def _own_reservation(item_id, worker):
    if not worker:
        return None
    return next((x for x in read("reservations") if int(x["id"]) == item_id and str(x.get("worker_id")) == str(worker["id"])), None)


@bp.post("/company/confirm")
@roles_required("worker")
def company_confirm():
    worker = _current_worker()
    if not worker or worker.get("company_confirmation") != "pending":
        flash("No tienes una invitación de empresa pendiente.", "error")
        return redirect(url_for("worker.dashboard"))
    update("workers", worker["id"], {"company_confirmation": "accepted", "status": "active", "availability": worker.get("availability") or "Disponible"})
    replicate("worker", worker["id"], "COMPANY-CONFIRM")
    if worker.get("provider_email"):
        send_email(worker["provider_email"], "Guía confirmó su incorporación", f"{session['name']} confirmó que trabajará contigo en Turismo Chiriquí. Su perfil ya está activo y puede recibir giras.", email_type="guía confirmó empresa", related_id=worker["id"])
    flash("Confirmaste tu incorporación. Tu perfil ya está activo.", "success")
    return redirect(url_for("worker.dashboard"))


@bp.post("/company/reject")
@roles_required("worker")
def company_reject():
    worker = _current_worker()
    if not worker or worker.get("company_confirmation") != "pending":
        flash("No tienes una invitación de empresa pendiente.", "error")
        return redirect(url_for("worker.dashboard"))
    update("workers", worker["id"], {"company_confirmation": "rejected", "status": "inactive", "availability": "No disponible"})
    replicate("worker", worker["id"], "COMPANY-REJECT")
    if worker.get("provider_email"):
        send_email(worker["provider_email"], "Guía rechazó la incorporación", f"{session['name']} no aceptó trabajar contigo en Turismo Chiriquí.", email_type="guía rechazó empresa", related_id=worker["id"])
    flash("Rechazaste la incorporación con esta empresa.", "success")
    return redirect(url_for("worker.dashboard"))


@bp.get("/")
@roles_required("worker")
def dashboard():
    worker = _current_worker()
    if not worker:
        flash("Tu usuario de guía todavía no está vinculado a un expediente de guía. Contacta a administración.", "error")
        return render_template("worker/dashboard.html", rows=[], worker=None)
    return render_template("worker/dashboard.html", rows=[x for x in read("reservations") if str(x.get("worker_id")) == str(worker["id"])], worker=worker)


@bp.post("/reservation/<int:item_id>/status")
@roles_required("worker")
def status(item_id):
    worker = _current_worker()
    if not _own_reservation(item_id, worker):
        return ("Asignación no encontrada", 404)
    update("reservations", item_id, {"status": request.form["status"]})
    replicate("reservation", item_id, "STATUS")
    flash("Estado actualizado", "success")
    return redirect(url_for("worker.dashboard"))


@bp.post("/reservation/<int:item_id>/tracking")
@roles_required("worker")
def tracking_status(item_id):
    worker = _current_worker()
    reservation = _own_reservation(item_id, worker)
    if not reservation:
        return ("Asignación no encontrada", 404)
    state = request.form["tracking_status"]
    event = create("tracking_events", {
        "reservation_id": item_id,
        "status": state,
        "note": request.form.get("note", ""),
        "actor": session["name"],
        "created_at": datetime.now().isoformat(timespec="seconds")
    })
    changes = {"tracking_status": state}
    if state == "gira finalizada":
        changes.update({
            "status": "completed",
            "itinerary_status": "finalizado",
            "finished_at": datetime.now().isoformat(timespec="seconds"),
            "finished_by": session["name"],
            "final_observations": request.form.get("note", "")
        })
    update("reservations", item_id, changes)
    body = f"Reserva #{item_id}\nGira: {reservation['tour_name']}\nEstado: {state}\nDetalle: {event['note'] or 'Sin observaciones'}"
    send_email(reservation["notification_email"], f"Seguimiento de gira: {state}", body, email_type="seguimiento de gira", related_id=item_id, reservation_id=item_id)
    if reservation.get("emergency_authorized") and reservation.get("emergency_email") and state in ("gira iniciada", "incidencia reportada", "gira finalizada"):
        send_email(reservation["emergency_email"], f"Seguimiento de seguridad: {state}", body, email_type="contacto de emergencia", related_id=item_id, reservation_id=item_id)
    if state == "gira finalizada":
        send_email(reservation["notification_email"], "Gira finalizada exitosamente", f"Tu experiencia #{item_id} fue finalizada por {session['name']}. Ingresa al sistema para dejar tu evaluación.", email_type="gira finalizada", related_id=item_id, reservation_id=item_id)
    flash("Estado de la gira actualizado.", "success")
    return redirect(url_for("worker.dashboard"))


@bp.post("/reservation/<int:item_id>/activity/<int:activity_index>/<state>")
@roles_required("worker")
def activity_state(item_id, activity_index, state):
    worker = _current_worker()
    reservation = _own_reservation(item_id, worker)
    if not reservation:
        return ("Asignación no encontrada", 404)
    itinerary = list(reservation.get("final_itinerary") or [])
    if activity_index < 0 or activity_index >= len(itinerary):
        return ("Actividad no encontrada", 404)
    state_map = {"start": "en ejecución", "complete": "completada", "issue": "incidencia"}
    itinerary[activity_index]["status"] = state_map.get(state, "pendiente")
    update("reservations", item_id, {
        "final_itinerary": itinerary,
        "itinerary_status": "en ejecución" if state == "start" else reservation.get("itinerary_status")
    })
    create("tracking_events", {
        "reservation_id": item_id,
        "status": f"Actividad {itinerary[activity_index]['status']}",
        "note": itinerary[activity_index].get("activity", ""),
        "actor": session["name"],
        "created_at": datetime.now().isoformat(timespec="seconds")
    })
    flash("Actividad actualizada en el itinerario.", "success")
    return redirect(url_for("worker.dashboard"))


@bp.route("/proposals", methods=["GET", "POST"])
@roles_required("worker")
def proposals():
    if request.method == "POST":
        item = create("tour_proposals", {
            "guide_id": session["user"],
            "guide_name": session["name"],
            "name": request.form["name"],
            "destination": request.form["destination"],
            "description": request.form["description"],
            "duration": request.form["duration"],
            "suggested_price": request.form["suggested_price"],
            "suggested_capacity": request.form["suggested_capacity"],
            "difficulty": request.form["difficulty"],
            "includes_transport": request.form.get("includes_transport") == "yes",
            "includes_food": request.form.get("includes_food") == "yes",
            "recommendations": request.form["recommendations"],
            "suggested_itinerary": request.form["suggested_itinerary"],
            "status": "pending review",
            "admin_comment": ""
        })
        replicate("tour proposal", item["id"])
        flash("Propuesta enviada para revisión. No será publicada hasta que un administrador la apruebe.", "success")

    # Corregido: manejar guide_id que puede ser None
    rows = [x for x in read("tour_proposals") if int(x.get("guide_id") or 0) == int(session["user"])]
    return render_template("worker/proposals.html", rows=rows)


@bp.post("/availability")
@roles_required("worker")
def availability():
    worker = _current_worker()
    if not worker:
        flash("Tu usuario de guía todavía no está vinculado a un expediente de guía. Contacta a administración.", "error")
        return redirect(url_for("worker.dashboard"))
    update("workers", worker["id"], {"availability": request.form["availability"]})
    flash("Disponibilidad actualizada", "success")
    return redirect(url_for("worker.dashboard"))


@bp.post("/reservation/<int:item_id>/assignment")
@roles_required("worker")
def assignment(item_id):
    worker = _current_worker()
    if not _own_reservation(item_id, worker):
        return ("Asignación no encontrada", 404)
    action = request.form["action"]
    state = "accepted" if action == "accept" else "rejected"
    changes = {"assignment_status": state}
    if state == "accepted":
        changes["status"] = "guide assigned"
    else:
        changes.update(worker_id=None, status="payment validated")
    update("reservations", item_id, changes)
    replicate("reservation", item_id, "ASSIGNMENT")
    flash("Asignación actualizada", "success")
    return redirect(url_for("worker.dashboard"))


@bp.post("/reservation/<int:item_id>/check-in")
@roles_required("worker")
def check_in(item_id):
    worker = _current_worker()
    if not _own_reservation(item_id, worker):
        return ("Asignación no encontrada", 404)
    update("reservations", item_id, {"check_in_status": "check-in completed"})
    replicate("reservation", item_id, "CHECK-IN")
    flash("Llegada del cliente confirmada", "success")
    return redirect(url_for("worker.dashboard"))


@bp.route("/reports", methods=["GET", "POST"])
@roles_required("worker")
def reports():
    worker = _current_worker()
    reservations = [x for x in read("reservations") if worker and str(x.get("worker_id")) == str(worker["id"])]
    if request.method == "POST":
        photo = ""
        if request.files.get("photo") and request.files["photo"].filename:
            photo = save_upload(request.files["photo"], "reports")
        item = create("guide_reports", {
            "guide_id": session["user"],
            "guide_name": session["name"],
            "reservation_id": int(request.form["reservation_id"]),
            "type": request.form["type"],
            "message": request.form["message"],
            "location": request.form.get("location", ""),
            "priority": request.form["priority"],
            "photo": photo,
            "status": "open",
            "created_at": datetime.now().isoformat(timespec="seconds")
        })
        replicate("guide report", item["id"], "INSERT")
        attachment = [str(current_app.config["UPLOAD_DIR"] / photo)] if photo else None
        for recipient in [x["email"] for x in read("users") if x.get("role") in ("admin", "operator") and x.get("email")]:
            send_email(recipient, "Problema reportado por guía", f"Guía: {session['name']}\nReserva: #{item['reservation_id']}\nTipo: {item['type']}\nPrioridad: {item['priority']}\nUbicación: {item['location']}\nDetalle: {item['message']}", email_type="problema reportado", related_id=item["id"], attachments=attachment)
        reservation = next((x for x in reservations if int(x["id"]) == item["reservation_id"]), None)
        if reservation:
            update("reservations", reservation["id"], {"tracking_status": "incidencia reportada"})
            create("tracking_events", {
                "reservation_id": reservation["id"],
                "status": "incidencia reportada",
                "note": item["message"],
                "actor": session["name"],
                "created_at": datetime.now().isoformat(timespec="seconds")
            })
            if item["type"] in ("Emergencia", "Emergencia médica") and reservation.get("emergency_authorized") and reservation.get("emergency_email"):
                send_email(reservation["emergency_email"], "Alerta de seguridad de la gira", f"Se reportó una incidencia en la reserva #{reservation['id']}. Estado: {item['type']}. La empresa está dando seguimiento.", email_type="contacto de emergencia", related_id=reservation["id"], reservation_id=reservation["id"])
        flash("Reporte enviado a administración y operaciones.", "success")
        return redirect(url_for("worker.reports"))
    return render_template("worker/reports.html", reservations=reservations, rows=[x for x in read("guide_reports") if str(x.get("guide_id")) == str(session["user"])])


@bp.route("/location", methods=["GET", "POST"])
@roles_required("worker")
def location():
    worker = _current_worker()
    reservations = [x for x in read("reservations") if worker and str(x.get("worker_id")) == str(worker["id"])]
    if request.method == "POST":
        item = create("locations", {
            "guide_id": session["user"],
            "guide_name": session["name"],
            "reservation_id": int(request.form["reservation_id"]),
            "latitude": request.form["latitude"],
            "longitude": request.form["longitude"],
            "status": request.form["status"],
            "updated_at": datetime.now().isoformat(timespec="seconds")
        })
        replicate("location", item["id"], "INSERT")
        flash("Ubicación enviada al centro de operaciones.", "success")
        return redirect(url_for("worker.location"))
    return render_template("worker/location.html", reservations=reservations, rows=[x for x in read("locations") if str(x.get("guide_id")) == str(session["user"])])