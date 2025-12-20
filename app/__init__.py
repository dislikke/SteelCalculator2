
from flask import Flask
from .extensions import db, migrate
from .config import Config
from .routes.user import user

from .routes.main import main
from .routes.form import form_bp
from .routes.results import results_bp
from .routes.variants import variants_bp
from .routes.plots import plots_bp

from .routes.report import report_bp




def  create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    app.register_blueprint(user)
    app.register_blueprint(main)
    app.register_blueprint(form_bp)
    app.register_blueprint(results_bp)
    app.register_blueprint(variants_bp)
    app.register_blueprint(plots_bp)
    app.register_blueprint(report_bp)


    db.init_app(app)
    migrate.init_app(app, db)

   # with app.app_context():
    #    db.create_all()

    return app
