/**
 * CAYE v3.0 — Veto Transparency Log
 * Every rejected market with exact reason.
 * "Correct Empty State — No fake opportunities."
 */

import React, { useState } from 'react';
import {
  formatTimeAgo,
  formatPrice,
  formatNumber
} from '../utils/formatters';
import { useVetoLog } from '../hooks/useApi';

const GATE_COLORS = {
  1: { text: 'text-purple-400', bg: 'bg-purple-500/10', border: 'border-purple-500/20' },
  2: { text: 'text-red-400',    bg: 'bg-red-500/10',    border: 'border-red-500/20' },
  3: { text: 'text-blue-400',   bg: 'bg-blue-500/10',   border: 'border-blue-500/20' },
  4: { text: 'text-yellow-400', bg: 'bg-yellow-500/10', border: 'border-yellow-500/20' },
};

const GATE_NAMES = {
  1: 'Price Ceiling',
  2: 'CIS Threshold',
  3: 'Liquidity Minimum',
  4: 'Expiry Guard',
};

const VetoLog = () => {
  const { data, loading, error } = useVetoLog();
  const [gateFilter, setGateFilter] = useState(null);

  const vetoes = data?.vetoes || [];

  const filtered = gateFilter
    ? vetoes.filter(v => v.gate_number === gateFilter)
    : vetoes;

  return (
    <div className="bg-caye-surface rounded-xl border border-caye-border p-4">

      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-cyan-400 font-bold text-sm font-mono">
          🚫 VETO TRANSPARENCY LOG
        </h2>
        <span className="text-xs text-slate-500 font-mono">
          {data?.total || 0} total vetoes
        </span>
      </div>

      {/* Gate filter buttons */}
      <div className="flex flex-wrap gap-2 mb-4">
        <button
          onClick={() => setGateFilter(null)}
          className={`
            text-xs font-mono px-3 py-1 rounded border
            transition-colors
            ${!gateFilter
              ? 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30'
              : 'text-slate-400 border-slate-600/30 hover:border-slate-500/50'
            }
          `}
        >
          All
        </button>
        {[1, 2, 3, 4].map(gate => {
          const colors = GATE_COLORS[gate];
          return (
            <button
              key={gate}
              onClick={() => setGateFilter(
                gateFilter === gate ? null : gate
              )}
              className={`
                text-xs font-mono px-3 py-1 rounded border
                transition-colors
                ${gateFilter === gate
                  ? `${colors.bg} ${colors.text} ${colors.border}`
                  : 'text-slate-400 border-slate-600/30 hover:border-slate-500/50'
                }
              `}
            >
              Gate {gate}: {GATE_NAMES[gate]}
            </button>
          );
        })}
      </div>

      {/* Veto list */}
      {loading ? (
        <div className="space-y-2">
          {Array(5).fill(0).map((_, i) => (
            <div
              key={i}
              className="h-14 bg-caye-bg rounded-lg border border-caye-border animate-pulse"
            ></div>
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-8 text-slate-500 text-xs font-mono">
          No vetoes to display.
        </div>
      ) : (
        <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
          {filtered.map(veto => {
            const colors = GATE_COLORS[veto.gate_number]
              || GATE_COLORS[1];

            return (
              <div
                key={veto.id}
                className={`
                  rounded-lg border p-3
                  ${colors.bg} ${colors.border}
                `}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">

                    {/* Gate badge */}
                    <div className="flex items-center gap-2 mb-1">
                      <span
                        className={`
                          text-xs font-mono font-bold
                          ${colors.text}
                        `}
                      >
                        ✗ Gate {veto.gate_number}:
                        {GATE_NAMES[veto.gate_number]}
                      </span>
                    </div>

                    {/* Question */}
                    {veto.question && (
                      <p className="text-xs text-slate-300 font-mono truncate">
                        {veto.question}
                      </p>
                    )}

                    {/* Reason */}
                    <p className="text-xs text-slate-500 font-mono mt-1">
                      {veto.reason}
                    </p>
                  </div>

                  {/* Time */}
                  <span className="text-xs text-slate-600 font-mono flex-shrink-0">
                    {formatTimeAgo(veto.created_at)}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}

    </div>
  );
};

export default VetoLog;