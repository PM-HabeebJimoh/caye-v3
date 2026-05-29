/**
 * CAYE v3.0 — Scan Statistics Panel
 * Shows latest scan counters, veto breakdown,
 * and gate rejection reasons.
 */

import React from 'react';
import { formatTimeAgo, formatNumber } from '../utils/formatters';
import { useVetoSummary } from '../hooks/useApi';

const StatBox = ({ label, value, color = 'text-white', sub }) => (
  <div className="bg-caye-bg rounded-lg p-3 border border-caye-border text-center">
    <div className={`text-xl font-bold font-mono ${color}`}>
      {formatNumber(value)}
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

const ScanStats = ({ lastScan }) => {
  const { data: vetoSummary } = useVetoSummary();

  if (!lastScan) {
    return (
      <div className="bg-caye-surface rounded-xl border border-caye-border p-4">
        <h2 className="text-cyan-400 font-bold text-sm font-mono mb-4">
          📊 SCAN STATISTICS
        </h2>
        <div className="text-slate-500 text-xs font-mono text-center py-6">
          Awaiting first scan...
        </div>
      </div>
    );
  }

  const vetoTotal = (lastScan.gate1_vetoed || 0)
    + (lastScan.gate2_vetoed || 0)
    + (lastScan.gate3_vetoed || 0)
    + (lastScan.gate4_vetoed || 0);

  return (
    <div className="bg-caye-surface rounded-xl border border-caye-border p-4">

      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-cyan-400 font-bold text-sm font-mono">
          📊 SCAN STATISTICS
        </h2>
        <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
          <span className="w-1.5 h-1.5 rounded-full bg-green-400 signal-pulse"></span>
          <span>Every 60s</span>
          <span className="text-slate-500">|</span>
          <span>{formatTimeAgo(lastScan.scanned_at)}</span>
        </div>
      </div>

      {/* Main stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
        <StatBox
          label="Markets Fetched"
          value={lastScan.markets_fetched}
          color="text-white"
        />
        <StatBox
          label="Crypto Filtered"
          value={lastScan.markets_crypto}
          color="text-cyan-400"
        />
        <StatBox
          label="Vetoed"
          value={lastScan.markets_vetoed}
          color="text-orange-400"
        />
        <StatBox
          label="Opportunities"
          value={lastScan.opportunities_found}
          color="text-green-400"
          sub="Found this scan"
        />
      </div>

      {/* Gate veto breakdown */}
      <div className="bg-caye-bg rounded-lg border border-caye-border p-3">
        <div className="text-xs text-slate-500 font-mono mb-3">
          GATE VETO BREAKDOWN (this scan)
        </div>

        <div className="space-y-2">
          {[
            {
              num: 3,
              name: 'Liquidity Minimum',
              count: lastScan.gate3_vetoed || 0,
              req: '≥ $50,000',
              color: 'bg-blue-400'
            },
            {
              num: 1,
              name: 'Price Ceiling',
              count: lastScan.gate1_vetoed || 0,
              req: '≤ $0.52',
              color: 'bg-purple-400'
            },
            {
              num: 4,
              name: 'Expiry Guard',
              count: lastScan.gate4_vetoed || 0,
              req: '> 2 days',
              color: 'bg-yellow-400'
            },
            {
              num: 2,
              name: 'CIS Threshold',
              count: lastScan.gate2_vetoed || 0,
              req: '≥ 0.89',
              color: 'bg-red-400'
            },
          ].map(gate => {
            const pct = vetoTotal > 0
              ? (gate.count / vetoTotal * 100)
              : 0;

            return (
              <div key={gate.num}>
                <div className="flex items-center justify-between text-xs font-mono mb-1">
                  <span className="text-slate-400">
                    Gate {gate.num}: {gate.name}
                    <span className="text-slate-600 ml-1">
                      ({gate.req})
                    </span>
                  </span>
                  <span className="text-white font-bold">
                    {gate.count}
                  </span>
                </div>
                <div className="h-1 bg-slate-700 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${gate.color} rounded-full transition-all duration-500`}
                    style={{ width: `${pct}%` }}
                  ></div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Duration */}
      {lastScan.scan_duration_ms && (
        <div className="mt-3 text-xs text-slate-500 font-mono text-right">
          Scan duration: {lastScan.scan_duration_ms}ms
          {lastScan.signal_data_stale && (
            <span className="text-yellow-400 ml-2">
              ⚠ Stale signals
            </span>
          )}
        </div>
      )}

    </div>
  );
};

export default ScanStats;