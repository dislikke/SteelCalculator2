from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from sqlalchemy import or_
from ..models.variant import Variant
from ..models.result import Result
from ..services.optimizer import optimize_custom, default_params
from ..extensions import db
import datetime


form_bp = Blueprint("form", __name__, url_prefix="/form")


def to_float(x):
    """Безопасное преобразование в float (numpy.float64 → float)."""
    try:
        return float(x) if x is not None else None
    except Exception:
        return None

def build_default_values():
    defaults = default_params()
    return {
        "bounds": {
            "cr": [0, 0],
            "ni": [0, 0],
            "mo": [0, 0],
            "mn": [0, 0],
        },
        "cost": {
            "cr": 1.0,
            "ni": 1.0,
            "mo": 1.0,
            "mn": 1.0,
        },
        "req": {
            "sigma": defaults["req"]["sigma"],
            "hrc": defaults["req"]["hrc"],
            "t": defaults["req"]["t"],
        },
        "limits": {
            "sum_max": defaults["limits"]["sum_max"],
            "sum_min": defaults["limits"]["sum_min"],
            "crni_max": defaults["limits"]["crni_max"],
        },
        "coef": defaults["coef"],
    }


def build_variants_data(variants):
    return {
        str(v.id): {
            "bounds": {
                "cr": [v.cr_min, v.cr_max],
                "ni": [v.ni_min, v.ni_max],
                "mo": [v.mo_min, v.mo_max],
                "mn": [v.mn_min, v.mn_max],
            },
            "cost": {
                "cr": v.cost_cr,
                "ni": v.cost_ni,
                "mo": v.cost_mo,
                "mn": v.cost_mn,
            },
            "req": {
                "sigma": v.sigma_req,
                "hrc": v.hard_req,
                "t": v.t_req,
            },
            "limits": {
                "sum_max": v.sum_max,
                "sum_min": v.sum_min,
                "crni_max": v.crni_max,
            },
            "coef": {
                "sigma_base": float(v.coef.get("sigma_base", 500)),
                "sigma_Cr": float(v.coef.get("sigma_Cr", 200)),
                "sigma_Mo": float(v.coef.get("sigma_Mo", 150)),
                "sigma_CrMo": float(v.coef.get("sigma_CrMo", 50)),
                "hrc_base": float(v.coef.get("hrc_base", 30)),
                "hrc_Ni": float(v.coef.get("hrc_Ni", 3)),
                "hrc_Mn": float(v.coef.get("hrc_Mn", 8)),
                "hrc_NiMn": float(v.coef.get("hrc_NiMn", 2)),
                "T_base": float(v.coef.get("T_base", 1530)),
                "T_drop": float(v.coef.get("T_drop", 15)),
            },
        }
        for v in variants
    }

