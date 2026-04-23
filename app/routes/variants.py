from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort, send_file
from sqlalchemy import or_
from pathlib import Path

from ..extensions import db
from ..models.variant import Variant
from ..utils.auth import login_required
from ..services.excel_service import read_variants_from_excel
from ..services.excel_export_service import build_excel_export

BASE_DIR = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = BASE_DIR / "resources" / "excel_template.xlsx"

variants_bp = Blueprint("variants", __name__, url_prefix="/variants")

ADMIN_ID = 2

@variants_bp.route("/", methods=["GET"])
def list_variants():
    q = request.args.get("q", "").strip()
    sort = request.args.get("sort", "id")
    direction = request.args.get("direction", "desc")
    page = request.args.get("page", 1, type=int)

    if "user_id" in session:
        query = Variant.query.filter(
            or_(
                Variant.user_id == ADMIN_ID,
                Variant.user_id == session["user_id"]
            )
        )
    else:
        query = Variant.query.filter_by(user_id=ADMIN_ID)

    if q:
        if q.isdigit():
            query = query.filter(
                or_(
                    Variant.name.ilike(f"%{q}%"),
                    Variant.id == int(q)
                )
            )
        else:
            query = query.filter(Variant.name.ilike(f"%{q}%"))

    sort_map = {
        "id": Variant.id,
        "name": Variant.name,
        "cr_min": Variant.cr_min,
        "ni_min": Variant.ni_min,
        "mo_min": Variant.mo_min,
        "mn_min": Variant.mn_min,
    }

    sort_column = sort_map.get(sort, Variant.id)

    if direction == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    pagination = query.paginate(page=page, per_page=10, error_out=False)

    return render_template(
        "variants/list.html",
        variants=pagination.items,
        pagination=pagination,
        q=q,
        sort=sort,
        direction=direction,
    )

