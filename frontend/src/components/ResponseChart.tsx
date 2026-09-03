import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { CheckRecord } from "../types";

export default function ResponseChart({ data }: { data: CheckRecord[] }) {
  const processed = data
    .slice(-50)
    .map((d) => ({
      time: new Date(d.checked_at).toLocaleTimeString(),
      value: d.response_time_ms ?? null,
    }))
    .reverse();

  return (
    <div className="chart-wrapper" style={{ height: 160 }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={processed}>
          <XAxis dataKey="time" tick={{ fill: "#94a3b8" }} />
          <YAxis tick={{ fill: "#94a3b8" }} />
          <Tooltip />
          <Line type="monotone" dataKey="value" stroke="#67e8f9" dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
