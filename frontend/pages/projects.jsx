import { useEffect, useState } from "react";
import Layout from "../components/Layout";
import { apiFetch, setToken } from "../lib/api";

export default function Projects() {
  const [projects, setProjects] = useState([]);
  const [name, setName] = useState("");
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    const out = await apiFetch("/api/projects");
    setProjects(out || []);
  };

  useEffect(() => {
    // Handle return from Google OAuth connect flow
    const params = new URLSearchParams(window.location.search);
    if (params.get("google_connected") === "1") {
      const t = params.get("token");
      if (t) setToken(t);
      setNotice("Google account connected! You can now link any doc you have access to.");
      // Clean up the URL
      window.history.replaceState({}, "", "/projects");
    }
    load().catch((e) => {
      setError(String(e.message || e));
      if (String(e.message || e).toLowerCase().includes("not authenticated")) {
        window.location.href = "/signin";
      }
    });
  }, []);

  const create = async () => {
    setBusy(true);
    setError(null);
    try {
      const out = await apiFetch("/api/projects", { method: "POST", body: { name } });
      window.location.href = `/project?id=${encodeURIComponent(out.id)}`;
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Layout title="Projects" maxWidth="max-w-4xl">
      {notice ? <div className="alert-success mb-6">{notice}</div> : null}
      {error ? <div className="alert-error mb-6">{error}</div> : null}
      <div className="grid md:grid-cols-5 gap-6">

        {/* New project */}
        <div className="md:col-span-2">
          <div className="card p-6">
            <h2 className="section-title mb-4">New project</h2>
            <div className="space-y-3">
              <div>
                <label className="label">Project name</label>
                <input
                  className="input"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g., Alzheimer biomarker review"
                />
              </div>
              <button className="btn-primary w-full" disabled={busy || !name} onClick={create}>
                {busy ? "Creating..." : "Create project"}
              </button>
            </div>
            <p className="text-xs text-slate-500 mt-3 leading-relaxed">
              After creating, link your Google Doc to start monitoring.
            </p>
          </div>
        </div>

        {/* Existing projects */}
        <div className="md:col-span-3">
          <h2 className="section-title mb-4">Your projects</h2>
          {projects.length === 0 ? (
            <div className="card p-10 text-center">
              <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center mx-auto mb-3">
                <svg className="w-6 h-6 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                </svg>
              </div>
              <p className="text-sm text-slate-500">No projects yet. Create your first one.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {projects.map((p) => (
                <a
                  key={p.id}
                  href={`/project?id=${encodeURIComponent(p.id)}`}
                  className="card p-4 flex items-center justify-between hover:shadow-md hover:border-emerald-200 transition-all group"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-9 h-9 rounded-lg bg-emerald-50 flex items-center justify-center shrink-0">
                      <svg className="w-5 h-5 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                    </div>
                    <span className="font-medium text-slate-900 group-hover:text-emerald-700 transition-colors truncate">
                      {p.name}
                    </span>
                  </div>
                  <svg className="w-4 h-4 text-slate-400 group-hover:text-emerald-500 transition-colors shrink-0 ml-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </a>
              ))}
            </div>
          )}
        </div>

      </div>
    </Layout>
  );
}