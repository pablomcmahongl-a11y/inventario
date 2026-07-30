from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required

from ..extensions import db
from ..models import Box, Item, Photo, Activity
from ..utils import save_upload, delete_upload, log_activity, all_categories

bp = Blueprint("items", __name__, url_prefix="/items")


@bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    boxes = Box.query.order_by(Box.name).all()
    categories = all_categories()
    preselect_box = request.args.get("box_id")

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("El nombre es obligatorio.", "error")
            return render_template("item_form.html", item=None, boxes=boxes,
                                    categories=categories, preselect_box=preselect_box)
        try:
            item = Item(
                name=name,
                quantity=int(request.form.get("quantity") or 1),
                category=request.form.get("category", "").strip() or None,
                notes=request.form.get("notes", "").strip() or None,
                box_id=int(request.form["box_id"]) if request.form.get("box_id") else None,
            )
            db.session.add(item)
            db.session.flush()

            for file_storage in request.files.getlist("photos"):
                filename = save_upload(file_storage)
                if filename:
                    db.session.add(Photo(item_id=item.id, filename=filename))

            log_activity("item", item.id, item.name, "created")
            db.session.commit()
            flash("Objeto añadido.", "success")

            if item.box_id:
                return redirect(url_for("boxes.detail", box_id=item.box_id))
            return redirect(url_for("items.detail", item_id=item.id))
        except Exception as e:
            db.session.rollback()
            flash(f"Error al crear el objeto: {e}", "error")
            return render_template("item_form.html", item=None, boxes=boxes,
                                    categories=categories, preselect_box=preselect_box)

    return render_template("item_form.html", item=None, boxes=boxes,
                            categories=categories, preselect_box=preselect_box)


@bp.route("/<int:item_id>")
@login_required
def detail(item_id):
    item = Item.query.get_or_404(item_id)
    history = (
        Activity.query
        .filter_by(entity_type="item", entity_id=item.id)
        .order_by(Activity.timestamp.desc())
        .all()
    )
    return render_template("item_detail.html", item=item, history=history)


@bp.route("/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
def edit(item_id):
    item = Item.query.get_or_404(item_id)
    boxes = Box.query.order_by(Box.name).all()
    categories = all_categories()

    if request.method == "POST":
        try:
            old_box = item.box.name if item.box else "sin caja"
            item.name = request.form.get("name", "").strip() or item.name
            item.quantity = int(request.form.get("quantity") or 1)
            item.category = request.form.get("category", "").strip() or None
            item.notes = request.form.get("notes", "").strip() or None
            item.box_id = int(request.form["box_id"]) if request.form.get("box_id") else None
            new_box = item.box.name if item.box else "sin caja"

            for photo_id in request.form.getlist("remove_photo_ids"):
                photo = Photo.query.filter_by(id=int(photo_id), item_id=item.id).first()
                if photo:
                    delete_upload(photo.filename)
                    db.session.delete(photo)

            for file_storage in request.files.getlist("photos"):
                filename = save_upload(file_storage)
                if filename:
                    db.session.add(Photo(item_id=item.id, filename=filename))

            if old_box != new_box:
                log_activity("item", item.id, item.name, "moved", detail=f"{old_box} → {new_box}")
            else:
                log_activity("item", item.id, item.name, "updated")

            db.session.commit()
            flash("Objeto actualizado.", "success")
            if item.box_id:
                return redirect(url_for("boxes.detail", box_id=item.box_id))
            return redirect(url_for("items.detail", item_id=item.id))
        except Exception as e:
            db.session.rollback()
            flash(f"Error al actualizar el objeto: {e}", "error")

    return render_template("item_form.html", item=item, boxes=boxes, categories=categories)


@bp.route("/<int:item_id>/quantity", methods=["POST"])
@login_required
def quantity(item_id):
    item = Item.query.get_or_404(item_id)
    try:
        delta = int(request.form.get("delta", 0))
        item.quantity = max(0, (item.quantity or 0) + delta)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f"Error al actualizar la cantidad: {e}", "error")
    next_url = request.form.get("next") or url_for("items.detail", item_id=item.id)
    return redirect(next_url)


@bp.route("/<int:item_id>/delete", methods=["POST"])
@login_required
def delete(item_id):
    box_id = None
    try:
        item = Item.query.get_or_404(item_id)
        box_id = item.box_id
        for photo in item.photos:
            delete_upload(photo.filename)
        log_activity("item", item.id, item.name, "deleted")
        db.session.delete(item)
        db.session.commit()
        flash("Objeto eliminado.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al eliminar el objeto: {e}", "error")

    if box_id:
        return redirect(url_for("boxes.detail", box_id=box_id))
    return redirect(url_for("main.dashboard"))
