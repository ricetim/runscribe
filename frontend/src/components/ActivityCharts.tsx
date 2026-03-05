import { useMemo, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Brush,
  CartesianGrid,
  Legend,
} from "recharts";
import { DataPoint } from "../types";
import { useUnits } from "../contexts/UnitsContext";

interface Props {
  datapoints: DataPoint[];
  onRangeChange?: (startIdx: number, endIdx: number) => void;
  onHoverIndex?: (idx: number | null) => void;
}

type Overlay = "pace" | "hr" | "elevation" | "cadence" | "power";

const OVERLAYS: { key: Overlay; label: string; colour: string }[] = [
  { key: "pace", label: "Pace", colour: "#3b82f6" },
  { key: "hr", label: "Heart Rate", colour: "#ef4444" },
  { key: "elevation", label: "Elevation", colour: "#10b981" },
  { key: "cadence", label: "Cadence", colour: "#f59e0b" },
  { key: "power", label: "Power", colour: "#8b5cf6" },
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
}

export default function ActivityCharts({ datapoints, onRangeChange, onHoverIndex }: Props) {
  const { fmtPace, fmtElev } = useUnits();
  const [activeOverlays, setActiveOverlays] = useState<Set<Overlay>>(
    new Set(["pace", "hr", "elevation"])
  );

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
      return {
        idx,
        elapsed_s,
        pace,
        hr: dp.heart_rate ?? null,
        elevation: dp.altitude_m ?? null,
        cadence: dp.cadence ?? null,
        power: dp.power_w ?? null,
      };
    });
  }, [datapoints]);

  const hasPower = datapoints.some((dp) => dp.power_w !== null);

  function toggleOverlay(key: Overlay) {
    setActiveOverlays((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  if (!data.length) return null;

  const visibleOverlays = OVERLAYS.filter(
    (o) => activeOverlays.has(o.key) && (o.key !== "power" || hasPower)
  );

  // Build Y-axis assignments — pace gets its own left axis (reversed), rest share right
  const paceActive = activeOverlays.has("pace");

  const CustomTooltip = ({
    active,
    payload,
    label,
  }: {
    active?: boolean;
    payload?: any[];
    label?: number;
  }) => {
    if (!active || !payload?.length) return null;
    return (
      <div className="bg-white border border-gray-200 rounded shadow-lg p-3 text-sm">
        <div className="font-medium text-gray-500 mb-1">
          {formatElapsed(label ?? 0)}
        </div>
        {payload.map((p: any) => (
          <div key={p.dataKey} style={{ color: p.color }}>
            {p.name}:{" "}
            <span className="font-semibold">
              {p.dataKey === "pace"
                ? fmtPace(p.value)
                : p.dataKey === "elevation"
                ? fmtElev(p.value)
                : p.dataKey === "hr"
                ? `${p.value} bpm`
                : p.dataKey === "cadence"
                ? `${p.value} spm`
                : p.dataKey === "power"
                ? `${p.value} W`
                : p.value}
            </span>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="space-y-3">
      {/* Overlay toggles */}
      <div className="flex gap-2 flex-wrap">
        {OVERLAYS.filter((o) => o.key !== "power" || hasPower).map((o) => (
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
      </div>

      {/* Main chart */}
      <ResponsiveContainer width="100%" height={240}>
        <LineChart
          data={data}
          margin={{ top: 4, right: 16, left: 0, bottom: 0 }}
          onMouseMove={(e: any) => onHoverIndex?.(e?.activeTooltipIndex ?? null)}
          onMouseLeave={() => onHoverIndex?.(null)}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            dataKey="elapsed_s"
            tickFormatter={formatElapsed}
            minTickGap={60}
            tick={{ fontSize: 11 }}
          />
          {/* Pace axis — reversed so faster pace (lower s/km) is higher */}
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
          {/* Secondary axis for HR, elevation, cadence, power */}
          <YAxis
            yAxisId="right"
            orientation="right"
            domain={["auto", "auto"]}
            tick={{ fontSize: 10 }}
            width={40}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend wrapperStyle={{ fontSize: 12 }} />

          {visibleOverlays.map((o) => (
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
          ))}

          <Brush
            dataKey="elapsed_s"
            height={22}
            stroke="#94a3b8"
            tickFormatter={formatElapsed}
            onChange={(e: any) => {
              if (
                e.startIndex !== undefined &&
                e.endIndex !== undefined
              ) {
                onRangeChange?.(e.startIndex, e.endIndex);
              }
            }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
