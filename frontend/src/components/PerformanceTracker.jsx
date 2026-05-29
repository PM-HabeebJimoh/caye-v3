/**
 * CAYE v3.0 — Performance Tracker
 * Win rate, ROI, P&L, drawdown statistics.
 * Loaded from REST API (not WebSocket).
 */

import React from 'react';
import {
  formatWinRate,
  formatROI,
  formatDollars,
  formatNumber,
  getEngineInfo
} from '../utils/formatters';
import { usePerformance } from '../hooks/useApi';

const MetricBox = ({
  label, value, sub, color = 'text-white'
}) => (
  <div className="bg-caye-bg rounded-lg p-3 border border-caye-border">
    <div className={`text-xl font-bold font-mono ${color}`}>
      {value}
    </div>
    <div className="text-xs text-slate-500 font-mono mt-1">
      {label}
    </div>
    {sub && (
      <div className="text-xs text-slate-600 font-mono">
        {sub}
      </div>
    )}
  </div>
);

const PerformanceTracker = () => {
  const { data: perf, loading, error } = usePerformance();

  if (loading) {
    return (
      <div className="bg-caye-surface rounded-xl border border-caye-border p-4">
        <h2 className="text-cyan-400 font-bold text-sm font-mono mb-4">
          📈 PERFORMANCE TRACKER
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {Array(8).fill(0).map((_, i) => (
            <div
              key={i}
              className="h-16 bg-caye-bg rounded-lg border border-caye-border animate-pulse"
            ></div>
          ))}
        </div>
      </div>
    );
  }

  if (error || !perf) {
    return (
      <div className="bg-caye-surface rounded-xl border border-caye-border p-4">
        <h2 className="text-cyan-400 font-bold text-sm font-mono mb-2">
          📈 PERFORMANCE TRACKER
        </h2>
        <div className="text-slate-500 text-xs font-mono">
          No trade history yet. Opportunities will appear as markets resolve.
        </div>
      </div>
    );
  }

  const resolvedTotal = (perf.won_trades || 0)
    + (perf.lost_trades || 0);

  return (
    <div className="bg-caye-surface rounded-xl border border-caye-border p-4">

      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-cyan-400 font-bold text-sm font-mono">
          📈 PERFORMANCE TRACKER
        </h2>
        <span className="text-xs text-slate-500 font-mono">
          {resolvedTotal} resolved trades
        </span>
      </div>

      {/* Core metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
        <MetricBox
          label="Win Rate"
          value={formatWinRate(perf.win_rate)}
          color="text-green-400"
          sub={`${perf.won_trades || 0}W / ${perf.lost_trades || 0}L`}
        />
        <MetricBox
          label="Avg ROI"
          value={formatROI(perf.average_roi)}
          color="text-cyan-400"
          sub="Won trades"
        />
        <MetricBox
          label="Total P&L"
          value={formatDollars(perf.total_profit_loss)}
          color={
            (perf.total_profit_loss || 0) >= 0
              ? 'text-green-400'
              : 'text-red-400'
          }
        />
        <MetricBox
          label="Max Drawdown"
          value={`-${formatDollars(perf.max_drawdown || 0)}`}
          color="text-red-400"
          sub="Single loss"
        />
      </div>

      {/* Status counts */}
      <div className="grid grid-cols-4 gap-2 mb-4">
        {[
          {
            label: 'Active',
            value: perf.active_trades || 0,
            color: 'text-cyan-400',
            bg: 'bg-cyan-500/10 border-cyan-500/20'
          },
          {
            label: 'Won',
            value: perf.won_trades || 0,
            color: 'text-green-400',
            bg: 'bg-green-500/10 border-green-500/20'
          },
          {
            label: 'Lost',
            value: perf.lost_trades || 0,
            color: 'text-red-400',
            bg: 'bg-red-500/10 border-red-500/20'
          },
          {
            label: 'Expired',
            value: perf.expired_trades || 0,
            color: 'text-slate-400',
            bg: 'bg-slate-700/30 border-slate-600/20'
          },
        ].map(item => (
          <div
            key={item.label}
            className={`rounded-lg border ${item.bg} p-2 text-center`}
          >
            <div className={`text-lg font-bold font-mono ${item.color}`}>
              {item.value}
            </div>
            <div className="text-xs text-slate-500 font-mono">
              {item.label}
            </div>
          </div>
        ))}
      </div>

      {/* Engine breakdown */}
      {perf.engine_breakdown && (
        <div className="bg-caye-bg rounded-lg border border-caye-border p-3">
          <div className="text-xs text-slate-500 font-mono mb-3">
            PERFORMANCE BY ENGINE
          </div>
          <div className="space-y-2">
            {Object.entries(perf.engine_breakdown).map(
              ([key, data]) => {
                const engineId = parseInt(key.replace('engine_', ''));
                const info = getEngineInfo(engineId);
                const resolved = data.won + data.lost;

                return (
                  <div
                    key={key}
                    className="flex items-center justify-between text-xs font-mono"
                  >
                    <div className="flex items-center gap-2">
                      <span style={{ color: info.color }}>
                        {info.icon}
                      </span>
                      <span className="text-slate-400">
                        E{engineId}: {info.name}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 text-xs">
                      <span className="text-green-400">
                        {data.won}W
                      </span>
                      <span className="text-red-400">
                        {data.lost}L
                      </span>
                      <span className="text-slate-400">
                        {resolved > 0
                          ? `${data.win_rate.toFixed(0)}%`
                          : 'N/A'
                        }
                      </span>
                    </div>
                  </div>
                );
              }
            )}
          </div>
        </div>
      )}

    </div>
  );
};

export default PerformanceTracker;