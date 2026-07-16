import json
import os
import random
from datetime import datetime
from decimal import Decimal, InvalidOperation

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    url_for,
)
from werkzeug.utils import secure_filename

from config import ALLOWED_EXTENSIONS, MAX_CONTENT_LENGTH, UPLOAD_FOLDER
from models import AsignacionAseo, Gasto, db

app = Flask(__name__)
app.config["SECRET_KEY"] = "examen-parcial-1-cambiar-en-produccion"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///examen_parcial1.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

db.init_app(app)

EDIFICIOS = ("A", "B", "C", "Otros")
CATEGORIAS_GASTO = ("comida", "viáticos", "otros")
MIN_FOTOS = 1
MAX_FOTOS = 20


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_photos(files):
    """Guarda archivos válidos y devuelve lista de nombres seguros."""
    saved = []
    for f in files:
        if not f or not f.filename:
            continue
        if allowed_file(f.filename):
            name = secure_filename(f.filename)
            base, ext = os.path.splitext(name)
            unique = f"{base}_{os.urandom(4).hex()}{ext}"
            path = os.path.join(app.config["UPLOAD_FOLDER"], unique)
            f.save(path)
            saved.append(unique)
    return saved


def cleanup_saved_files(filenames):
    for fn in filenames:
        try:
            os.remove(os.path.join(app.config["UPLOAD_FOLDER"], fn))
        except OSError:
            pass


def validar_cantidad_fotos(cantidad):
    if cantidad < MIN_FOTOS:
        return (
            False,
            f"Debe incluir al menos {MIN_FOTOS} imagen (png, jpg, jpeg, gif, webp).",
        )
    if cantidad > MAX_FOTOS:
        return False, f"Máximo {MAX_FOTOS} imágenes por registro."
    return True, None


def parse_time_24h(s):
    return datetime.strptime(s.strip(), "%H:%M").time()


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.route("/")
def menu():
    return render_template("menu.html")


@app.route("/asignaciones")
def listar_asignaciones():
    items = AsignacionAseo.query.order_by(AsignacionAseo.dia.desc(), AsignacionAseo.id.desc()).all()
    return render_template("asignaciones_lista.html", items=items)


@app.route("/asignaciones/nueva", methods=["GET", "POST"])
def nueva_asignacion():
    if request.method == "POST":
        try:
            files = request.files.getlist("fotos")
            saved = save_uploaded_photos(files)
            ok, msg = validar_cantidad_fotos(len(saved))
            if not ok:
                cleanup_saved_files(saved)
                flash(msg, "danger")
                return redirect(url_for("nueva_asignacion"))

            dia = datetime.strptime(request.form["dia"], "%Y-%m-%d").date()
            hora = parse_time_24h(request.form["hora"])

            reg = AsignacionAseo(
                nombre=request.form["nombre"].strip(),
                apellido=request.form["apellido"].strip(),
                cip=request.form["cip"].strip(),
                cargo=request.form["cargo"].strip(),
                dia=dia,
                hora=hora,
                descripcion=request.form["descripcion"].strip(),
                edificio=request.form["edificio"],
                facultad=request.form.get("facultad", "").strip() or None,
                fotos_json=json.dumps(saved),
            )
            db.session.add(reg)
            db.session.commit()
            flash("Asignación registrada correctamente.", "success")
            return redirect(url_for("listar_asignaciones"))
        except (ValueError, KeyError, OSError) as e:
            db.session.rollback()
            flash(f"Error al guardar (verifique datos): {e}", "danger")
        except Exception as e:
            db.session.rollback()
            flash(f"Error inesperado: {e}", "danger")

    return render_template("asignacion_form.html", item=None, edificios=EDIFICIOS)


@app.route("/asignaciones/<int:aid>/editar", methods=["GET", "POST"])
def editar_asignacion(aid):
    item = AsignacionAseo.query.get_or_404(aid)
    if request.method == "POST":
        try:
            files = request.files.getlist("fotos")
            saved_new = save_uploaded_photos(files)
            existing = item._foto_list()
            fotos_final = existing + saved_new

            ok, msg = validar_cantidad_fotos(len(fotos_final))
            if not ok:
                cleanup_saved_files(saved_new)
                flash(msg, "danger")
                return redirect(url_for("editar_asignacion", aid=aid))

            item.nombre = request.form["nombre"].strip()
            item.apellido = request.form["apellido"].strip()
            item.cip = request.form["cip"].strip()
            item.cargo = request.form["cargo"].strip()
            item.dia = datetime.strptime(request.form["dia"], "%Y-%m-%d").date()
            item.hora = parse_time_24h(request.form["hora"])
            item.descripcion = request.form["descripcion"].strip()
            item.edificio = request.form["edificio"]
            item.facultad = request.form.get("facultad", "").strip() or None
            item.fotos_json = json.dumps(fotos_final)
            db.session.commit()
            flash("Asignación actualizada.", "success")
            return redirect(url_for("listar_asignaciones"))
        except (ValueError, KeyError, OSError) as e:
            db.session.rollback()
            flash(f"Error al actualizar: {e}", "danger")
        except Exception as e:
            db.session.rollback()
            flash(f"Error inesperado: {e}", "danger")

    return render_template("asignacion_form.html", item=item, edificios=EDIFICIOS)


