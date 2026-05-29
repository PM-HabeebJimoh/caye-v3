/**
 * CAYE v3.0 — Main Application Component
 * Root dashboard layout.
 * All panels assembled here.
 */

import React, { useState } from 'react';
import { useWebSocket } from './hooks/useWebSocket';

// Components
import ScopeBanner from './components/ScopeBanner';
import SystemStatus from './components/SystemStatus';
import SignalPanel from './components/SignalPanel';
import OpportunityCard from './components/OpportunityCard';
import ScanStats from './components/ScanStats';
import PerformanceTracker from './components/PerformanceTracker';
import VetoLog from './components/VetoLog';
import HistoricalLog from './components/HistoricalLog';
import EmptyState from './components/EmptyState';

// Tab definitions
const TABS = [
  { id: 'opportunities', label: '⚡ Active Opportunities' },
  { id: 'signals',       label: '📡 Live Signals' },
  { id: 'performance',   label: '📈 Performance' },
  { id: 'history',       label: '📋 History & Vetoes' },
];

const App = () => {
  const [activeTab, setActiveTab] = useState('opportunities');

  // All live data from WebSocket
  const {
    isConnected,
    isReconnecting,
    systemStatus,
    activeOpportunities,
    signalState,
    lastScan,
    requestStateRefresh,
  } = useWebSocket();

  // Count active signals for badge
  const activeSignalCount = signalState
    ? [
        signalState.stablecoin_exodus,
        signalState.macro_draining,
        signalState.insider_activity,
        signalState.any_abandonment,
        signalState.any_over_leveraged,
        signalState.regulatory_pressure,
        signalState.major_unlock_imminent,
      ].filter(Boolean).length
    : 0;

  return (
    <div
      className="min-h-screen"
      style={{ backgroundColor: '#0a0e1a' }}
    >

      {/* ─── LAYER 5: SCOPE BANNER ─── */}
      <ScopeBanner />

      {/* ─── SYSTEM STATUS BAR ─── */}
      <SystemStatus
        isConnected={isConnected}
        isReconnecting={isReconnecting}
        systemStatus={systemStatus}
        lastScan={lastScan}
      />

      {/* ─── MAIN CONTENT ─── */}
      <div className="max-w-screen-2xl mx-auto px-4 py-6">

        {/* Page header */}
        <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
          <div>
            <h1 className="text-2xl font-bold text-white font-mono">
              ⚡ CAYE v3.0
            </h1>
            <p className="text-slate-400 text-sm font-mono mt-1">
              Crypto-Asymmetric Yield Engine —
              Polymarket Intelligence Dashboard
            </p>
          </div>

          <div className="flex items-center gap-3">
            {/* Active signal count */}
            <div className={`
              flex items-center gap-2 px-3 py-1.5 rounded-lg
              border text-xs font-mono
              ${activeSignalCount > 0
                ? 'bg-green-500/10 border-green-500/30 text-green-400'
                : 'bg-slate-700/30 border-slate-600/30 text-slate-400'
              }
            `}>
              <span className={`
                w-1.5 h-1.5 rounded-full
                ${activeSignalCount > 0 ? 'bg-green-400 signal-pulse' : 'bg-slate-500'}
              `}></span>
              {activeSignalCount}/7 Signals Active
            </div>

            {/* Opportunity count */}
            <div className={`
              flex items-center gap-2 px-3 py-1.5 rounded-lg
              border text-xs font-mono
              ${activeOpportunities.length > 0
                ? 'bg-cyan-500/10 border-cyan-500/30 text-cyan-400'
                : 'bg-slate-700/30 border-slate-600/30 text-slate-400'
              }
            `}>
              ⚡ {activeOpportunities.length} Active
            </div>

            {/* Refresh button */}
            <button
              onClick={requestStateRefresh}
              className="
                px-3 py-1.5 rounded-lg border
                border-slate-600/30 text-slate-400
                text-xs font-mono
                hover:border-cyan-500/30 hover:text-cyan-400
                transition-all duration-200
              "
              title="Refresh state"
            >
              ↺ Refresh
            </button>
          </div>
        </div>

        {/* ─── TAB NAVIGATION ─── */}
        <div className="flex flex-wrap gap-1 mb-6 border-b border-caye-border pb-3">
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`
                px-4 py-2 rounded-t-lg text-xs font-mono
                transition-all duration-200
                ${activeTab === tab.id
                  ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 border-b-transparent'
                  : 'text-slate-400 hover:text-slate-300 border border-transparent'
                }
              `}
            >
              {tab.label}
              {tab.id === 'opportunities'
                && activeOpportunities.length > 0 && (
                <span className="ml-2 px-1.5 py-0.5 bg-cyan-500/20 text-cyan-400 rounded-full text-xs">
                  {activeOpportunities.length}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* ─── TAB: ACTIVE OPPORTUNITIES ─── */}
        {activeTab === 'opportunities' && (
          <div className="space-y-4">

            {activeOpportunities.length === 0 ? (
              <EmptyState
                lastScan={lastScan}
                isConnected={isConnected}
              />
            ) : (
              <>
                <div className="flex items-center justify-between">
                  <h2 className="text-sm text-slate-400 font-mono">
                    {activeOpportunities.length} opportunit
                    {activeOpportunities.length === 1 ? 'y' : 'ies'}
                    {' '}— sorted by CIS score (highest conviction first)
                  </h2>
                </div>

                <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
                  {activeOpportunities.map((opp, index) => (
                    <OpportunityCard
                      key={opp.market_id || opp.id || index}
                      opportunity={opp}
                      isNew={index === 0}
                    />
                  ))}
                </div>
              </>
            )}

          </div>
        )}

        {/* ─── TAB: LIVE SIGNALS ─── */}
        {activeTab === 'signals' && (
          <div className="space-y-4">
            <SignalPanel signalState={signalState} />
            <ScanStats lastScan={lastScan} />
          </div>
        )}

        {/* ─── TAB: PERFORMANCE ─── */}
        {activeTab === 'performance' && (
          <div className="space-y-4">
            <PerformanceTracker />
          </div>
        )}

        {/* ─── TAB: HISTORY & VETOES ─── */}
        {activeTab === 'history' && (
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
            <HistoricalLog />
            <VetoLog />
          </div>
        )}

      </div>

      {/* ─── FOOTER ─── */}
      <footer className="border-t border-caye-border mt-12 py-4 px-4">
        <div className="max-w-screen-2xl mx-auto flex flex-wrap items-center justify-between gap-2 text-xs text-slate-600 font-mono">
          <span>
            ⚡ CAYE v3.0 — Crypto-Asymmetric Yield Engine
          </span>
          <span>
            Polymarket Cryptocurrency &amp; DeFi Markets ONLY
            | 6-Layer Enforcement
          </span>
          <span>
            Gates: Price ≤$0.52 | CIS ≥0.89 | Liq ≥$50K | Exp &gt;2d
          </span>
        </div>
      </footer>

    </div>
  );
};

export default App;