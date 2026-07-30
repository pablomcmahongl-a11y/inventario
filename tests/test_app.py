from app.models import Room, Box, Item
from app.extensions import db


def test_dashboard_requires_login(client):
    resp = client.get("/", follow_redirects=True)
    assert b"Iniciar sesi\xc3\xb3n" in resp.data or b"Usuario" in resp.data
    assert resp.request.path == "/login"


def test_login_wrong_password(client):
    resp = client.post("/login", data={"username": "admin", "password": "nope"}, follow_redirects=True)
    assert "incorrectos".encode() in resp.data


def test_login_success(client):
    resp = client.post("/login", data={"username": "admin", "password": "test"}, follow_redirects=True)
    assert resp.request.path == "/"


def test_full_room_box_item_flow(auth_client, app):
    r = auth_client.post("/rooms/new", data={"name": "Salón"}, follow_redirects=True)
    with app.app_context():
        room = Room.query.filter_by(name="Salón").one()

    r = auth_client.post("/boxes/new", data={"name": "Caja A", "room_id": room.id}, follow_redirects=True)
    with app.app_context():
        box = Box.query.filter_by(name="Caja A").one()
        assert box.room_id == room.id

    r = auth_client.post("/items/new", data={"name": "Taladro", "quantity": 2, "box_id": box.id},
                          follow_redirects=True)
    assert r.status_code == 200
    with app.app_context():
        item = Item.query.filter_by(name="Taladro").one()
        assert item.quantity == 2
        assert item.box_id == box.id


def test_deleting_box_orphans_items_instead_of_deleting_them(auth_client, app):
    with app.app_context():
        box = Box(name="Caja B")
        db.session.add(box)
        db.session.commit()
        item = Item(name="Martillo", quantity=1, box_id=box.id)
        db.session.add(item)
        db.session.commit()
        item_id = item.id
        box_id = box.id

    auth_client.post(f"/boxes/{box_id}/delete", follow_redirects=True)

    with app.app_context():
        assert Box.query.get(box_id) is None
        surviving_item = Item.query.get(item_id)
        assert surviving_item is not None
        assert surviving_item.box_id is None


def test_deleting_room_orphans_boxes_instead_of_deleting_them(auth_client, app):
    with app.app_context():
        room = Room(name="Cocina")
        db.session.add(room)
        db.session.commit()
        box = Box(name="Caja C", room_id=room.id)
        db.session.add(box)
        db.session.commit()
        room_id = room.id
        box_id = box.id

    auth_client.post(f"/rooms/{room_id}/delete", follow_redirects=True)

    with app.app_context():
        assert Room.query.get(room_id) is None
        surviving_box = Box.query.get(box_id)
        assert surviving_box is not None
        assert surviving_box.room_id is None


def test_quantity_quick_buttons(auth_client, app):
    with app.app_context():
        item = Item(name="Cinta aislante", quantity=3)
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    auth_client.post(f"/items/{item_id}/quantity", data={"delta": "1"})
    auth_client.post(f"/items/{item_id}/quantity", data={"delta": "1"})
    auth_client.post(f"/items/{item_id}/quantity", data={"delta": "-1"})

    with app.app_context():
        assert Item.query.get(item_id).quantity == 4


def test_quantity_never_goes_negative(auth_client, app):
    with app.app_context():
        item = Item(name="Bombilla", quantity=0)
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    auth_client.post(f"/items/{item_id}/quantity", data={"delta": "-5"})

    with app.app_context():
        assert Item.query.get(item_id).quantity == 0


def test_search_finds_item_by_name(auth_client, app):
    with app.app_context():
        db.session.add(Item(name="Destornillador estrella", quantity=1))
        db.session.add(Item(name="Llave inglesa", quantity=1))
        db.session.commit()

    resp = auth_client.get("/search?q=destornillador")
    assert "Destornillador estrella".encode() in resp.data
    assert "Llave inglesa".encode() not in resp.data


def test_export_csv_contains_items(auth_client, app):
    with app.app_context():
        db.session.add(Item(name="Sierra", quantity=1, category="Herramientas"))
        db.session.commit()

    resp = auth_client.get("/export.csv")
    assert resp.status_code == 200
    assert resp.mimetype == "text/csv"
    assert "Sierra".encode() in resp.data


def test_item_detail_records_history(auth_client, app):
    with app.app_context():
        item = Item(name="Escalera", quantity=1)
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    auth_client.post(f"/items/{item_id}/edit", data={"name": "Escalera plegable", "quantity": 1})
    resp = auth_client.get(f"/items/{item_id}")
    assert "actualizado".encode() in resp.data


def test_health_endpoint_does_not_require_login(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_uploads_require_login(client):
    resp = client.get("/uploads/nonexistent.png", follow_redirects=True)
    assert resp.request.path == "/login"
