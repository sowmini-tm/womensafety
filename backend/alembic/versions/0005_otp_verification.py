"""otp_verifications: hash storage + attempts/resend throttling (Phase 12)

Revision ID: 0005_otp_verification
Revises: 0004_location_sharing
Create Date: 2026-08-27 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0005_otp_verification'
down_revision = '0004_location_sharing'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Widen otp_code so it can hold a SHA-256 hash (previously plaintext String(16)).
    op.alter_column('otp_verifications', 'otp_code', existing_type=sa.String(length=16), type_=sa.String(length=255), existing_nullable=False)
    # New attempt / resend-throttle bookkeeping columns.
    op.add_column('otp_verifications', sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('otp_verifications', sa.Column('last_sent_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('otp_verifications', 'last_sent_at')
    op.drop_column('otp_verifications', 'attempts')
    op.alter_column('otp_verifications', 'otp_code', existing_type=sa.String(length=255), type_=sa.String(length=16), existing_nullable=False)
