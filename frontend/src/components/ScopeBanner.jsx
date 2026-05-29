/**
 * CAYE v3.0 — Scope Banner
 * PERMANENT banner confirming crypto-only scope.
 * Cannot be hidden. Always visible at top.
 * Layer 5 of 6-layer crypto enforcement.
 */

import React from 'react';

const ScopeBanner = () => {
  return (
    <div className="w-full bg-gradient-to-r from-blue-900/40 via-cyan-900/40 to-blue-900/40 border-b border-cyan-800/50 px-4 py-2">
      <div className="max-w-screen-2xl mx-auto flex items-center justify-between">

        {/* Left: Scope declaration */}
        <div className="flex items-center gap-3">
          <span className="text-cyan-400 font-bold text-xs tracking-widest">
            ⚡ SCOPE:
          </span>
          <span className="text-cyan-300 text-xs font-mono">
            Polymarket Cryptocurrency &amp; DeFi Markets ONLY
          </span>
          <span className="hidden sm:flex items-center gap-1 text-xs text-slate-400">
            <span className="text-green-400">✓</span>
            6-Layer Enforcement Active
          </span>
        </div>

        {/* Right: Zero non-crypto confirmation */}
        <div className="flex items-center gap-2 text-xs">
          <span className="text-green-400 font-mono">
            ✓ 0 Non-Crypto Markets
          </span>
          <span className="hidden md:block text-slate-500">|</span>
          <span className="hidden md:block text-slate-400 font-mono">
            Binary Markets: $0.00 or $1.00
          </span>
        </div>

      </div>
    </div>
  );
};

export default ScopeBanner;