from flask import Blueprint, render_template
from app.extensions import db
from app.models.requirement import Requirement

main = Blueprint("main", __name__)


@main.route("/")
@main.route("/index")
def index():
    return render_template("main/index.html")


@main.route("/about")
def about():
    return render_template("main/about.html")


@main.route("/db-test")
def db_test():
    # создаём таблицы, если их ещё нет
    db.create_all()

    # создаём запись в существующей таблице requirements
    req = Requirement(sigma_req=1234.0, hard_req=55.0, t_req=1500.0)
    db.session.add(req)
    db.session.commit()

    # читаем последнюю запись
    last = Requirement.query.order_by(Requirement.id.desc()).first()

    return (
        f"OK. Requirement saved: "
        f"id={last.id}, sigma={last.sigma_req}, "
        f"hardness={last.hard_req}, T={last.t_req}"
    )
