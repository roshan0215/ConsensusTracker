import { useMemo, useState } from "react";
import Layout from "../components/Layout";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export default function Onboarding() {
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState({
    email: "",
    googleDocUrl: "",
    reviewLastUpdated: "",
  });
  const [aiProfile, setAiProfile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const canAnalyze = useMemo(() => {
    return formData.googleDocUrl.length > 10;
  }, [formData.googleDocUrl]);

  const handleAnalyze = async () => {
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/extract-topic`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ google_doc_url: formData.googleDocUrl }),
      });
      if (!res.ok) throw new Error(await res.text());
      const profile = await res.json();
      setAiProfile({
        topic: profile.topic || "",
        keywords: profile.keywords || [],
        methodology: profile.methodology || "",
        key_questions: profile.key_questions || [],
      });
      setStep(2);
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setBusy(false);
    }
  };

  const handleStart = async () => {
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/onboard`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: formData.email,
          google_doc_url: formData.googleDocUrl,
          review_last_updated: formData.reviewLastUpdated || null,
          profile: aiProfile,
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      const out = await res.json();
      window.location.href = `/dashboard?user_id=${encodeURIComponent(out.user_id)}`;
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Layout title="ConsensusTracker — Onboarding">
      {error ? (
        <div className="mb-4 p-3 border rounded bg-red-50 text-red-700 text-sm">{error}</div>
      ) : null}

      {step === 1 ? (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium">Email</label>
            <input
              className="mt-1 w-full border rounded p-2"
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              placeholder="you@example.com"
            />
          </div>

          <div>
            <label className="block text-sm font-medium">Google Doc URL</label>
            <input
              className="mt-1 w-full border rounded p-2"
              type="url"
              value={formData.googleDocUrl}
              onChange={(e) => setFormData({ ...formData, googleDocUrl: e.target.value })}
              placeholder="https://docs.google.com/document/d/..."
            />
          </div>

          <div>
            <label className="block text-sm font-medium">Last updated (optional)</label>
            <input
              className="mt-1 w-full border rounded p-2"
              type="date"
              value={formData.reviewLastUpdated}
              onChange={(e) => setFormData({ ...formData, reviewLastUpdated: e.target.value })}
            />
          </div>

          <button
            className="px-4 py-2 rounded bg-black text-white disabled:opacity-50"
            onClick={handleAnalyze}
            disabled={!canAnalyze || busy}
          >
            {busy ? "Analyzing..." : "Analyze My Review"}
          </button>
        </div>
      ) : null}

      {step === 2 && aiProfile ? (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium">Research topic</label>
            <input
              className="mt-1 w-full border rounded p-2"
              value={aiProfile.topic}
              onChange={(e) => setAiProfile({ ...aiProfile, topic: e.target.value })}
            />
          </div>

          <div>
            <label className="block text-sm font-medium">Keywords</label>
            <div className="mt-2 space-y-2">
              {aiProfile.keywords.map((kw, i) => (
                <div key={i} className="flex gap-2">
                  <input
                    className="flex-1 border rounded p-2"
                    value={kw}
                    onChange={(e) => {
                      const next = [...aiProfile.keywords];
                      next[i] = e.target.value;
                      setAiProfile({ ...aiProfile, keywords: next });
                    }}
                  />
                  <button
                    className="px-3 py-2 border rounded"
                    onClick={() => {
                      const next = aiProfile.keywords.filter((_, idx) => idx !== i);
                      setAiProfile({ ...aiProfile, keywords: next });
                    }}
                    type="button"
                  >
                    Remove
                  </button>
                </div>
              ))}
              <button
                className="px-3 py-2 border rounded"
                type="button"
                onClick={() => setAiProfile({ ...aiProfile, keywords: [...aiProfile.keywords, ""] })}
              >
                Add keyword
              </button>
            </div>
          </div>

          <button
            className="px-4 py-2 rounded bg-black text-white disabled:opacity-50"
            onClick={handleStart}
            disabled={busy || !formData.email}
          >
            {busy ? "Starting..." : "Start Monitoring"}
          </button>
        </div>
      ) : null}
    </Layout>
  );
}
