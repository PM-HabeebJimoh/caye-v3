/**
 * CAYE v3.0 — API Hook
 * REST API calls for data not delivered
 * via WebSocket (performance, history, vetoes).
 */

import { useState, useEffect, useCallback } from 'react';

const API_URL = process.env.REACT_APP_API_URL
  || 'http://localhost:8000';

const useFetch = (endpoint, deps = []) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch(
        `${API_URL}${endpoint}`
      );
      if (!response.ok) {
        throw new Error(
          `HTTP ${response.status}`
        );
      }
      const json = await response.json();
      setData(json);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [endpoint]);

  useEffect(() => {
    fetchData();
  }, [fetchData, ...deps]);

  return { data, loading, error, refetch: fetchData };
};

export const usePerformance = () => {
  return useFetch('/api/performance/summary');
};

export const useVetoLog = () => {
  return useFetch('/api/scanlogs/vetoes?limit=50');
};

export const useHistoricalOpportunities = () => {
  return useFetch(
    '/api/opportunities/historical/list?page_size=50'
  );
};

export const useLatestScan = () => {
  return useFetch('/api/scanlogs/latest');
};

export const useVetoSummary = () => {
  return useFetch('/api/scanlogs/vetoes/summary');
};

export const useSignalHistory = (hours = 24) => {
  return useFetch(`/api/signals/history?hours=${hours}`);
};

export default useFetch;