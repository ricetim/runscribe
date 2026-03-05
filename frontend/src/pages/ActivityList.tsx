import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { getActivities, uploadFit } from "../api/client";
import { Activity } from "../types";
import { useUnits } from "../contexts/UnitsContext";
import RouteThumbnail from "../components/RouteThumbnail";
import RpeBadge from "../components/RpeBadge";

function formatDuration(s: number): string {
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    weekday: "short", month: "short", day: "numeric", year: "numeric",
  });
}

function formatWorkoutName(sportType: string, plannedWorkoutType?: string | null, name?: string | null): string {
  if (name) return name;
  if (plannedWorkoutType) return plannedWorkoutType;
  return sportType
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export default function ActivityList() {
  const qc = useQueryClient();
  const { fmtDist, fmtPace } = useUnits();
  const { data: activities = [], isLoading } = useQuery<Activity[]>({
    queryKey: ["activities"],
    queryFn: getActivities,
  });

  const upload = useMutation({
    mutationFn: uploadFit,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["activities"] }),
  });

  return (
    <div className="p-4 max-w-4xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Activities</h1>
        <label className="cursor-pointer bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium">
          {upload.isPending ? "Uploading…" : "Upload .fit"}
          <input
            type="file"
            accept=".fit"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) upload.mutate(f);
              e.target.value = "";
            }}
          />
        </label>
      </div>

      {upload.isError && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
          Upload failed — make sure the file is a valid .fit file.
        </div>
      )}

      {isLoading && <p className="text-gray-500">Loading…</p>}

      {!isLoading && activities.length === 0 && (
        <div className="text-center py-16 text-gray-400">
          <p className="text-lg">No activities yet.</p>
          <p className="text-sm mt-1">Upload a .fit file to get started.</p>
        </div>
      )}

      <ul className="space-y-3">
        {activities.map((a) => (
          <li key={a.id}>
            <Link
              to={`/activities/${a.id}`}
              className="flex items-center gap-4 p-3 bg-white rounded-xl border border-gray-200 hover:border-blue-400 hover:shadow-sm transition-all"
            >
              {/* Route thumbnail */}
              <RouteThumbnail track={a.track} width={112} height={84} />

              {/* Main info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="text-xs text-gray-400">{formatDate(a.started_at)}</span>
                  {a.rpe != null && a.rpe > 0 && <RpeBadge rpe={a.rpe} />}
                </div>
                <div className="text-base font-semibold text-gray-900 mb-0.5">
                  {formatWorkoutName(a.sport_type, a.planned_workout_type, a.name)}
                </div>
                {a.notes && (
                  <p className="text-xs text-gray-400 truncate leading-relaxed">
                    {a.notes.length > 120 ? a.notes.slice(0, 120) + "…" : a.notes}
                  </p>
                )}
              </div>

              {/* Stats */}
              <div className="flex gap-4 text-sm text-right flex-shrink-0">
                <div>
                  <div className="font-semibold text-gray-900">{fmtDist(a.distance_m)}</div>
                  <div className="text-xs text-gray-400">dist</div>
                </div>
                <div>
                  <div className="font-semibold text-gray-900">{formatDuration(a.duration_s)}</div>
                  <div className="text-xs text-gray-400">time</div>
                </div>
                <div>
                  <div className="font-semibold text-gray-900">{fmtPace(a.avg_pace_s_per_km)}</div>
                  <div className="text-xs text-gray-400">pace</div>
                </div>
                {a.avg_hr && (
                  <div>
                    <div className="font-semibold text-gray-900">{a.avg_hr}</div>
                    <div className="text-xs text-gray-400">bpm</div>
                  </div>
                )}
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
