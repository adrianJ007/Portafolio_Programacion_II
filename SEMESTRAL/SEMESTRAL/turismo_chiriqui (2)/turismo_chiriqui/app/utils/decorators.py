from functools import wraps
from flask import session, redirect, url_for, abort
def login_required(fn):
    @wraps(fn)
    def wrapper(*a,**k): return fn(*a,**k) if session.get("user") else redirect(url_for("auth.login"))
    return wrapper
def roles_required(*roles):
    def deco(fn):
        @wraps(fn)
        def wrapper(*a,**k):
            if not session.get("user"): return redirect(url_for("auth.login"))
            if session.get("role") not in roles: abort(403)
            return fn(*a,**k)
        return wrapper
    return deco
