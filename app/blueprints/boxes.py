import io

import qrcode
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, current_app
from flask_login import login_required

from ..extensions import db
from ..models import Room, Box
from ..utils import save_upload, delete_upload, log_activity

bp = Blueprint("boxes", __name__, url_prefix="/boxes")


@bp.route("/")
@login_required
def list_boxes():
    boxes = Box.query.order_by(Box.name).all()
    return render_template("box_list.html", boxes=boxes)


@bp.route("/qr-sheet")
@login_required
def qr_sheet():
    boxes = Box.query.order_by(Box.name).all()
    return render_template("qr_sheet.html", boxes=boxes)


@bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    rooms = Room.query.order_by(Room.name).all()
    preselect_room = request.args.get("room_id")

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("El nombre de la caja es obligatorio.", "error")
            return render_template("box_form.html", box=None, rooms=rooms, preselect_room=preselect_room)
        try:
            box = Box(
                name=name,
                location=request.form.get("location", "").strip() or None,
                description=request.form.get("description", "").strip() or None,
                room_id=int(request.form["room_id"]) if request.form.get("room_id") else None,
                photo_filename=save_upload(request.files.get("photo")),
            )
            db.session.add(box)
            db.session.flush()
            log_activity("box", box.id, box.name, "created")
            db.session.commit()
            flash("Caja creada. Ya puedes imprimir su código QR.", "success")
            return redirect(url_for("boxes.detail", box_id=box.id))
        except Exception as e:
            db.session.rollback()
            flash(f"Error al crear la caja: {e}", "error")
            return render_template("box_form.html", box=None, rooms=rooms, preselect_room=preselect_room)

    return render_template("box_form.html", box=None, rooms=rooms, preselect_room=preselect_room)


@bp.route("/<int:box_id>")
@login_required
def detail(box_id):
    box = Box.query.get_or_404(box_id)
    qr_url = url_for("boxes.qr", box_id=box.id)
    public_url = f"{current_app.config['BASE_URL']}{url_for('boxes.detail', box_id=box.id)}"
    return render_template("box_detail.html", box=box, qr_url=qr_url, public_url=public_url)


@bp.route("/<int:box_id>/edit", methods=["GET", "POST"])
@login_required
def edit(box_id):
    box = Box.query.get_or_404(box_id)
    rooms = Room.query.order_by(Room.name).all()
    if request.method == "POST":
        try:
            box.name = request.form.get("name", "").strip() or box.name
            box.location = request.form.get("location", "").strip() or None
            box.description = request.form.get("description", "").strip() or None
            box.room_id = int(request.form["room_id"]) if request.form.get("room_id") else None
            if request.form.get("remove_photo") == "1":
                delete_upload(box.photo_filename)
                box.photo_filename = None
            new_photo = save_upload(request.files.get("photo"))
            if new_photo:
                delete_upload(box.photo_filename)
                box.photo_filename = new_photo
            log_activity("box", box.id, box.name, "updated")
            db.session.commit()
            flash("Caja actualizada.", "success")
            return redirect(url_for("boxes.detail", box_id=box.id))
        except Exception as e:
            db.session.rollback()
            flash(f"Error al actualizar la caja: {e}", "error")
    return render_template("box_form.html", box=box, rooms=rooms)


@bp.route("/<int:box_id>/delete", methods=["POST"])
@login_required
def delete(box_id):
    room_id = None
    try:
        box = Box.query.get_or_404(box_id)
        room_id = box.room_id
        for item in box.items:
            item.box_id = None
        log_activity("box", box.id, box.name, "deleted")
        db.session.delete(box)
        db.session.commit()
        flash("Caja eliminada. Sus objetos ahora no tienen caja asignada.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al eliminar la caja: {e}", "error")

    if room_id:
        return redirect(url_for("rooms.detail", room_id=room_id))
    return redirect(url_for("boxes.list_boxes"))


@bp.route("/<int:box_id>/qr.png")
@login_required
def qr(box_id):
    box = Box.query.get_or_404(box_id)
    target_url = f"{current_app.config['BASE_URL']}{url_for('boxes.detail', box_id=box.id)}"

    img = qrcode.make(target_url, box_size=10, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")
