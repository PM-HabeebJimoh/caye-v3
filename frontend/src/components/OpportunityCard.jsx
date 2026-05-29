/**
 * CAYE v3.0 — Opportunity Card
 * Displays a single trade opportunity.
 * Shows engine, entry price, CIS, position,
 * and link to Polymarket.
 */

import React, { useState } from 'react';
import GateBreakdown from './GateBreakdown';
import {
  formatPrice,
  formatROI,
  formatDollars,
  formatExpiry,
  formatCIS,
  formatLiquidity,
  getEngineInfo,
  getCISInterpretation
} from '../utils/formatters';

const OpportunityCard = ({
  opportunity,
  isNew = false
}) => {
  const [showDetails, setShowDetails] = useState(false);

  if (!opportunity) return null;

  const {
    engine_id,
    engine_name,
    question,
    entry_price,
    target_side,
    cis_score,
    recommended_position,
    potential_profit,
    roi_pct,
    expected_value,
    liquidity,
    days_to_expiry,
    expiry_date,
    polymarket_url,
    subcategory
  } = opportunity;

  const engineInfo = getEngineInfo(engine_id);
  const cisInfo = getCISInterpretation(cis_score || 0);

  return (
    <div className={`
      opportunity-card bg-caye-card rounded-xl border
      p-4 transition-all duration-300
      ${isNew ? 'new-opportunity-animation' : ''}
      border-caye-border hover:border-cyan-800/50
    `}>

      {/* ─── HEADER ─── */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">

          {/* Engine badge */}
          <div className="flex items-center gap-2 mb-2">
            <span
              className={`
                text-xs font-mono font-bold px-2 py-0.5
                rounded border ${engineInfo.bgClass}
              `}
              style={{ color: engineInfo.color }}
            >
              {engineInfo.icon} ENGINE {engine_id}: {engineInfo.name.toUpperCase()}
            </span>

            {subcategory && (
              <span className="text-xs text-slate-500 font-mono">
                {subcategory}
              </span>
            )}
          </div>

          {/* Question */}
          <p className="text-sm text-white font-mono leading-relaxed">
            {question}
          </p>
        </div>

        {/* CIS Badge */}
        <div
          className="flex-shrink-0 ml-3 text-center px-3 py-1 rounded border"
          style={{
            borderColor: cisInfo.color + '40',
            backgroundColor: cisInfo.bgColor
          }}
        >
          <div
            className="text-lg font-bold font-mono"
            style={{ color: cisInfo.color }}
          >
            {formatCIS(cis_score)}
          </div>
          <div
            className="text-xs font-mono"
            style={{ color: cisInfo.color }}
          >
            CIS
          </div>
        </div>
      </div>

      {/* ─── TRADE INFO ─── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-3">

        {/* Entry */}
        <div className="bg-caye-bg rounded-lg p-2 border border-caye-border">
          <div className="text-xs text-slate-500 font-mono mb-1">
            BUY {target_side}
          </div>
          <div className="text-sm font-bold text-white font-mono">
            {formatPrice(entry_price)}
          </div>
          <div className="text-xs text-slate-400 font-mono">
            Entry price
          </div>
        </div>

        {/* ROI */}
        <div className="bg-caye-bg rounded-lg p-2 border border-caye-border">
          <div className="text-xs text-slate-500 font-mono mb-1">
            MIN ROI
          </div>
          <div className="text-sm font-bold text-green-400 font-mono">
            {formatROI(roi_pct)}
          </div>
          <div className="text-xs text-slate-400 font-mono">
            If correct
          </div>
        </div>

        {/* Position */}
        <div className="bg-caye-bg rounded-lg p-2 border border-caye-border">
          <div className="text-xs text-slate-500 font-mono mb-1">
            POSITION
          </div>
          <div className="text-sm font-bold text-cyan-400 font-mono">
            {formatDollars(recommended_position)}
          </div>
          <div className="text-xs text-slate-400 font-mono">
            Quarter-Kelly
          </div>
        </div>

        {/* Profit */}
        <div className="bg-caye-bg rounded-lg p-2 border border-caye-border">
          <div className="text-xs text-slate-500 font-mono mb-1">
            POTENTIAL
          </div>
          <div className="text-sm font-bold text-green-400 font-mono">
            +{formatDollars(potential_profit)}
          </div>
          <div className="text-xs text-slate-400 font-mono">
            Profit
          </div>
        </div>

      </div>

      {/* ─── META ROW ─── */}
      <div className="flex flex-wrap items-center gap-3 text-xs font-mono mb-3">
        <span className="text-slate-400">
          Liquidity:{' '}
          <span className="text-white">
            {formatLiquidity(liquidity)}
          </span>
        </span>
        <span className="text-slate-500">|</span>
        <span className="text-slate-400">
          Expires:{' '}
          <span className={
            days_to_expiry <= 7
              ? 'text-yellow-400'
              : 'text-white'
          }>
            {formatExpiry(expiry_date, days_to_expiry)}
          </span>
        </span>
        {expected_value && (
          <>
            <span className="text-slate-500">|</span>
            <span className="text-slate-400">
              EV:{' '}
              <span className="text-green-400">
                +{formatDollars(expected_value)}
              </span>
            </span>
          </>
        )}
      </div>

      {/* ─── CIS BREAKDOWN ─── */}
      <GateBreakdown opportunity={opportunity} />

      {/* ─── ACTION ROW ─── */}
      <div className="flex items-center justify-between mt-3 pt-3 border-t border-caye-border">

        <button
          onClick={() => setShowDetails(!showDetails)}
          className="text-xs text-slate-500 hover:text-cyan-400 font-mono transition-colors"
        >
          {showDetails ? '▲ Less' : '▼ More details'}
        </button>

        {polymarket_url && (
          <a
            href={polymarket_url}
            target="_blank"
            rel="noopener noreferrer"
            className="
              flex items-center gap-2 px-4 py-1.5 rounded-lg
              bg-cyan-500/10 border border-cyan-500/30
              text-cyan-400 text-xs font-mono font-bold
              hover:bg-cyan-500/20 hover:border-cyan-400/50
              transition-all duration-200
            "
          >
            VIEW ON POLYMARKET ↗
          </a>
        )}
      </div>

      {/* ─── EXTENDED DETAILS ─── */}
      {showDetails && (
        <div className="mt-3 pt-3 border-t border-caye-border animate-fade-in">
          <div className="grid grid-cols-2 gap-2 text-xs font-mono">
            <div>
              <span className="text-slate-500">Engine: </span>
              <span className="text-slate-300">{engine_name}</span>
            </div>
            <div>
              <span className="text-slate-500">CIS: </span>
              <span style={{ color: cisInfo.color }}>
                {formatCIS(cis_score)} — {cisInfo.label}
              </span>
            </div>
            <div>
              <span className="text-slate-500">Gate 1 (Price): </span>
              <span className="text-green-400">
                ${entry_price?.toFixed(2)} ≤ $0.52 ✓
              </span>
            </div>
            <div>
              <span className="text-slate-500">Gate 3 (Liquid): </span>
              <span className="text-green-400">
                {formatLiquidity(liquidity)} ≥ $50K ✓
              </span>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};

export default OpportunityCard;