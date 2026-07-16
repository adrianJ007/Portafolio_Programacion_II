from flask import Flask
from config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    for folder in (app.config["DATA_DIR"], app.config["UPLOAD_DIR"], app.config["JSON_EXPORT_DIR"]):
        folder.mkdir(parents=True, exist_ok=True)
    from app.routes.auth_routes import bp as auth
    from app.routes.admin_routes import bp as admin
    from app.routes.client_routes import bp as client
    from app.routes.worker_routes import bp as worker
    from app.routes.operator_routes import bp as operator
    from app.routes.email_routes import bp as emails
    from app.routes.payment_routes import bp as payments
    from app.routes.json_routes import bp as json_api
    from app.routes.chatbot_routes import bp as chatbot
    from app.routes.provider_routes import bp as provider
    @app.errorhandler(403)
    def forbidden(_):
        from flask import flash, redirect, session, url_for
        flash("Tu usuario no tiene permiso para esa sección. Te llevé a tu panel principal.", "error")
        role = session.get("role")
        if role in ("admin", "client", "worker", "operator", "provider"):
            return redirect(url_for(f"{role}.dashboard"))
        return redirect(url_for("auth.login"))
    for blueprint in (auth, admin, client, worker, operator, provider, emails, payments, json_api, chatbot):
        app.register_blueprint(blueprint)
    return app
