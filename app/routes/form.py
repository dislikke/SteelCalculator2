from flask import Blueprint, render_template, request, redirect, url_for, flash, session
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


@form_bp.route("/", methods=["GET", "POST"])
def form():
    variants = Variant.query.all()
    values = {}

    if request.method == "POST":
        variant_id = request.form.get("variant_id")
        variant = Variant.query.get(int(variant_id)) if variant_id else None

        # --- Берём параметры по умолчанию ---
        params = default_params()
        values["variant_id"] = variant.id if variant else None

        if variant:  # выбран готовый вариант
            params["cost"] = {
                "Cr": variant.cost_cr,
                "Ni": variant.cost_ni,
                "Mo": variant.cost_mo,
                "Mn": variant.cost_mn,
            }
            params["req"] = {
                "sigma": variant.sigma_req,
                "hrc": variant.hard_req,
                "t": variant.t_req,
            }
            params["bounds"] = {
                "Cr": (variant.cr_min, variant.cr_max),
                "Ni": (variant.ni_min, variant.ni_max),
                "Mo": (variant.mo_min, variant.mo_max),
                "Mn": (variant.mn_min, variant.mn_max),
            }
        else:  # ручной ввод
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
                "Cr": (float(request.form.get("cr_min", 0)), float(request.form.get("cr_max", 0))),
                "Ni": (float(request.form.get("ni_min", 0)), float(request.form.get("ni_max", 0))),
                "Mo": (float(request.form.get("mo_min", 0)), float(request.form.get("mo_max", 0))),
                "Mn": (float(request.form.get("mn_min", 0)), float(request.form.get("mn_max", 0))),
            }

        # --- Лимиты ---
        values["sum_max"] = float(request.form.get("sum_max", 6.0))
        values["sum_min"] = float(request.form.get("sum_min", 0.0))
        values["crni_max"] = float(request.form.get("crni_max", 2.0))
        params["limits"] = {
            "sum_max": values["sum_max"],
            "sum_min": values["sum_min"],
            "crni_max": values["crni_max"]
        }

        # --- Дополнительные коэффициенты ---
        coef_keys = ['sigma_base','sigma_Cr','sigma_Mo','sigma_CrMo',
                     'hrc_base','hrc_Ni','hrc_Mn','hrc_NiMn',
                     'T_base','T_drop']
        values["coef"] = {}
        for key in coef_keys:
            values["coef"][key] = float(request.form.get(key, 0))
            params.setdefault("coef", {})[key] = values["coef"][key]

        # --- Подставляем параметры для автозаполнения формы ---
        values["cost"] = params["cost"]
        values["req"] = params["req"]
        values["bounds"] = params["bounds"]

        try:
            # --- Оптимизация ---
            result_data = optimize_custom(params)
            if not result_data:
                flash("❌ Подходящего варианта решения не найдено.", "danger")
                return render_template("form.html", variants=variants, values=values)

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
            new_result = Result(
                variant_id=int(variant_id) if variant_id else None,
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
                    "crni_max": values["crni_max"]
                },
                req=params.get("req", {})
            )

            db.session.add(new_result)
            db.session.commit()

            # --- Сохраняем для графиков и отчёта ---
            session["last_result"] = {
                "id": new_result.id,
                "composition": composition,
                "properties": properties,
                "cost": result_data.get("cost", 0),
                "coef": params.get("coef", {}),
                "reasons": reasons
            }

            # --- Сообщение пользователю ---
            if reasons:
                flash(
                    "⚠️ Не удалось достичь всех требований. "
                    "Показан наиболее близкий результат. Причины: " + "; ".join(reasons),
                    "warning"
                )
            else:
                flash("✅ Оптимизация выполнена успешно — найдено решение, удовлетворяющее всем требованиям!", "success")

            return redirect(url_for("results.show", result_id=new_result.id))

        except Exception as e:
            db.session.rollback()
            flash(f"Ошибка при оптимизации: {str(e)}", "danger")
            return render_template("form.html", variants=variants, values=values)

    # GET → показываем форму
    if not values:
        defaults = default_params()
        values = {
            "variant_id": None,
            "cost": defaults.get("cost", {}),
            "req": defaults.get("req", {}),
            "bounds": defaults.get("bounds", {}),
            "coef": defaults.get("coef", {}),
            "sum_max": 6.0,
            "sum_min": 0.0,
            "crni_max": 2.0
        }

    return render_template("form.html", variants=variants, values=values)
