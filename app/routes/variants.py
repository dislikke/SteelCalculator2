from flask import Blueprint, render_template, request, redirect, url_for, flash
from ..extensions import db
from ..models.variant import Variant
import json

variants_bp = Blueprint("variants", __name__, url_prefix="/variants")

@variants_bp.route("/", methods=["GET"])
def list_variants():
    variants = Variant.query.all()
    return render_template("variants/list.html", variants=variants)

@variants_bp.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        try:
            coef = {
                "sigma_base": request.form.get("sigma_base", 500),
                "sigma_Cr": request.form.get("sigma_Cr", 200),
                "sigma_Mo": request.form.get("sigma_Mo", 150),
                "sigma_CrMo": request.form.get("sigma_CrMo", 50),
                "hrc_base": request.form.get("hrc_base", 30),
                "hrc_Ni": request.form.get("hrc_Ni", 3),
                "hrc_Mn": request.form.get("hrc_Mn", 8),
                "hrc_NiMn": request.form.get("hrc_NiMn", 2),
                "T_base": request.form.get("T_base", 1530),
                "T_drop": request.form.get("T_drop", 15)
            }
            v = Variant(
                name=request.form["name"],
                cr_min=float(request.form.get("cr_min", 0)),
                cr_max=float(request.form.get("cr_max", 0)),
                ni_min=float(request.form.get("ni_min", 0)),
                ni_max=float(request.form.get("ni_max", 0)),
                mo_min=float(request.form.get("mo_min", 0)),
                mo_max=float(request.form.get("mo_max", 0)),
                mn_min=float(request.form.get("mn_min", 0)),
                mn_max=float(request.form.get("mn_max", 0)),
                cost_cr=float(request.form.get("cost_cr", 0)),
                cost_ni=float(request.form.get("cost_ni", 0)),
                cost_mo=float(request.form.get("cost_mo", 0)),
                cost_mn=float(request.form.get("cost_mn", 0)),
                sigma_req=float(request.form.get("sigma_req", 0)),
                hard_req=float(request.form.get("hard_req", 0)),
                t_req=float(request.form.get("t_req", 0)),
                sum_max=float(request.form.get("sum_max", 6.0)),
                sum_min=float(request.form.get("sum_min", 0.0)),
                crni_max=float(request.form.get("crni_max", 2.0)),
                coef=coef
            )

            db.session.add(v)
            db.session.commit()
            flash("Вариант успешно добавлен!", "success")
            return redirect(url_for("variants.list_variants"))
        except Exception as e:
            db.session.rollback()
            flash(f"Ошибка при добавлении варианта: {str(e)}", "danger")
    return render_template("variants/add.html")

@variants_bp.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):
    v = Variant.query.get_or_404(id)
    if request.method == "POST":
        try:
            v.name = request.form["name"]
            for field in ["cr_min", "cr_max", "ni_min", "ni_max", "mo_min", "mo_max", "mn_min", "mn_max",
                          "cost_cr", "cost_ni", "cost_mo", "cost_mn", "sum_max", "sum_min", "crni_max"]:
                setattr(v, field, float(request.form.get(field, 0)))

            v.sigma_req = float(request.form.get("sigma_req", 0))
            v.hard_req = float(request.form.get("hard_req", 0))
            v.t_req = float(request.form.get("t_req", 0))
            v.coef = {k: request.form.get(k) for k in ["sigma_base","sigma_Cr","sigma_Mo","sigma_CrMo",
                                                       "hrc_base","hrc_Ni","hrc_Mn","hrc_NiMn",
                                                       "T_base","T_drop"]}
            db.session.commit()
            flash("Вариант обновлён!", "success")
            return redirect(url_for("variants.list_variants"))
        except Exception as e:
            db.session.rollback()
            flash(f"Ошибка при обновлении варианта: {str(e)}", "danger")
    return render_template("variants/edit.html", v=v)

@variants_bp.route("/delete/<int:id>", methods=["GET"])
def delete(id):
    v = Variant.query.get_or_404(id)
    try:
        db.session.delete(v)
        db.session.commit()
        flash("Вариант удалён", "info")
    except Exception as e:
        db.session.rollback()
        flash(f"Ошибка при удалении варианта: {str(e)}", "danger")
    return redirect(url_for("variants.list_variants"))

