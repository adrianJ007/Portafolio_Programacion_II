from flask import Blueprint,render_template,request,redirect,url_for,flash
from app.utils.decorators import roles_required
from app.services.storage_service import read
from app.services.email_service import resend_email,send_manual_email,send_email
bp=Blueprint("emails",__name__,url_prefix="/admin/emails")
@bp.route("/",methods=["GET","POST"])
@roles_required("admin","operator")
def center():
    if request.method=="POST":
        result=send_manual_email(request.form["to"],request.form["subject"],request.form["message"]); flash("Correo enviado" if result["status"]=="sent" else f"Error SMTP: {result['smtp_error']}","success" if result["status"]=="sent" else "error"); return redirect(url_for("emails.center"))
    rows=read("emails"); q=request.args.get("q","").lower(); kind=request.args.get("type",""); status=request.args.get("status",""); rows=[x for x in rows if q in x.get("to","").lower() and (not kind or x.get("type")==kind) and (not status or x.get("status")==status)]; return render_template("admin/emails.html",rows=rows)
@bp.post("/<int:item_id>/resend")
@roles_required("admin","operator")
def resend(item_id): result=resend_email(item_id); flash("Reenvío procesado" if result else "Correo no encontrado","success"); return redirect(url_for("emails.center"))
@bp.post("/<int:item_id>/receipt")
@roles_required("admin","operator")
def resend_receipt(item_id):
    email=next((x for x in read("emails") if int(x["id"])==item_id),None); related=email.get("related_id") if email else None; record=next((x for x in read("reservations")+read("payments") if str(x.get("id"))==str(related)),None)
    if email and record and record.get("receipt_path"): send_email(email["to"],"Reenvío de comprobante",f"Adjuntamos nuevamente el comprobante relacionado con la operación #{related}.",attachments=[record["receipt_path"]],email_type="reenvío de comprobante",related_id=related); flash("Comprobante reenviado","success")
    else: flash("Este correo no tiene un comprobante relacionado","error")
    return redirect(url_for("emails.center"))
