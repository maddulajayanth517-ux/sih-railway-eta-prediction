import { create } from "zustand";
import { DashboardAggregate, DashboardTrainState, EtaPredictionPayload, LiveTelemetryPayload } from "@/types/dashboard";

interface DashboardState {
  trains: Record<string, DashboardTrainState>;
  aggregate: DashboardAggregate;
  connectionStatus: "connecting" | "connected" | "reconnecting" | "disconnected" | "error";
  isHydrated: boolean;
  setConnectionStatus: (status: DashboardState["connectionStatus"]) => void;
  upsertTelemetry: (payload: LiveTelemetryPayload) => void;
  upsertPrediction: (payload: EtaPredictionPayload) => void;
  syncAggregate: () => void;
  reset: () => void;
}

const initialAggregate: DashboardAggregate = {
  totalTrains: 0,
  delayedTrains: 0,
  averageDelayMinutes: 0,
  activeAlerts: 0,
};

const initialState = {
  trains: {},
  aggregate: initialAggregate,
  connectionStatus: "connecting" as const,
  isHydrated: false,
};

export const useDashboardStore = create<DashboardState>((set, get) => ({
  ...initialState,
  setConnectionStatus: (status) => set({ connectionStatus: status, isHydrated: true }),
  upsertTelemetry: (payload) => {
    const existing = get().trains[payload.train_id] ?? {
      telemetry: null,
      prediction: null,
      lastUpdated: null,
    };

    set({
      trains: {
        ...get().trains,
        [payload.train_id]: {
          ...existing,
          telemetry: payload,
          lastUpdated: payload.timestamp,
        },
      },
    });

    get().syncAggregate();
  },
  upsertPrediction: (payload) => {
    const existing = get().trains[payload.train_id] ?? {
      telemetry: null,
      prediction: null,
      lastUpdated: null,
    };

    set({
      trains: {
        ...get().trains,
        [payload.train_id]: {
          ...existing,
          prediction: payload,
          lastUpdated: new Date().toISOString(),
        },
      },
    });

    get().syncAggregate();
  },
  syncAggregate: () => {
    const trains = Object.values(get().trains);
    const totalTrains = trains.length;
    const delayedTrains = trains.filter(
      ({ prediction }) => prediction !== null && prediction.predicted_delay_minutes > 0,
    ).length;
    const averageDelayMinutes =
      trains.reduce((sum, { prediction }) => {
        if (prediction === null) {
          return sum;
        }

        return sum + prediction.predicted_delay_minutes;
      }, 0) / (delayedTrains || 1);

    const activeAlerts = trains.filter(
      ({ telemetry, prediction }) => {
        if (!telemetry || !prediction) {
          return false;
        }

        return telemetry.current_speed < 10 || prediction.has_platform_conflict;
      },
    ).length;

    set({
      aggregate: {
        totalTrains,
        delayedTrains,
        averageDelayMinutes: Number.isFinite(averageDelayMinutes) ? averageDelayMinutes : 0,
        activeAlerts,
      },
    });
  },
  reset: () => set({ ...initialState }),
}));
