/**
 * CAYE v3.0 — Utility Formatters
 * Currency, percentage, date, and
 * signal formatting functions.
 */

// ─────────────────────────────────────────
// CURRENCY FORMATTERS
// ─────────────────────────────────────────

export const formatCurrency = (value, decimals = 0) => {
  if (value === null || value === undefined) return '$0';
  const num = parseFloat(value);
  if (isNaN(num)) return '$0';

  if (Math.abs(num) >= 1_000_000_000) {
    return `$${(num / 1_000_000_000).toFixed(2)}B`;
  }
  if (Math.abs(num) >= 1_000_000) {
    return `$${(num / 1_000_000).toFixed(1)}M`;
  }
  if (Math.abs(num) >= 1_000) {
    return `$${(num / 1_000).toFixed(1)}K`;
  }
  return `$${num.toFixed(decimals)}`;
};

export const formatDollars = (value) => {
  if (value === null || value === undefined) return '$0.00';
  const num = parseFloat(value);
  if (isNaN(num)) return '$0.00';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(num);
};

export const formatPrice = (value) => {
  if (value === null || value === undefined) return '$0.00';
  const num = parseFloat(value);
  if (isNaN(num)) return '$0.00';
  return `$${num.toFixed(2)}`;
};

// ─────────────────────────────────────────
// PERCENTAGE FORMATTERS
// ─────────────────────────────────────────

export const formatPercent = (value, decimals = 1) => {
  if (value === null || value === undefined) return '0%';
  const num = parseFloat(value);
  if (isNaN(num)) return '0%';
  const sign = num > 0 ? '+' : '';
  return `${sign}${num.toFixed(decimals)}%`;
};

export const formatROI = (value) => {
  if (value === null || value === undefined) return '0%';
  const num = parseFloat(value);
  if (isNaN(num)) return '0%';
  return `${num.toFixed(1)}%`;
};

export const formatCIS = (value) => {
  if (value === null || value === undefined) return '0.00';
  const num = parseFloat(value);
  if (isNaN(num)) return '0.00';
  return num.toFixed(4);
};

export const formatWinRate = (value) => {
  if (value === null || value === undefined) return '0.0%';
  const num = parseFloat(value);
  if (isNaN(num)) return '0.0%';
  return `${num.toFixed(1)}%`;
};

// ─────────────────────────────────────────
// DATE / TIME FORMATTERS
// ─────────────────────────────────────────

export const formatDateTime = (isoString) => {
  if (!isoString) return 'N/A';
  try {
    const date = new Date(isoString);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    });
  } catch {
    return 'N/A';
  }
};

export const formatTimeAgo = (isoString) => {
  if (!isoString) return 'Never';
  try {
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now - date;
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHr = Math.floor(diffMin / 60);
    const diffDay = Math.floor(diffHr / 24);

    if (diffSec < 60) return `${diffSec}s ago`;
    if (diffMin < 60) return `${diffMin}m ago`;
    if (diffHr < 24) return `${diffHr}h ago`;
    return `${diffDay}d ago`;
  } catch {
    return 'N/A';
  }
};

