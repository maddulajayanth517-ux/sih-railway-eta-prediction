'use client';

import { useWebSocket } from '@/hooks/useWebSocket';
import { useDashboardStore } from '@/store/useDashboardStore';

export default function HomePage() {
  const { connectionStatus, isConnected } = useWebSocket({
    url: 'ws://localhost:8000/ws/train-stream',
  });

  const trains = Object.values(useDashboardStore((state) => state.trains));
  const aggregate = useDashboardStore((state) => state.aggregate);

  return (
    <main className="min-h-screen bg-slate-950 p-6 text-slate-100">
      <div className="mx-auto max-w-7xl space-y-6">
        <header className="flex items-center justify-between rounded-2xl border border-slate-800 bg-slate-900/80 p-5 shadow-2xl shadow-slate-950/50">
          <div>
            <p className="text-xs uppercase tracking-[0.24em] text-sky-300">Command Center</p>
            <h1 className="mt-2 text-3xl font-bold text-white">Station Master Dashboard</h1>
          </div>
          <div className="rounded-full border border-slate-700 bg-slate-800 px-4 py-2 text-sm text-slate-200">
            Status: <span className={isConnected ? 'text-emerald-400' : 'text-amber-400'}>{connectionStatus}</span>
          </div>
        </header>

        <section className="grid gap-4 md:grid-cols-4">
          <StatCard label="Total Trains" value={String(aggregate.totalTrains)} tone="sky" />
          <StatCard label="Delayed" value={String(aggregate.delayedTrains)} tone="amber" />
          <StatCard label="Avg Delay" value={`${aggregate.averageDelayMinutes.toFixed(1)} min`} tone="rose" />
          <StatCard label="Active Alerts" value={String(aggregate.activeAlerts)} tone="red" />
        </section>

        <section className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white">Live Fleet Overview</h2>
            <span className="text-sm text-slate-400">{trains.length} active train records</span>
          </div>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {trains.length === 0 ? (
              <div className="col-span-full rounded-xl border border-dashed border-slate-700 bg-slate-950/50 p-6 text-sm text-slate-400">
                Waiting for telemetry data from the live stream.
              </div>
            ) : (
              trains.map(({ telemetry, prediction }) => {
                const speed = telemetry?.current_speed ?? 0;
                const platformStatus = prediction?.has_platform_conflict ? 'Conflict' : 'Stable';

                return (
                  <div key={telemetry?.train_id ?? prediction?.train_id ?? 'unknown'} className="rounded-xl border border-slate-800 bg-slate-950/70 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-xs uppercase tracking-[0.2em] text-slate-400">{telemetry?.train_name ?? prediction?.train_id ?? 'Train'}</p>
                        <p className="mt-2 text-xl font-semibold text-white">{telemetry?.train_id ?? prediction?.train_id}</p>
                      </div>
                      <span className={`rounded-full border px-2 py-1 text-xs font-medium ${
                        speed >= 60
                          ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300'
                          : speed >= 10
                            ? 'border-yellow-500/40 bg-yellow-500/10 text-yellow-300'
                            : 'border-red-500/40 bg-red-500/10 text-red-300'
                      }`}
                      >
                        {speed} km/h
                      </span>
                    </div>

                    <div className="mt-4 grid grid-cols-2 gap-3 text-sm text-slate-300">
                      <div>
                        <p className="text-slate-500">From</p>
                        <p className="font-medium">{telemetry?.last_station_code ?? '--'}</p>
                      </div>
                      <div>
                        <p className="text-slate-500">Next</p>
                        <p className="font-medium">{telemetry?.next_station_code ?? prediction?.next_station_code ?? '--'}</p>
                      </div>
                      <div>
                        <p className="text-slate-500">ETA</p>
                        <p className="font-medium">{prediction?.predicted_eta ?? '--'}</p>
                      </div>
                      <div>
                        <p className="text-slate-500">Delay</p>
                        <p className="font-medium">{prediction?.predicted_delay_minutes ?? 0} min</p>
                      </div>
                    </div>

                    <div className="mt-4 flex items-center justify-between border-t border-slate-800 pt-3 text-xs text-slate-400">
                      <span>Platform {prediction?.assigned_platform ?? '--'}</span>
                      <span className={prediction?.has_platform_conflict ? 'text-red-400' : 'text-emerald-400'}>{platformStatus}</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </section>
      </div>
    </main>
  );
}

function StatCard({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: 'sky' | 'amber' | 'rose' | 'red';
}) {
  const tones = {
    sky: 'border-sky-500/30 bg-sky-500/10 text-sky-200',
    amber: 'border-amber-500/30 bg-amber-500/10 text-amber-200',
    rose: 'border-rose-500/30 bg-rose-500/10 text-rose-200',
    red: 'border-red-500/30 bg-red-500/10 text-red-200',
  };

  return (
    <div className={`rounded-2xl border p-4 ${tones[tone]}`}>
      <p className="text-xs uppercase tracking-[0.2em] text-slate-300">{label}</p>
      <p className="mt-3 text-2xl font-bold text-white">{value}</p>
    </div>
  );
}
