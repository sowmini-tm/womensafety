"""notification delivery tracking

Revision ID: 0002_notification
Revises: 0001_initial
Create Date: 2026-08-26 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0002_notification'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'notifications',
        sa.Column('emergency_contact_id', sa.String(length=36), nullable=True),
    )
    op.add_column(
        'notifications',
        sa.Column('channel', sa.Enum('SMS', 'EMAIL', name='notificationchannel'), nullable=True),
    )
    op.add_column(
        'notifications',
        sa.Column('failure_reason', sa.Text(), nullable=True),
    )
    op.create_index(
        'ix_notifications_emergency_contact_id',
        'notifications',
        ['emergency_contact_id'],
    )
    op.create_index('ix_notifications_channel', 'notifications', ['channel'])
    op.create_foreign_key(
        'fk_notifications_emergency_contact_id',
        'notifications',
        'emergency_contacts',
        ['emergency_contact_id'],
        ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint(
        'fk_notifications_emergency_contact_id',
        'notifications',
        type_='foreignkey',
    )
    op.drop_index('ix_notifications_channel', table_name='notifications')
    op.drop_index(
        'ix_notifications_emergency_contact_id',
        table_name='notifications',
    )
    op.drop_column('notifications', 'failure_reason')
    op.drop_column('notifications', 'channel')
    op.drop_column('notifications', 'emergency_contact_id')