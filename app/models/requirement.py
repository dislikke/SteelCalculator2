from ..extensions import db


class Requirement(db.Model):
    __tablename__ = "requirements"

    id = db.Column(db.Integer, primary_key=True)
    sigma_req = db.Column(db.Float, default=1000.0)
    hard_req = db.Column(db.Float, default=50.0)
    t_req = db.Column(db.Float, default=1450.0)
    sum_limit = db.Column(db.Float, default=6.0)
    interaction_limit = db.Column(db.Float, default=2.0)

    def __repr__(self):
        return f"<Requirement σ={self.sigma_req}, HRC={self.hard_req}>"
