import io
import base64
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Без окон, только для сохранения в файл или буфер
import matplotlib.pyplot as plt
from flask import Blueprint, render_template, session

plots_bp = Blueprint("plots", __name__, url_prefix="/plots")


def fig_to_base64(fig):
    """Конвертирует matplotlib.figure в base64 строку для вставки в HTML."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return encoded


def generate_plots(result):
    """Генерация всех графиков по результату (ORM-объект или словарь из session)."""
    if not result:
        return []

    # Поддерживаем как ORM-объект, так и словарь из session
    if hasattr(result, "cr"):
        Cr, Ni, Mo, Mn = result.cr, result.ni, result.mo, result.mn
        sigma, hrc, T = result.sigma, result.hardness, result.t_melt
        coef = getattr(result, "coef", {})
    else:
        Cr = result["composition"]["Cr"]
        Ni = result["composition"]["Ni"]
        Mo = result["composition"]["Mo"]
        Mn = result["composition"]["Mn"]
      #  sigma = result["properties"]["sigma"]
      #  hrc = result["properties"]["hrc"]
        T = result["properties"]["T"]
        coef = result.get("coef", {})

    plots = []

    # ---------- Bar chart ----------
    fig, ax = plt.subplots()
    elements = ["Cr", "Ni", "Mo", "Mn"]
    values = [Cr, Ni, Mo, Mn]
    # Заменяем None/NaN на 0
    values = [0 if v is None or (isinstance(v, float) and np.isnan(v)) else v for v in values]
    ax.bar(elements, values, color=["#e74c3c", "#3498db", "#9b59b6", "#2ecc71"])
    ax.set_title("Состав сплава (%)")
    plots.append(fig_to_base64(fig))

    # ---------- Pie chart ----------
    fig, ax = plt.subplots()
    if sum(values) > 0:
        ax.pie(values, labels=elements, autopct="%1.1f%%", startangle=90)
    else:
        ax.text(0.5, 0.5, "Нет данных для графика", ha='center', va='center')
    ax.set_title("Доли элементов")
    plots.append(fig_to_base64(fig))

    # ---------- Sigma vs Cr/Mo ----------
    fig, ax = plt.subplots()
    cr_vals = np.linspace(0, 3, 30)
    mo_vals = np.linspace(0, 2, 30)
    Cr_grid, Mo_grid = np.meshgrid(cr_vals, mo_vals)
    sigma_grid = (
        coef.get("sigma_base", 200)
        + coef.get("sigma_Cr", 50) * Cr_grid
        + coef.get("sigma_Mo", 40) * Mo_grid
        + coef.get("sigma_CrMo", 10) * Cr_grid * Mo_grid
    )
    cs = ax.contourf(Cr_grid, Mo_grid, sigma_grid, levels=20, cmap="viridis")
    fig.colorbar(cs, ax=ax)
    ax.scatter(Cr, Mo, color="red", marker="x", s=100, label="Оптимум")
    ax.legend()
    ax.set_xlabel("Cr (%)")
    ax.set_ylabel("Mo (%)")
    ax.set_title("Прочность σ (МПа)")
    plots.append(fig_to_base64(fig))

    # ---------- Hardness HRC vs Ni/Mn ----------
    fig, ax = plt.subplots()
    ni_vals = np.linspace(0, 2, 30)
    mn_vals = np.linspace(0, 3, 30)
    Ni_grid, Mn_grid = np.meshgrid(ni_vals, mn_vals)
    hrc_grid = (
        coef.get("hrc_base", 30)
        + coef.get("hrc_Ni", 5) * Ni_grid
        + coef.get("hrc_Mn", 3) * Mn_grid
        + coef.get("hrc_NiMn", 2) * Ni_grid * Mn_grid
    )
    cs = ax.contourf(Ni_grid, Mn_grid, hrc_grid, levels=20, cmap="plasma")
    fig.colorbar(cs, ax=ax)
    ax.scatter(Ni, Mn, color="red", marker="x", s=100, label="Оптимум")
    ax.legend()
    ax.set_xlabel("Ni (%)")
    ax.set_ylabel("Mn (%)")
    ax.set_title("Твёрдость HRC")
    plots.append(fig_to_base64(fig))

    # ---------- Temperature vs sum ----------
    fig, ax = plt.subplots()
    total_vals = np.linspace(0, 10, 100)
    T_vals = coef.get("T_base", 1600) - coef.get("T_drop", 20) * total_vals
    ax.plot(total_vals, T_vals, label="T расчётная")
    ax.axhline(y=T, color="r", linestyle="--", label=f"Оптимум T={T:.1f}°C")
    ax.set_xlabel("Сумма добавок (%)")
    ax.set_ylabel("Температура (°C)")
    ax.set_title("Температура плавления")
    ax.legend()
    plots.append(fig_to_base64(fig))

    return plots


@plots_bp.route("/")
def show_plots():
    result = session.get("last_result")
    plots = generate_plots(result)
    message = None if plots else "Результат не найден"
    return render_template("plots/index.html", plots=plots, message=message)
