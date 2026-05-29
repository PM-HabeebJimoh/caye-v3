/**
 * CAYE v3.0 — Historical Log
 * Past resolved and expired opportunities.
 * Shows actual ROI and outcomes.
 */

import React, { useState } from 'react';
import {
  formatTimeAgo,
  formatROI,
  formatDollars,
  formatPrice,
  getEngineInfo,
  getStatusColor
} from '../utils/formatters';
import { useHistoricalOpportunities } from '../hooks/useApi';

const HistoricalLog = () => {
  const { data, loading } = useHistoricalOpportunities();
  const [filter, setFilter] = useState('ALL');

  const records = data?.records || [];

  const filtered = filter === 'ALL'
    ? records
    : records.filter(r => r.status === filter);

  const wonCount = records.filter(r => r.status === 'WON').length;
  const lostCount = records.filter(r => r.status === 'LOST').length;
  const expiredCount = records.filter(
    r => r.status === 'EXPIRED'
  ).length;

  return (
    <div className="bg-caye-surface rounded-xl border border-caye-border p-4">

      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-cyan-400 font-bold text-sm font-mono">
          📋 HISTORICAL LOG
        </h2>
        <div className="flex items-center gap-3 text-xs font-mono">
          <span className="text-green-400">
            {wonCount}W
          </span>
          <span className="text-red-400">
            {lostCount}L
          </span>
          <span className="text-slate-400">
            {expiredCount}E
          </span>
        </div>
      </div>

      {/* Filter buttons */}
      <div className="flex flex-wrap gap-2 mb-4">
        {['ALL', 'WON', 'LOST', 'EXPIRED'].map(f => {
          const colors = f === 'ALL'
            ? 'text-cyan-400 border-cyan-500/30 bg-cyan-500/10'
            : f === 'WON'
            ? 'text-green-400 border-green-500/30 bg-green-500/10'
            : f === 'LOST'
            ? 'text-red-400 border-red-500/30 bg-red-500/10'
            : 'text-slate-400 border-slate-500/30 bg-slate-700/30';

          return (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`
                text-xs font-mono px-3 py-1 rounded border
                transition-opacity
                ${filter === f
                  ? colors
                  : 'text-slate-500 border-slate-700/30 opacity-50 hover:opacity-75'
                }
              `}
            >
              {f}
            </button>
          );
        })}
      </div>

      {/* Records */}
      {loading ? (
        <div className="space-y-2">
          {Array(4).fill(0).map((_, i) => (
            <div
              key={i}
              className="h-16 bg-caye-bg rounded-lg border border-caye-border animate-pulse"
            ></div>
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-8 text-slate-500 text-xs font-mono">
          {filter === 'ALL'
            ? 'No resolved trades yet. History will appear as markets resolve.'
            : `No ${filter} trades yet.`
          }
        </div>
      ) : (
        <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
          {filtered.map(record => {
            const engineInfo = getEngineInfo(record.engine_id);
            const statusColor = getStatusColor(record.status);

            return (
              <div
                key={record.id}
                className="bg-caye-bg rounded-lg border border-caye-border p-3 hover:border-slate-600/50 transition-colors"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">

                    {/* Status + Engine */}
                    <div className="flex items-center gap-2 mb-1">
                      <span
                        className="text-xs font-mono font-bold"
                        style={{ color: statusColor.text }}
                      >
                        {record.status === 'WON' ? '🟢' : record.status === 'LOST' ? '🔴' : '⚪'}
                        {' '}{record.status}
                      </span>
                      <span
                        className="text-xs font-mono"
                        style={{ color: engineInfo.color }}
                      >
                        {engineInfo.icon} E{record.engine_id}
                      </span>
                      <span className="text-xs text-slate-500 font-mono">
                        {record.target_side} @ {formatPrice(record.entry_price)}
                      </span>
                    </div>

                    {/* Question */}
                    <p className="text-xs text-slate-300 font-mono truncate">
                      {record.question}
                    </p>

                    {/* ROI */}
                    <div className="flex items-center gap-3 mt-1 text-xs font-mono">
                      {record.actual_roi !== null
                        && record.actual_roi !== undefined ? (
                        <span className={
                          record.actual_roi > 0
                            ? 'text-green-400'
                            : 'text-red-400'
                        }>
                          {record.actual_roi > 0 ? '+' : ''}
                          {formatROI(record.actual_roi)} ROI
                        </span>
                      ) : null}

                      {record.actual_profit !== null
                        && record.actual_profit !== undefined ? (
                        <span className={
                          record.actual_profit > 0
                            ? 'text-green-400'
                            : 'text-red-400'
                        }>
                          {record.actual_profit > 0 ? '+' : ''}
                          {formatDollars(record.actual_profit)}
                        </span>
                      ) : null}

                      {record.cis_score && (
                        <span className="text-slate-500">
                          CIS: {record.cis_score.toFixed(2)}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Time */}
                  <span className="text-xs text-slate-600 font-mono flex-shrink-0">
                    {formatTimeAgo(
                      record.resolved_at || record.archived_at
                    )}
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

export default HistoricalLog;