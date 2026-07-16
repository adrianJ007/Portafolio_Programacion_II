from pathlib import Path

from flask import Blueprint, current_app, flash, redirect, render_template, request, send_from_directory, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from app.services.email_service import send_email
from app.services.storage_service import create, read, update, worker_for_user
from app.services.upload_service import save_document, save_upload

bp = Blueprint("auth", __name__)


@bp.get("/")
def landing():
    return render_template("landing.html", tours=read("tours")[:5], providers=[x for x in read("providers") if x.get("status") == "aprobada"][:6])


@bp.get("/public-media/<path:filename>")
def public_media(filename):
    path = Path(filename)
    allowed_roots = {"tours", "providers", "profiles"}
    allowed_ext = {".png", ".jpg", ".jpeg", ".webp"}
    if not path.parts or path.parts[0] not in allowed_roots or path.suffix.lower() not in allowed_ext:
        return "Archivo no disponible", 404
    return send_from_directory(current_app.config["UPLOAD_DIR"], filename)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = next((u for u in read("users") if u["username"] == request.form["username"]), None)
        if user and check_password_hash(user["password_hash"], request.form["password"]):
            session.update(user=user["id"], username=user["username"], role=user["role"], name=user["name"], email=user.get("email",""))
            return redirect(url_for(f"{user['role']}.dashboard"))
        flash("Usuario o contraseña incorrectos", "error")
    return render_template("auth/login.html")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        if any(x["username"] == request.form["username"] for x in read("users")):
            flash("El usuario ya existe", "error")
        else:
            if request.form["password"] != request.form["password_confirm"]:
                flash("Las contraseñas no coinciden", "error")
                return render_template("auth/register.html")
            import random
            import secrets

            code = f"{secrets.randbelow(1000000):06d}"
            coupon = random.choice(["BEBIDA-GRATIS-2026", "COMIDA-GRATIS-2026", "NUEVO10"])
            item = create("users", {
                "username": request.form["username"],
                "name": request.form["name"],
                "email": request.form["email"],
                "phone": request.form["phone"],
                "identity": request.form.get("identity", ""),
                "birth_date": request.form.get("birth_date", ""),
                "address": request.form.get("address", ""),
                "emergency_contact": request.form.get("emergency_contact", ""),
                "password_hash": generate_password_hash(request.form["password"]),
                "role": "client",
                "status": "active",
                "email_verified": False,
                "verification_code": code,
                "welcome_coupon": coupon,
                "terms_accepted": True,
            })
            create("clients", {"user_id": item["id"], "name": item["name"], "email": item["email"], "phone": item["phone"], "status": "active", "welcome_coupon": coupon})
            send_email(item["email"], "¡Bienvenido a Turismo Chiriquí!", f"Tu cuenta fue creada. Tu cupón de bienvenida es {coupon}.", email_type="bienvenida")
            send_email(item["email"], "Código de verificación", f"Tu código de verificación es {code}.", email_type="código de verificación", related_id=item["id"])
            session["pending_verification_user"] = item["id"]
            flash("Cuenta creada. Revisa tu correo e ingresa el código de verificación.", "success")
            return redirect(url_for("auth.verify"))
    return render_template("auth/register.html")


@bp.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.landing"))


