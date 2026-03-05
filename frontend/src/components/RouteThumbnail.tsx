interface Props {
  track?: [number, number][];
  width?: number;
  height?: number;
}

export default function RouteThumbnail({ track, width = 112, height = 84 }: Props) {
  if (!track || track.length < 2) {
    return (
      <div
        style={{ width, height, flexShrink: 0 }}
        className="bg-gray-100 rounded-lg flex items-center justify-center text-gray-300 text-xs"
      >
        no GPS
      </div>
    );
  }

  const lats = track.map(([lat]) => lat);
  const lons = track.map(([, lon]) => lon);
  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const minLon = Math.min(...lons);
  const maxLon = Math.max(...lons);

  const pad = 6;
  const vw = width - pad * 2;
  const vh = height - pad * 2;

  const latRange = maxLat - minLat || 1e-6;
  const lonRange = maxLon - minLon || 1e-6;

  // Correct for longitude compression at the given latitude
  const midLat = (minLat + maxLat) / 2;
  const lonRangeCorrected = lonRange * Math.cos((midLat * Math.PI) / 180);

  const scale = Math.min(vw / lonRangeCorrected, vh / latRange);
  const scaledW = lonRangeCorrected * scale;
  const scaledH = latRange * scale;
  const xOffset = pad + (vw - scaledW) / 2;
  const yOffset = pad + (vh - scaledH) / 2;

  const toX = (lon: number) => xOffset + (lon - minLon) * Math.cos((midLat * Math.PI) / 180) * scale;
  const toY = (lat: number) => yOffset + scaledH - (lat - minLat) * scale;

  const points = track.map(([lat, lon]) => `${toX(lon).toFixed(1)},${toY(lat).toFixed(1)}`).join(" ");

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      style={{ flexShrink: 0 }}
      className="rounded-lg bg-gray-50 border border-gray-100"
    >
      <polyline
        points={points}
        fill="none"
        stroke="#f97316"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity="0.85"
      />
    </svg>
  );
}
