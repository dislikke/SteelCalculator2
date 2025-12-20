from ..extensions import db
from sqlalchemy.dialects.postgresql import JSON


class Variant(db.Model):
    __tablename__ = "variants"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

    cr_min = db.Column(db.Float)
    cr_max = db.Column(db.Float)
    ni_min = db.Column(db.Float)
    ni_max = db.Column(db.Float)
    mo_min = db.Column(db.Float)
    mo_max = db.Column(db.Float)
    mn_min = db.Column(db.Float)
    mn_max = db.Column(db.Float)

    cost_cr = db.Column(db.Float)
    cost_ni = db.Column(db.Float)
    cost_mo = db.Column(db.Float)
    cost_mn = db.Column(db.Float)

    sigma_req = db.Column(db.Float)
    hard_req = db.Column(db.Float)
    t_req = db.Column(db.Float)

    sum_max = db.Column(db.Float, default=6.0)
    sum_min = db.Column(db.Float, default=0.0)
    crni_max = db.Column(db.Float, default=2.0)

    coef = db.Column(JSON, default={})  # коэффициенты для графиков и оптимизации

    def __repr__(self):
        return f"<Variant {self.name}>"
