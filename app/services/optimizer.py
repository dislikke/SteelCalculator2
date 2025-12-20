# app/services/optimizer.py
from __future__ import annotations
from typing import Dict, Any, List, Tuple, Optional, Sequence, Union
import math
import numpy as np
from scipy.optimize import minimize, LinearConstraint, NonlinearConstraint


def default_params() -> Dict[str, Any]:
    """
    Базовые параметры из диплома (можно переопределять из формы/вариантов).
    Формулы соответствуют:
      - σ = 500 + 200*Cr + 150*Mo + 50*Cr*Mo
      - HRC = 30 + 3*Ni + 8*Mn + 2*Ni*Mn
      - T = 1530 - 15*(Cr + Ni + Mo + Mn)
    """
    return {
        "cost": {"Cr": 2.0, "Ni": 3.0, "Mo": 4.0, "Mn": 1.0},
        "req": {"sigma": 1000.0, "hrc": 50.0, "t": 1450.0},
        "bounds": {
            "Cr": (0.5, 2.0),
            "Ni": (0.5, 2.0),
            "Mo": (0.2, 1.5),
            "Mn": (0.5, 2.0),
        },
        "coef": {
            "sigma_base": 500.0,
            "sigma_Cr": 200.0,
            "sigma_Mo": 150.0,
            "sigma_CrMo": 50.0,
            "hrc_base": 30.0,
            "hrc_Ni": 3.0,
            "hrc_Mn": 8.0,
            "hrc_NiMn": 2.0,
            "T_base": 1530.0,
            "T_drop": 15.0,
        },
        "limits": {
            "sum_max": 6.0,
            "sum_min": 0.0,
            "crni_max": 2.0,
            "ni_max": None,
        },
        "solver": {
            "method": "SLSQP",
            "maxiter": 500,
            "tol": 1e-9,
            "multistart": True,
            "n_starts": 7,
            "seed": 42,
        },
    }


def _bounds_array(bounds_dict: Dict[str, Tuple[float, float]]) -> List[Tuple[float, float]]:
    return [bounds_dict["Cr"], bounds_dict["Ni"], bounds_dict["Mo"], bounds_dict["Mn"]]


def _midpoint(bounds: List[Tuple[float, float]]) -> np.ndarray:
    return np.array([(lo + hi) / 2.0 for (lo, hi) in bounds], dtype=float)


def _random_start(bounds: List[Tuple[float, float]], rng: np.random.Generator) -> np.ndarray:
    lo = np.array([b[0] for b in bounds], dtype=float)
    hi = np.array([b[1] for b in bounds], dtype=float)
    return lo + (hi - lo) * rng.random(size=4)


def _properties(x: np.ndarray, coef: Dict[str, float]) -> Dict[str, float]:
    Cr, Ni, Mo, Mn = x
    sigma = (
        coef["sigma_base"]
        + coef["sigma_Cr"] * Cr
        + coef["sigma_Mo"] * Mo
        + coef["sigma_CrMo"] * Cr * Mo
    )
    hrc = (
        coef["hrc_base"]
        + coef["hrc_Ni"] * Ni
        + coef["hrc_Mn"] * Mn
        + coef["hrc_NiMn"] * Ni * Mn
    )
    T = coef["T_base"] - coef["T_drop"] * (Cr + Ni + Mo + Mn)
    return {"sigma": sigma, "hrc": hrc, "T": T}


def _objective_cost(x: np.ndarray, cost: Dict[str, float]) -> float:
    Cr, Ni, Mo, Mn = x
    return cost["Cr"] * Cr + cost["Ni"] * Ni + cost["Mo"] * Mo + cost["Mn"] * Mn


