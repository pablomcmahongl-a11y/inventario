import os
import io
import uuid
from datetime import datetime

from flask import (
    Flask, render_template, request, redirect, url_for,
    send_from_directory, abort, send_file, flash
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import qrcode

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
DB_PATH = os.path.join(BASE_DIR, "instance", "inventario.db")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# URL base con la que se generan los códigos QR de las cajas.
# Configúrala con la variable de entorno BASE_URL, por ejemplo:
# BASE_URL=http://192.168.1.50:8000  o  BASE_URL=https://inventario.midominio.com
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000").rstrip("/")

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB por foto
app.secret_key = os.environ.get("SECRET_KEY", "cambia-esto-en-produccion")

db = SQLAlchemy(app)


# ---------------------------------------------------------------- MODELOS

class Box(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    location = db.Column(db.String(120))
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship("Item", backref="box", lazy=True,
                             order_by="Item.name")


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    category = db.Column(db.String(120))
    notes = db.Column(db.Text)
    photo_filename = db.Column(db.String(300))
    box_id = db.Column(db.Integer, db.ForeignKey("box.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


with app.app_context():
    db.create_all()


# ---------------------------------------------------------------- HELPERS

def allowed_file(filename):
    return "." in filename and \
        filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_photo(file_storage):
    if not file_storage or file_storage.filename == "":
        return None
    if not allowed_file(file_storage.filename):
        return None
    ext = file_storage.filename.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    file_storage.save(os.path.join(UPLOAD_DIR, filename))
    return filename


def delete_photo(filename):
    if not filename:
        return
    path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(path):
        os.remove(path)


def all_categories():
    rows = db.session.query(Item.category).filter(
        Item.category.isnot(None), Item.category != ""
    ).distinct().order_by(Item.category).all()
    return [r[0] for r in rows]


# ---------------------------------------------------------------- RUTAS: DASHBOARD / ITEMS

@app.route("/")
def index():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    box_id = request.args.get("box_id", "").strip()

    query = Item.query

    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(Item.name.ilike(like), Item.notes.ilike(like))
        )
    if category:
        query = query.filter(Item.category == category)
    if box_id:
        query = query.filter(Item.box_id == int(box_id))

    items = query.order_by(Item.name).all()
    boxes = Box.query.order_by(Box.name).all()
    categories = all_categories()

    return render_template(
        "index.html", items=items, boxes=boxes, categories=categories,
        q=q, selected_category=category, selected_box=box_id
    )


@app.route("/items/new", methods=["GET", "POST"])
def item_new():
    boxes = Box.query.order_by(Box.name).all()
    categories = all_categories()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("El nombre es obligatorio.", "error")
            return render_template("item_form.html", item=None, boxes=boxes,
                                    categories=categories)

        item = Item(
            name=name,
            quantity=int(request.form.get("quantity") or 1),
            category=request.form.get("category", "").strip() or None,
            notes=request.form.get("notes", "").strip() or None,
            box_id=int(request.form["box_id"]) if request.form.get("box_id") else None,
        )
        item.photo_filename = save_photo(request.files.get("photo"))
        db.session.add(item)
        db.session.commit()
        flash("Objeto añadido.", "success")

        if item.box_id:
            return redirect(url_for("box_detail", box_id=item.box_id))
        return redirect(url_for("index"))

    preselect_box = request.args.get("box_id")
    return render_template("item_form.html", item=None, boxes=boxes,
                            categories=categories, preselect_box=preselect_box)


@app.route("/items/<int:item_id>/edit", methods=["GET", "POST"])
def item_edit(item_id):
    item = Item.query.get_or_404(item_id)
    boxes = Box.query.order_by(Box.name).all()
    categories = all_categories()

    if request.method == "POST":
        item.name = request.form.get("name", "").strip() or item.name
        item.quantity = int(request.form.get("quantity") or 1)
        item.category = request.form.get("category", "").strip() or None
        item.notes = request.form.get("notes", "").strip() or None
        item.box_id = int(request.form["box_id"]) if request.form.get("box_id") else None

        if request.form.get("remove_photo") == "1":
            delete_photo(item.photo_filename)
            item.photo_filename = None

        new_photo = save_photo(request.files.get("photo"))
        if new_photo:
            delete_photo(item.photo_filename)
            item.photo_filename = new_photo

        db.session.commit()
        flash("Objeto actualizado.", "success")
        return redirect(url_for("index"))

    return render_template("item_form.html", item=item, boxes=boxes,
                            categories=categories)


@app.route("/items/<int:item_id>/delete", methods=["POST"])
def item_delete(item_id):
    item = Item.query.get_or_404(item_id)
    box_id = item.box_id
    delete_photo(item.photo_filename)
    db.session.delete(item)
    db.session.commit()
    flash("Objeto eliminado.", "success")
    if box_id:
        return redirect(url_for("box_detail", box_id=box_id))
    return redirect(url_for("index"))


# ---------------------------------------------------------------- RUTAS: CAJAS

@app.route("/boxes")
def box_list():
    boxes = Box.query.order_by(Box.name).all()
    return render_template("box_list.html", boxes=boxes)


@app.route("/boxes/new", methods=["GET", "POST"])
def box_new():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("El nombre de la caja es obligatorio.", "error")
            return render_template("box_form.html", box=None)

        box = Box(
            name=name,
            location=request.form.get("location", "").strip() or None,
            description=request.form.get("description", "").strip() or None,
        )
        db.session.add(box)
        db.session.commit()
        flash("Caja creada. Ya puedes imprimir su código QR.", "success")
        return redirect(url_for("box_detail", box_id=box.id))

    return render_template("box_form.html", box=None)


@app.route("/boxes/<int:box_id>")
def box_detail(box_id):
    box = Box.query.get_or_404(box_id)
    qr_url = url_for("box_qr", box_id=box.id)
    public_url = f"{BASE_URL}{url_for('box_detail', box_id=box.id)}"
    return render_template("box_detail.html", box=box, qr_url=qr_url,
                            public_url=public_url)


@app.route("/boxes/<int:box_id>/edit", methods=["GET", "POST"])
def box_edit(box_id):
    box = Box.query.get_or_404(box_id)
    if request.method == "POST":
        box.name = request.form.get("name", "").strip() or box.name
        box.location = request.form.get("location", "").strip() or None
        box.description = request.form.get("description", "").strip() or None
        db.session.commit()
        flash("Caja actualizada.", "success")
        return redirect(url_for("box_detail", box_id=box.id))
    return render_template("box_form.html", box=box)


@app.route("/boxes/<int:box_id>/delete", methods=["POST"])
def box_delete(box_id):
    box = Box.query.get_or_404(box_id)
    for item in box.items:
        item.box_id = None
    db.session.delete(box)
    db.session.commit()
    flash("Caja eliminada. Sus objetos ahora no tienen caja asignada.", "success")
    return redirect(url_for("box_list"))


@app.route("/boxes/<int:box_id>/qr.png")
def box_qr(box_id):
    box = Box.query.get_or_404(box_id)
    target_url = f"{BASE_URL}{url_for('box_detail', box_id=box.id)}"

    img = qrcode.make(target_url, box_size=10, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


# ---------------------------------------------------------------- ARCHIVOS

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
