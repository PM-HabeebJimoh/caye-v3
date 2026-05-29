"""Initial CAYE v3.0 database schema

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # ─────────────────────────────────────────
    # SIGNAL STATE TABLE
    # Stores all 9 signal boolean states
    # ─────────────────────────────────────────
    op.create_table(
        'signal_state',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),

        # Signal 3: DefiLlama
        sa.Column('stablecoin_exodus', sa.Boolean(),
                  nullable=False, server_default='false'),
        sa.Column('stablecoin_delta_48h', sa.Float(), nullable=True),
        sa.Column('total_stablecoin_mcap', sa.Float(), nullable=True),

        # Signal 5: FRED
        sa.Column('macro_draining', sa.Boolean(),
                  nullable=False, server_default='false'),
        sa.Column('weekly_delta_pct', sa.Float(), nullable=True),
        sa.Column('current_net_liquidity', sa.Float(), nullable=True),

        # Signal 4: Etherscan
        sa.Column('insider_activity', sa.Boolean(),
                  nullable=False, server_default='false'),
        sa.Column('gas_acceleration_rate', sa.Float(), nullable=True),
        sa.Column('current_gas_gwei', sa.Integer(), nullable=True),

        # Signal 6: GitHub
        sa.Column('any_abandonment', sa.Boolean(),
                  nullable=False, server_default='false'),
        sa.Column('abandonment_details', postgresql.JSONB(), nullable=True),

        # Signal 8: Coinglass
        sa.Column('any_over_leveraged', sa.Boolean(),
                  nullable=False, server_default='false'),
        sa.Column('funding_rate_details', postgresql.JSONB(), nullable=True),

        # Signal 7: CourtListener
        sa.Column('regulatory_pressure', sa.Boolean(),
                  nullable=False, server_default='false'),
        sa.Column('total_dockets_7d', sa.Integer(), nullable=True),

        # Signal 9: TokenUnlocks
        sa.Column('major_unlock_imminent', sa.Boolean(),
                  nullable=False, server_default='false'),
        sa.Column('upcoming_unlocks', postgresql.JSONB(), nullable=True),

        # Signal 2: CoinGecko
        sa.Column('spot_prices', postgresql.JSONB(), nullable=True),

        # Meta
        sa.Column('signal_data_stale', sa.Boolean(),
                  nullable=False, server_default='false'),
        sa.Column('source_flags', postgresql.JSONB(), nullable=True),

        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_signal_state_created_at',
                    'signal_state', ['created_at'])

    # ─────────────────────────────────────────
    # OPPORTUNITIES TABLE
    # Active + historical trade opportunities
    # ─────────────────────────────────────────
    op.create_table(
        'opportunities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),

        # Market identification
        sa.Column('market_id', sa.String(255), nullable=False),
        sa.Column('condition_id', sa.String(255), nullable=True),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('polymarket_url', sa.String(500), nullable=True),
        sa.Column('market_category', sa.String(50),
                  nullable=False, server_default='CRYPTO'),
        sa.Column('subcategory', sa.String(100), nullable=True),

        # Engine
        sa.Column('engine_id', sa.Integer(), nullable=False),
        sa.Column('engine_name', sa.String(100), nullable=False),

        # Trade parameters
        sa.Column('entry_price', sa.Float(), nullable=False),
        sa.Column('target_side', sa.String(10), nullable=False),
        sa.Column('yes_price_at_entry', sa.Float(), nullable=True),
        sa.Column('no_price_at_entry', sa.Float(), nullable=True),

        # CIS
        sa.Column('cis_score', sa.Float(), nullable=False),
        sa.Column('signal_breakdown', postgresql.JSONB(), nullable=True),
        sa.Column('gate_results', postgresql.JSONB(), nullable=True),

        # Position sizing
        sa.Column('recommended_position', sa.Float(), nullable=False),
        sa.Column('potential_profit', sa.Float(), nullable=False),
        sa.Column('roi_pct', sa.Float(), nullable=False),
        sa.Column('kelly_fraction', sa.Float(), nullable=False),
        sa.Column('expected_value', sa.Float(), nullable=True),

        # Market metadata
        sa.Column('liquidity', sa.Float(), nullable=True),
        sa.Column('volume', sa.Float(), nullable=True),
        sa.Column('expiry_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('days_to_expiry', sa.Integer(), nullable=True),

        # Status lifecycle
        sa.Column('status', sa.String(50),
                  nullable=False, server_default='ACTIVE'),

        # Resolution
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('actual_roi', sa.Float(), nullable=True),
        sa.Column('actual_profit', sa.Float(), nullable=True),
        sa.Column('resolution_price', sa.Float(), nullable=True),

        # Constraints
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("market_category = 'CRYPTO'",
                           name='crypto_only_constraint'),
        sa.CheckConstraint(
            "status IN ('ACTIVE','VETOED','EXPIRED','WON','LOST')",
            name='valid_status_constraint'
        ),
        sa.CheckConstraint(
            "target_side IN ('YES', 'NO')",
            name='valid_side_constraint'
        ),
        sa.CheckConstraint(
            "engine_id IN (1, 2, 3, 4)",
            name='valid_engine_constraint'
        ),
        sa.CheckConstraint(
            "entry_price > 0 AND entry_price <= 0.52",
            name='price_ceiling_constraint'
        ),
        sa.CheckConstraint(
            "cis_score >= 0.89 AND cis_score <= 1.0",
            name='cis_threshold_constraint'
        ),
    )
    op.create_index('ix_opportunities_status',
                    'opportunities', ['status'])
    op.create_index('ix_opportunities_market_id',
                    'opportunities', ['market_id'])
    op.create_index('ix_opportunities_created_at',
                    'opportunities', ['created_at'])
    op.create_index('ix_opportunities_engine_id',
                    'opportunities', ['engine_id'])

    # ─────────────────────────────────────────
    # VETO LOG TABLE
    # Records all gate rejections with reasons
    # ─────────────────────────────────────────
    op.create_table(
        'veto_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),

        sa.Column('market_id', sa.String(255), nullable=True),
        sa.Column('question', sa.Text(), nullable=True),
        sa.Column('gate_number', sa.Integer(), nullable=False),
        sa.Column('gate_name', sa.String(100), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('actual_value', sa.Float(), nullable=True),
        sa.Column('required_value', sa.Float(), nullable=True),
        sa.Column('entry_price', sa.Float(), nullable=True),
        sa.Column('engine_id', sa.Integer(), nullable=True),
        sa.Column('cis_score', sa.Float(), nullable=True),
        sa.Column('signal_breakdown', postgresql.JSONB(), nullable=True),

        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_veto_log_created_at',
                    'veto_log', ['created_at'])
    op.create_index('ix_veto_log_gate_number',
                    'veto_log', ['gate_number'])

    # ─────────────────────────────────────────
    # SCAN LOG TABLE
    # Records every scan run statistics
    # ─────────────────────────────────────────
    op.create_table(
        'scan_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('scanned_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),

        sa.Column('markets_fetched', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('markets_crypto', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('markets_vetoed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('opportunities_found', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('gate1_vetoed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('gate2_vetoed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('gate3_vetoed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('gate4_vetoed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('scan_duration_ms', sa.Integer(), nullable=True),
        sa.Column('signal_data_stale', sa.Boolean(),
                  nullable=False, server_default='false'),
        sa.Column('error_message', sa.Text(), nullable=True),

        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_scan_log_scanned_at',
                    'scan_log', ['scanned_at'])

    # ─────────────────────────────────────────
    # STABLECOIN SNAPSHOTS TABLE
    # Historical stablecoin market cap data
    # ─────────────────────────────────────────
    op.create_table(
        'stablecoin_snapshots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('usdt_mcap', sa.Float(), nullable=True),
        sa.Column('usdc_mcap', sa.Float(), nullable=True),
        sa.Column('total_mcap', sa.Float(), nullable=False),

        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_stablecoin_snapshots_recorded_at',
                    'stablecoin_snapshots', ['recorded_at'])

    # ─────────────────────────────────────────
    # GAS SNAPSHOTS TABLE
    # Historical Ethereum gas price data
    # ─────────────────────────────────────────
    op.create_table(
        'gas_snapshots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('gas_price_gwei', sa.Integer(), nullable=False),
        sa.Column('propose_gas_price', sa.Integer(), nullable=True),
        sa.Column('fast_gas_price', sa.Integer(), nullable=True),

        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_gas_snapshots_recorded_at',
                    'gas_snapshots', ['recorded_at'])

    # ─────────────────────────────────────────
    # GITHUB SNAPSHOTS TABLE
    # Developer commit velocity history
    # ─────────────────────────────────────────
    op.create_table(
        'github_snapshots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('repo', sa.String(255), nullable=False),
        sa.Column('recent_avg_commits', sa.Float(), nullable=True),
        sa.Column('prior_avg_commits', sa.Float(), nullable=True),
        sa.Column('velocity_ratio', sa.Float(), nullable=True),
        sa.Column('abandonment_detected', sa.Boolean(),
                  nullable=False, server_default='false'),

        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_github_snapshots_recorded_at',
                    'github_snapshots', ['recorded_at'])
    op.create_index('ix_github_snapshots_repo',
                    'github_snapshots', ['repo'])

    # ─────────────────────────────────────────
    # HISTORICAL OPPORTUNITIES TABLE
    # Archive of all resolved/expired trades
    # ─────────────────────────────────────────
    op.create_table(
        'historical_opportunities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('opportunity_id', sa.Integer(), nullable=False),
        sa.Column('archived_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),

        sa.Column('market_id', sa.String(255), nullable=True),
        sa.Column('question', sa.Text(), nullable=True),
        sa.Column('polymarket_url', sa.String(500), nullable=True),
        sa.Column('engine_id', sa.Integer(), nullable=True),
        sa.Column('engine_name', sa.String(100), nullable=True),
        sa.Column('entry_price', sa.Float(), nullable=True),
        sa.Column('target_side', sa.String(10), nullable=True),
        sa.Column('cis_score', sa.Float(), nullable=True),
        sa.Column('recommended_position', sa.Float(), nullable=True),
        sa.Column('roi_pct', sa.Float(), nullable=True),
        sa.Column('status', sa.String(50), nullable=True),
        sa.Column('actual_roi', sa.Float(), nullable=True),
        sa.Column('actual_profit', sa.Float(), nullable=True),
        sa.Column('expiry_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('signal_breakdown', postgresql.JSONB(), nullable=True),

        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_historical_archived_at',
                    'historical_opportunities', ['archived_at'])
    op.create_index('ix_historical_status',
                    'historical_opportunities', ['status'])


def downgrade() -> None:
    op.drop_table('historical_opportunities')
    op.drop_table('github_snapshots')
    op.drop_table('gas_snapshots')
    op.drop_table('stablecoin_snapshots')
    op.drop_table('scan_log')
    op.drop_table('veto_log')
    op.drop_table('opportunities')
    op.drop_table('signal_state')