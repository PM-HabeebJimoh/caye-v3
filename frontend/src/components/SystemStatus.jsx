/**
 * CAYE v3.0 — System Status Bar
 * Shows WebSocket connection, last scan time,
 * markets scanned, and signal freshness.
 */

import React from 'react';
import { formatTimeAgo } from '../utils/formatters';

const SystemStatus = ({
  isConnected,
  isReconnecting,
  systemStatus,
  lastScan
}) => {

  const getStatusDisplay = () => {
    if (isReconnecting) return {
      dot: 'bg-yellow-400 animate-pulse',
      text: 'text-yellow-400',
      label: 'RECONNECTING...'
    };
    if (isConnected) return {
      dot: 'bg-green-400 signal-pulse',
      text: 'text-green-400',
      label: 'ONLINE'
    };
    return {
      dot: 'bg-red-500',
      text: 'text-red-400',
      label: 'OFFLINE'
    };
  };

  const status = getStatusDisplay();

  return (
    <div className="w-full bg-caye-surface border-b border-caye-border px-4 py-2">
      <div className="max-w-screen-2xl mx-auto flex flex-wrap items-center justify-between gap-2">

        {/* Left: System name + status */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${status.dot}`}></span>
            <span className={`text-xs font-bold font-mono ${status.text}`}>
              {status.label}
            </span>
          </div>

          <span className="text-slate-500 text-xs">|</span>

          <span className="text-slate-300 text-xs font-mono font-bold">
            ⚡ CAYE v3.0
          </span>

          <span className="hidden sm:block text-slate-500 text-xs">|</span>

          <span className="hidden sm:block text-slate-400 text-xs font-mono">
            Crypto-Asymmetric Yield Engine
          </span>
        </div>

        {/* Right: Scan stats */}
        <div className="flex items-center gap-4 text-xs font-mono">
          {lastScan && (
            <>
              <span className="text-slate-400">
                Last scan:{' '}
                <span className="text-cyan-400">
                  {formatTimeAgo(lastScan.scanned_at)}
                </span>
              </span>

              <span className="hidden sm:block text-slate-500">|</span>

              <span className="hidden sm:block text-slate-400">
                Scanned:{' '}
                <span className="text-white">
                  {lastScan.markets_crypto || 0}
                </span>
                <span className="text-slate-500"> crypto</span>
              </span>

              <span className="hidden md:block text-slate-500">|</span>

              <span className="hidden md:block text-slate-400">
                Found:{' '}
                <span className="text-green-400">
                  {lastScan.opportunities_found || 0}
                </span>
              </span>
            </>
          )}

          {!lastScan && (
            <span className="text-slate-500 text-xs">
              Awaiting first scan...
            </span>
          )}
        </div>

      </div>
    </div>
  );
};

export default SystemStatus;