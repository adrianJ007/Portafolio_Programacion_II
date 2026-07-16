from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import generate_password_hash

from app.services.email_service import send_email
from app.services.mock_replication_service import replicate
from app.services.storage_service import create, read, update
from app.services.upload_service import save_document, save_upload
from app.utils.decorators import roles_required

bp = Blueprint("provider", __name__, url_prefix="/provider")


def _provider():
    provider = next((p for p in read("providers") if p.get("email") == session.get("username") or p.get("email") == session.get("email")), None)
    return provider


@bp.get("/")
@roles_required("provider")
def dashboard():
    provider = _provider()
    services = [s for s in read("provider_services") if s.get("provider_email") == (provider or {}).get("email")]
    tours = [t for t in read("tour_proposals") if str(t.get("provider_id")) == str((provider or {}).get("id"))]
    guides = [w for w in read("workers") if str(w.get("provider_id", "")) == str((provider or {}).get("id"))]
    tracking = [t for t in read("provider_tracking") if t.get("provider_name") == (provider or {}).get("name")]
    return render_template("provider/dashboard.html", provider=provider, services=services, tours=tours, guides=guides, tracking=tracking)


@bp.route("/services/new", methods=["GET", "POST"])
@roles_required("provider")
def new_service():
    provider = _provider()
    if request.method == "POST":
        if not provider:
            flash("No se encontró la empresa asociada a esta cuenta.", "error")
            return redirect(url_for("provider.dashboard"))
        item = create("provider_services", {
            "provider_id": provider["id"], "provider_name": provider["name"], "provider_email": provider["email"],
            "name": request.form["name"], "type": request.form["type"], "description": request.form["description"],
            "price": request.form["price"], "applies_itbms": request.form.get("applies_itbms", "Sí"),
            "profit_percent": request.form.get("profit_percent", 15), "capacity_daily": request.form.get("capacity_daily", ""),
            "coverage_zone": request.form.get("coverage_zone", ""), "availability": request.form.get("availability", "Disponible"),
            "policy": request.form.get("policy", ""), "status": "pendiente de revisión", "image": "",
            "created_at": datetime.now().isoformat(timespec="seconds"),
        })
        replicate("provider service", item["id"], "INSERT")
        for user in read("users"):
            if user.get("role") in ("admin", "operator") and user.get("email"):
                send_email(user["email"], "Servicio de proveedor pendiente", f"{provider['name']} propuso: {item['name']}.", email_type="servicio proveedor", related_id=item["id"])
        flash("Servicio enviado para revisión.", "success")
        return redirect(url_for("provider.dashboard"))
    return render_template("provider/new_service.html", provider=provider)


@bp.route("/tours/new", methods=["GET", "POST"])
@roles_required("provider")
def new_tour():
    provider = _provider()
    if request.method == "POST":
        if not provider:
            flash("No se encontró la empresa asociada a esta cuenta.", "error")
            return redirect(url_for("provider.dashboard"))
        image = save_upload(request.files["image"], "tours") if request.files.get("image") and request.files["image"].filename else ""
        item = create("tour_proposals", {
            "provider_id": provider["id"],
            "provider_name": provider["name"],
            "provider_email": provider["email"],
            "source": "provider",
            "name": request.form["name"].strip(),
            "destination": request.form["destination"].strip(),
            "description": request.form["description"].strip(),
            "suggested_price": float(request.form["suggested_price"]),
            "duration": request.form["duration"].strip(),
            "suggested_capacity": int(request.form["suggested_capacity"]),
            "difficulty": request.form["difficulty"],
            "includes_transport": request.form.get("includes_transport") == "yes",
            "includes_food": request.form.get("includes_food") == "yes",
            "route_options": request.form.get("route_options", "").strip(),
            "requirements": request.form.get("requirements", "").strip(),
            "policy": request.form.get("policy", "").strip(),
            "image": image,
            "status": "pendiente de revisión",
            "admin_comment": "",
            "created_at": datetime.now().isoformat(timespec="seconds"),
        })
        replicate("tour proposal", item["id"], "INSERT")
        for user in read("users"):
            if user.get("role") in ("admin", "operator") and user.get("email"):
                send_email(user["email"], "Nueva gira de empresa pendiente", f"{provider['name']} propuso la gira: {item['name']} en {item['destination']}.", email_type="gira de empresa", related_id=item["id"])
        flash("Gira enviada para revisión administrativa.", "success")
        return redirect(url_for("provider.dashboard"))
    return render_template("provider/new_tour.html", provider=provider)


@bp.get("/guides")
@roles_required("provider")
def guides():
    provider = _provider()
    rows = [w for w in read("workers") if str(w.get("provider_id", "")) == str((provider or {}).get("id"))]
    return render_template("provider/guides.html", provider=provider, rows=rows)


