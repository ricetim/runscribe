import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { getActivities, uploadFit } from "../api/client";
import { Activity } from "../types";
import { useUnits } from "../contexts/UnitsContext";

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

      <ul className="space-y-2">
        {activities.map((a) => (
          <li key={a.id}>
            <Link
              to={`/activities/${a.id}`}
              className="flex items-center justify-between p-4 bg-white rounded-lg border border-gray-200 hover:border-blue-400 hover:shadow-sm transition-all"
            >
              <div>
                <div className="font-medium text-gray-900">{formatDate(a.started_at)}</div>
                <div className="text-sm text-gray-500 capitalize">{a.sport_type.replace("_", " ")}</div>
              </div>
              <div className="flex gap-6 text-sm text-gray-600 text-right">
                <div>
                  <div className="font-semibold text-gray-900">{fmtDist(a.distance_m)}</div>
                  <div className="text-xs text-gray-400">distance</div>
                </div>
                <div>
                  <div className="font-semibold text-gray-900">{formatDuration(a.duration_s)}</div>
                  <div className="text-xs text-gray-400">time</div>
                </div>
                <div>
                  <div className="font-semibold text-gray-900">{fmtPace(a.avg_pace_s_per_km)}</div>
                  <div className="text-xs text-gray-400">avg pace</div>
                </div>
                {a.avg_hr && (
                  <div>
                    <div className="font-semibold text-gray-900">{a.avg_hr} bpm</div>
                    <div className="text-xs text-gray-400">avg HR</div>
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
