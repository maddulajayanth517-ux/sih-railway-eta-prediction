'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useDashboardStore } from '@/store/useDashboardStore';
import {
  ConnectionStatus,
  EtaPredictionPayload,
  LiveTelemetryPayload,
} from '@/types/dashboard';

interface UseWebSocketOptions {
  url: string;
  reconnectIntervalMs?: number;
  maxReconnectAttempts?: number;
  onTelemetry?: (payload: LiveTelemetryPayload) => void;
  onPrediction?: (payload: EtaPredictionPayload) => void;
  onError?: (error: Event | Error) => void;
}

export function useWebSocket({
  url,
  reconnectIntervalMs = 3000,
  maxReconnectAttempts = 10,
  onTelemetry,
  onPrediction,
  onError,
}: UseWebSocketOptions) {
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectCountRef = useRef(0);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('connecting');

  const setStatus = useCallback((status: ConnectionStatus) => {
    setConnectionStatus(status);
    useDashboardStore.getState().setConnectionStatus(status);
  }, []);

  const handleMessage = useCallback(
    (event: MessageEvent<string>) => {
      try {
        const raw = JSON.parse(event.data) as Partial<LiveTelemetryPayload & EtaPredictionPayload>;

        const isTelemetry = 'current_latitude' in raw && 'current_speed' in raw && 'train_name' in raw;
        const isPrediction = 'predicted_eta' in raw && 'predicted_delay_minutes' in raw && 'confidence_score' in raw;

        if (isTelemetry && raw.train_id && raw.train_name) {
          const telemetryPayload = raw as LiveTelemetryPayload;
          useDashboardStore.getState().upsertTelemetry(telemetryPayload);
          onTelemetry?.(telemetryPayload);
          return;
        }

        if (isPrediction && raw.train_id && raw.next_station_code) {
          const predictionPayload = raw as EtaPredictionPayload;
          useDashboardStore.getState().upsertPrediction(predictionPayload);
          onPrediction?.(predictionPayload);
          return;
        }
      } catch (error) {
        console.error('Failed to parse incoming socket message:', error);
        setStatus('error');
        onError?.(error instanceof Error ? error : new Error('Unable to parse WebSocket message'));
      }
    },
    [onError, onPrediction, onTelemetry, setStatus],
  );

  const connect = useCallback(() => {
    if (typeof window === 'undefined') {
      return;
    }

    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      const socket = new WebSocket(url);
      socketRef.current = socket;

      setStatus('connecting');

      socket.onopen = () => {
        reconnectCountRef.current = 0;
        setStatus('connected');
      };

      socket.onmessage = handleMessage;

      socket.onerror = (event) => {
        setStatus('error');
        onError?.(event);
      };

      socket.onclose = (event) => {
        const shouldReconnect = reconnectCountRef.current < maxReconnectAttempts;

        if (shouldReconnect) {
          reconnectCountRef.current += 1;
          setStatus('reconnecting');
          window.setTimeout(() => {
            connect();
          }, reconnectIntervalMs);
          return;
        }

        setStatus('disconnected');
      };
    } catch (error) {
      console.error('WebSocket connection failed:', error);
      setStatus('error');
      onError?.(error instanceof Error ? error : new Error('WebSocket connection failed'));
    }
  }, [handleMessage, maxReconnectAttempts, onError, reconnectIntervalMs, setStatus, url]);

  useEffect(() => {
    connect();

    return () => {
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, [connect]);

  return {
    connectionStatus,
    isConnected: connectionStatus === 'connected',
    reconnect: connect,
    socket: socketRef.current,
  };
}
