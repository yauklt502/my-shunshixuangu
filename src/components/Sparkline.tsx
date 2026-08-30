type SparklineProps = {
  points: number[];
  tone?: "up" | "down" | "flat" | "gold";
  className?: string;
};

export function Sparkline({ points, tone = "flat", className }: SparklineProps) {
  if (points.length < 2) {
    return <div className={`h-10 rounded bg-elev-2/80 ${className ?? ""}`} />;
  }
  const min = Math.min(...points);
  const max = Math.max(...points);
  const span = max - min || 1;
  const coords = points.map((value, index) => {
    const x = (index / (points.length - 1)) * 100;
    const y = 100 - ((value - min) / span) * 100;
    return `${x},${y}`;
  });
  const polyline = coords.join(" ");
  const area = `0,100 ${polyline} 100,100`;
  const stroke =
    tone === "up" ? "#ff4d57" : tone === "down" ? "#2ecf8f" : tone === "gold" ? "#e7b84c" : "#8b95a8";
  const fill =
    tone === "up"
      ? "rgba(255,77,87,0.16)"
      : tone === "down"
        ? "rgba(46,207,143,0.14)"
        : tone === "gold"
          ? "rgba(231,184,76,0.16)"
          : "rgba(139,149,168,0.12)";

  return (
    <svg
      viewBox="0 0 100 100"
      preserveAspectRatio="none"
      className={`h-10 w-full overflow-visible ${className ?? ""}`}
      aria-hidden
    >
      <polygon points={area} fill={fill} />
      <polyline
        points={polyline}
        fill="none"
        stroke={stroke}
        strokeWidth="2.2"
        vectorEffect="non-scaling-stroke"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}
