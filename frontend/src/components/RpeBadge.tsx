const RPE_CONFIG: Record<number, { label: string; bg: string; text: string }> = {
  1: { label: "Very Easy", bg: "#dcfce7", text: "#166534" },
  2: { label: "Easy",      bg: "#bbf7d0", text: "#14532d" },
  3: { label: "Moderate",  bg: "#fef08a", text: "#713f12" },
  4: { label: "Hard",      bg: "#fed7aa", text: "#7c2d12" },
  5: { label: "Maximum",   bg: "#fecaca", text: "#7f1d1d" },
};

export default function RpeBadge({ rpe }: { rpe: number }) {
  const cfg = RPE_CONFIG[rpe];
  if (!cfg) return null;
  return (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
      style={{ backgroundColor: cfg.bg, color: cfg.text }}
      title={`RPE ${rpe}/5`}
    >
      {cfg.label}
    </span>
  );
}
