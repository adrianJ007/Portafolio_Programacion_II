from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, send_file, session, url_for

from app.services.email_service import send_email
from app.services.mock_replication_service import replicate
from app.services.reservation_service import make_reservation
from app.services.storage_service import create, read, update
from app.services.upload_service import save_document
from app.services.pdf_service import build_itinerary_pdf
from app.utils.decorators import roles_required

bp = Blueprint("client", __name__, url_prefix="/client")


@bp.get("/")
@roles_required("client")
def dashboard():
    reservations = [x for x in read("reservations") if int(x.get("user_id", 0)) == int(session["user"])]
    return render_template("client/dashboard.html", reservations=reservations, tours=read("tours"), events=read("tracking_events"))


@bp.get("/tours")
@roles_required("client")
def tours():
    return render_template("client/tours.html", tours=read("tours"))


@bp.route("/reservation", methods=["GET", "POST"])
@roles_required("client")
def reservation():
    if request.method == "POST":
        try:
            payload = {
                "user_id": session["user"], "client": session["name"], "tour_id": int(request.form["tour_id"]),
                "date": request.form["date"], "people": int(request.form["people"]), "duration": request.form["duration"],
                "notification_email": request.form["email"], "client_phone": request.form.get("client_phone", ""),
                "route_name": request.form["route_name"], "preferences": request.form.get("preferences", ""),
                "physical_restrictions": request.form.get("physical_restrictions", ""), "allergies": request.form.get("allergies", ""),
                "traveler_profile": request.form.get("traveler_profile", ""), "pace": request.form.get("pace", "Equilibrado"),
                "preferred_departure": request.form.get("preferred_departure", ""), "emergency_name": request.form.get("emergency_name", ""),
                "emergency_phone": request.form.get("emergency_phone", ""), "emergency_email": request.form.get("emergency_email", ""),
                "emergency_relationship": request.form.get("emergency_relationship", ""),
                "emergency_authorized": request.form.get("emergency_authorized") == "yes",
                "service_ids": request.form.getlist("service_ids"),
                "optional_extra_guide": request.form.get("optional_extra_guide") == "yes",
                "promo_code": request.form.get("promo_code", ""),
            }
            item = make_reservation(payload)
            detail = (
                f"Pre-reserva #{item['id']}\nGira: {item['tour_name']}\nRuta: {item['route_name']}\n"
                f"Fecha: {item['date']}\nPersonas: {item['people']}\nGuías requeridos: {item['required_guides']}\n"
                f"Subtotal: ${item['subtotal']}\nITBMS: ${item['itbms']}\nDescuento: ${item['discount']}\nTotal: ${item['total']}"
            )
            send_email(item["notification_email"], "Comprobante de pre-reserva", detail, attachments=[item["receipt_path"]], email_type="comprobante de reserva", related_id=item["id"], reservation_id=item["id"])
            send_email(item["notification_email"], "Instrucciones de pago", f"Elige Yappy, tarjeta simulada o efectivo. Total exacto: ${item['total']}.", email_type="instrucciones de pago", related_id=item["id"], reservation_id=item["id"])
            flash("Pre-reserva creada. Continúa con el método de pago.", "success")
            return redirect(url_for("payments.upload"))
        except (ValueError, StopIteration) as exc:
            flash(str(exc), "error")
    approved = {"approved", "aprobado", "active", "activo"}
    services = [x for x in read("services") if str(x.get("status", "")).lower() in approved]
    return render_template("client/reservation_form.html", tours=read("tours"), services=services, selected_tour=request.args.get("tour_id", type=int))


@bp.get("/itinerary")
@roles_required("client")
def itinerary():
    rows = [x for x in read("reservations") if int(x.get("user_id", 0)) == int(session["user"])]
    return render_template("client/itinerary_builder.html", reservations=rows, events=read("tracking_events"), workers=read("workers"))


@bp.post("/itinerary/<int:item_id>/<action>")
@roles_required("client")
def itinerary_action(item_id, action):
    item = next((x for x in read("reservations") if int(x["id"]) == item_id and int(x.get("user_id", 0)) == int(session["user"])), None)
    if not item:
        return "Reserva no encontrada", 404
    state = "confirmado por cliente" if action == "confirm" else "cambio solicitado"
    comment = request.form.get("comment", "").strip()
    history = list(item.get("itinerary_history") or [])
    history.append({"date": datetime.now().isoformat(timespec="seconds"), "actor": session["name"], "action": action, "comment": comment, "status": state})
    changes = {"itinerary_status": state, "itinerary_client_comment": comment, "itinerary_history": history, "tracking_status": "itinerario confirmado" if action == "confirm" else item.get("tracking_status", "pendiente")}
    if action == "confirm":
        worker = next((x for x in read("workers") if str(x.get("id")) == str(item.get("worker_id"))), None)
        pdf_path = build_itinerary_pdf({**item, **changes}, worker)
        changes["itinerary_pdf"] = str(pdf_path)
        changes["status"] = "itinerary confirmed"
        create("tracking_events", {"reservation_id": item_id, "status": "itinerario confirmado", "note": "El cliente confirmó el itinerario final.", "actor": item["client"], "created_at": datetime.now().isoformat(timespec="seconds")})
    update("reservations", item_id, changes)
    subject = "Itinerario confirmado por el cliente" if action == "confirm" else "Solicitud de cambio de itinerario"
    for address in [x["email"] for x in read("users") if x.get("role") in ("admin", "operator") and x.get("email")]:
        send_email(address, subject, f"Reserva #{item_id}\nCliente: {item['client']}\nComentario: {comment or 'Sin comentarios'}", email_type="itinerario", related_id=item_id, reservation_id=item_id)
    attachments = [changes["itinerary_pdf"]] if changes.get("itinerary_pdf") else None
    send_email(item["notification_email"], subject, f"Estado del itinerario de la reserva #{item_id}: {state}.", attachments=attachments, email_type="itinerario", related_id=item_id, reservation_id=item_id)
    flash("Respuesta registrada correctamente.", "success")
    return redirect(url_for("client.itinerary"))