@bp.route("/profile", methods=["GET", "POST"])
def profile():
    if not session.get("user"):
        return redirect(url_for("auth.login"))
    user = next((x for x in read("users") if int(x.get("id", 0)) == int(session["user"])), None)
    if not user:
        session.clear()
        return redirect(url_for("auth.login"))
    if request.method == "POST":
        payload = {
            "name": request.form["name"].strip(),
            "email": request.form["email"].strip(),
            "phone": request.form.get("phone", "").strip(),
            "preferences": request.form.get("preferences", "").strip(),
        }
        if request.form.get("password"):
            payload["password_hash"] = generate_password_hash(request.form["password"])
        uploaded_photo = ""
        if request.files.get("profile_photo") and request.files["profile_photo"].filename:
            uploaded_photo = save_upload(request.files["profile_photo"], "profiles")
            payload["profile_photo"] = uploaded_photo
        update("users", user["id"], payload)
        session["name"] = payload["name"]
        session["email"] = payload["email"]

        role = user.get("role")
        if role == "client":
            client = next((x for x in read("clients") if int(x.get("user_id", 0)) == int(user["id"])), None)
            if client:
                client_payload = {"name": payload["name"], "email": payload["email"], "phone": payload["phone"], "preferences": payload["preferences"]}
                if uploaded_photo:
                    client_payload["profile_photo"] = uploaded_photo
                update("clients", client["id"], client_payload)
        elif role == "worker":
            worker = worker_for_user(user)
            if worker:
                worker_payload = {"name": payload["name"], "email": payload["email"], "phone": payload["phone"], "languages": request.form.get("languages") or worker.get("languages", ""), "experience": request.form.get("experience") or worker.get("experience", ""), "specialty": request.form.get("specialty") or worker.get("specialty", ""), "certification": request.form.get("certification") or worker.get("certification", ""), "professional_description": request.form.get("professional_description") or worker.get("professional_description", ""), "availability": request.form.get("availability") or worker.get("availability", "Disponible")}
                if uploaded_photo:
                    worker_payload["profile_photo"] = uploaded_photo
                for field in ("identity_front", "identity_back", "certification_document", "experience_document"):
                    if request.files.get(field) and request.files[field].filename:
                        worker_payload[field] = save_document(request.files[field], "workers")
                update("workers", worker["id"], worker_payload)
        elif role == "provider":
            provider = next((x for x in read("providers") if x.get("email") == user.get("email")), None)
            if provider:
                provider_payload = {"name": payload["name"], "email": payload["email"], "phone": payload["phone"], "description": request.form.get("description") or provider.get("description", ""), "website": request.form.get("website") or provider.get("website", ""), "social": request.form.get("social") or provider.get("social", "")}
                if uploaded_photo:
                    provider_payload["logo"] = uploaded_photo
                if request.files.get("validation_document") and request.files["validation_document"].filename:
                    provider_payload["validation_document"] = save_document(request.files["validation_document"], "providers")
                update("providers", provider["id"], provider_payload)
        flash("Perfil actualizado correctamente.", "success")
        return redirect(url_for("auth.profile"))
    role_profile = dict(user)
    if user.get("role") == "worker":
        worker = worker_for_user(user)
        if worker:
            role_profile.update(worker)
            role_profile["role"] = user.get("role")
            role_profile["username"] = user.get("username")
            role_profile["status"] = user.get("status", worker.get("status"))
    elif user.get("role") == "provider":
        provider = next((x for x in read("providers") if x.get("email") == user.get("email")), None)
        if provider:
            role_profile.update(provider)
            role_profile["role"] = user.get("role")
            role_profile["username"] = user.get("username")
            role_profile["status"] = user.get("status", provider.get("status"))
    elif user.get("role") == "client":
        client = next((x for x in read("clients") if int(x.get("user_id", 0)) == int(user["id"])), None)
        if client:
            role_profile.update(client)
            role_profile["role"] = user.get("role")
            role_profile["username"] = user.get("username")
            role_profile["status"] = user.get("status", client.get("status"))
    return render_template("auth/profile.html", user=role_profile)


@bp.route("/verify", methods=["GET", "POST"])
def verify():
    user_id = session.get("pending_verification_user")
    if not user_id:
        return redirect(url_for("auth.login"))
    user = next((x for x in read("users") if int(x["id"]) == int(user_id)), None)
    if request.method == "POST":
        if request.form["code"] == user.get("verification_code"):
            update("users", user_id, {"email_verified": True, "verification_code": ""})
            session.pop("pending_verification_user", None)
            flash("Correo verificado correctamente", "success")
            return redirect(url_for("auth.login"))
        flash("Código incorrecto", "error")
    return render_template("auth/verify.html", email=user["email"])