@bp.route("/guides/new", methods=["GET", "POST"])
@bp.route("/guides/<int:item_id>/edit", methods=["GET", "POST"])
@roles_required("provider")
def guide_form(item_id=None):
    provider = _provider()
    item = None
    if item_id:
        item = next((w for w in read("workers") if int(w.get("id", 0)) == item_id and str(w.get("provider_id", "")) == str((provider or {}).get("id"))), None)
        if not item:
            return "Guía no encontrado", 404
    if request.method == "POST":
        if not provider:
            flash("No se encontró la empresa asociada a esta cuenta.", "error")
            return redirect(url_for("provider.dashboard"))
        confirmed = bool(item) and item.get("company_confirmation") == "accepted"
        payload = {
            "provider_id": provider["id"],
            "provider_name": provider["name"],
            "provider_email": provider["email"],
            "name": request.form["name"].strip(),
            "email": request.form["email"].strip(),
            "phone": request.form["phone"].strip(),
            "identity": request.form.get("identity", "").strip(),
            "type": request.form.get("type", "guía turístico"),
            "specialty": request.form.get("specialty", "Turismo").strip(),
            "languages": request.form.get("languages", "Español").strip(),
            "experience": request.form.get("experience", "").strip(),
            "professional_description": request.form.get("professional_description", "").strip(),
            "recommended_capacity": int(request.form.get("recommended_capacity") or 8),
            "availability": request.form.get("availability", "Disponible"),
            "documents_verified": "Pendientes",
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
        # A guide's active/assignable status can only ever be set by their own
        # confirmation (see worker.company_confirm / company_reject). The
        # company can edit the rest of the profile freely, but cannot use
        # this form to force activation before the guide has confirmed.
        if confirmed:
            payload["status"] = request.form.get("status", "active")
        file_fields = {
            "profile_photo": ("profiles", save_upload),
            "identity_front": ("workers", save_document),
            "identity_back": ("workers", save_document),
            "certification_document": ("workers", save_document),
            "license_document": ("workers", save_document),
            "experience_document": ("workers", save_document),
        }
        for field, (category, saver) in file_fields.items():
            if request.files.get(field) and request.files[field].filename:
                payload[field] = saver(request.files[field], category)
        if item:
            update("workers", item["id"], payload)
            flash("Guía actualizado correctamente.", "success")
        else:
            existing_user = next((u for u in read("users") if u.get("email", "").strip().lower() == payload["email"].strip().lower()), None)
            if existing_user and existing_user.get("role") != "worker":
                flash("Ese correo ya pertenece a una cuenta con otro rol en el sistema. Usa un correo distinto para este guía.", "error")
                return render_template("provider/guide_form.html", provider=provider, item=item)
            if existing_user and any(w.get("user_id") == existing_user["id"] for w in read("workers")):
                flash("Esta persona ya tiene un expediente de guía activo en el sistema (posiblemente con otra empresa). No es posible registrarla de nuevo.", "error")
                return render_template("provider/guide_form.html", provider=provider, item=item)
            username = payload["email"].split("@")[0].replace(".", "_")[:20]
            password = None
            if existing_user:
                user = existing_user
            else:
                base_username, suffix = username, 1
                while any(u.get("username") == username for u in read("users")):
                    suffix += 1
                    username = f"{base_username}{suffix}"
                password = f"Guia{provider['id']}{suffix if suffix > 1 else ''}2026"
                user = create("users", {"username": username, "name": payload["name"], "email": payload["email"], "phone": payload["phone"], "password_hash": generate_password_hash(password), "role": "worker", "status": "active"})
            payload["user_id"] = user["id"]
            payload["status"] = "pending confirmation"
            payload["company_confirmation"] = "pending"
            payload["created_at"] = datetime.now().isoformat(timespec="seconds")
            worker = create("workers", payload)
            replicate("worker", worker["id"], "INSERT")
            if password:
                send_email(payload["email"], "Te registraron como guía en Turismo Chiriquí",
                            f"{provider['name']} te registró como guía en Turismo Chiriquí.\n\nUsuario: {username}\nContraseña temporal: {password}\n\nIngresa a tu panel para completar tu perfil, subir tu documentación y confirmar si aceptas trabajar con esta empresa. Solo quedarás activo y podrás recibir giras después de confirmar.",
                            email_type="guía registrado por empresa", related_id=worker["id"])
            else:
                send_email(payload["email"], "Nueva empresa te registró como guía",
                            f"{provider['name']} te registró como guía en Turismo Chiriquí. Ingresa a tu panel con tu cuenta existente para completar tu perfil, tu documentación y confirmar si aceptas trabajar con esta empresa.",
                            email_type="guía registrado por empresa", related_id=worker["id"])
            flash("Guía registrado. Se le notificó para que complete su perfil y confirme su incorporación.", "success")
        return redirect(url_for("provider.guides"))
    return render_template("provider/guide_form.html", provider=provider, item=item)


@bp.get("/guides/<int:item_id>")
@roles_required("provider")
def guide_detail(item_id):
    provider = _provider()
    item = next((w for w in read("workers") if int(w.get("id", 0)) == item_id and str(w.get("provider_id", "")) == str((provider or {}).get("id"))), None)
    if not item:
        return "Guía no encontrado", 404
    reservations = [r for r in read("reservations") if str(r.get("worker_id", "")) == str(item_id)]
    return render_template("provider/guide_detail.html", provider=provider, item=item, reservations=reservations)


@bp.post("/guides/<int:item_id>/toggle")
@roles_required("provider")
def guide_toggle(item_id):
    provider = _provider()
    item = next((w for w in read("workers") if int(w.get("id", 0)) == item_id and str(w.get("provider_id", "")) == str((provider or {}).get("id"))), None)
    if not item:
        return "Guía no encontrado", 404
    if item.get("company_confirmation") == "pending":
        flash("Este guía todavía no confirma su incorporación; no puede activarse manualmente todavía.", "error")
        return redirect(url_for("provider.guides"))
    update("workers", item_id, {"status": "inactive" if item.get("status") == "active" else "active", "availability": "No disponible" if item.get("status") == "active" else "Disponible"})
    flash("Estado del guía actualizado.", "success")
    return redirect(url_for("provider.guides"))
