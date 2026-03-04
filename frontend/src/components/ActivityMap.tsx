import { useEffect, useMemo } from "react";
import { MapContainer, TileLayer, Polyline, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { DataPoint, Photo } from "../types";

// Leaflet's default icon URLs break under Vite's asset bundling — fix manually
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

const cameraIcon = L.divIcon({
  html: `<div style="font-size:20px;line-height:1;cursor:pointer" title="Photo">📷</div>`,
  className: "",
  iconSize: [24, 24],
  iconAnchor: [12, 12],
});

interface Props {
  datapoints: DataPoint[];
  photos?: Photo[];
  highlightRange?: [number, number] | null;
}

/** Fits the map to the track bounds whenever coords change. */
function FitBounds({ coords }: { coords: [number, number][] }) {
  const map = useMap();
  useEffect(() => {
    if (coords.length >= 2) {
      map.fitBounds(coords as [number, number][], { padding: [32, 32] });
    }
  }, [coords, map]);
  return null;
}

/** Colours a polyline by a per-point value using a red→green scale. */
function ColouredTrack({
  segments,
}: {
  segments: { coords: [number, number][]; colour: string }[];
}) {
  return (
    <>
      {segments.map((seg, i) => (
        <Polyline key={i} positions={seg.coords} color={seg.colour} weight={3} />
      ))}
    </>
  );
}

/** Build coloured segments from speed data (green = fast, red = slow). */
function buildPaceSegments(
  datapoints: DataPoint[]
): { coords: [number, number][]; colour: string }[] {
  const withGps = datapoints.filter(
    (dp) => dp.lat !== null && dp.lon !== null && dp.speed_m_s !== null
  );
  if (withGps.length < 2) return [];

  const speeds = withGps.map((dp) => dp.speed_m_s!);
  const minSpeed = Math.min(...speeds);
  const maxSpeed = Math.max(...speeds);
  const range = maxSpeed - minSpeed || 1;

  const segments: { coords: [number, number][]; colour: string }[] = [];
  for (let i = 0; i < withGps.length - 1; i++) {
    const dp = withGps[i];
    const next = withGps[i + 1];
    const t = (dp.speed_m_s! - minSpeed) / range; // 0 = slow, 1 = fast
    // Interpolate red (#ef4444) → yellow (#eab308) → green (#22c55e)
    const r = t < 0.5 ? 239 : Math.round(239 - (t - 0.5) * 2 * (239 - 34));
    const g = t < 0.5 ? Math.round(t * 2 * 163) : Math.round(163 + (t - 0.5) * 2 * (197 - 163));
    const b = t < 0.5 ? 68 : Math.round(68 + (t - 0.5) * 2 * (94 - 68));
    segments.push({
      coords: [
        [dp.lat!, dp.lon!],
        [next.lat!, next.lon!],
      ],
      colour: `rgb(${r},${g},${b})`,
    });
  }
  return segments;
}

export default function ActivityMap({ datapoints, photos = [], highlightRange }: Props) {
  const coords: [number, number][] = useMemo(
    () =>
      datapoints
        .filter((dp) => dp.lat !== null && dp.lon !== null)
        .map((dp) => [dp.lat!, dp.lon!]),
    [datapoints]
  );

  const paceSegments = useMemo(() => buildPaceSegments(datapoints), [datapoints]);

  const highlighted: [number, number][] = useMemo(() => {
    if (!highlightRange) return [];
    const gps = datapoints.filter((dp) => dp.lat !== null && dp.lon !== null);
    return gps
      .slice(highlightRange[0], highlightRange[1])
      .map((dp) => [dp.lat!, dp.lon!]);
  }, [datapoints, highlightRange]);

  const gpsPhotos = useMemo(
    () => photos.filter((p) => p.lat !== null && p.lon !== null),
    [photos]
  );

  if (coords.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center bg-gray-100 rounded-lg text-gray-400">
        No GPS data available
      </div>
    );
  }

  return (
    <MapContainer
      center={coords[0]}
      zoom={13}
      style={{ height: 420, borderRadius: 8 }}
      className="z-0"
    >
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution='&copy; <a href="https://openstreetmap.org">OpenStreetMap</a>'
      />
      <FitBounds coords={coords} />

      {/* Pace-coloured track */}
      {paceSegments.length > 0 ? (
        <ColouredTrack segments={paceSegments} />
      ) : (
        <Polyline positions={coords} color="#3b82f6" weight={3} />
      )}

      {/* Brush-selected highlight */}
      {highlighted.length > 1 && (
        <Polyline positions={highlighted} color="#f97316" weight={6} opacity={0.8} />
      )}

      {/* GPS-tagged photo markers */}
      {gpsPhotos.map((photo) => (
        <Marker
          key={photo.id}
          position={[photo.lat!, photo.lon!]}
          icon={cameraIcon}
        >
          <Popup maxWidth={300}>
            <img
              src={photo.url}
              alt="Run photo"
              style={{ maxWidth: 280, maxHeight: 200, objectFit: "cover", borderRadius: 4 }}
            />
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}
