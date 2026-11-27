"""add group_invites table

Revision ID: 0002_add_group_invites
Revises: 1eafb6ed5e01
Create Date: 2026-11-27 11:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002_add_group_invites'
down_revision: Union[str, Sequence[str], None] = '1eafb6ed5e01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the group_invites table for consent-based group joining."""
    op.create_table(
        'group_invites',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('invited_user_id', sa.Integer(), nullable=False),
        sa.Column('invited_by', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('pending', 'accepted', 'declined')", name='ck_group_invites_status'),
        sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['invited_by'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['invited_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_group_invites_invited_user_status',
        'group_invites',
        ['invited_user_id', 'status'],
        unique=False,
    )
    op.create_index(
        'uq_group_invites_pending',
        'group_invites',
        ['group_id', 'invited_user_id'],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )


def downgrade() -> None:
    """Drop the group_invites table."""
    op.drop_index('uq_group_invites_pending', table_name='group_invites', postgresql_where=sa.text("status = 'pending'"))
    op.drop_index('ix_group_invites_invited_user_status', table_name='group_invites')
    op.drop_table('group_invites')
