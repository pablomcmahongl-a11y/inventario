import csv
import io
import os

from flask import Blueprint, render_template, request, Response, current_app, send_from_directory
from flask_login import login_required
from sqlalchemy import or_, func

from ..extensions import db
from ..models import Room, Box, Item, Activity
from ..utils import all_categories

bp = Blueprint("main", __name__)


@bp.route("/health")
def health():
    return {"status": "ok"}


@bp.route("/")
@login_required
def dashboard():
    room_count = Room.query.count()
    box_count = Box.query.count()
    item_count = Item.query.count()
    total_units = db.session.query(func.coalesce(func.sum(Item.quantity), 0)).scalar()

    category_counts = (
        db.session.query(Item.category, func.count(Item.id))
        .filter(Item.category.isnot(None), Item.category != "")
        .group_by(Item.category)
        .order_by(func.count(Item.id).desc())
        .limit(8)
        .all()
    )
    max_cat = max((c for _, c in category_counts), default=0)

    recent_items = Item.query.order_by(Item.created_at.desc()).limit(6).all()
    recent_activity = Activity.query.order_by(Activity.timestamp.desc()).limit(12).all()
    empty_boxes = Box.query.filter(~Box.items.any()).order_by(Box.name).limit(6).all()

    return render_template(
        "dashboard.html",
        room_count=room_count, box_count=box_count, item_count=item_count,
        total_units=total_units, category_counts=category_counts, max_cat=max_cat,
        recent_items=recent_items, recent_activity=recent_activity,
        empty_boxes=empty_boxes,
    )


@bp.route("/search")
@login_required
def search():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "")
    box_id = request.args.get("box_id", "")
    room_id = request.args.get("room_id", "")

    query = Item.query
    if q:
        like = f"%{q}%"
        query = query.filter(or_(
            Item.name.ilike(like),
            Item.notes.ilike(like),
            Item.category.ilike(like),
        ))
    if category:
        query = query.filter(Item.category == category)
    if box_id.isdigit():
        query = query.filter(Item.box_id == int(box_id))
    if room_id.isdigit():
        query = query.join(Box, Item.box_id == Box.id).filter(Box.room_id == int(room_id))

    items = query.order_by(Item.name).all()

    return render_template(
        "search.html",
        items=items, q=q,
        categories=all_categories(),
        boxes=Box.query.order_by(Box.name).all(),
        rooms=Room.query.order_by(Room.name).all(),
        selected_category=category, selected_box=box_id, selected_room=room_id,
        has_filters=bool(q or category or box_id or room_id),
    )


@bp.route("/export.csv")
@login_required
def export_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Objeto", "Cantidad", "Categoría", "Notas", "Caja", "Habitación", "Creado"])
    for item in Item.query.order_by(Item.name).all():
        writer.writerow([
            item.name,
            item.quantity,
            item.category or "",
            item.notes or "",
            item.box.name if item.box else "",
            item.box.room.name if item.box and item.box.room else "",
            item.created_at.strftime("%Y-%m-%d") if item.created_at else "",
        ])
    csv_bytes = output.getvalue().encode("utf-8-sig")
    return Response(
        csv_bytes,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=inventario.csv"},
    )


@bp.route("/uploads/<path:filename>")
@login_required
def uploaded_file(filename):
    return send_from_directory(current_app.config["UPLOAD_DIR"], filename)