@app.route("/asignaciones/<int:aid>/eliminar", methods=["POST"])
def eliminar_asignacion(aid):
    item = AsignacionAseo.query.get_or_404(aid)
    try:
        for fn in item._foto_list():
            try:
                os.remove(os.path.join(app.config["UPLOAD_FOLDER"], fn))
            except OSError:
                pass
        db.session.delete(item)
        db.session.commit()
        flash("Registro eliminado.", "info")
    except Exception as e:
        db.session.rollback()
        flash(f"No se pudo eliminar: {e}", "danger")
    return redirect(url_for("listar_asignaciones"))


@app.route("/asignaciones/exportar_json")
def exportar_asignaciones_json():
    try:
        rows = AsignacionAseo.query.order_by(AsignacionAseo.id).all()
        data = [r.to_dict() for r in rows]
        payload = json.dumps(data, ensure_ascii=False, indent=2)
        from io import BytesIO

        mem = BytesIO(payload.encode("utf-8"))
        mem.seek(0)
        return send_file(
            mem,
            mimetype="application/json",
            as_attachment=True,
            download_name="asignaciones_aseo.json",
        )
    except Exception as e:
        flash(f"Error al generar JSON: {e}", "danger")
        return redirect(url_for("listar_asignaciones"))


@app.route("/gastos")
def listar_gastos():
    cat = request.args.get("categoria", "").strip().lower()
    q = Gasto.query
    if cat in CATEGORIAS_GASTO:
        q = q.filter(Gasto.categoria == cat)
    items = q.order_by(Gasto.id.desc()).all()
    total = 0.0
    try:
        for g in items:
            total += float(g.monto)
        total = round(total, 2)
    except (TypeError, ValueError):
        total = 0.0
    return render_template(
        "gastos_lista.html",
        items=items,
        categorias=CATEGORIAS_GASTO,
        filtro=cat if cat in CATEGORIAS_GASTO else "",
        total=total,
    )


@app.route("/gastos/nuevo", methods=["GET", "POST"])
def nuevo_gasto():
    if request.method == "POST":
        try:
            monto_raw = request.form["monto"].replace(",", ".").strip()
            monto = Decimal(monto_raw)
            monto = monto.quantize(Decimal("0.01"))
            cat = request.form["categoria"].strip().lower()
            if cat not in CATEGORIAS_GASTO:
                raise ValueError("Categoría no válida.")
            g = Gasto(
                categoria=cat,
                concepto=request.form.get("concepto", "").strip() or None,
                monto=monto,
            )
            db.session.add(g)
            db.session.commit()
            flash("Gasto guardado (monto con 2 cifras decimales).", "success")
            return redirect(url_for("listar_gastos"))
        except (InvalidOperation, ValueError) as e:
            db.session.rollback()
            flash(f"Monto o categoría inválidos: {e}", "danger")
        except Exception as e:
            db.session.rollback()
            flash(f"Error: {e}", "danger")
    return render_template("gasto_form.html", item=None, categorias=CATEGORIAS_GASTO)


@app.route("/gastos/<int:gid>/editar", methods=["GET", "POST"])
def editar_gasto(gid):
    item = Gasto.query.get_or_404(gid)
    if request.method == "POST":
        try:
            monto_raw = request.form["monto"].replace(",", ".").strip()
            monto = Decimal(monto_raw).quantize(Decimal("0.01"))
            cat = request.form["categoria"].strip().lower()
            if cat not in CATEGORIAS_GASTO:
                raise ValueError("Categoría no válida.")
            item.categoria = cat
            item.concepto = request.form.get("concepto", "").strip() or None
            item.monto = monto
            db.session.commit()
            flash("Gasto actualizado.", "success")
            return redirect(url_for("listar_gastos"))
        except (InvalidOperation, ValueError) as e:
            db.session.rollback()
            flash(f"Datos inválidos: {e}", "danger")
        except Exception as e:
            db.session.rollback()
            flash(f"Error: {e}", "danger")
    return render_template("gasto_form.html", item=item, categorias=CATEGORIAS_GASTO)


@app.route("/gastos/<int:gid>/eliminar", methods=["POST"])
def eliminar_gasto(gid):
    item = Gasto.query.get_or_404(gid)
    try:
        db.session.delete(item)
        db.session.commit()
        flash("Gasto eliminado.", "info")
    except Exception as e:
        db.session.rollback()
        flash(f"No se pudo eliminar: {e}", "danger")
    return redirect(url_for("listar_gastos"))


@app.route("/simulacion", methods=["GET", "POST"])
def simulacion():
    """
    Simulación N veces: promedia costos estimados de rutas de aseo (valores sintéticos).
    Salida con 2 decimales. Control Try/Except.
    """
    resultado = None
    errores = []
    if request.method == "POST":
        try:
            n = int(request.form.get("n", "0"))
            if n < 1 or n > 100_000:
                raise ValueError("N debe estar entre 1 y 100000.")
        except ValueError as e:
            errores.append(str(e))
            n = 0

        if n > 0:
            suma = 0.0
            for i in range(n):
                try:
                    # "Cálculo" simulado por iteración (costo aleatorio acotado)
                    costo = random.uniform(5.0, 250.0)
                    suma += costo
                except Exception as e:
                    errores.append(f"Iteración {i}: {e}")
            try:
                promedio = round(suma / n, 2)
                resultado = {"n": n, "promedio": promedio, "suma": round(suma, 2)}
            except ZeroDivisionError:
                errores.append("División por cero.")

    return render_template("simulacion.html", resultado=resultado, errores=errores)


@app.cli.command("init-db")
def init_db():
    with app.app_context():
        db.create_all()
        print("Base de datos inicializada.")


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(debug=True, port=5000)
