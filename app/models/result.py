from datetime import datetime, timezone
from ..extensions import db
from sqlalchemy.dialects.postgresql import JSONB  # если используешь PostgreSQL


class Result(db.Model):
    __tablename__ = "results"

    id = db.Column(db.Integer, primary_key=True)
    variant_id = db.Column(db.Integer, db.ForeignKey("variants.id"), nullable=True)

    cr = db.Column(db.Float)
    ni = db.Column(db.Float)
    mo = db.Column(db.Float)
    mn = db.Column(db.Float)

    cost = db.Column(db.Float)
    sigma = db.Column(db.Float)
    hardness = db.Column(db.Float)
    t_melt = db.Column(db.Float)

    created_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    variant = db.relationship("Variant", backref="results")

    # --- Новые поля для ручного ввода ---
    limits = db.Column(
        JSONB, default={}
    )  # {"sum_min": 0, "sum_max": 6, "crni_max": 2.0}
    req = db.Column(JSONB, default={})  # {"sigma": ..., "hrc": ..., "t": ...}

    def __repr__(self):
        return f"<Result Variant={self.variant_id} Cost={self.cost}>"


def result_to_dict(result: "Result") -> dict:
    """Преобразует ORM-объект Result в словарь для session/графиков."""
    return {
        "id": result.id,
        "composition": {
            "Cr": result.cr,
            "Ni": result.ni,
            "Mo": result.mo,
            "Mn": result.mn,
        },
        "properties": {
            "sigma": result.sigma,
            "hrc": result.hardness,
            "T": result.t_melt,
        },
        "cost": result.cost,
        "coef": getattr(result, "coef", {}) or {},
        "limits": result.limits or {},
        "req": result.req or {},
    }
