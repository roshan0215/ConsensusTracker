import { useEffect, useState } from "react";
import Layout from "../components/Layout";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const userId = typeof window !== "undefined" ? new URLSearchParams(window.location.search).get("user_id") : null;

  const load = async () => {
    if (!userId) return;
    setError(null);
    const res = await fetch(`${API_BASE}/api/dashboard?user_id=${encodeURIComponent(userId)}`);
    if (!res.ok) throw new Error(await res.text());
    setData(await res.json());
  };

  useEffect(() => {
    load().catch((e) => setError(String(e.message || e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  const manualCheck = async () => {
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/manual-check`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId }),
      });
      if (!res.ok) throw new Error(await res.text());
      await load();
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Layout title="ConsensusTracker — Dashboard">
      {!userId ? <div className="text-sm">Missing user_id.</div> : null}
      {error ? <div className="mb-4 p-3 border rounded bg-red-50 text-red-700 text-sm">{error}</div> : null}

      <div className="flex items-center justify-between mb-4">
        <button className="px-4 py-2 rounded bg-black text-white disabled:opacity-50" onClick={manualCheck} disabled={busy || !userId}>
          {busy ? "Checking..." : "Manual Check Now"}
        </button>
        <button className="px-3 py-2 border rounded" onClick={() => load().catch((e) => setError(String(e.message || e)))}>
          Refresh
        </button>
      </div>

      {!data ? <div className="text-sm">Loading...</div> : null}

      {data ? (
        <div className="space-y-6">
          <section>
            <h2 className="text-lg font-medium mb-2">Profile</h2>
            <div className="text-sm">
              <div><b>Topic:</b> {data.profile?.topic || "—"}</div>
              <div><b>Keywords:</b> {(data.profile?.keywords || []).join(", ") || "—"}</div>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-medium mb-2">Findings</h2>
            <div className="space-y-3">
              {(data.findings || []).length === 0 ? (
                <div className="text-sm">No findings yet.</div>
              ) : (
                data.findings.map((f) => (
                  <div key={f.id} className="border rounded p-3">
                    <div className="font-medium">{f.paper_title}</div>
                    <div className="text-xs text-gray-600">{f.severity || ""} {f.contradiction_type ? `• ${f.contradiction_type}` : ""}</div>
                    {f.explanation ? <div className="text-sm mt-2">{f.explanation}</div> : null}
                    {f.suggested_update ? (
                      <div className="text-sm mt-2">
                        <div className="font-medium">Suggested update</div>
                        <div className="whitespace-pre-wrap">{f.suggested_update}</div>
                      </div>
                    ) : null}
                  </div>
                ))
              )}
            </div>
          </section>
        </div>
      ) : null}
    </Layout>
  );
}