@form_bp.route("/", methods=["GET", "POST"])
def form():

    ADMIN_ID = 2

    if session.get("user_id"):
        variants = Variant.query.filter(
            or_(
                Variant.user_id == ADMIN_ID,
                Variant.user_id == session["user_id"]
            )
        ).all()
    else:
        variants = Variant.query.filter_by(user_id=ADMIN_ID).all()

    values = {}
    default_values = build_default_values()
    variants_data = build_variants_data(variants)
    if request.method == "POST":
        variant_id = request.form.get("variant_id")
        variant = Variant.query.get(int(variant_id)) if variant_id else None

        # --- Берём параметры по умолчанию ---
        params = default_params()
        values["variant_id"] = variant.id if variant else None

        use_selected_variant = request.form.get("use_selected_variant") == "1"

        params["cost"] = {
            "Cr": float(request.form.get("cost_cr", 0)),
            "Ni": float(request.form.get("cost_ni", 0)),
            "Mo": float(request.form.get("cost_mo", 0)),
            "Mn": float(request.form.get("cost_mn", 0)),
        }
        params["req"] = {
            "sigma": float(request.form.get("sigma_req", 0)),
            "hrc": float(request.form.get("hard_req", 0)),
            "t": float(request.form.get("t_req", 0)),
        }
        params["bounds"] = {
            "Cr": (
                float(request.form.get("cr_min", 0)),
                float(request.form.get("cr_max", 0)),
            ),
            "Ni": (
                float(request.form.get("ni_min", 0)),
                float(request.form.get("ni_max", 0)),
            ),
            "Mo": (
                float(request.form.get("mo_min", 0)),
                float(request.form.get("mo_max", 0)),
            ),
            "Mn": (
                float(request.form.get("mn_min", 0)),
                float(request.form.get("mn_max", 0)),
            ),
        }

        # --- Лимиты ---
        values["sum_max"] = float(request.form.get("sum_max", 6.0))
        values["sum_min"] = float(request.form.get("sum_min", 0.0))
        values["crni_max"] = float(request.form.get("crni_max", 2.0))
        params["limits"] = {
            "sum_max": values["sum_max"],
            "sum_min": values["sum_min"],
            "crni_max": values["crni_max"],
        }

        # --- Дополнительные коэффициенты ---
        coef_keys = [
            "sigma_base",
            "sigma_Cr",
            "sigma_Mo",
            "sigma_CrMo",
            "hrc_base",
            "hrc_Ni",
            "hrc_Mn",
            "hrc_NiMn",
            "T_base",
            "T_drop",
        ]
        values["coef"] = {}
        for key in coef_keys:
            values["coef"][key] = float(request.form.get(key, 0))
            params.setdefault("coef", {})[key] = values["coef"][key]

        # --- Подставляем параметры для автозаполнения формы ---
        values["cost"] = {
            "cr": params["cost"]["Cr"],
            "ni": params["cost"]["Ni"],
            "mo": params["cost"]["Mo"],
            "mn": params["cost"]["Mn"],
        }
        values["req"] = params["req"]
        values["bounds"] = {
            "cr": params["bounds"]["Cr"],
            "ni": params["bounds"]["Ni"],
            "mo": params["bounds"]["Mo"],
            "mn": params["bounds"]["Mn"],
        }

        try:
            # --- Оптимизация ---
            result_data = optimize_custom(params)
            if not result_data:
                flash("❌ Подходящего варианта решения не найдено.", "danger")
                return render_template("form.html", variants=variants, values=values, default_values=default_values,
variants_data=variants_data,)

            composition = result_data.get("composition", {})
            properties = result_data.get("properties", {})

            # --- Сбор причин нарушения условий ---
            reasons = []

            Cr = composition.get("Cr", 0)
            Ni = composition.get("Ni", 0)
            Mo = composition.get("Mo", 0)
            Mn = composition.get("Mn", 0)
            sum_additives = Cr + Ni + Mo + Mn

            if sum_additives < values["sum_min"] or sum_additives > values["sum_max"]:
                reasons.append(
                    f"Сумма добавок ({sum_additives:.2f}%) вне диапазона ({values['sum_min']}–{values['sum_max']})"
                )
            if Cr * Ni > values["crni_max"]:  # поправил на умножение вместо сложения
                reasons.append(
                    f"Cr*Ni ({Cr * Ni:.2f}) превышает максимум {values['crni_max']}"
                )

            sigma = properties.get("sigma", 0)
            hrc = properties.get("hrc", 0)
            T = properties.get("T", 0)
            req = params.get("req", {})

            EPS = 0.1  # допуск

            if sigma + EPS < req.get("sigma", 0):
                reasons.append(f"σ={sigma:.1f} меньше требуемого {req.get('sigma')}")
            if hrc + EPS < req.get("hrc", 0):
                reasons.append(f"HRC={hrc:.1f} меньше требуемого {req.get('hrc')}")
            if T + EPS < req.get("t", 0):
                reasons.append(f"T={T:.1f} меньше требуемого {req.get('t')}")

            # --- Сохраняем результат в БД ---
            # --- Авторизованный пользователь: сохраняем в БД ---
            saved_variant_id = int(variant_id) if variant_id and use_selected_variant else None
            if session.get("user_id"):
                new_result = Result(
                    user_id=session["user_id"],

                    variant_id = saved_variant_id,
                    cr=to_float(Cr),
                    ni=to_float(Ni),
                    mo=to_float(Mo),
                    mn=to_float(Mn),
                    sigma=to_float(sigma),
                    hardness=to_float(hrc),
                    t_melt=to_float(T),
                    cost=to_float(result_data.get("cost", 0)),
                    created_at=datetime.datetime.now(datetime.timezone.utc),
                    limits={
                        "sum_min": values["sum_min"],
                        "sum_max": values["sum_max"],
                        "crni_max": values["crni_max"],
                    },
                    req=req,
                )

                db.session.add(new_result)
                db.session.commit()

                session["last_result"] = {
                    "id": new_result.id,
                    "variant_id": saved_variant_id,
                    "variant_name": variant.name if saved_variant_id and variant else "Ручной ввод",
                    "composition": composition,
                    "properties": properties,
                    "cost": result_data.get("cost", 0),
                    "coef": params.get("coef", {}),
                    "reasons": reasons,
                }

                if reasons:
                    flash(
                        "⚠️ Не удалось достичь всех требований. "
                        "Показан наиболее близкий результат. Причины: "
                        + "; ".join(reasons),
                        "warning",
                    )
                else:
                    flash(
                        "✅ Оптимизация выполнена успешно — найдено решение, удовлетворяющее всем требованиям!",
                        "success",
                    )

                return redirect(url_for("report.report", result_id=new_result.id))

            # --- Гость: только временный результат, без сохранения ---
            else:
                session["last_result"] = {
                    "id": None,
                    "variant_id": saved_variant_id,
                    "variant_name": variant.name if saved_variant_id and variant else "Ручной ввод",
                    "composition": composition,
                    "properties": properties,
                    "cost": result_data.get("cost", 0),
                    "coef": params.get("coef", {}),
                    "reasons": reasons,
                }

                if reasons:
                    flash(
                        "⚠️ Расчёт выполнен без сохранения. "
                        "Показан наиболее близкий результат. Причины: "
                        + "; ".join(reasons),
                        "warning",
                    )
                else:
                    flash(
                        "✅ Расчёт выполнен без сохранения. Войдите в систему, чтобы сохранить результат.",
                        "info",
                    )

                return redirect(url_for("report.temp_report"))

        except Exception as e:
            db.session.rollback()
            flash(f"Ошибка при оптимизации: {str(e)}", "danger")
            return render_template("form.html", variants=variants, values=values, default_values=default_values,
variants_data=variants_data,)

    # GET → показываем форму
    if not values:
        defaults = default_params()
        values = {
            "variant_id": None,
            "cost": {
                "cr": 1.0,
                "ni": 1.0,
                "mo": 1.0,
                "mn": 1.0,
            },
            "req": defaults["req"],
            "bounds": {
                "cr": [0, 0],
                "ni": [0, 0],
                "mo": [0, 0],
                "mn": [0, 0],
            },
            "coef": defaults["coef"],
            "sum_max": defaults["limits"]["sum_max"],
            "sum_min": defaults["limits"]["sum_min"],
            "crni_max": defaults["limits"]["crni_max"],
        }

    return render_template("form.html", variants=variants, values=values, default_values=default_values,
variants_data=variants_data,)
