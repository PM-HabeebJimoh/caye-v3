/**
 * CAYE v3.0 — Signal Panel
 * Displays all 9 live data signals.
 * GREEN = active | GREY = inactive
 * Shows current values and last updated time.
 */

import React from 'react';
import {
  formatTimeAgo,
  formatCurrency,
  formatPercent,
  formatGwei,
  getSignalInfo
} from '../utils/formatters';

// ─────────────────────────────────────────
// INDIVIDUAL SIGNAL CARD
// ─────────────────────────────────────────

const SignalCard = ({
  signalKey,
  isActive,
  value,
  extra
}) => {
  const info = getSignalInfo(signalKey);

  const dimensionColors = {
    'INVISIBLE': 'text-blue-400',
    'HIDDEN':    'text-purple-400',
    'SCATTERED': 'text-yellow-400',
    'VISIBLE':   'text-slate-400',
  };

  return (
    <div className={`
      rounded-lg border p-3 transition-all duration-300
      ${isActive
        ? 'bg-green-900/20 border-green-500/60 signal-active'
        : 'bg-caye-card border-caye-border'
      }
    `}>
      {/* Header */}
      <div className="flex items-start justify-between mb-2">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <div className={`
              w-2 h-2 rounded-full flex-shrink-0
              ${isActive
                ? 'bg-green-400 signal-pulse'
                : 'bg-slate-600'
              }
            `}></div>
            <span className={`
              text-xs font-bold font-mono
              ${isActive ? 'text-green-300' : 'text-slate-400'}
            `}>
              {info.name}
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1 ml-4">
            {info.description}
          </p>
        </div>

        {/* Status badge */}
        <span className={`
          text-xs font-mono px-2 py-0.5 rounded
          flex-shrink-0 ml-2
          ${isActive
            ? 'bg-green-500/20 text-green-400 border border-green-500/30'
            : 'bg-slate-700/50 text-slate-500 border border-slate-600/30'
          }
        `}>
          {isActive ? 'ACTIVE' : 'INACTIVE'}
        </span>
      </div>

      {/* Value */}
      {value && (
        <div className="ml-4">
          <span className={`
            text-xs font-mono
            ${isActive ? 'text-green-200' : 'text-slate-500'}
          `}>
            {value}
          </span>
        </div>
      )}

      {/* Extra info */}
      {extra && (
        <div className="ml-4 mt-1">
          <span className="text-xs text-slate-500 font-mono">
            {extra}
          </span>
        </div>
      )}

      {/* Source + Dimension */}
      <div className="flex items-center justify-between mt-2 ml-4">
        <span className="text-xs text-slate-600">
          {info.source}
        </span>
        <span className={`
          text-xs font-mono
          ${dimensionColors[info.dimension] || 'text-slate-500'}
        `}>
          {info.dimension}
        </span>
      </div>
    </div>
  );
};

// ─────────────────────────────────────────
// SIGNAL PANEL MAIN COMPONENT
// ─────────────────────────────────────────