@bp.post("/itinerary/<int:item_id>/activity/<int:activity_index>/change")
@roles_required("client")
def itinerary_activity_change(item_id, activity_index):
    item = next((x for x in read("reservations") if int(x["id"]) == item_id and int(x.get("user_id", 0)) == int(session["user"])), None)
    if not item:
        return "Reserva no encontrada", 404
    history = list(item.get("itinerary_history") or [])
    history.append({
        "date": datetime.now().isoformat(timespec="seconds"),
        "actor": session["name"],
        "action": request.form.get("action", "cambio de actividad"),
        "activity_index": activity_index,
        "comment": request.form.get("comment", ""),
        "status": "cambio solicitado",
    })
    update("reservations", item_id, {"itinerary_status": "cambio solicitado", "itinerary_history": history})
    flash("Solicitud registrada. Operaciones revisará el cambio.", "success")
    return redirect(url_for("client.itinerary"))


@bp.route("/complaints", methods=["GET", "POST"])
@roles_required("client")
def complaints():
    if request.method == "POST":
        create("complaints", {"user_id": session["user"], "email": request.form["email"], "subject": request.form["subject"], "message": request.form["message"], "priority": request.form["priority"], "status": "open"})
        send_email(request.form["email"], "Queja recibida", "Tu solicitud está en revisión.", email_type="queja recibida")
        flash("Queja enviada", "success")
    return render_template("client/complaints.html", rows=read("complaints"))


@bp.get("/terms")
@roles_required("client", "admin", "operator", "worker")
def terms():
    return render_template("client/terms.html")


@bp.get("/receipt/<int:item_id>")
@roles_required("client")
def receipt(item_id):
    item = next((x for x in read("reservations") if int(x["id"]) == item_id and int(x.get("user_id", 0)) == int(session["user"])), None)
    return send_file(item["receipt_path"], as_attachment=True) if item and item.get("receipt_path") else ("Comprobante no encontrado", 404)


@bp.get("/itinerary/<int:item_id>/pdf")
@roles_required("client")
def itinerary_pdf(item_id):
    item = next((x for x in read("reservations") if int(x["id"]) == item_id and int(x.get("user_id", 0)) == int(session["user"])), None)
    return send_file(item["itinerary_pdf"], as_attachment=True) if item and item.get("itinerary_pdf") else ("PDF no disponible todavía", 404)


@bp.route("/feedback/<int:item_id>", methods=["GET", "POST"])
@roles_required("client")
def feedback(item_id):
    reservation = next((x for x in read("reservations") if int(x["id"]) == item_id and int(x.get("user_id", 0)) == int(session["user"])), None)
    if not reservation:
        return "Reserva no encontrada", 404
    if request.method == "POST":
        create("feedbacks", {
            "reservation_id": item_id,
            "user_id": session["user"],
            "client": session["name"],
            "tour": reservation.get("tour_name"),
            "general_rating": int(request.form["general_rating"]),
            "guide_rating": int(request.form["guide_rating"]),
            "itinerary_rating": int(request.form["itinerary_rating"]),
            "comments": request.form.get("comments", ""),
            "suggestions": request.form.get("suggestions", ""),
            "created_at": datetime.now().isoformat(timespec="seconds"),
        })
        update("reservations", item_id, {"feedback_status": "recibido"})
        flash("Gracias por evaluar tu experiencia.", "success")
        return redirect(url_for("client.dashboard"))
    return render_template("client/feedback.html", reservation=reservation)


@bp.route("/consents", methods=["GET", "POST"])
@roles_required("client")
def consents():
    reservations = [x for x in read("reservations") if int(x.get("user_id", 0)) == int(session["user"])]
    if request.method == "POST":
        reservation = next((x for x in reservations if int(x["id"]) == int(request.form["reservation_id"])), None)
        if not reservation:
            flash("Reserva no válida.", "error")
            return redirect(url_for("client.consents"))
        try:
            document = save_document(request.files.get("document"), "consents")
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("client.consents"))
        item = create("consents", {"reservation_id": reservation["id"], "user_id": session["user"], "client": session["name"], "email": reservation["notification_email"], "tour_name": reservation["tour_name"], "document": document, "uploaded_at": datetime.now().isoformat(timespec="seconds"), "status": "received", "reviewed_by": "", "observations": ""})
        replicate("consent", item["id"], "INSERT")
        send_email(item["email"], "Consentimiento recibido", f"Recibimos el consentimiento para la reserva #{reservation['id']}.", email_type="consentimiento recibido", related_id=item["id"])
        flash("Documento recibido.", "success")
        return redirect(url_for("client.consents"))
    return render_template("client/consents.html", reservations=reservations, rows=[x for x in read("consents") if int(x.get("user_id", 0)) == int(session["user"])])
