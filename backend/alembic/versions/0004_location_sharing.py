"""location_share_sessions: secure live-location sharing (Phase 10)

Revision ID: 0004_location_sharing
Revises: 0003_geofence_state
Create Date: 2026-08-27 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0004_location_sharing'
down_revision = '0003_geofence_state'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'location_share_sessions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('share_token_hash', sa.String(length=64), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('stopped_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'is_active', name='uq_location_share_sessions_active_owner'),
    )
    op.create_index('ix_location_share_sessions_user_id', 'location_share_sessions', ['user_id'])
    op.create_index('ix_location_share_sessions_share_token_hash', 'location_share_sessions', ['share_token_hash'])
    op.create_index('ix_location_share_sessions_is_active', 'location_share_sessions', ['is_active'])


def downgrade() -> None:
    op.drop_index('ix_location_share_sessions_is_active', table_name='location_share_sessions')
    op.drop_index('ix_location_share_sessions_share_token_hash', table_name='location_share_sessions')
    op.drop_index('ix_location_share_sessions_user_id', table_name='location_share_sessions')
    op.drop_table('location_share_sessions')