import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Config:
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(BASE_DIR, "instance", "inventario.db"),
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get("SECRET_KEY", "cambia-esto-en-produccion")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB por foto

    UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}

    # URL base con la que se generan los códigos QR de las cajas.
    BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000").rstrip("/")

    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH", "")

    WTF_CSRF_TIME_LIMIT = None
