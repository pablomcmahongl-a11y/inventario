import os
import uuid

from flask import current_app

from .extensions import db
from .models import Activity


def allowed_file(filename):
    return "." in filename and \
        filename.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]


def save_upload(file_storage):
    if not file_storage or file_storage.filename == "":
        return None
    if not allowed_file(file_storage.filename):
        return None
    ext = file_storage.filename.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    file_storage.save(os.path.join(current_app.config["UPLOAD_DIR"], filename))
    return filename


def delete_upload(filename):
    if not filename:
        return
    path = os.path.join(current_app.config["UPLOAD_DIR"], filename)
    if os.path.exists(path):
        os.remove(path)


def log_activity(entity_type, entity_id, entity_name, action, detail=None):
    db.session.add(Activity(
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=entity_name,
        action=action,
        detail=detail,
    ))


def all_categories():
    from .models import Item
    rows = db.session.query(Item.category).filter(
        Item.category.isnot(None), Item.category != ""
    ).distinct().order_by(Item.category).all()
    return [r[0] for r in rows]
