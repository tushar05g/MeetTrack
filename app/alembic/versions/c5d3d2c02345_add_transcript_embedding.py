"""add transcript embedding

Revision ID: c5d3d2c02345
Revises: b4c2c1b01234
Create Date: 2026-09-17 10:05:00.000000

"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision = 'c5d3d2c02345'
down_revision = 'b4c2c1b01234'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('transcripts', sa.Column('embedding', Vector(384), nullable=True))


def downgrade():
    op.drop_column('transcripts', 'embedding')
