/**
 * CAYE v3.0 — Empty State Component
 * Shown when no opportunities are active.
 * System is scanning — just no gates passed yet.
 * "Correct Empty State — No fake opportunities."
 */

import React from 'react';

const EmptyState = ({ lastScan, isConnected }) => {
  return (
    <div className="bg-caye-card rounded-xl border border-caye-border p-12 text-center">

      {/* Icon */}
      <div className="text-5xl mb-4">🔍</div>

      {/* Title */}
      <h3 className="text-cyan-400 font-bold text-lg font-mono mb-2">
        NO OPPORTUNITIES CURRENTLY ACTIVE
      </h3>

      {/* Description */}
      <p className="text-slate-400 text-sm font-mono mb-6 max-w-lg mx-auto leading-relaxed">
        The system is scanning all Polymarket cryptocurrency
        markets every 60 seconds. An opportunity will appear
        here only when all 4 mathematical gates pass.
      </p>

      {/* Gate requirements */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 max-w-2xl mx-auto mb-6">
        {[
          {
            gate: 'Gate 1',
            name: 'Price Ceiling',
            req: 'Entry ≤ $0.52',
            color: 'border-purple-500/30 text-purple-400'
          },
          {
            gate: 'Gate 2',
            name: 'CIS Threshold',
            req: 'Score ≥ 0.89',
            color: 'border-red-500/30 text-red-400'
          },
          {
            gate: 'Gate 3',
            name: 'Liquidity',
            req: '≥ $50,000',
            color: 'border-blue-500/30 text-blue-400'
          },
          {
            gate: 'Gate 4',
            name: 'Expiry Guard',
            req: '> 2 days',
            color: 'border-yellow-500/30 text-yellow-400'
          },
        ].map(g => (
          <div
            key={g.gate}
            className={`
              rounded-lg border p-3 bg-caye-bg
              ${g.color}
            `}
          >
            <div className={`text-xs font-bold font-mono ${g.color.split(' ')[1]}`}>
              {g.gate}
            </div>
            <div className="text-xs text-slate-300 font-mono mt-1">
              {g.name}
            </div>
            <div className="text-xs text-slate-500 font-mono">
              {g.req}
            </div>
          </div>
        ))}
      </div>

      {/* Status */}
      {isConnected ? (
        <div className="flex items-center justify-center gap-2 text-sm text-green-400 font-mono">
          <span className="w-2 h-2 rounded-full bg-green-400 signal-pulse"></span>
          <span>
            System scanning — {lastScan
              ? `${lastScan.markets_crypto || 0} crypto markets checked`
              : 'awaiting first scan'
            }
          </span>
        </div>
      ) : (
        <div className="flex items-center justify-center gap-2 text-sm text-yellow-400 font-mono">
          <span className="w-2 h-2 rounded-full bg-yellow-400 animate-pulse"></span>
          <span>Connecting to live data...</span>
        </div>
      )}

      {/* Discipline note */}
      <p className="text-slate-600 text-xs font-mono mt-4">
        Discipline is the edge. 40-50% of the year is spent in cash.
      </p>

    </div>
  );
};

export default EmptyState;