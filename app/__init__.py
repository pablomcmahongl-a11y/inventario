import os

from flask import Flask, render_template

from .config import Config
from .extensions import db, migrate, login_manager, csrf
from .security import ensure_admin_password_configured


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def create_app(config_object=Config, **config_overrides):
    app = Flask(
        __name__,
        template_folder=os.path.join(REPO_ROOT, "templates"),
        static_folder=os.path.join(REPO_ROOT, "static"),
    )
    app.config.from_object(config_object)
    app.config.update(config_overrides)

    os.makedirs(app.config["UPLOAD_DIR"], exist_ok=True)
    os.makedirs(os.path.dirname(app.config["SQLALCHEMY_DATABASE_URI"].replace("sqlite:///", "")), exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Inicia sesión para continuar."
    login_manager.login_message_category = "error"
    csrf.init_app(app)

    ensure_admin_password_configured(app)

    from . import models  # noqa: F401 (registra los modelos en SQLAlchemy)
    from . import security  # noqa: F401 (registra el user_loader)

    from .blueprints.auth import bp as auth_bp
    from .blueprints.main import bp as main_bp
    from .blueprints.rooms import bp as rooms_bp
    from .blueprints.boxes import bp as boxes_bp
    from .blueprints.items import bp as items_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(rooms_bp)
    app.register_blueprint(boxes_bp)
    app.register_blueprint(items_bp)

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("errors/500.html"), 500

    return app
