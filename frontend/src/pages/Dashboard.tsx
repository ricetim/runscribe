import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
  CartesianGrid,
  ReferenceLine,
} from "recharts";
import { getStatsSummary, getTrainingLoad, getVdot, getActivities } from "../api/client";
import type { Activity } from "../types";
import { useUnits } from "../contexts/UnitsContext";
import RouteThumbnail from "../components/RouteThumbnail";
import RpeBadge from "../components/RpeBadge";

// ── helpers ──────────────────────────────────────────────────────────────────

function fmtTime(s: number): string {
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${sec}s`;
  return `${sec}s`;
}

// ── stat card ─────────────────────────────────────────────────────────────────

function StatCard({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 flex flex-col gap-1 shadow-sm">
      <div className="text-xs text-gray-500 uppercase tracking-wide">{label}</div>
      <div className="text-2xl font-bold text-gray-800">{value}</div>
      {sub && <div className="text-xs text-gray-400">{sub}</div>}
    </div>
  );
}

// ── VDOT zone row ─────────────────────────────────────────────────────────────

function ZoneRow({
  label,
  pace,
  color,
}: {
  label: string;
  pace: string;
  color: string;
}) {
  return (
    <div className="flex items-center gap-3 py-1">
      <span className={`w-2 h-2 rounded-full ${color}`} />
      <span className="w-20 text-sm font-medium text-gray-700">{label}</span>
      <span className="text-sm text-gray-500 font-mono">{pace}</span>
    </div>
  );
}

// ── training load chart ───────────────────────────────────────────────────────

function TrainingLoadChart({ days }: { days: number }) {
  const { data, isLoading } = useQuery({
    queryKey: ["training-load", days],
    queryFn: () => getTrainingLoad(days),
  });

  if (isLoading) return <div className="h-48 flex items-center justify-center text-gray-400 text-sm">Loading…</div>;
  if (!data?.length) return <div className="h-48 flex items-center justify-center text-gray-400 text-sm">No training data</div>;

  // Show every N-th label to avoid clutter
  const step = days > 60 ? 14 : 7;

  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={data} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 10 }}
          interval={step - 1}
          tickFormatter={(v: string) => v.slice(5)} // MM-DD
        />
        <YAxis tick={{ fontSize: 10 }} />
        <Tooltip
          formatter={(v: unknown, name: string) => [(v as number)?.toFixed(1) ?? "–", name.toUpperCase()]}
          labelFormatter={(l) => `Date: ${l}`}
        />
        <Legend wrapperStyle={{ fontSize: 11 }} />
        <ReferenceLine y={0} stroke="#ccc" />
        <Line type="monotone" dataKey="ctl" name="CTL (fitness)" stroke="#3b82f6" dot={false} strokeWidth={2} />
        <Line type="monotone" dataKey="atl" name="ATL (fatigue)" stroke="#ef4444" dot={false} strokeWidth={1.5} strokeDasharray="4 2" />
        <Line type="monotone" dataKey="tsb" name="TSB (form)" stroke="#22c55e" dot={false} strokeWidth={1.5} />
      </LineChart>
    </ResponsiveContainer>
  );
}

// ── recent activity row ───────────────────────────────────────────────────────

function formatWorkoutName(sportType: string, plannedWorkoutType?: string | null): string {
  if (plannedWorkoutType) return plannedWorkoutType;
  return sportType.split("_").map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
}

function ActivityRow({ act }: { act: Activity }) {
  const { fmtDist, fmtPace } = useUnits();
  return (
    <Link
      to={`/activities/${act.id}`}
      className="flex items-center gap-3 p-3 rounded-xl border border-gray-200 hover:border-blue-400 hover:shadow-sm transition-all"
    >
      <RouteThumbnail track={act.track} width={96} height={72} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className="text-xs text-gray-400">
            {new Date(act.started_at).toLocaleDateString(undefined, {
              weekday: "short", month: "short", day: "numeric",
            })}
          </span>
          {act.rpe != null && act.rpe > 0 && <RpeBadge rpe={act.rpe} />}
        </div>
        <div className="text-sm font-semibold text-gray-900 mb-0.5">
          {formatWorkoutName(act.sport_type, act.planned_workout_type)}
        </div>
        {act.notes && (
          <p className="text-xs text-gray-400 truncate">
            {act.notes.length > 80 ? act.notes.slice(0, 80) + "…" : act.notes}
          </p>
        )}
      </div>
      <div className="flex gap-3 text-sm text-right flex-shrink-0">
        <div>
          <div className="font-semibold text-gray-900">{fmtDist(act.distance_m)}</div>
          <div className="text-xs text-gray-400">dist</div>
        </div>
        <div>
          <div className="font-semibold text-gray-900">{fmtTime(act.duration_s)}</div>
          <div className="text-xs text-gray-400">time</div>
        </div>
        <div>
          <div className="font-semibold text-gray-900">{fmtPace(act.avg_pace_s_per_km)}</div>
          <div className="text-xs text-gray-400">pace</div>
        </div>
      </div>
    </Link>
  );
}

// ── main Dashboard ────────────────────────────────────────────────────────────

const PERIODS = ["week", "month", "year", "all"] as const;
type Period = (typeof PERIODS)[number];

export default function Dashboard() {
  const [period, setPeriod] = useState<Period>("week");
  const [loadDays, setLoadDays] = useState(90);
  const { fmtDist, fmtPace, fmtElev } = useUnits();

  const { data: summary } = useQuery({
    queryKey: ["stats-summary", period],
    queryFn: () => getStatsSummary(period),
  });

  const { data: vdotData } = useQuery({
    queryKey: ["vdot"],
    queryFn: getVdot,
  });

  const { data: activities } = useQuery({
    queryKey: ["activities"],
    queryFn: getActivities,
  });

  const recentActs: Activity[] = activities ? activities.slice(0, 8) : [];

  const zones = vdotData?.pace_zones_s_per_km;

  return (
    <div className="p-4 max-w-5xl mx-auto space-y-6">

      {/* Period toggle */}
      <div className="flex items-center gap-2">
        {PERIODS.map((p) => (
          <button
            key={p}
            onClick={() => setPeriod(p)}
            className={`px-3 py-1 text-sm rounded-full border transition-colors ${
              period === p
                ? "bg-blue-600 text-white border-blue-600"
                : "bg-white text-gray-600 border-gray-300 hover:border-blue-400"
            }`}
          >
            {p.charAt(0).toUpperCase() + p.slice(1)}
          </button>
        ))}
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatCard
          label="Runs"
          value={summary?.count ?? "–"}
        />
        <StatCard
          label="Distance"
          value={summary ? fmtDist(summary.total_distance_km * 1000) : "–"}
        />
        <StatCard
          label="Time"
          value={summary ? fmtTime(summary.total_duration_s) : "–"}
        />
        <StatCard
          label="Avg pace"
          value={fmtPace(summary?.avg_pace_s_per_km ?? null)}
          sub={summary ? `${fmtElev(summary.total_elevation_m)} gain` : "–"}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* Training load chart */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-gray-700">Training Load (CTL / ATL / TSB)</h2>
            <div className="flex gap-1">
              {[30, 60, 90].map((d) => (
                <button
                  key={d}
                  onClick={() => setLoadDays(d)}
                  className={`px-2 py-0.5 text-xs rounded border ${
                    loadDays === d
                      ? "bg-blue-600 text-white border-blue-600"
                      : "text-gray-500 border-gray-300 hover:border-blue-400"
                  }`}
                >
                  {d}d
                </button>
              ))}
            </div>
          </div>
          <TrainingLoadChart days={loadDays} />
        </div>

        {/* VDOT + pace zones */}
        <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm space-y-4">
          <div>
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Current VDOT</div>
            <div className="text-3xl font-bold text-blue-600">
              {vdotData?.vdot ?? "–"}
            </div>
            {vdotData?.race_predictions_s && (
              <div className="mt-2 space-y-0.5">
                {Object.entries(vdotData.race_predictions_s).map(([dist, s]) => (
                  <div key={dist} className="flex justify-between text-xs text-gray-500">
                    <span className="uppercase">{dist}</span>
                    <span className="font-mono">{s ? fmtTime(s as number) : "–"}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {zones && (
            <div>
              <div className="text-xs text-gray-500 uppercase tracking-wide mb-2">Pace Zones</div>
              <ZoneRow label="Easy" pace={`${fmtPace(zones.easy_hi)} – ${fmtPace(zones.easy_lo)}`} color="bg-green-400" />
              <ZoneRow label="Marathon" pace={fmtPace(zones.marathon)} color="bg-blue-400" />
              <ZoneRow label="Threshold" pace={fmtPace(zones.threshold)} color="bg-yellow-400" />
              <ZoneRow label="Interval" pace={fmtPace(zones.interval)} color="bg-orange-400" />
              <ZoneRow label="Reps" pace={fmtPace(zones.repetition)} color="bg-red-500" />
            </div>
          )}
        </div>
      </div>

      {/* Recent activities */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-sm font-semibold text-gray-700">Recent Activities</h2>
          <Link to="/activities" className="text-xs text-blue-600 hover:underline">
            View all →
          </Link>
        </div>
        {recentActs.length === 0 ? (
          <div className="text-sm text-gray-400 py-4 text-center">
            No activities yet.{" "}
            <Link to="/activities" className="text-blue-600 hover:underline">
              Upload a .fit file
            </Link>
          </div>
        ) : (
          <div className="space-y-2">
            {recentActs.map((act) => (
              <ActivityRow key={act.id} act={act} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
