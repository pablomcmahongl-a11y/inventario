"""Fotos múltiples por objeto, historial de actividad y fotos de sala/caja.

- Nuevas tablas: photo, activity.
- Nuevas columnas: room.photo_filename, box.photo_filename, item.updated_at.
- Migra los datos de item.photo_filename (una foto) a la tabla photo (varias
  fotos), y elimina la columna item.photo_filename.

Revision ID: 0002_photos_activity
Revises: 0001_initial_schema
Create Date: 2026-07-30
"""
from datetime import datetime

from alembic import op
import sqlalchemy as sa

revision = "0002_photos_activity"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "photo",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("filename", sa.String(length=300), nullable=False),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("item.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "activity",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("timestamp", sa.DateTime(), nullable=True),
        sa.Column("entity_type", sa.String(length=20), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("entity_name", sa.String(length=200), nullable=False),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("detail", sa.String(length=300), nullable=True),
    )
    op.create_index("ix_activity_timestamp", "activity", ["timestamp"])

    with op.batch_alter_table("room") as batch_op:
        batch_op.add_column(sa.Column("photo_filename", sa.String(length=300), nullable=True))

    with op.batch_alter_table("box") as batch_op:
        batch_op.add_column(sa.Column("photo_filename", sa.String(length=300), nullable=True))

    with op.batch_alter_table("item") as batch_op:
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(), nullable=True))

    # --- migrar la foto única existente de cada objeto a la tabla photo ---
    item_table = sa.table(
        "item",
        sa.column("id", sa.Integer),
        sa.column("photo_filename", sa.String),
        sa.column("created_at", sa.DateTime),
    )
    photo_table = sa.table(
        "photo",
        sa.column("item_id", sa.Integer),
        sa.column("filename", sa.String),
        sa.column("created_at", sa.DateTime),
    )
    bind = op.get_bind()
    rows = bind.execute(
        sa.select(item_table.c.id, item_table.c.photo_filename, item_table.c.created_at)
        .where(item_table.c.photo_filename.isnot(None))
    ).fetchall()
    for item_id, filename, created_at in rows:
        bind.execute(photo_table.insert().values(
            item_id=item_id, filename=filename, created_at=created_at or datetime.utcnow(),
        ))

    with op.batch_alter_table("item") as batch_op:
        batch_op.drop_column("photo_filename")


def downgrade():
    with op.batch_alter_table("item") as batch_op:
        batch_op.add_column(sa.Column("photo_filename", sa.String(length=300), nullable=True))

    item_table = sa.table(
        "item", sa.column("id", sa.Integer), sa.column("photo_filename", sa.String),
    )
    photo_table = sa.table(
        "photo", sa.column("item_id", sa.Integer), sa.column("filename", sa.String),
    )
    bind = op.get_bind()
    rows = bind.execute(sa.select(photo_table.c.item_id, photo_table.c.filename)).fetchall()
    seen = set()
    for item_id, filename in rows:
        if item_id in seen:
            continue
        seen.add(item_id)
        bind.execute(
            item_table.update().where(item_table.c.id == item_id).values(photo_filename=filename)
        )

    with op.batch_alter_table("item") as batch_op:
        batch_op.drop_column("updated_at")
    with op.batch_alter_table("box") as batch_op:
        batch_op.drop_column("photo_filename")
    with op.batch_alter_table("room") as batch_op:
        batch_op.drop_column("photo_filename")

    op.drop_index("ix_activity_timestamp", table_name="activity")
    op.drop_table("activity")
    op.drop_table("photo")
