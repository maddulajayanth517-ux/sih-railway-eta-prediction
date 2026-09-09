export type ConnectionStatus =
  | "connecting"
  | "connected"
  | "reconnecting"
  | "disconnected"
  | "error";

export type SpeedBand = "high" | "medium" | "low";

export interface LiveTelemetryPayload {
  train_id: string;
  train_name: string;
  current_latitude: number;
  current_longitude: number;
  current_speed: number;
  last_station_code: string;
  next_station_code: string;
  timestamp: string;
}

export interface EtaPredictionPayload {
  train_id: string;
  next_station_code: string;
  scheduled_arrival: string;
  predicted_eta: string;
  predicted_delay_minutes: number;
  confidence_score: number;
  delay_reasons: string[];
  assigned_platform: number;
  has_platform_conflict: boolean;
}

export interface ManualOverridePayload {
  station_code: string;
  train_id: string;
  new_platform_assignment: number;
  maintenance_block_active: boolean;
  blocked_section_id?: string;
  operator_notes: string;
}

export interface DashboardTrainState {
  telemetry: LiveTelemetryPayload | null;
  prediction: EtaPredictionPayload | null;
  lastUpdated: string | null;
}

export interface DashboardAggregate {
  totalTrains: number;
  delayedTrains: number;
  averageDelayMinutes: number;
  activeAlerts: number;
}

export function getSpeedBand(speed: number): SpeedBand {
  if (speed >= 60) {
    return "high";
  }

  if (speed >= 10) {
    return "medium";
  }

  return "low";
}

export function getSpeedTone(speed: number): string {
  const speedBand = getSpeedBand(speed);

  if (speedBand === "high") {
    return "text-emerald-400";
  }

  if (speedBand === "medium") {
    return "text-yellow-400";
  }

  return "text-red-400";
}

export function getDelaySeverity(minutes: number): "low" | "medium" | "high" {
  if (minutes >= 20) {
    return "high";
  }

  if (minutes >= 8) {
    return "medium";
  }

  return "low";
}

export function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);

  if (Number.isNaN(date.getTime())) {
    return "--:--";
  }

  return date.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}
