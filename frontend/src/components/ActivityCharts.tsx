import { useMemo, useState } from "react";
import {
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
  ReferenceArea,
} from "recharts";
import { DataPoint } from "../types";
import { useUnits } from "../contexts/UnitsContext";

interface Props {
  datapoints: DataPoint[];
  onRangeChange?: (startIdx: number, endIdx: number) => void;
  onRangeClear?: () => void;
  onHoverIndex?: (idx: number | null) => void;
}

type Overlay =
  | "pace" | "hr" | "elevation" | "cadence" | "power"
  | "vert_osc" | "stride_length" | "vert_ratio" | "gct" | "flight_time";

const OVERLAYS: { key: Overlay; label: string; colour: string }[] = [
  { key: "pace",          label: "Pace",          colour: "#3b82f6" },
  { key: "hr",            label: "Heart Rate",    colour: "#ef4444" },
  { key: "elevation",     label: "Elevation",     colour: "#94a3b8" },
  { key: "cadence",       label: "Cadence",       colour: "#f59e0b" },
  { key: "power",         label: "Power",         colour: "#8b5cf6" },
  { key: "vert_osc",      label: "Vert. Osc.",    colour: "#06b6d4" },
  { key: "stride_length", label: "Stride Length", colour: "#d946ef" },
  { key: "vert_ratio",    label: "Vert. Ratio",   colour: "#ec4899" },
  { key: "gct",           label: "Ground Contact",colour: "#f97316" },
  { key: "flight_time",   label: "Flight Time",   colour: "#84cc16" },
];

