from functools import wraps
from flask import session, redirect, url_for, flash

def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            flash("Сначала войдите в систему", "warning")
            return redirect(url_for("user.login"))
        return view(*args, **kwargs)

    return wrapped_view