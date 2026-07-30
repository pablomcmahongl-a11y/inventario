from datetime import datetime

from .extensions import db


class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    photo_filename = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Sin cascade de borrado: al eliminar una habitación, sus cajas se
    # desasocian (room_id = NULL) en vez de borrarse. Ver blueprints/rooms.py.
    boxes = db.relationship("Box", backref="room", lazy=True, order_by="Box.name")


class Box(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    location = db.Column(db.String(120))
    description = db.Column(db.Text)
    photo_filename = db.Column(db.String(300))
    room_id = db.Column(db.Integer, db.ForeignKey("room.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Igual que con Room.boxes: sin cascade de borrado, los objetos se
    # desasocian (box_id = NULL) al borrar la caja. Ver blueprints/boxes.py.
    items = db.relationship("Item", backref="box", lazy=True, order_by="Item.name")


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    category = db.Column(db.String(120))
    notes = db.Column(db.Text)
    box_id = db.Column(db.Integer, db.ForeignKey("box.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    photos = db.relationship(
        "Photo", backref="item", lazy=True,
        order_by="Photo.created_at", cascade="all, delete-orphan",
    )

    @property
    def cover_photo(self):
        return self.photos[0] if self.photos else None


class Photo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(300), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey("item.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Activity(db.Model):
    """Registro de alta/edición/traslado/baja de habitaciones, cajas y objetos.

    entity_name se guarda en el momento del evento (no es una FK "viva") para
    que el historial siga teniendo sentido aunque la entidad se borre después.
    """
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    entity_type = db.Column(db.String(20), nullable=False)  # room | box | item
    entity_id = db.Column(db.Integer)
    entity_name = db.Column(db.String(200), nullable=False)
    action = db.Column(db.String(20), nullable=False)  # created | updated | moved | deleted
    detail = db.Column(db.String(300))