function formatElapsed(totalSeconds: number): string {
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = totalSeconds % 60;
  if (h > 0) return `${h}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

interface ChartRow {
  idx: number;
  elapsed_s: number;
  pace: number | null;
  hr: number | null;
  elevation: number | null;
  cadence: number | null;
  power: number | null;
  vert_osc: number | null;
  stride_length: number | null; // stored as cm for display
  vert_ratio: number | null;
  gct: number | null;
  flight_time: number | null;
}

export default function ActivityCharts({ datapoints, onRangeChange, onRangeClear, onHoverIndex }: Props) {
  const { fmtPace, fmtElev } = useUnits();
  const [activeOverlays, setActiveOverlays] = useState<Set<Overlay>>(
    new Set(["pace", "hr", "elevation"])
  );
  const [zoomedRange, setZoomedRange] = useState<[number, number] | null>(null);
  const [dragStart, setDragStart] = useState<number | null>(null);
  const [dragEnd, setDragEnd] = useState<number | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const data: ChartRow[] = useMemo(() => {
    if (!datapoints.length) return [];
    const t0 = new Date(datapoints[0].timestamp).getTime();
    return datapoints.map((dp, idx) => {
      const elapsed_s = Math.round(
        (new Date(dp.timestamp).getTime() - t0) / 1000
      );
      const pace =
        dp.speed_m_s && dp.speed_m_s > 0.5
          ? Math.round((1000 / dp.speed_m_s) * 10) / 10
          : null;
      // Derive flight time: step_period - ground_contact_time
      const flight_time =
        dp.cadence && dp.cadence > 0 && dp.stance_time_ms != null
          ? Math.max(0, Math.round(60000 / dp.cadence - dp.stance_time_ms))
          : null;
      return {
        idx,
        elapsed_s,
        pace,
        hr: dp.heart_rate ?? null,
        elevation: dp.altitude_m ?? null,
        cadence: dp.cadence ?? null,
        power: dp.power_w ?? null,
        vert_osc: dp.vertical_oscillation_mm ?? null,
        stride_length: dp.stride_length_m != null ? Math.round(dp.stride_length_m * 100) : null,
        vert_ratio: dp.vertical_ratio ?? null,
        gct: dp.stance_time_ms ?? null,
        flight_time,
      };
    });
  }, [datapoints]);

  const offset = zoomedRange?.[0] ?? 0;
  const displayData = zoomedRange ? data.slice(zoomedRange[0], zoomedRange[1] + 1) : data;

  const hasPower = datapoints.some((dp) => dp.power_w !== null);
  const hasDynamics = datapoints.some(
    (dp) => dp.vertical_oscillation_mm != null || dp.stance_time_ms != null
  );

  function toggleOverlay(key: Overlay) {
    setActiveOverlays((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  function zoomOut() {
    setZoomedRange(null);
    onRangeClear?.();
  }

  function commitZoom() {
    if (dragStart === null || dragEnd === null) return;
    const left = Math.min(dragStart, dragEnd);
    const right = Math.max(dragStart, dragEnd);
    if (left === right) return;

    let startIdx = 0;
    let endIdx = displayData.length - 1;
    for (let i = 0; i < displayData.length; i++) {
      if (displayData[i].elapsed_s >= left) { startIdx = i; break; }
    }
    for (let i = displayData.length - 1; i >= 0; i--) {
      if (displayData[i].elapsed_s <= right) { endIdx = i; break; }
    }
    if (endIdx <= startIdx) return;

    const absStart = offset + startIdx;
    const absEnd = offset + endIdx;
    setZoomedRange([absStart, absEnd]);
    onRangeChange?.(absStart, absEnd);
  }

  if (!data.length) return null;

  const visibleOverlays = OVERLAYS.filter((o) => {
    if (!activeOverlays.has(o.key)) return false;
    if (o.key === "power" && !hasPower) return false;
    if (["vert_osc", "stride_length", "vert_ratio", "gct", "flight_time"].includes(o.key) && !hasDynamics) return false;
    return true;
  });
  const paceActive = activeOverlays.has("pace");

  const refLeft  = dragStart !== null && dragEnd !== null ? Math.min(dragStart, dragEnd) : null;
  const refRight = dragStart !== null && dragEnd !== null ? Math.max(dragStart, dragEnd) : null;

  // Which overlays to show in the toggle bar (hide power/dynamics if no data)
  const availableOverlays = OVERLAYS.filter((o) => {
    if (o.key === "power" && !hasPower) return false;
    if (["vert_osc", "stride_length", "vert_ratio", "gct", "flight_time"].includes(o.key) && !hasDynamics) return false;
    return true;
  });

  const tooltipUnit: Record<string, (v: number) => string> = {
    pace:          (v) => fmtPace(v),
    elevation:     (v) => fmtElev(v),
    hr:            (v) => `${v} bpm`,
    cadence:       (v) => `${v} spm`,
    power:         (v) => `${v} W`,
    vert_osc:      (v) => `${v.toFixed(1)} mm`,
    stride_length: (v) => `${v} cm`,
    vert_ratio:    (v) => `${v.toFixed(1)} %`,
    gct:           (v) => `${v.toFixed(0)} ms`,
    flight_time:   (v) => `${v.toFixed(0)} ms`,
  };

  const CustomTooltip = ({
    active, payload, label,
  }: { active?: boolean; payload?: any[]; label?: number }) => {
    if (!active || !payload?.length || isDragging) return null;
    return (
      <div className="bg-white border border-gray-200 rounded shadow-lg p-3 text-sm">
        <div className="font-medium text-gray-500 mb-1">{formatElapsed(label ?? 0)}</div>
        {payload.map((p: any) => (
          <div key={p.dataKey} style={{ color: p.color }}>
            {p.name}:{" "}
            <span className="font-semibold">
              {tooltipUnit[p.dataKey]?.(p.value) ?? p.value}
            </span>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="space-y-3">
      {/* Toolbar */}
      <div className="flex items-center gap-2 flex-wrap">
        {availableOverlays.map((o) => (
          <button
            key={o.key}
            onClick={() => toggleOverlay(o.key)}
            className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
              activeOverlays.has(o.key)
                ? "text-white border-transparent"
                : "bg-white text-gray-600 border-gray-300 hover:border-gray-400"
            }`}
            style={
              activeOverlays.has(o.key)
                ? { backgroundColor: o.colour, borderColor: o.colour }
                : {}
            }
          >
            {o.label}
          </button>
        ))}

        {zoomedRange && (
          <button
            onClick={zoomOut}
            className="ml-auto px-2.5 py-1 text-xs rounded border bg-gray-50 text-gray-600 border-gray-300 hover:bg-gray-100"
          >
            Reset zoom
          </button>
        )}
      </div>

      {/* Main chart — drag to zoom */}
      <ResponsiveContainer width="100%" height={260}>
        <ComposedChart
          data={displayData}
          margin={{ top: 4, right: 16, left: 0, bottom: 0 }}
          style={{ cursor: isDragging ? "col-resize" : "crosshair" }}
          onMouseDown={(e: any) => {
            const label = e?.activeLabel;
            if (label == null) return;
            setDragStart(label);
            setDragEnd(label);
            setIsDragging(true);
          }}
          onMouseMove={(e: any) => {
            const label = e?.activeLabel;
            const idx   = e?.activeTooltipIndex;
            if (!isDragging) {
              onHoverIndex?.(idx != null ? offset + idx : null);
            } else if (label != null) {
              setDragEnd(label);
            }
          }}
          onMouseUp={() => {
            if (isDragging) {
              commitZoom();
              setDragStart(null);
              setDragEnd(null);
              setIsDragging(false);
            }
          }}
          onMouseLeave={() => {
            onHoverIndex?.(null);
            if (isDragging) {
              setDragStart(null);
              setDragEnd(null);
              setIsDragging(false);
            }
          }}
        >
          <defs>
            <linearGradient id="elevGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#94a3b8" stopOpacity={0.5} />
              <stop offset="95%" stopColor="#94a3b8" stopOpacity={0.05} />
            </linearGradient>
          </defs>

          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            dataKey="elapsed_s"
            tickFormatter={formatElapsed}
            minTickGap={60}
            tick={{ fontSize: 11 }}
            allowDataOverflow
          />
          {paceActive && (
            <YAxis
              yAxisId="pace"
              orientation="left"
              reversed
              domain={["auto", "auto"]}
              tickFormatter={(v) => fmtPace(v)}
              tick={{ fontSize: 10 }}
              width={52}
            />
          )}
          <YAxis
            yAxisId="right"
            orientation="right"
            domain={["auto", "auto"]}
            tick={{ fontSize: 10 }}
            width={40}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend wrapperStyle={{ fontSize: 12 }} />

          {visibleOverlays.map((o) =>
            o.key === "elevation" ? (
              <Area
                key={o.key}
                yAxisId="right"
                type="monotone"
                dataKey="elevation"
                stroke="#94a3b8"
                fill="url(#elevGradient)"
                strokeWidth={1.5}
                name="Elevation"
                dot={false}
                connectNulls={false}
                isAnimationActive={false}
              />
            ) : (
              <Line
                key={o.key}
                yAxisId={o.key === "pace" ? "pace" : "right"}
                type="monotone"
                dataKey={o.key}
                dot={false}
                stroke={o.colour}
                strokeWidth={1.5}
                name={o.label}
                connectNulls={false}
                isAnimationActive={false}
              />
            )
          )}

          {isDragging && refLeft !== null && refRight !== null && refLeft !== refRight && (
            <ReferenceArea
              yAxisId="right"
              x1={refLeft}
              x2={refRight}
              fill="#3b82f6"
              fillOpacity={0.15}
              stroke="#3b82f6"
              strokeOpacity={0.4}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