@bp.post("/verify/resend")
def resend_code():
    user_id = session.get("pending_verification_user")
    user = next((x for x in read("users") if int(x["id"]) == int(user_id)), None)
    if user:
        send_email(user["email"], "Código de verificación", f"Tu código es {user['verification_code']}.", email_type="código de verificación", related_id=user_id)
        flash("Código reenviado", "success")
    return redirect(url_for("auth.verify"))


@bp.route("/trabaja-con-nosotros", methods=["GET", "POST"])
def guide_application():
    if request.method == "POST":
        try:
            photo = save_upload(request.files.get("photo"), "profiles")
            identity_front = save_document(request.files.get("identity_front"), "profiles") if request.files.get("identity_front") and request.files["identity_front"].filename else ""
            identity_back = save_document(request.files.get("identity_back"), "profiles") if request.files.get("identity_back") and request.files["identity_back"].filename else ""
            certificate = save_document(request.files.get("certificate"), "profiles") if request.files.get("certificate") and request.files["certificate"].filename else ""
            resume = save_document(request.files.get("resume"), "profiles") if request.files.get("resume") and request.files["resume"].filename else ""
            item = create("guide_applications", {
                "name": request.form["name"], "identity": request.form["identity"], "email": request.form["email"],
                "phone": request.form["phone"], "address": request.form["address"], "experience": request.form["experience"],
                "specialty": request.form["specialty"], "languages": request.form["languages"], "photo": photo,
                "identity_front": identity_front, "identity_back": identity_back, "certificate": certificate, "resume": resume,
                "message": request.form["message"], "status": "pending review", "admin_comment": "",
            })
            send_email(item["email"], "Solicitud recibida", f"Hola {item['name']}, recibimos tu solicitud para trabajar como guía. Estado: pendiente de revisión.", email_type="solicitud de guía", related_id=item["id"])
            admin = current_app.config.get("MAIL_ADMIN_RECEIVER")
            if admin:
                send_email(admin, "Nueva solicitud de guía", f"{item['name']} envió una solicitud. Especialidad: {item['specialty']}.", attachments=[current_app.config["UPLOAD_DIR"] / photo], email_type="solicitud de guía", related_id=item["id"])
            flash("Solicitud enviada correctamente", "success")
            return redirect(url_for("auth.landing"))
        except ValueError as exc:
            flash(str(exc), "error")
    return render_template("auth/guide_application.html")


@bp.route("/empresas-aliadas", methods=["GET", "POST"])
def provider_application():
    if request.method == "POST":
        try:
            logo = save_upload(request.files.get("logo"), "providers") if request.files.get("logo") and request.files["logo"].filename else ""
            document = save_document(request.files.get("validation_document"), "providers") if request.files.get("validation_document") and request.files["validation_document"].filename else ""
            item = create("providers", {
                "name": request.form["name"],
                "ruc": request.form["ruc"],
                "legal_representative": request.form["legal_representative"],
                "email": request.form["email"],
                "phone": request.form["phone"],
                "address": request.form["address"],
                "service_type": request.form["service_type"],
                "description": request.form["description"],
                "logo": logo,
                "validation_document": document,
                "website": request.form.get("website", ""),
                "social": request.form.get("social", ""),
                "message": request.form.get("message", ""),
                "status": "pendiente de revisión",
                "admin_comment": "",
                "created_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
            })
            send_email(item["email"], "Solicitud de empresa recibida", f"Hola {item['name']}, recibimos tu solicitud para ofrecer servicios con Turismo Chiriquí. El estado inicial es pendiente de revisión.", email_type="solicitud empresa", related_id=item["id"])
            admin = current_app.config.get("MAIL_ADMIN_RECEIVER")
            if admin:
                send_email(admin, "Nueva empresa aliada pendiente", f"Empresa: {item['name']}\nTipo: {item['service_type']}\nRepresentante: {item['legal_representative']}\nCorreo: {item['email']}", email_type="solicitud empresa", related_id=item["id"])
            flash("Solicitud recibida. Te notificaremos por correo cuando sea revisada.", "success")
            return redirect(url_for("auth.landing"))
        except ValueError as exc:
            flash(str(exc), "error")
    return render_template("auth/provider_application.html")
