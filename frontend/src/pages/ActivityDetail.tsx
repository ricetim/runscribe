import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getActivity, getDataPoints, getPhotos } from "../api/client";
import { Activity, DataPoint, Photo } from "../types";
import ActivityMap from "../components/ActivityMap";
import ActivityCharts from "../components/ActivityCharts";
import PhotoGallery from "../components/PhotoGallery";

function formatPace(s: number | null): string {
  if (!s) return "—";
  const m = Math.floor(s / 60);
  const sec = Math.round(s % 60).toString().padStart(2, "0");
  return `${m}:${sec} /km`;
}

function formatDuration(s: number): string {
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  if (h > 0) return `${h}:${m.toString().padStart(2, "0")}:${sec.toString().padStart(2, "0")}`;
  return `${m}:${sec.toString().padStart(2, "0")}`;
}

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
      <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">{label}</div>
      <div className="text-2xl font-bold text-gray-900">{value}</div>
      {sub && <div className="text-xs text-gray-400 mt-0.5">{sub}</div>}
    </div>
  );
}

/** Summary stats for the brush-selected range */
function RangeSummary({
  datapoints,
  range,
}: {
  datapoints: DataPoint[];
  range: [number, number];
}) {
  const slice = datapoints.slice(range[0], range[1] + 1);
  if (slice.length < 2) return null;

  const startDist = slice[0].distance_m ?? 0;
  const endDist = slice[slice.length - 1].distance_m ?? 0;
  const distKm = (endDist - startDist) / 1000;

  const t0 = new Date(slice[0].timestamp).getTime();
  const t1 = new Date(slice[slice.length - 1].timestamp).getTime();
  const durationS = Math.round((t1 - t0) / 1000);

  const speeds = slice.filter((d) => d.speed_m_s && d.speed_m_s > 0).map((d) => d.speed_m_s!);
  const avgPace = speeds.length ? 1000 / (speeds.reduce((a, b) => a + b, 0) / speeds.length) : null;

  const hrs = slice.filter((d) => d.heart_rate).map((d) => d.heart_rate!);
  const avgHr = hrs.length ? Math.round(hrs.reduce((a, b) => a + b, 0) / hrs.length) : null;

  return (
    <div className="bg-orange-50 border border-orange-200 rounded-lg p-3 text-sm">
      <span className="font-medium text-orange-700 mr-3">Selected range:</span>
      <span className="text-gray-700 mr-4">{distKm.toFixed(2)} km</span>
      <span className="text-gray-700 mr-4">{formatDuration(durationS)}</span>
      {avgPace && <span className="text-gray-700 mr-4">{formatPace(avgPace)}</span>}
      {avgHr && <span className="text-gray-700">{avgHr} bpm avg</span>}
    </div>
  );
}

export default function ActivityDetail() {
  const { id } = useParams<{ id: string }>();
  const actId = Number(id);
  const [brushRange, setBrushRange] = useState<[number, number] | null>(null);

  const { data: act, isLoading: actLoading } = useQuery<Activity>({
    queryKey: ["activity", actId],
    queryFn: () => getActivity(actId),
  });

  const { data: datapoints = [], isLoading: dpLoading } = useQuery<DataPoint[]>({
    queryKey: ["datapoints", actId],
    queryFn: () => getDataPoints(actId),
  });

  const { data: photos = [] } = useQuery<Photo[]>({
    queryKey: ["photos", actId],
    queryFn: () => getPhotos(actId),
  });

  if (actLoading) {
    return <div className="p-6 text-gray-500">Loading activity…</div>;
  }
  if (!act) {
    return (
      <div className="p-6 text-gray-500">
        Activity not found.{" "}
        <Link to="/activities" className="text-blue-600 hover:underline">
          Back to list
        </Link>
      </div>
    );
  }

  const startDate = new Date(act.started_at).toLocaleDateString(undefined, {
    weekday: "long", year: "numeric", month: "long", day: "numeric",
  });
  const startTime = new Date(act.started_at).toLocaleTimeString(undefined, {
    hour: "2-digit", minute: "2-digit",
  });

  return (
    <div className="p-4 max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <Link to="/activities" className="text-sm text-blue-600 hover:underline mb-1 block">
            ← Activities
          </Link>
          <h1 className="text-2xl font-bold text-gray-900 capitalize">
            {act.sport_type.replace("_", " ")}
          </h1>
          <p className="text-gray-500 text-sm">
            {startDate} at {startTime}
          </p>
        </div>
        <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded capitalize">
          {act.source.replace("_", " ")}
        </span>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatCard
          label="Distance"
          value={`${(act.distance_m / 1000).toFixed(2)} km`}
        />
        <StatCard
          label="Time"
          value={formatDuration(act.duration_s)}
        />
        <StatCard
          label="Avg Pace"
          value={formatPace(act.avg_pace_s_per_km)}
        />
        <StatCard
          label="Elevation"
          value={`${act.elevation_gain_m.toFixed(0)} m`}
          sub="gain"
        />
        {act.avg_hr && (
          <StatCard label="Avg HR" value={`${act.avg_hr}`} sub="bpm" />
        )}
      </div>

      {/* Map */}
      {dpLoading ? (
        <div className="h-64 bg-gray-100 rounded-lg flex items-center justify-center text-gray-400">
          Loading GPS data…
        </div>
      ) : (
        <ActivityMap
          datapoints={datapoints}
          photos={photos}
          highlightRange={brushRange}
        />
      )}

      {/* Range summary */}
      {brushRange && datapoints.length > 0 && (
        <RangeSummary datapoints={datapoints} range={brushRange} />
      )}

      {/* Charts */}
      {!dpLoading && datapoints.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <h2 className="text-lg font-semibold text-gray-800 mb-3">
            Analysis
            <span className="text-xs font-normal text-gray-400 ml-2">
              {datapoints.length.toLocaleString()} data points
            </span>
          </h2>
          <ActivityCharts
            datapoints={datapoints}
            onRangeChange={(start, end) => setBrushRange([start, end])}
          />
        </div>
      )}

      {/* Photos */}
      {photos.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <PhotoGallery photos={photos} />
        </div>
      )}

      {/* Notes */}
      {act.notes && (
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <h2 className="text-lg font-semibold text-gray-800 mb-2">Notes</h2>
          <p className="text-gray-700 whitespace-pre-wrap">{act.notes}</p>
        </div>
      )}
    </div>
  );
}
