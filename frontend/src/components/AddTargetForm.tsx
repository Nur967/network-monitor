import { useState } from "react";
import { createTarget } from "../services/api";

export default function AddTargetForm({ onCreated }: { onCreated?: () => void }) {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e?: React.FormEvent) => {
    e?.preventDefault();
    setError(null);
    if (!url.trim()) {
      setError("URL is required");
      return;
    }
    setLoading(true);
    try {
      await createTarget(url.trim());
      setUrl("");
      onCreated && onCreated();
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || "Failed to add target");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={submit} className="row">
      <input
        aria-label="target-url"
        placeholder="https://example.com"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        style={{ flex: 1, padding: "8px 10px", borderRadius: 8, border: "1px solid rgba(255,255,255,0.06)", background: "transparent", color: "#e6eef8" }}
      />
      <button className="btn" disabled={loading} type="submit">
        {loading ? "Adding..." : "Add Monitor"}
      </button>
      {error && <div style={{ color: "#ffb4b4", marginTop: 8 }}>{error}</div>}
    </form>
  );
}
