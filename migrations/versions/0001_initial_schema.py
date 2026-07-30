"""Esquema inicial (el que ya está desplegado en producción sin migraciones).

Esta migración no crea nada nuevo cuando se aplica a la base de datos real:
sirve para que Alembic tenga un punto de partida documentado. En un despliegue
existente se marca como ya aplicada con `flask db stamp 0001_initial_schema`
en vez de ejecutarla.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-07-30
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "room",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "box",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("location", sa.String(length=120), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("room_id", sa.Integer(), sa.ForeignKey("room.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "item",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("category", sa.String(length=120), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("photo_filename", sa.String(length=300), nullable=True),
        sa.Column("box_id", sa.Integer(), sa.ForeignKey("box.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_table("item")
    op.drop_table("box")
    op.drop_table("room")
