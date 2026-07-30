from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required

from ..extensions import db
from ..models import Room
from ..utils import save_upload, delete_upload, log_activity

bp = Blueprint("rooms", __name__, url_prefix="/rooms")


@bp.route("/")
@login_required
def list_rooms():
    rooms = Room.query.order_by(Room.name).all()
    return render_template("room_list.html", rooms=rooms)


@bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("El nombre de la habitación es obligatorio.", "error")
            return render_template("room_form.html", room=None)
        try:
            room = Room(
                name=name,
                description=request.form.get("description", "").strip() or None,
                photo_filename=save_upload(request.files.get("photo")),
            )
            db.session.add(room)
            db.session.flush()
            log_activity("room", room.id, room.name, "created")
            db.session.commit()
            flash("Habitación creada.", "success")
            return redirect(url_for("rooms.detail", room_id=room.id))
        except Exception as e:
            db.session.rollback()
            flash(f"Error al crear la habitación: {e}", "error")
            return render_template("room_form.html", room=None)
    return render_template("room_form.html", room=None)


@bp.route("/<int:room_id>")
@login_required
def detail(room_id):
    room = Room.query.get_or_404(room_id)
    return render_template("room_detail.html", room=room, boxes=room.boxes)


@bp.route("/<int:room_id>/edit", methods=["GET", "POST"])
@login_required
def edit(room_id):
    room = Room.query.get_or_404(room_id)
    if request.method == "POST":
        try:
            room.name = request.form.get("name", "").strip() or room.name
            room.description = request.form.get("description", "").strip() or None
            if request.form.get("remove_photo") == "1":
                delete_upload(room.photo_filename)
                room.photo_filename = None
            new_photo = save_upload(request.files.get("photo"))
            if new_photo:
                delete_upload(room.photo_filename)
                room.photo_filename = new_photo
            log_activity("room", room.id, room.name, "updated")
            db.session.commit()
            flash("Habitación actualizada.", "success")
            return redirect(url_for("rooms.detail", room_id=room.id))
        except Exception as e:
            db.session.rollback()
            flash(f"Error al actualizar la habitación: {e}", "error")
    return render_template("room_form.html", room=room)


@bp.route("/<int:room_id>/delete", methods=["POST"])
@login_required
def delete(room_id):
    try:
        room = Room.query.get_or_404(room_id)
        for box in room.boxes:
            box.room_id = None
        log_activity("room", room.id, room.name, "deleted")
        db.session.delete(room)
        db.session.commit()
        flash("Habitación eliminada.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al eliminar la habitación: {e}", "error")
    return redirect(url_for("rooms.list_rooms"))
