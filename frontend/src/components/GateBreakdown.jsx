/**
 * CAYE v3.0 — Gate & CIS Breakdown
 * Displays CIS score with signal contributions
 * and gate pass/fail results per opportunity.
 */

import React, { useState } from 'react';
import {
  formatCIS,
  getCISInterpretation,
  getCISBarWidth,
  getSignalInfo
} from '../utils/formatters';

const GateBreakdown = ({ opportunity }) => {
  const [expanded, setExpanded] = useState(false);

  if (!opportunity) return null;

  const {
    cis_score,
    signal_breakdown,
    gate_results,
    engine_id
  } = opportunity;

  const cisInfo = getCISInterpretation(cis_score || 0);

  // Signal contributions for this engine
  const signalContributions = signal_breakdown
    ? Object.entries(signal_breakdown).filter(
        ([key, val]) => {
          // Only show signals relevant to this engine
          const engineWeights = {
            1: ['stablecoin_exodus','macro_draining','any_over_leveraged','any_abandonment','regulatory_pressure'],
            2: ['any_abandonment','insider_activity','regulatory_pressure','stablecoin_exodus'],
            3: ['major_unlock_imminent','stablecoin_exodus','any_over_leveraged','macro_draining'],
            4: ['macro_draining','stablecoin_exodus','any_over_leveraged','any_abandonment']
          };
          return (engineWeights[engine_id] || []).includes(key);
        }
      )
    : [];

  return (
    <div className="mt-3 border-t border-caye-border pt-3">

      {/* CIS SCORE BAR */}
      <div className="mb-3">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs text-slate-400 font-mono">
            CIS SCORE
          </span>
          <div className="flex items-center gap-2">
            <span
              className="text-xs font-bold font-mono"
              style={{ color: cisInfo.color }}
            >
              {formatCIS(cis_score)}
            </span>
            <span
              className="text-xs font-mono px-2 py-0.5 rounded"
              style={{
                color: cisInfo.color,
                backgroundColor: cisInfo.bgColor
              }}
            >
              {cisInfo.label}
            </span>
          </div>
        </div>

        {/* Progress bar */}
        <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
          <div
            className="h-full cis-bar rounded-full"
            style={{ width: getCISBarWidth(cis_score || 0) }}
          ></div>
        </div>

        {/* Threshold marker */}
        <div className="relative h-2">
          <div
            className="absolute top-0 w-px h-2 bg-yellow-500/50"
            style={{ left: '89%' }}
            title="0.89 threshold"
          ></div>
        </div>
      </div>

      {/* SIGNAL BREAKDOWN TOGGLE */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left text-xs text-slate-500 hover:text-cyan-400 font-mono transition-colors flex items-center gap-1"
      >
        <span>{expanded ? '▼' : '▶'}</span>
        <span>Signal Breakdown</span>
      </button>

      {/* SIGNAL BREAKDOWN EXPANDED */}
      {expanded && (
        <div className="mt-2 space-y-1 animate-fade-in">
          {signalContributions.map(([key, contribution]) => {
            const info = getSignalInfo(key);
            const isActive = contribution > 0;

            return (
              <div
                key={key}
                className="flex items-center justify-between text-xs font-mono"
              >
                <div className="flex items-center gap-2">
                  <span className={
                    isActive ? 'text-green-400' : 'text-slate-600'
                  }>
                    {isActive ? '✓' : '✗'}
                  </span>
                  <span className={
                    isActive ? 'text-slate-300' : 'text-slate-600'
                  }>
                    {info.name}
                  </span>
                </div>
                <span className={
                  isActive ? 'text-green-400' : 'text-slate-600'
                }>
                  +{contribution.toFixed(2)}
                </span>
              </div>
            );
          })}

          {/* Separator + Total */}
          <div className="border-t border-caye-border pt-1 flex items-center justify-between text-xs font-mono">
            <span className="text-slate-400">CIS Total</span>
            <span
              className="font-bold"
              style={{ color: cisInfo.color }}
            >
              {formatCIS(cis_score)} ✓ GATE 2 PASSED
            </span>
          </div>
        </div>
      )}

      {/* GATE RESULTS */}
      {gate_results && expanded && (
        <div className="mt-3 grid grid-cols-2 gap-1">
          {[
            { num: 3, key: 'gate3', name: 'Liquidity' },
            { num: 1, key: 'gate1', name: 'Price Ceiling' },
            { num: 4, key: 'gate4', name: 'Expiry Guard' },
            { num: 2, key: 'gate2', name: 'CIS Threshold' },
          ].map(gate => {
            const passed = gate_results[`${gate.key}_passed`];
            return (
              <div
                key={gate.key}
                className={`
                  flex items-center gap-1 text-xs font-mono
                  px-2 py-1 rounded
                  ${passed
                    ? 'bg-green-900/20 text-green-400'
                    : 'bg-red-900/20 text-red-400'
                  }
                `}
              >
                <span>{passed ? '✓' : '✗'}</span>
                <span>Gate {gate.num}: {gate.name}</span>
              </div>
            );
          })}
        </div>
      )}

    </div>
  );
};

export default GateBreakdown;