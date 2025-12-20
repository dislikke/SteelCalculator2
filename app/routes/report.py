from flask import Blueprint, render_template
from ..models.result import Result

from .plots import generate_plots

report_bp = Blueprint("report", __name__, url_prefix="/report")


@report_bp.route("/<int:result_id>")
def report(result_id):
    result = Result.query.get(result_id)
    if not result:
        return "Результат не найден", 404

    plots = generate_plots(result)

    # --- Подтягиваем лимиты и требования ---
    limits = result.limits or {"sum_min": 0.0, "sum_max": 6.0, "crni_max": 2.0}
    req = result.req or {"sigma": 0.0, "hrc": 0.0, "t": 0.0}

    # Если результат привязан к Variant, можем использовать его требования
    if result.variant_id and result.variant:
        variant = result.variant
        req = {
            "sigma": variant.sigma_req,
            "hrc": variant.hard_req,
            "t": variant.t_req,
        }

    # --- Проверка условий ---
    Cr = result.cr
    Ni = result.ni
    Mo = result.mo
    Mn = result.mn
    sigma = result.sigma
    hrc = result.hardness
    T = result.t_melt

    EPS = 0.1  # допуск
    reasons = []

    sum_additives = Cr + Ni + Mo + Mn
    if sum_additives < limits["sum_min"] or sum_additives > limits["sum_max"]:
        reasons.append(
            f"Сумма добавок ({sum_additives:.2f}%) вне диапазона ({limits['sum_min']}–{limits['sum_max']})"
        )

    if Cr * Ni > limits.get("crni_max", 2.0):
        reasons.append(f"Cr×Ni ({Cr*Ni:.2f}) превышает максимум {limits.get('crni_max', 2.0)}")

    if sigma + EPS < req.get("sigma", 0):
        reasons.append(f"σ={sigma:.1f} меньше требуемого {req.get('sigma')}")
    if hrc + EPS < req.get("hrc", 0):
        reasons.append(f"HRC={hrc:.1f} меньше требуемого {req.get('hrc')}")
    if T + EPS < req.get("t", 0):
        reasons.append(f"T={T:.1f} меньше требуемого {req.get('t')}")

    return render_template("report/list.html", result=result, plots=plots, reasons=reasons)