@variants_bp.route("/template")
@login_required
def download_template():
    return send_file(
        TEMPLATE_PATH,
        as_attachment=True,
        download_name="excel_template.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

@variants_bp.route("/export")
@login_required
def export_variants():
    user_id = session["user_id"]

    variants = (
        Variant.query.filter(
            or_(
                Variant.user_id == ADMIN_ID,
                Variant.user_id == user_id
            )
        )
        .order_by(Variant.id.asc())
        .all()
    )

    output = build_excel_export(variants, [])

    return send_file(
        output,
        as_attachment=True,
        download_name="variants_export.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

def normalize_coef(coef: dict | None) -> dict:
    if not coef:
        return {}

    keys = [
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

    normalized = {}
    for key in keys:
        value = coef.get(key)
        normalized[key] = float(value) if value is not None else None
    return normalized


def find_duplicate_variant(user_id, item):
    candidates = Variant.query.filter_by(
        user_id=user_id,
        cr_min=item["cr_min"],
        cr_max=item["cr_max"],
        ni_min=item["ni_min"],
        ni_max=item["ni_max"],
        mo_min=item["mo_min"],
        mo_max=item["mo_max"],
        mn_min=item["mn_min"],
        mn_max=item["mn_max"],
        cost_cr=item["cost_cr"],
        cost_ni=item["cost_ni"],
        cost_mo=item["cost_mo"],
        cost_mn=item["cost_mn"],
        sigma_req=item["sigma_req"],
        hard_req=item["hard_req"],
        t_req=item["t_req"],
        sum_min=item["sum_min"],
        sum_max=item["sum_max"],
        crni_max=item["crni_max"],
    ).all()

    target_coef = normalize_coef(item.get("coef"))

    for candidate in candidates:
        candidate_coef = normalize_coef(candidate.coef)
        if candidate_coef == target_coef:
            return candidate

    return None

@variants_bp.route("/import", methods=["POST"])
@login_required
def import_excel():
    file = request.files.get("excel_file")

    if not file or file.filename == "":
        flash("Выберите Excel-файл для загрузки", "warning")
        return redirect(url_for("variants.list_variants"))

    if not file.filename.lower().endswith(".xlsx"):
        flash("Поддерживаются только файлы формата .xlsx", "danger")
        return redirect(url_for("variants.list_variants"))

    try:
        variants_data = read_variants_from_excel(file)

        added_count = 0
        skipped_count = 0
        user_id = session["user_id"]

        for item in variants_data:
            duplicate = find_duplicate_variant(user_id, item)
            if duplicate:
                skipped_count += 1
                continue

            variant = Variant(
                user_id=user_id,
                name=item["name"],
                cr_min=item["cr_min"],
                cr_max=item["cr_max"],
                ni_min=item["ni_min"],
                ni_max=item["ni_max"],
                mo_min=item["mo_min"],
                mo_max=item["mo_max"],
                mn_min=item["mn_min"],
                mn_max=item["mn_max"],
                cost_cr=item["cost_cr"],
                cost_ni=item["cost_ni"],
                cost_mo=item["cost_mo"],
                cost_mn=item["cost_mn"],
                sigma_req=item["sigma_req"],
                hard_req=item["hard_req"],
                t_req=item["t_req"],
                sum_min=item["sum_min"],
                sum_max=item["sum_max"],
                crni_max=item["crni_max"],
                coef=item["coef"],
            )
            db.session.add(variant)
            added_count += 1

        db.session.commit()

        if skipped_count:
            flash(
                f"Импорт завершён: добавлено {added_count}, пропущено дубликатов {skipped_count}.",
                "success",
            )
        else:
            flash(f"Успешно загружено вариантов: {added_count}", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Ошибка при импорте Excel: {str(e)}", "danger")

    return redirect(url_for("variants.list_variants"))

@variants_bp.route("/add", methods=["GET", "POST"])
@login_required
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
                "T_drop": request.form.get("T_drop", 15),
            }
            v = Variant(
                user_id=session["user_id"],
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
                coef=coef,
            )

            db.session.add(v)
            db.session.flush()
            db.session.commit()
            flash("Вариант успешно добавлен!", "success")
            return redirect(url_for("variants.list_variants"))
        except Exception as e:
            db.session.rollback()
            flash(f"Ошибка при добавлении варианта: {str(e)}", "danger")
    return render_template("variants/add.html")


@variants_bp.route("/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit(id):
    v = Variant.query.get_or_404(id)
    if v.user_id != session["user_id"]:
        abort(403)
    if request.method == "POST":
        try:
            v.name = request.form["name"]
            for field in [
                "cr_min",
                "cr_max",
                "ni_min",
                "ni_max",
                "mo_min",
                "mo_max",
                "mn_min",
                "mn_max",
                "cost_cr",
                "cost_ni",
                "cost_mo",
                "cost_mn",
                "sum_max",
                "sum_min",
                "crni_max",
            ]:
                setattr(v, field, float(request.form.get(field, 0)))

            v.sigma_req = float(request.form.get("sigma_req", 0))
            v.hard_req = float(request.form.get("hard_req", 0))
            v.t_req = float(request.form.get("t_req", 0))
            v.coef = {
                k: request.form.get(k)
                for k in [
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
            }
            db.session.commit()
            flash("Вариант обновлён!", "success")
            return redirect(url_for("variants.list_variants"))
        except Exception as e:
            db.session.rollback()
            flash(f"Ошибка при обновлении варианта: {str(e)}", "danger")
    return render_template("variants/edit.html", v=v)

@login_required
@variants_bp.route("/delete/<int:id>", methods=["GET"])
def delete(id):
    v = Variant.query.get_or_404(id)

    if v.user_id != session["user_id"]:
        abort(403)
    try:
        db.session.delete(v)
        db.session.commit()
        flash("Вариант удалён", "info")
    except Exception as e:
        db.session.rollback()
        flash(f"Ошибка при удалении варианта: {str(e)}", "danger")
    return redirect(url_for("variants.list_variants"))
