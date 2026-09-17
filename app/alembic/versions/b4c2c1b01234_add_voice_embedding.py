"""add voice embedding

Revision ID: b4c2c1b01234
Revises: acb2b1b03513
Create Date: 2026-09-17 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision = 'b4c2c1b01234'
down_revision = 'acb2b1b03513'
branch_labels = None
depends_on = None


def upgrade():
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector;')
    
    # Add voice_embedding column
    op.add_column('users', sa.Column('voice_embedding', Vector(192), nullable=True))


def downgrade():
    op.drop_column('users', 'voice_embedding')
