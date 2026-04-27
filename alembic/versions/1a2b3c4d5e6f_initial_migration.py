"""Initial migration

Revision ID: 1a2b3c4d5e6f
Revises: 
Create Date: 2026-04-27 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '1a2b3c4d5e6f'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table('users',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('user_id')
    )
    op.create_table('sessions',
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('trade_count', sa.Integer(), nullable=True),
        sa.Column('win_rate', sa.Float(), nullable=True),
        sa.Column('total_pnl', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('session_id')
    )
    op.create_table('trades',
        sa.Column('trade_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('asset', sa.String(), nullable=False),
        sa.Column('asset_class', sa.String(), nullable=False),
        sa.Column('direction', sa.String(), nullable=False),
        sa.Column('entry_price', sa.Float(), nullable=False),
        sa.Column('exit_price', sa.Float(), nullable=True),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('entry_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('exit_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('outcome', sa.String(), nullable=True),
        sa.Column('pnl', sa.Float(), nullable=True),
        sa.Column('plan_adherence', sa.Integer(), nullable=True),
        sa.Column('emotional_state', sa.String(), nullable=True),
        sa.Column('entry_rationale', sa.Text(), nullable=True),
        sa.Column('revenge_flag', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.session_id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('trade_id')
    )
    op.create_table('memory_sessions',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('metrics_json', sa.JSON(), nullable=False),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.session_id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('user_id', 'session_id')
    )
    op.create_table('profiles',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('profile_json', sa.JSON(), nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('user_id')
    )

def downgrade() -> None:
    op.drop_table('profiles')
    op.drop_table('memory_sessions')
    op.drop_table('trades')
    op.drop_table('sessions')
    op.drop_table('users')
