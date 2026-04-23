from flask import Blueprint, render_template, request, send_file, session
from datetime import datetime, time
from pathlib import Path

from ..models.result import Result
from ..models.variant import Variant
from ..services.excel_export_service import build_excel_export
from ..utils.auth import login_required
from sqlalchemy import or_

results_bp = Blueprint("results", __name__, url_prefix="/results")

BASE_DIR = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = BASE_DIR / "resources" / "excel_template.xlsx"


@results_bp.route("/")
@login_required
def list_results():
    user_id = session["user_id"]

    q = request.args.get("q", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()
    sort = request.args.get("sort", "created_at")
    direction = request.args.get("direction", "desc")
    page = request.args.get("page", 1, type=int)

    query = Result.query.filter(Result.user_id == user_id).outerjoin(Variant)

    # Поиск
    if q:
        filters = [Variant.name.ilike(f"%{q}%")]
        if q.isdigit():
            filters.append(Result.id == int(q))
        query = query.filter(or_(*filters))

    # Фильтр по дате
    if date_from:
        dt_from = datetime.combine(
            datetime.strptime(date_from, "%Y-%m-%d").date(),
            time.min
        )
        query = query.filter(Result.created_at >= dt_from)

    if date_to:
        dt_to = datetime.combine(
            datetime.strptime(date_to, "%Y-%m-%d").date(),
            time.max
        )
        query = query.filter(Result.created_at <= dt_to)

    # Сортировка
    sort_map = {
        "id": Result.id,
        "cost": Result.cost,
        "sigma": Result.sigma,
        "hardness": Result.hardness,
        "t_melt": Result.t_melt,
        "created_at": Result.created_at,
    }

    sort_column = sort_map.get(sort, Result.created_at)

    if direction == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    # Пагинация
    pagination = query.paginate(page=page, per_page=10, error_out=False)

    return render_template(
        "results/list.html",
        results=pagination.items,
        pagination=pagination,
        q=q,
        date_from=date_from,
        date_to=date_to,
        sort=sort,
        direction=direction,
    )


@results_bp.route("/export", methods=["POST"])
@login_required
def export_results():
    user_id = session["user_id"]

    q = request.form.get("q", "").strip()
    date_from = request.form.get("date_from", "").strip()
    date_to = request.form.get("date_to", "").strip()

    export_mode = request.form.get("export_mode", "all")
    variants_mode = request.form.get("variants_mode", "related")

    selected_ids = request.form.getlist("selected_result_ids")

    query = Result.query.filter(Result.user_id == user_id).outerjoin(Variant)

    # Поиск
    if q:
        filters = [Variant.name.ilike(f"%{q}%")]
        if q.isdigit():
            filters.append(Result.id == int(q))
        query = query.filter(or_(*filters))

    # Фильтр по дате
    if date_from:
        dt_from = datetime.combine(
            datetime.strptime(date_from, "%Y-%m-%d").date(),
            time.min
        )
        query = query.filter(Result.created_at >= dt_from)

    if date_to:
        dt_to = datetime.combine(
            datetime.strptime(date_to, "%Y-%m-%d").date(),
            time.max
        )
        query = query.filter(Result.created_at <= dt_to)

    # Какие результаты экспортировать
    if export_mode == "selected":
        if not selected_ids:
            pagination = (
                Result.query.filter(Result.user_id == user_id)
                .outerjoin(Variant)
                .order_by(Result.created_at.desc())
                .paginate(page=1, per_page=10, error_out=False)
            )

            return render_template(
                "results/list.html",
                results=pagination.items,
                pagination=pagination,
                q=q,
                date_from=date_from,
                date_to=date_to,
                sort="created_at",
                direction="desc",
                export_error="Выберите хотя бы один результат для экспорта.",
            )

        selected_ids_int = [int(x) for x in selected_ids]
        query = query.filter(Result.id.in_(selected_ids_int))

    results = query.order_by(Result.created_at.desc()).all()

    # Какие варианты включать в файл
    if variants_mode == "none":
        variants = []

    elif variants_mode == "related":
        variant_ids = sorted({r.variant_id for r in results if r.variant_id is not None})
        if variant_ids:
            variants = (
                Variant.query.filter(Variant.id.in_(variant_ids))
                .order_by(Variant.id.asc())
                .all()
            )
        else:
            variants = []

    elif variants_mode == "all":
        variants = (
            Variant.query.filter(Variant.user_id == user_id)
            .order_by(Variant.id.asc())
            .all()
        )

    else:
        variants = []

    output = build_excel_export(variants, results)

    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = f"results_export_{stamp}.xlsx"

    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@results_bp.route("/template")
@login_required
def download_template():
    return send_file(
        TEMPLATE_PATH,
        as_attachment=True,
        download_name="excel_template.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@results_bp.route("/<int:result_id>")
@login_required
def show(result_id):
    result = Result.query.get_or_404(result_id)

    if result.user_id != session["user_id"]:
        return "Нет доступа", 403

    limits = result.limits or {"sum_min": 0.0, "sum_max": 6.0, "crni_max": 2.0}
    req = result.req or {"sigma": 0.0, "hrc": 0.0, "t": 0.0}

    if result.variant_id and result.variant:
        variant = result.variant
        req = {
            "sigma": variant.sigma_req,
            "hrc": variant.hard_req,
            "t": variant.t_req,
        }

    Cr = result.cr
    Ni = result.ni
    Mo = result.mo
    Mn = result.mn
    sigma = result.sigma
    hrc = result.hardness
    T = result.t_melt

    EPS = 0.1
    reasons = []

    sum_additives = Cr + Ni + Mo + Mn
    if sum_additives < limits["sum_min"] or sum_additives > limits["sum_max"]:
        reasons.append(
            f"Сумма добавок ({sum_additives:.2f}%) вне диапазона ({limits['sum_min']}–{limits['sum_max']})"
        )

    if Cr * Ni > limits.get("crni_max", 2.0):
        reasons.append(
            f"Cr×Ni ({Cr*Ni:.2f}) превышает максимум {limits.get('crni_max', 2.0)}"
        )

    if sigma + EPS < req.get("sigma", 0):
        reasons.append(f"σ={sigma:.1f} меньше требуемого {req.get('sigma')}")
    if hrc + EPS < req.get("hrc", 0):
        reasons.append(f"HRC={hrc:.1f} меньше требуемого {req.get('hrc')}")
    if T + EPS < req.get("t", 0):
        reasons.append(f"T={T:.1f} меньше требуемого {req.get('t')}")

    return render_template("results/show.html", result=result, reasons=reasons)