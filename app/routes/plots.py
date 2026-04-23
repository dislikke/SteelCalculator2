import io
import base64
import numpy as np
import matplotlib
import plotly.graph_objects as go
from ..utils.auth import login_required
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

matplotlib.use("Agg")  # Без окон, только для сохранения в файл или буфер
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

def generate_interactive_sigma_plot(result):
    if not result:
        return None

    if hasattr(result, "cr"):
        Cr, Mo = result.cr, result.mo
        coef = getattr(result, "coef", {}) or {}
    else:
        Cr = result["composition"]["Cr"]
        Mo = result["composition"]["Mo"]
        coef = result.get("coef", {}) or {}

    cr_vals = np.linspace(0, 3, 40)
    mo_vals = np.linspace(0, 2, 40)
    Cr_grid, Mo_grid = np.meshgrid(cr_vals, mo_vals)

    sigma_grid = (
        coef.get("sigma_base", 500)
        + coef.get("sigma_Cr", 200) * Cr_grid
        + coef.get("sigma_Mo", 150) * Mo_grid
        + coef.get("sigma_CrMo", 50) * Cr_grid * Mo_grid
    )

    sigma_point = (
        coef.get("sigma_base", 500)
        + coef.get("sigma_Cr", 200) * Cr
        + coef.get("sigma_Mo", 150) * Mo
        + coef.get("sigma_CrMo", 50) * Cr * Mo
    )

    fig = go.Figure()

    fig.add_trace(go.Surface(
        x=Cr_grid,
        y=Mo_grid,
        z=sigma_grid,
        colorscale="Viridis",
        opacity=0.9,
        showscale=True,
        name="Поверхность прочности"
    ))

    fig.add_trace(go.Scatter3d(
        x=[Cr],
        y=[Mo],
        z=[sigma_point],
        mode="markers",
        marker=dict(size=6, color="red"),
        name="Оптимум"
    ))

    fig.update_layout(
        title="Интерактивная 3D-поверхность прочности σ(Cr, Mo)",
        scene=dict(
            xaxis_title="Cr (%)",
            yaxis_title="Mo (%)",
            zaxis_title="σ (МПа)"
        ),
        margin=dict(l=0, r=0, b=0, t=50),
        height=500
    )

    return fig.to_html(full_html=False, include_plotlyjs="cdn")

def generate_plots(result):
    """Генерация всех графиков по результату (ORM-объект или словарь из session)."""
    if not result:
        return []

    # Поддерживаем как ORM-объект, так и словарь из session
    if hasattr(result, "cr"):
        Cr, Ni, Mo, Mn = result.cr, result.ni, result.mo, result.mn
        #  sigma, hrc, T = result.sigma, result.hardness, result.t_melt
        T = result.t_melt

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
    values = [
        0 if v is None or (isinstance(v, float) and np.isnan(v)) else v for v in values
    ]
    ax.bar(elements, values, color=["#e74c3c", "#3498db", "#9b59b6", "#2ecc71"])
    ax.set_title("Состав сплава (%)")
    plots.append(fig_to_base64(fig))

    # ---------- Pie chart ----------
    fig, ax = plt.subplots()
    if sum(values) > 0:
        ax.pie(values, labels=elements, autopct="%1.1f%%", startangle=90)
    else:
        ax.text(0.5, 0.5, "Нет данных для графика", ha="center", va="center")
    ax.set_title("Доли элементов")
    plots.append(fig_to_base64(fig))

    # ---------- Sigma vs Cr/Mo ----------
    fig, ax = plt.subplots()
    cr_vals = np.linspace(0, 3, 30)
    mo_vals = np.linspace(0, 2, 30)
    Cr_grid, Mo_grid = np.meshgrid(cr_vals, mo_vals)
    sigma_grid = (
        coef.get("sigma_base", 500)
        + coef.get("sigma_Cr", 200) * Cr_grid
        + coef.get("sigma_Mo", 150) * Mo_grid
        + coef.get("sigma_CrMo", 50) * Cr_grid * Mo_grid
    )
    cs = ax.contourf(Cr_grid, Mo_grid, sigma_grid, levels=20, cmap="viridis")
    fig.colorbar(cs, ax=ax)
    ax.scatter(Cr, Mo, color="red", marker="x", s=100, label="Оптимум")
    ax.legend()
    ax.set_xlabel("Cr (%)")
    ax.set_ylabel("Mo (%)")
    ax.set_title("Прочность σ (МПа)")
    plots.append(fig_to_base64(fig))

    # ---------- 3D Sigma vs Cr/Mo ----------
    fig = plt.figure()
    ax = fig.add_subplot(111, projection="3d")

    cr_vals = np.linspace(0, 3, 30)
    mo_vals = np.linspace(0, 2, 30)
    Cr_grid, Mo_grid = np.meshgrid(cr_vals, mo_vals)

    sigma_grid = (
            coef.get("sigma_base", 500)
            + coef.get("sigma_Cr", 200) * Cr_grid
            + coef.get("sigma_Mo", 150) * Mo_grid
            + coef.get("sigma_CrMo", 50) * Cr_grid * Mo_grid
    )

    ax.plot_surface(Cr_grid, Mo_grid, sigma_grid, cmap="viridis", edgecolor="none", alpha=0.9)

    sigma_point = (
            coef.get("sigma_base", 500)
            + coef.get("sigma_Cr", 200) * Cr
            + coef.get("sigma_Mo", 150) * Mo
            + coef.get("sigma_CrMo", 50) * Cr * Mo
    )

    ax.scatter(Cr, Mo, sigma_point, color="red", s=60, label="Оптимум")

    ax.set_xlabel("Cr (%)")
    ax.set_ylabel("Mo (%)")
    ax.set_zlabel("σ (МПа)")
    ax.set_title("3D-поверхность прочности σ")
    ax.legend()

    plots.append(fig_to_base64(fig))

    # ---------- Hardness HRC vs Ni/Mn ----------
    fig, ax = plt.subplots()
    ni_vals = np.linspace(0, 2, 30)
    mn_vals = np.linspace(0, 3, 30)
    Ni_grid, Mn_grid = np.meshgrid(ni_vals, mn_vals)
    hrc_grid = (
        coef.get("hrc_base", 30)
        + coef.get("hrc_Ni", 3) * Ni_grid
        + coef.get("hrc_Mn", 8) * Mn_grid
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
    T_vals = coef.get("T_base", 1530) - coef.get("T_drop",15) * total_vals
    ax.plot(total_vals, T_vals, label="T расчётная")
    ax.axhline(y=T, color="r", linestyle="--", label=f"Оптимум T={T:.1f}°C")
    ax.set_xlabel("Сумма добавок (%)")
    ax.set_ylabel("Температура (°C)")
    ax.set_title("Температура плавления")
    ax.legend()
    plots.append(fig_to_base64(fig))

    return plots


@plots_bp.route("/")
@login_required
def show_plots():
    result = session.get("last_result")
    plots = generate_plots(result)
    interactive_sigma_plot = generate_interactive_sigma_plot(result)
    message = None if plots else "Результат не найден"

    return render_template(
        "plots/index.html",
        plots=plots,
        interactive_sigma_plot=interactive_sigma_plot,
        message=message
    )