def optimize_custom(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Основной оптимизатор.
    Возвращает состав, свойства, стоимость и отчёт по ограничениям.
    """
    cost: Dict[str, float] = params["cost"]
    req: Dict[str, float] = params["req"]
    coef: Dict[str, float] = params["coef"]
    limits: Dict[str, Optional[float]] = params.get("limits", {})
    solver: Dict[str, Any] = params.get("solver", {})

    bounds_list: List[Tuple[float, float]] = _bounds_array(params["bounds"])

    sum_max = limits.get("sum_max", None)
    sum_min = limits.get("sum_min", 0.0) or 0.0
    crni_max = limits.get("crni_max", None)
    ni_max = limits.get("ni_max", None)

    # ---- функции ограничений ----
    def c_strength(x: np.ndarray) -> float:
        return _properties(x, coef)["sigma"] - req["sigma"]

    def c_hardness(x: np.ndarray) -> float:
        return _properties(x, coef)["hrc"] - req["hrc"]

    def c_temperature(x: np.ndarray) -> float:
        return _properties(x, coef)["T"] - req["t"]

    def c_sum_max(x: np.ndarray) -> float:
        if sum_max is None:
            return 1.0
        return sum_max - float(np.sum(x))

    def c_sum_min(x: np.ndarray) -> float:
        return float(np.sum(x)) - float(sum_min)

    def c_crni(x: np.ndarray) -> float:
        if crni_max is None:
            return 1.0
        Cr, Ni, _, _ = x
        return crni_max - Cr * Ni

    def c_ni_max(x: np.ndarray) -> float:
        if ni_max is None:
            return 1.0
        _, Ni, _, _ = x
        return ni_max - Ni

    # ---- аннотация ограничений ----
    ConstraintType = Union[dict[str, Any], LinearConstraint, NonlinearConstraint]
    constraints: Sequence[ConstraintType] = [
        {"type": "ineq", "fun": c_strength},
        {"type": "ineq", "fun": c_hardness},
        {"type": "ineq", "fun": c_temperature},
        {"type": "ineq", "fun": c_sum_max},
        {"type": "ineq", "fun": c_sum_min},
        {"type": "ineq", "fun": c_crni},
        {"type": "ineq", "fun": c_ni_max},
    ]

    # ---- запуск оптимизации ----
    method = solver.get("method", "SLSQP")
    maxiter = solver.get("maxiter", 500)
    tol = solver.get("tol", 1e-9)
    multistart = bool(solver.get("multistart", True))
    n_starts = int(solver.get("n_starts", 7))
    seed = int(solver.get("seed", 42))

    results: List[Tuple[float, Any]] = []
    rng = np.random.default_rng(seed)

    starts: List[np.ndarray] = [_midpoint(bounds_list)]
    if multistart:
        for _ in range(max(0, n_starts - 1)):
            starts.append(_random_start(bounds_list, rng))

    for x0 in starts:
        res = minimize(
            fun=lambda v: _objective_cost(v, cost),
            x0=x0,
            method=method,
            bounds=bounds_list,
            constraints=constraints,
            options={"maxiter": maxiter, "ftol": tol, "disp": False},
        )
        if res.success:
            results.append((_objective_cost(res.x, cost), res))
        else:
            results.append((math.inf, res))

    best = None
    best_cost = math.inf
    for val, res in results:
        if res.success and val < best_cost:
            best_cost = val
            best = res
    if best is None:
        best = min(results, key=lambda t: t[0])[1]

    x_opt = np.clip(best.x, [b[0] for b in bounds_list], [b[1] for b in bounds_list])
    props = _properties(x_opt, coef)
    total_cost = _objective_cost(x_opt, cost)
    Cr, Ni, Mo, Mn = x_opt
    total = float(np.sum(x_opt))

    slacks = {
        "strength": float(c_strength(x_opt)),
        "hardness": float(c_hardness(x_opt)),
        "temperature": float(c_temperature(x_opt)),
        "sum_max": float(c_sum_max(x_opt)),
        "sum_min": float(c_sum_min(x_opt)),
        "crni": float(c_crni(x_opt)),
        "ni_max": float(c_ni_max(x_opt)),
    }
    active = {k: (v <= 1e-6) for k, v in slacks.items()}

    return {
        "composition": {"Cr": Cr, "Ni": Ni, "Mo": Mo, "Mn": Mn, "sum": total},
        "properties": {"sigma": props["sigma"], "hrc": props["hrc"], "T": props["T"]},
        "cost": total_cost,
        "success": bool(best.success),
        "message": str(best.message),
        "slacks": slacks,
        "active_constraints": active,
        "nit": int(getattr(best, "nit", 0)),
        "status": int(getattr(best, "status", -1)),
    }



