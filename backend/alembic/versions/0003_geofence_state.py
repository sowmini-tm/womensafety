"""geofence entry/exit state tracking

Revision ID: 0003_geofence_state
Revises: 0002_notification
Create Date: 2026-08-26 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0003_geofence_state'
down_revision = '0002_notification'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'geofence_states',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('geofence_id', sa.String(length=36), nullable=False),
        sa.Column('last_seen_inside', sa.Boolean(), nullable=True),
        sa.Column('last_distance_meters', sa.Float(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['geofence_id'], ['geofences.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'geofence_id', name='uq_geofence_states_user_geofence'),
    )
    op.create_index('ix_geofence_states_user_id', 'geofence_states', ['user_id'])
    op.create_index('ix_geofence_states_geofence_id', 'geofence_states', ['geofence_id'])


def downgrade() -> None:
    op.drop_index('ix_geofence_states_geofence_id', table_name='geofence_states')
    op.drop_index('ix_geofence_states_user_id', table_name='geofence_states')
    op.drop_table('geofence_states')
