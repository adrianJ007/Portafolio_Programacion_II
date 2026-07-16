from datetime import datetime

from flask import Blueprint, current_app, flash, redirect, render_template, request, send_from_directory, session, url_for

from app.services.email_service import send_email
from app.services.storage_service import create, read, update
from app.utils.decorators import roles_required

bp = Blueprint("operator", __name__, url_prefix="/operator")


@bp.get("/")
@roles_required("operator")
def dashboard():
    reservations = read("reservations")
    payments = read("payments")
    complaints = read("complaints")
    emails = read("emails")
    metrics = {
        "pending": sum(x.get("status") in ("pre-reservation", "payment received") for x in reservations),
        "payments": sum(x.get("status") == "received" for x in payments),
        "email_errors": sum(x.get("status") == "error" for x in emails),
        "complaints": sum(x.get("status") in ("open", "in review") for x in complaints),
    }
    return render_template("operator/dashboard.html", reservations=reservations, payments=payments, complaints=complaints, emails=emails, metrics=metrics)


@bp.get("/tracking")
@roles_required("operator", "admin")
def tracking():
    return render_template("operator/tracking.html", reservations=read("reservations"), locations=read("locations"), reports=read("guide_reports"), workers=read("workers"), events=read("tracking_events"))


@bp.get("/consents")
@roles_required("operator", "admin")
def consents():
    return render_template("operator/consents.html", rows=read("consents"))


@bp.post("/consents/<int:item_id>/<action>")
@roles_required("operator", "admin")
def consent_action(item_id, action):
    state = {"approve": "approved", "reject": "rejected"}.get(action, "received")
    item = update("consents", item_id, {"status": state, "reviewed_by": session.get("name", "Equipo"), "observations": request.form.get("observations", "")})
    if item:
        send_email(item["email"], "Revisión de consentimiento", f"El consentimiento de tu reserva #{item['reservation_id']} tiene estado: {state}. {item.get('observations','')}", email_type="consentimiento revisado", related_id=item_id)
    flash("Consentimiento actualizado.", "success")
    return redirect(url_for("operator.consents"))


@bp.get("/consent-file/<path:filename>")
@roles_required("operator", "admin")
def consent_file(filename):
    return send_from_directory(current_app.config["UPLOAD_DIR"], filename)


@bp.get("/itineraries")
@roles_required("operator", "admin")
def itineraries():
    return render_template("operator/itineraries.html", reservations=read("reservations"), workers=read("workers"), provider_tracking=read("provider_tracking"))


@bp.post("/itineraries/<int:item_id>")
@roles_required("operator", "admin")
def propose_itinerary(item_id):
    reservation = next((x for x in read("reservations") if int(x["id"]) == item_id), None)
    if not reservation:
        return "Reserva no encontrada", 404

    activities = []
    times = request.form.getlist("activity_time")
    names = request.form.getlist("activity_name")
    durations = request.form.getlist("activity_duration")
    places = request.form.getlist("activity_place")
    responsibles = request.form.getlist("activity_responsible")
    providers = request.form.getlist("activity_provider")
    states = request.form.getlist("activity_status")
    notes = request.form.getlist("activity_notes")
    for index, name in enumerate(names):
        if not name.strip():
            continue
        activities.append({
            "time": times[index] if index < len(times) else "",
            "activity": name.strip(),
            "duration": durations[index] if index < len(durations) else "60 min",
            "place": places[index] if index < len(places) else "Por confirmar",
            "responsible": responsibles[index] if index < len(responsibles) else "Guía",
            "provider_name": providers[index] if index < len(providers) else "",
            "status": states[index] if index < len(states) else "pendiente",
            "notes": notes[index] if index < len(notes) else "",
        })

    if not activities:
        flash("Agrega al menos una actividad visual al itinerario.", "error")
        return redirect(url_for("operator.itineraries"))

    changes = {
        "final_itinerary": activities,
        "itinerary_status": "pendiente de confirmación del cliente",
        "meeting_point": request.form["meeting_point"],
        "meeting_time": request.form["meeting_time"],
        "transport": request.form.get("transport", ""),
        "map_url": request.form.get("map_url", ""),
        "final_recommendations": request.form.get("recommendations", ""),
        "operator_id": session["user"],
    }
    update("reservations", item_id, changes)
    send_email(reservation["notification_email"], "Tu itinerario está listo para revisión", f"Reserva #{item_id}\nGira: {reservation['tour_name']}\nRuta: {reservation['route_name']}\nHora: {changes['meeting_time']}\nPunto: {changes['meeting_point']}\nIngresa al sistema para confirmar o solicitar cambios.", email_type="itinerario propuesto", related_id=item_id, reservation_id=item_id)
    flash("Itinerario visual enviado al cliente para revisión.", "success")
    return redirect(url_for("operator.itineraries"))


@bp.post("/itineraries/<int:item_id>/change/<int:change_index>/<action>")
@roles_required("operator", "admin")
def itinerary_change_action(item_id, change_index, action):
    reservation = next((x for x in read("reservations") if int(x["id"]) == item_id), None)
    if not reservation:
        return "Reserva no encontrada", 404
    history = list(reservation.get("itinerary_history") or [])
    if 0 <= change_index < len(history):
        history[change_index]["operator_status"] = {"approve": "aprobado", "reject": "rechazado", "review": "en revisión"}.get(action, "en revisión")
        history[change_index]["operator_comment"] = request.form.get("comment", "")
    update("reservations", item_id, {"itinerary_history": history, "itinerary_status": "propuesto por operario" if action == "approve" else reservation.get("itinerary_status", "cambio solicitado")})
    flash("Solicitud de cambio actualizada.", "success")
    return redirect(url_for("operator.itineraries"))


@bp.post("/tracking/<int:item_id>")
@roles_required("operator", "admin")
def tracking_note(item_id):
    create("tracking_events", {"reservation_id": item_id, "status": request.form["status"], "note": request.form.get("note", ""), "actor": session.get("name", "Operaciones"), "created_at": datetime.now().isoformat(timespec="seconds")})
    update("reservations", item_id, {"tracking_status": request.form["status"]})
    flash("Seguimiento actualizado.", "success")
    return redirect(url_for("operator.tracking"))


@bp.get("/providers")
@roles_required("operator", "admin")
def providers():
    return render_template("operator/providers.html", providers=read("providers"), services=read("provider_services"), tracking=read("provider_tracking"))


@bp.post("/providers/<int:item_id>/<action>")
@roles_required("operator", "admin")
def provider_review(item_id, action):
    states = {"reviewed": "documentación revisada", "info": "requiere información", "recommend": "recomendado para aprobación"}
    provider = update("providers", item_id, {"operator_status": states.get(action, "en revisión"), "operator_comment": request.form.get("comment", "")})
    if provider:
        send_email(provider["email"], "Actualización de empresa aliada", f"Tu solicitud fue revisada por operaciones. Estado: {provider.get('operator_status')}. {provider.get('operator_comment','')}", email_type="empresa aliada", related_id=item_id)
    flash("Revisión operativa registrada.", "success")
    return redirect(url_for("operator.providers"))


@bp.post("/provider-tracking/<int:item_id>")
@roles_required("operator", "admin")
def provider_tracking_status(item_id):
    update("provider_tracking", item_id, {"status": request.form["status"], "observations": request.form.get("observations", ""), "required_time": request.form.get("required_time", "Por confirmar")})
    flash("Seguimiento de proveedor actualizado.", "success")
    return redirect(url_for("operator.providers"))
