from flask import Blueprint,request,jsonify
from app.services.chatbot_service import answer
bp=Blueprint("chatbot",__name__,url_prefix="/api/chatbot")
@bp.post("")
def chat(): return jsonify({"answer":answer((request.get_json(silent=True) or {}).get("message",""))})
