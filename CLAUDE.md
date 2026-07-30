# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A self-hosted Flask web app for keeping a household inventory. Rooms contain
boxes, boxes contain items. Each box gets a QR code sticker; scanning it opens
that box's contents directly. Runs on a home Ubuntu server via Docker, with
SQLite + uploaded photos persisted on disk under `data/` (bind-mounted into
the container). UI text and flash messages are in Spanish.

## Commands

Run locally without Docker (dev server, auto-reload via `debug=True`):
```bash
pip install -r requirements.txt
python app.py            # serves on 0.0.0.0:8000
```

Run via Docker (matches production deployment):
```bash
docker compose up -d --build
docker compose down
```

There is no test suite and no linter/formatter configured in this repo.

## Architecture

**Single-file Flask app.** `app.py` contains the models, all routes, and
helper functions — there is no blueprint split or service layer. Routes are
grouped by comment banners (`RUTAS: HABITACIONES` / `CAJAS` / `OBJETOS` /
`ARCHIVOS`).

**Data model is a strict 3-level hierarchy:** `Room` → `Box` → `Item`
(`app.py:39-69`). Both parent relationships use
`cascade="all, delete-orphan"`. Note that `box_delete` manually nulls out
`item.box_id` for every item in the box *before* deleting the box, rather
than relying on cascade — if you touch that route, be aware the cascade and
the manual null-out are both in play at once.

**No migrations.** `db.create_all()` runs once at import time
(`app.py:72-73`) and only creates tables that don't exist yet — it never
alters existing ones. Changing a model's columns requires either a manual
`ALTER TABLE` or deleting `instance/inventario.db` (or the mounted
`data/instance/` volume in Docker) and letting it regenerate, which loses
data. There's no Alembic/Flask-Migrate here.

**QR codes are generated on the fly, not stored.** `GET
/boxes/<id>/qr.png` builds a PNG in memory each request, encoding a URL built
from the `BASE_URL` env var (`app.py:264-273`). `BASE_URL` must be an address
actually reachable from whatever device scans the code — it's baked into
every QR image, so changing it means every previously printed sticker still
points at the old address.

**Uploaded photos** are saved under `uploads/` with randomized UUID
filenames (`save_photo`, `app.py:83-91`) and referenced by
`Item.photo_filename`; type is restricted to `ALLOWED_EXTENSIONS`, size
capped by `MAX_CONTENT_LENGTH` (16MB). Deletion (`delete_photo`) is called
both when a photo is explicitly removed/replaced on an item and when an item
is deleted.

**Two templates are currently unused:** `templates/index.html` and
`templates/box_list.html` are left over from before the `Room` level was
introduced (see git history: "Agregar nivel de habitaciones") and are not
referenced by any route in `app.py` — the item search/filter UI they contain
(by name, category, box) is not currently reachable. `index` now renders
`room_list.html`. Don't assume these templates are live without checking
`render_template` call sites.

## Deployment config

`docker-compose.yml` hardcodes real environment-specific values
(`BASE_URL` pointing at a Tailscale IP, `SECRET_KEY`) rather than
placeholders — this is the actual home-server config, not a template to copy
verbatim into other deployments.

## Repo quirks

Working copies of files sit alongside macOS AppleDouble sidecar files
(`._app.py`, `._README.md`, etc.), and both are tracked in git. Ignore the
`._*` ones — they're not real source files.
