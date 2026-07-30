import secrets

from flask import current_app
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import login_manager


class AdminUser(UserMixin):
    id = "admin"

    def __init__(self, username):
        self.username = username


@login_manager.user_loader
def load_user(user_id):
    if user_id == "admin":
        return AdminUser(current_app.config["ADMIN_USERNAME"])
    return None


def verify_credentials(username, password):
    cfg = current_app.config
    if not cfg.get("ADMIN_PASSWORD_HASH"):
        return False
    if username != cfg["ADMIN_USERNAME"]:
        return False
    return check_password_hash(cfg["ADMIN_PASSWORD_HASH"], password)


def ensure_admin_password_configured(app):
    """Si no hay ADMIN_PASSWORD_HASH en el entorno, genera una contraseña
    aleatoria de un solo arranque y la deja en el log, para que la app nunca
    quede accesible sin contraseña ni completamente bloqueada."""
    if app.config.get("ADMIN_PASSWORD_HASH"):
        return
    if app.config.get("TESTING"):
        app.config["ADMIN_PASSWORD_HASH"] = generate_password_hash("test")
        return

    temp_password = secrets.token_urlsafe(9)
    app.config["ADMIN_PASSWORD_HASH"] = generate_password_hash(temp_password)
    app.logger.warning(
        "\n"
        "==================================================================\n"
        " No se ha configurado ADMIN_PASSWORD_HASH en .env\n"
        " Contraseña temporal generada para el usuario '%s': %s\n"
        " Esta contraseña cambia cada vez que se reinicia el contenedor.\n"
        " Genera una fija con:\n"
        "   python3 -c \"from werkzeug.security import generate_password_hash;"
        " print(generate_password_hash('tu-contraseña'))\"\n"
        " y ponla en .env como ADMIN_PASSWORD_HASH=...\n"
        "==================================================================",
        app.config["ADMIN_USERNAME"], temp_password,
    )