const SignalPanel = ({ signalState }) => {

  if (!signalState) {
    return (
      <div className="bg-caye-surface rounded-xl border border-caye-border p-4">
        <h2 className="text-cyan-400 font-bold text-sm font-mono mb-4">
          ⚡ 9 LIVE SIGNALS
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
          {Array(7).fill(0).map((_, i) => (
            <div
              key={i}
              className="h-24 bg-caye-card rounded-lg border border-caye-border animate-pulse"
            ></div>
          ))}
        </div>
      </div>
    );
  }

  // Build signal values with human-readable numbers
  const signals = [
    {
      key: 'stablecoin_exodus',
      isActive: signalState.stablecoin_exodus || false,
      value: signalState.stablecoin_delta_48h
        ? `${formatCurrency(signalState.stablecoin_delta_48h)} (48h delta)`
        : signalState.total_stablecoin_mcap
        ? `Total: ${formatCurrency(signalState.total_stablecoin_mcap)}`
        : null,
      extra: signalState.stablecoin_exodus
        ? '⚠ Exodus threshold exceeded'
        : 'Threshold: -$500M in 48h'
    },
    {
      key: 'macro_draining',
      isActive: signalState.macro_draining || false,
      value: signalState.weekly_delta_pct !== null
        && signalState.weekly_delta_pct !== undefined
        ? `${formatPercent(signalState.weekly_delta_pct * 100)} weekly delta`
        : null,
      extra: signalState.current_net_liquidity
        ? `Net: ${formatCurrency(signalState.current_net_liquidity)}`
        : 'Threshold: < -2% weekly'
    },
    {
      key: 'insider_activity',
      isActive: signalState.insider_activity || false,
      value: signalState.current_gas_gwei
        ? formatGwei(signalState.current_gas_gwei)
        : null,
      extra: signalState.gas_acceleration_rate
        ? `Acceleration: ${(signalState.gas_acceleration_rate * 100).toFixed(0)}%`
        : 'Threshold: +300% in 5min'
    },
    {
      key: 'any_abandonment',
      isActive: signalState.any_abandonment || false,
      value: signalState.abandonment_details
        ? `${Object.keys(signalState.abandonment_details).length} repos monitored`
        : '6 repos monitored',
      extra: signalState.any_abandonment
        ? '⚠ Low commit velocity detected'
        : 'Threshold: < 20% velocity ratio'
    },
    {
      key: 'any_over_leveraged',
      isActive: signalState.any_over_leveraged || false,
      value: signalState.funding_rate_details
        ? Object.entries(signalState.funding_rate_details)
            .map(([sym, d]) =>
              `${sym}: ${
                d.funding_rate_pct
                  ? d.funding_rate_pct.toFixed(4)
                  : '0.0000'
              }%`
            ).join(' | ')
        : 'BTC | ETH | SOL',
      extra: 'Threshold: > 0.05% per 8h'
    },
    {
      key: 'regulatory_pressure',
      isActive: signalState.regulatory_pressure || false,
      value: signalState.total_dockets_7d !== null
        && signalState.total_dockets_7d !== undefined
        ? `${signalState.total_dockets_7d} dockets (7 days)`
        : null,
      extra: 'SDNY | 9th Circuit | DC Circuit'
    },
    {
      key: 'major_unlock_imminent',
      isActive: signalState.major_unlock_imminent || false,
      value: signalState.upcoming_unlocks?.length > 0
        ? signalState.upcoming_unlocks
            .map(u =>
              `${u.token}: ${u.days_until}d ($${(u.unlock_value_usd / 1e6).toFixed(0)}M)`
            ).join(' | ')
        : null,
      extra: 'Threshold: > $50M within 7 days'
    }
  ];

  // Count active signals
  const activeCount = signals.filter(s => s.isActive).length;

  return (
    <div className="bg-caye-surface rounded-xl border border-caye-border p-4">

      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <h2 className="text-cyan-400 font-bold text-sm font-mono">
            ⚡ 9 LIVE SIGNALS
          </h2>
          <span className={`
            text-xs font-mono px-2 py-0.5 rounded
            ${activeCount > 0
              ? 'bg-green-500/20 text-green-400 border border-green-500/30'
              : 'bg-slate-700/50 text-slate-400 border border-slate-600/30'
            }
          `}>
            {activeCount}/7 ACTIVE
          </span>
        </div>

        {/* Stale warning */}
        {signalState.signal_data_stale && (
          <span className="text-yellow-400 text-xs font-mono">
            ⚠ Signal data stale
          </span>
        )}

        {/* Last updated */}
        {signalState.created_at && (
          <span className="hidden sm:block text-slate-500 text-xs font-mono">
            Updated {formatTimeAgo(signalState.created_at)}
          </span>
        )}
      </div>

      {/* Signal Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
        {signals.map(signal => (
          <SignalCard
            key={signal.key}
            signalKey={signal.key}
            isActive={signal.isActive}
            value={signal.value}
            extra={signal.extra}
          />
        ))}
      </div>

    </div>
  );
};

export default SignalPanel;