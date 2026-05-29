/**
 * CAYE v3.0 — WebSocket Hook
 * Manages WebSocket connection lifecycle.
 * Handles connect, disconnect, reconnect,
 * and all incoming event types.
 */

import { useState, useEffect, useRef, useCallback } from 'react';

const WS_URL = process.env.REACT_APP_WS_URL
  || 'ws://localhost:8000/ws';

const RECONNECT_DELAYS = [3000, 5000, 10000, 15000, 30000];
const PING_INTERVAL = 30000; // 30 seconds

export const useWebSocket = () => {
  // Connection state
  const [isConnected, setIsConnected] = useState(false);
  const [isReconnecting, setIsReconnecting] = useState(false);
  const [connectionError, setConnectionError] = useState(null);

  // System state from WebSocket events
  const [activeOpportunities, setActiveOpportunities] = useState([]);
  const [signalState, setSignalState] = useState(null);
  const [lastScan, setLastScan] = useState(null);
  const [systemStatus, setSystemStatus] = useState('CONNECTING');

  // Refs
  const wsRef = useRef(null);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimerRef = useRef(null);
  const pingTimerRef = useRef(null);
  const mountedRef = useRef(true);

  // ─────────────────────────────────────
  // CONNECT TO WEBSOCKET
  // ─────────────────────────────────────

  const connect = useCallback(() => {
    if (!mountedRef.current) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!mountedRef.current) return;
        setIsConnected(true);
        setIsReconnecting(false);
        setConnectionError(null);
        setSystemStatus('ONLINE');
        reconnectAttemptRef.current = 0;

        // Start ping interval
        pingTimerRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          }
        }, PING_INTERVAL);
      };

      ws.onmessage = (event) => {
        if (!mountedRef.current) return;
        try {
          const data = JSON.parse(event.data);
          handleEvent(data);
        } catch (e) {
          console.warn('WS parse error:', e);
        }
      };

      ws.onclose = () => {
        if (!mountedRef.current) return;
        setIsConnected(false);
        setSystemStatus('OFFLINE');
        clearInterval(pingTimerRef.current);
        scheduleReconnect();
      };

      ws.onerror = (error) => {
        if (!mountedRef.current) return;
        setConnectionError('Connection failed');
        setSystemStatus('ERROR');
      };

    } catch (error) {
      setConnectionError(error.message);
      scheduleReconnect();
    }
  }, []);

  // ─────────────────────────────────────
  // RECONNECT LOGIC
  // ─────────────────────────────────────

  const scheduleReconnect = useCallback(() => {
    if (!mountedRef.current) return;

    const attempt = reconnectAttemptRef.current;
    const delay = RECONNECT_DELAYS[
      Math.min(attempt, RECONNECT_DELAYS.length - 1)
    ];

    setIsReconnecting(true);
    reconnectAttemptRef.current += 1;

    reconnectTimerRef.current = setTimeout(() => {
      if (mountedRef.current) {
        connect();
      }
    }, delay);
  }, [connect]);

  // ─────────────────────────────────────
  // EVENT HANDLER
  // Routes each WebSocket event type
  // ─────────────────────────────────────

  const handleEvent = useCallback((data) => {
    const { event, payload } = data;

    switch (event) {

      // Full initial state on connect
      case 'initial_state':
        setActiveOpportunities(
          payload.active_opportunities || []
        );
        setSignalState(payload.signal_state || null);
        setLastScan(payload.last_scan || null);
        setSystemStatus(payload.system_status || 'ONLINE');
        break;

      // New opportunity passed all gates
      case 'new_opportunity':
        if (payload.opportunity) {
          setActiveOpportunities(prev => {
            // Avoid duplicate market_ids
            const exists = prev.find(
              o => o.market_id === payload.opportunity.market_id
            );
            if (exists) {
              return prev.map(o =>
                o.market_id === payload.opportunity.market_id
                  ? payload.opportunity
                  : o
              );
            }
            // Add new — sorted by CIS descending
            const updated = [payload.opportunity, ...prev];
            return updated.sort(
              (a, b) => (b.cis_score || 0) - (a.cis_score || 0)
            );
          });
        }
        break;

      // Signal state changed
      case 'signal_update':
        if (payload.signal_state) {
          setSignalState(prev => ({
            ...prev,
            ...payload.signal_state
          }));
        }
        break;

      // Scan completed
      case 'scan_complete':
        if (payload.scan_log) {
          setLastScan(payload.scan_log);
        }
        break;

      // Opportunity resolved WIN/LOSS
      case 'opportunity_resolved':
        setActiveOpportunities(prev =>
          prev.filter(
            o => o.id !== payload.opportunity_id
          )
        );
        break;

      // Opportunity expired
      case 'opportunity_expired':
        setActiveOpportunities(prev =>
          prev.filter(
            o => o.id !== payload.opportunity_id
          )
        );
        break;

      // System status update
      case 'system_status':
        setSystemStatus(payload.status || 'ONLINE');
        break;

      // Keep-alive pong
      case 'pong':
        break;

      // Keep-alive ping from server
      case 'ping':
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(
            JSON.stringify({ type: 'pong' })
          );
        }
        break;

      default:
        break;
    }
  }, []);

  // ─────────────────────────────────────
  // SEND MESSAGE TO SERVER
  // ─────────────────────────────────────

  const sendMessage = useCallback((message) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  }, []);

  const requestStateRefresh = useCallback(() => {
    sendMessage({ type: 'request_state' });
  }, [sendMessage]);

  // ─────────────────────────────────────
  // LIFECYCLE
  // ─────────────────────────────────────

  useEffect(() => {
    mountedRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      clearTimeout(reconnectTimerRef.current);
      clearInterval(pingTimerRef.current);
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  return {
    isConnected,
    isReconnecting,
    connectionError,
    systemStatus,
    activeOpportunities,
    signalState,
    lastScan,
    sendMessage,
    requestStateRefresh,
  };
};