export const formatExpiry = (isoString, daysToExpiry) => {
  if (daysToExpiry !== null && daysToExpiry !== undefined) {
    if (daysToExpiry === 0) return 'Expires today';
    if (daysToExpiry === 1) return 'Expires tomorrow';
    if (daysToExpiry < 0) return 'Expired';
    return `${daysToExpiry} days`;
  }
  if (!isoString) return 'N/A';
  try {
    const date = new Date(isoString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  } catch {
    return 'N/A';
  }
};

// ─────────────────────────────────────────
// CIS INTERPRETATION
// ─────────────────────────────────────────

export const getCISInterpretation = (score) => {
  if (score >= 0.98) return {
    label: 'MAXIMUM CONVICTION',
    color: '#00ff88',
    bgColor: 'rgba(0,255,136,0.1)'
  };
  if (score >= 0.95) return {
    label: 'STRONG CONVERGENCE',
    color: '#00d4ff',
    bgColor: 'rgba(0,212,255,0.1)'
  };
  if (score >= 0.90) return {
    label: 'GOOD CONVERGENCE',
    color: '#00d4ff',
    bgColor: 'rgba(0,212,255,0.08)'
  };
  if (score >= 0.89) return {
    label: 'MINIMUM THRESHOLD',
    color: '#ffcc00',
    bgColor: 'rgba(255,204,0,0.1)'
  };
  return {
    label: 'BELOW THRESHOLD',
    color: '#ff4444',
    bgColor: 'rgba(255,68,68,0.1)'
  };
};

export const getCISBarWidth = (score) => {
  const pct = Math.min(score * 100, 100);
  return `${pct}%`;
};

// ─────────────────────────────────────────
// ENGINE METADATA
// ─────────────────────────────────────────

export const getEngineInfo = (engineId) => {
  const engines = {
    1: {
      name: 'Inverse Trap',
      shortName: 'E1',
      description: 'Extreme retail consensus reversal',
      color: '#8b5cf6',
      bgClass: 'engine-1',
      icon: '🔄'
    },
    2: {
      name: 'Tail-Risk Front-Run',
      shortName: 'E2',
      description: 'Low-probability structural decay',
      color: '#ef4444',
      bgClass: 'engine-2',
      icon: '⚠️'
    },
    3: {
      name: 'Deterministic Unlock Bleed',
      shortName: 'E3',
      description: 'Scheduled vesting cliff pressure',
      color: '#f97316',
      bgClass: 'engine-3',
      icon: '🔓'
    },
    4: {
      name: 'Macro Starvation Short',
      shortName: 'E4',
      description: 'Fed liquidity drain ceiling',
      color: '#10b981',
      bgClass: 'engine-4',
      icon: '📉'
    }
  };
  return engines[engineId] || {
    name: 'Unknown',
    shortName: 'E?',
    description: '',
    color: '#64748b',
    bgClass: '',
    icon: '❓'
  };
};

// ─────────────────────────────────────────
// STATUS COLORS
// ─────────────────────────────────────────

export const getStatusColor = (status) => {
  const colors = {
    'ACTIVE':  { text: '#00d4ff', bg: 'rgba(0,212,255,0.1)' },
    'WON':     { text: '#00ff88', bg: 'rgba(0,255,136,0.1)' },
    'LOST':    { text: '#ff4444', bg: 'rgba(255,68,68,0.1)' },
    'EXPIRED': { text: '#94a3b8', bg: 'rgba(148,163,184,0.1)' },
    'VETOED':  { text: '#f97316', bg: 'rgba(249,115,22,0.1)' },
  };
  return colors[status] || colors['ACTIVE'];
};

// ─────────────────────────────────────────
// SIGNAL METADATA
// ─────────────────────────────────────────

export const getSignalInfo = (signalKey) => {
  const signals = {
    stablecoin_exodus: {
      name: 'Stablecoin Exodus',
      description: 'USDT+USDC -$500M in 48h',
      dimension: 'INVISIBLE',
      source: 'DefiLlama'
    },
    macro_draining: {
      name: 'Macro Draining',
      description: 'Fed net liquidity < -2% weekly',
      dimension: 'SCATTERED',
      source: 'FRED'
    },
    insider_activity: {
      name: 'Insider Activity',
      description: 'Gas price +300% in 5 minutes',
      dimension: 'INVISIBLE',
      source: 'Etherscan'
    },
    any_abandonment: {
      name: 'Dev Abandonment',
      description: 'Commit velocity < 20% baseline',
      dimension: 'HIDDEN',
      source: 'GitHub'
    },
    any_over_leveraged: {
      name: 'Over-Leveraged',
      description: 'Funding rate > 0.05% per 8h',
      dimension: 'INVISIBLE',
      source: 'Coinglass'
    },
    regulatory_pressure: {
      name: 'Regulatory Pressure',
      description: '>3 federal dockets in 7 days',
      dimension: 'HIDDEN',
      source: 'CourtListener'
    },
    major_unlock_imminent: {
      name: 'Major Unlock Imminent',
      description: '>$50M vesting cliff in 7 days',
      dimension: 'HIDDEN',
      source: 'TokenUnlocks'
    }
  };
  return signals[signalKey] || {
    name: signalKey,
    description: '',
    dimension: 'UNKNOWN',
    source: 'Unknown'
  };
};

// ─────────────────────────────────────────
// NUMBER FORMATTERS
// ─────────────────────────────────────────

export const formatNumber = (value) => {
  if (value === null || value === undefined) return '0';
  const num = parseInt(value);
  if (isNaN(num)) return '0';
  return new Intl.NumberFormat('en-US').format(num);
};

export const formatGwei = (value) => {
  if (!value) return '0 Gwei';
  return `${parseInt(value)} Gwei`;
};

export const formatLiquidity = (value) => {
  if (!value) return '$0';
  return formatCurrency(value);
};