from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from ..extensions import db
from ..models.user import User

user = Blueprint("user", __name__, url_prefix="/auth")


@user.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not username or not email or not password:
            flash("Заполните все поля", "danger")
            return render_template("auth/register.html")

        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()

        if existing_user:
            flash("Пользователь с таким именем или email уже существует", "warning")
            return render_template("auth/register.html")

        new_user = User(username=username, email=email)
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        flash("Регистрация прошла успешно. Теперь войдите в систему.", "success")
        return redirect(url_for("user.login"))

    return render_template("auth/register.html")


@user.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        user_obj = User.query.filter_by(email=email).first()

        if user_obj and user_obj.check_password(password):
            session["user_id"] = user_obj.id
            session["username"] = user_obj.username
            flash("Вы успешно вошли в систему", "success")
            return redirect(url_for("main.index"))

        flash("Неверный email или пароль", "danger")

    return render_template("auth/login.html")


@user.route("/logout")
def logout():
    session.clear()
    flash("Вы вышли из аккаунта", "info")
    return redirect(url_for("main.index"))