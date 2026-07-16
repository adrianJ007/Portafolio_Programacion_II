import json
from pathlib import Path
from flask import Blueprint,render_template,request,send_file,current_app
from app.utils.decorators import roles_required
bp=Blueprint("json_api",__name__,url_prefix="/admin/json")
def files(): return sorted(Path(current_app.config["JSON_EXPORT_DIR"]).glob("**/*.json"),key=lambda p:p.stat().st_mtime,reverse=True)
@bp.get("/")
@roles_required("admin")
def viewer():
    kind=request.args.get("type",""); q=request.args.get("q","").lower(); rows=[]
    for p in files():
        if kind and p.parent.name!=kind: continue
        text=p.read_text(encoding="utf-8")
        if q and q not in text.lower() and q not in p.name.lower(): continue
        rows.append({"name":p.name,"type":p.parent.name,"content":text,"path":str(p)})
    return render_template("admin/json_viewer.html",rows=rows)
@bp.get("/download/<path:name>")
@roles_required("admin")
def download(name):
    item=next((p for p in files() if p.name==Path(name).name),None); return send_file(item,as_attachment=True) if item else ("No encontrado",404)
