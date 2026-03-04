import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getPlan, getPlanWorkouts } from "../api/client";

interface Workout {
  id: number;
  scheduled_date: string;
  week_number: number;
  workout_type: string;
  description: string;
  target_distance_m: number | null;
  target_pace_s_per_km: number | null;
  completed_activity_id: number | null;
  status: string;
}

interface Plan {
  id: number;
  name: string;
  source: string;
  goal_distance: string;
  goal_race_date: string;
  start_date: string;
  target_vdot: number | null;
  peak_weekly_km: number | null;
}

const TYPE_COLORS: Record<string, string> = {
  easy:         "bg-green-100 text-green-800 border-green-200",
  recovery:     "bg-green-50 text-green-600 border-green-100",
  long:         "bg-blue-100 text-blue-800 border-blue-200",
  marathon_pace:"bg-purple-100 text-purple-800 border-purple-200",
  threshold:    "bg-yellow-100 text-yellow-800 border-yellow-200",
  interval:     "bg-orange-100 text-orange-800 border-orange-200",
  repetition:   "bg-red-100 text-red-800 border-red-200",
  rest:         "bg-gray-50 text-gray-400 border-gray-100",
};

const STATUS_RING: Record<string, string> = {
  completed: "ring-2 ring-green-400",
  missed:    "ring-2 ring-red-300",
  today:     "ring-2 ring-blue-500",
  future:    "",
  rest:      "",
};

function fmtPace(s: number): string {
  const m = Math.floor(s / 60);
  const sec = Math.round(s % 60);
  return `${m}:${sec.toString().padStart(2, "0")} /km`;
}

function fmtDist(m: number): string {
  return (m / 1000).toFixed(1) + " km";
}

function WorkoutCell({ w }: { w: Workout }) {
  const colorClass = TYPE_COLORS[w.workout_type] ?? "bg-gray-100 text-gray-600 border-gray-200";
  const ringClass = STATUS_RING[w.status] ?? "";
  const dayLabel = new Date(w.scheduled_date).toLocaleDateString("en-GB", { weekday: "short", day: "numeric" });

  return (
    <div className={`border rounded-lg p-2 text-xs ${colorClass} ${ringClass} relative`}>
      <div className="font-medium text-[10px] mb-0.5 opacity-60">{dayLabel}</div>
      <div className="font-semibold capitalize leading-tight">
        {w.workout_type === "marathon_pace" ? "MP" : w.workout_type}
      </div>
      {w.target_distance_m && (
        <div className="opacity-70 mt-0.5">{fmtDist(w.target_distance_m)}</div>
      )}
      {w.target_pace_s_per_km && (
        <div className="opacity-60 font-mono text-[9px]">{fmtPace(w.target_pace_s_per_km)}</div>
      )}
      {w.completed_activity_id && (
        <Link
          to={`/activities/${w.completed_activity_id}`}
          className="absolute top-1 right-1 w-2 h-2 bg-green-500 rounded-full"
          title="Completed"
        />
      )}
    </div>
  );
}

export default function PlanDetail() {
  const { id } = useParams<{ id: string }>();
  const planId = parseInt(id ?? "0");

  const { data: plan } = useQuery<Plan>({
    queryKey: ["plan", planId],
    queryFn: () => getPlan(planId),
  });

  const { data: workouts = [], isLoading } = useQuery<Workout[]>({
    queryKey: ["plan-workouts", planId],
    queryFn: () => getPlanWorkouts(planId),
  });

  if (isLoading || !plan) {
    return <div className="p-8 text-center text-gray-400">Loading plan…</div>;
  }

  // Group workouts by week
  const weeks: Record<number, Workout[]> = {};
  for (const w of workouts) {
    if (!weeks[w.week_number]) weeks[w.week_number] = [];
    weeks[w.week_number].push(w);
  }

  const completedCount = workouts.filter((w) => w.status === "completed").length;
  const totalWorkouts = workouts.filter((w) => w.workout_type !== "rest").length;

  return (
    <div className="p-4 max-w-5xl mx-auto space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <Link to="/plans" className="text-xs text-blue-600 hover:underline">← Plans</Link>
          <h1 className="text-xl font-bold text-gray-800 mt-1">{plan.name}</h1>
          <div className="text-sm text-gray-500 mt-0.5">
            {plan.source === "daniels" ? "Daniels" : "Pfitzinger"} ·{" "}
            {plan.goal_distance.toUpperCase()} · Race:{" "}
            {new Date(plan.goal_race_date).toLocaleDateString("en-GB", {
              weekday: "long", month: "long", day: "numeric", year: "numeric",
            })}
          </div>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-blue-600">{completedCount}/{totalWorkouts}</div>
          <div className="text-xs text-gray-400">workouts done</div>
        </div>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-2 text-xs">
        {[
          ["easy", "Easy"], ["long", "Long"], ["marathon_pace", "MP"],
          ["threshold", "Threshold"], ["interval", "Interval"], ["rest", "Rest"],
        ].map(([type, label]) => (
          <span key={type} className={`px-2 py-0.5 rounded border ${TYPE_COLORS[type]}`}>
            {label}
          </span>
        ))}
        <span className="px-2 py-0.5 rounded ring-2 ring-green-400 bg-white text-gray-500 border border-gray-200">
          Completed
        </span>
        <span className="px-2 py-0.5 rounded ring-2 ring-red-300 bg-white text-gray-500 border border-gray-200">
          Missed
        </span>
        <span className="px-2 py-0.5 rounded ring-2 ring-blue-500 bg-white text-gray-500 border border-gray-200">
          Today
        </span>
      </div>

      {/* Week grid */}
      <div className="space-y-2">
        {Object.entries(weeks).map(([weekNum, days]) => (
          <div key={weekNum}>
            <div className="text-xs font-semibold text-gray-400 mb-1">Week {weekNum}</div>
            <div className="grid grid-cols-7 gap-1">
              {days.map((w) => (
                <WorkoutCell key={w.id} w={w} />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
