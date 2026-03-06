import { useEffect, useState } from "react";
import Layout from "../components/Layout";
import { apiFetch, getToken } from "../lib/api";

export default function Project() {
  const [data, setData] = useState(null);
  const [docUrl, setDocUrl] = useState("");
  const [lastUpdated, setLastUpdated] = useState("");
  const [runFromDate, setRunFromDate] = useState("");
  const [aiTabTitle, setAiTabTitle] = useState("AI-Revision");
  const [citationStyle, setCitationStyle] = useState("APA");
  const [revisionHeading, setRevisionHeading] = useState("AI Revision Draft");
  const [busy, setBusy] = useState(false);
  const [runBusy, setRunBusy] = useState(false);
  const [tabBusy, setTabBusy] = useState(false);
  const [aiBusy, setAiBusy] = useState(false);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [showResolved, setShowResolved] = useState(false);
  const [svcEmail, setSvcEmail] = useState(null);
  const [googleConnected, setGoogleConnected] = useState(false);

  const projectId = typeof window !== "undefined" ? new URLSearchParams(window.location.search).get("id") : null;

  function fmtDate(iso) {
    if (!iso) return "—";
    try {
      const d = new Date(iso);
      const now = new Date();
      const diffMs = now - d;
      const diffMins = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMs / 3600000);
      const diffDays = Math.floor(diffMs / 86400000);
      if (diffMins < 1) return "just now";
      if (diffMins < 60) return `${diffMins}m ago`;
      if (diffHours < 24) return `${diffHours}h ago`;
      if (diffDays === 1) return "yesterday";
      if (diffDays < 7) return `${diffDays}d ago`;
      return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: d.getFullYear() !== now.getFullYear() ? "numeric" : undefined });
    } catch { return iso; }
  }

  const load = async () => {
    const out = await apiFetch(`/api/projects/${encodeURIComponent(projectId)}`);
    setData(out);
    setDocUrl(out.profile?.google_doc_url || "");
    setAiTabTitle(out.profile?.ai_revision_tab_title || "AI-Revision");
    return out;
  };

  useEffect(() => {
    if (!projectId) return;
    load().catch((e) => setError(String(e.message || e)));
    apiFetch("/api/projects/service-account-email").then((r) => setSvcEmail(r.email || null)).catch(() => {});
    apiFetch("/api/auth/me").then((r) => setGoogleConnected(r.google_connected || false)).catch(() => {});
  }, [projectId]);

  const pollUntilDone = async () => {
    const INTERVAL = 3000;
    const MAX_POLLS = 60; // 3 min max
    for (let i = 0; i < MAX_POLLS; i++) {
      await new Promise((r) => setTimeout(r, INTERVAL));
      const out = await load();
      const status = out?.latest_job?.status;
      if (status && status !== "pending" && status !== "running") return;
    }
  };
  const setFindingStatus = async (findingId, status) => {
    try {
      await apiFetch(`/api/projects/${encodeURIComponent(projectId)}/findings/${encodeURIComponent(findingId)}?status=${status}`, { method: "PATCH" });
      await load();
    } catch (e) {
      setError(String(e.message || e));
    }
  };
  const linkDoc = async () => {
    setBusy(true);
    setError(null);
    try {
      await apiFetch(`/api/projects/${encodeURIComponent(projectId)}/link-google-doc`, {
        method: "POST",
        body: { google_doc_url: docUrl, review_last_updated: lastUpdated || null },
      });
      await load();
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setBusy(false);
    }
  };

  const runCheck = async () => {
    setRunBusy(true);
    setError(null);
    setNotice(null);
    try {
      const query = runFromDate ? `?date_after=${encodeURIComponent(runFromDate)}` : "";
      const out = await apiFetch(`/api/projects/${encodeURIComponent(projectId)}/run-check${query}`, { method: "POST" });
      setNotice(`Run check queued — checking for updates...`);
      await load();
      await pollUntilDone();
      setNotice("Check complete.");
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setRunBusy(false);
    }
  };

  const setMonitoring = async (active) => {
    setError(null);
    try {
      await apiFetch(`/api/projects/${encodeURIComponent(projectId)}/monitoring?active=${active ? "true" : "false"}`, { method: "POST" });
      await load();
    } catch (e) {
      setError(String(e.message || e));
    }
  };

  const setValidation = async (enabled) => {
    setError(null);
    try {
      await apiFetch(`/api/projects/${encodeURIComponent(projectId)}/validation?enabled=${enabled ? "true" : "false"}`, { method: "POST" });
      await load();
    } catch (e) {
      setError(String(e.message || e));
    }
  };

  const ensureAiTab = async () => {
    setTabBusy(true);
    setError(null);
    setNotice(null);
    try {
      const out = await apiFetch(`/api/projects/${encodeURIComponent(projectId)}/ai-revision-tab`, {
        method: "POST",
        body: { title: aiTabTitle || "AI-Revision" },
      });
      setNotice(`AI revision tab ready: ${out.ai_revision_tab_title} (${out.ai_revision_tab_id}).`);
      await load();
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setTabBusy(false);
    }
  };

  const generateAiRevision = async () => {
    setAiBusy(true);
    setError(null);
    setNotice(null);
    try {
      const out = await apiFetch(`/api/projects/${encodeURIComponent(projectId)}/generate-ai-revision`, {
        method: "POST",
        body: {
          citation_style: citationStyle || "APA",
          heading: revisionHeading || "AI Revision Draft",
        },
      });
      setNotice(
        `AI revision written to tab ${out.ai_revision_tab_title} (${out.ai_revision_tab_id}). ` +
          `References: ${out.references_count}, Notes: ${out.notes_count}.`
      );
      await load();
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setAiBusy(false);
    }
  };

  return (
    <Layout title={null} maxWidth="max-w-6xl">
      {/* ── Page header ── */}
      <div className="flex items-start justify-between gap-4 mb-6">
        <div>
          <a className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-900 transition-colors mb-2" href="/projects">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
            Back to projects
          </a>
          <h1 className="text-2xl font-bold text-slate-900">{data ? data.name : "Loading..."}</h1>
        </div>
        {data ? (
          <div className="flex items-center gap-2 shrink-0 pt-1">
            {data.profile?.google_doc_url ? (
              <a className="btn-secondary" href={data.profile.google_doc_url} target="_blank" rel="noreferrer">
                Open Google Doc ↗
              </a>
            ) : null}
            <button className="btn-primary" disabled={runBusy || !data.profile?.topic} onClick={runCheck}>
              {runBusy ? "Running..." : "Run check now"}
            </button>
          </div>
        ) : null}
      </div>

      {error ? <div className="alert-error mb-5">{error}</div> : null}
      {notice ? <div className="alert-info mb-5">{notice}</div> : null}

      {!data ? <div className="text-sm text-slate-500">Loading...</div> : null}

      {data ? (
        <div className="space-y-5">

          {/* ── Status strip ── */}
          <div className="card px-5 py-4 flex flex-wrap items-center gap-x-8 gap-y-3 text-sm">
            <div>
              <span className="text-slate-500 text-xs uppercase tracking-wide font-medium">Topic</span>
              <div className="font-medium text-slate-900 mt-0.5">{data.profile?.topic || "—"}</div>
            </div>
            <div>
              <span className="text-slate-500 text-xs uppercase tracking-wide font-medium">Last run</span>
              <div className="font-medium text-slate-900 mt-0.5" title={data.profile?.last_checked_at}>{fmtDate(data.profile?.last_checked_at)}</div>
            </div>
            <div>
              <span className="text-slate-500 text-xs uppercase tracking-wide font-medium">Status</span>
              <div className="mt-0.5">
                {(() => {
                  const s = data.latest_job?.status;
                  const cls = { completed: "badge-green", running: "badge-indigo", pending: "badge-amber", failed: "badge-red" }[s] ?? "badge-slate";
                  return s ? <span className={cls}>{s}</span> : <span className="badge-slate">—</span>;
                })()}
              </div>
            </div>
            <div>
              <span className="text-slate-500 text-xs uppercase tracking-wide font-medium">Papers checked</span>
              <div className="font-medium text-slate-900 mt-0.5">{data.latest_job?.papers_found ?? "—"}</div>
            </div>
            <div>
              <span className="text-slate-500 text-xs uppercase tracking-wide font-medium">Findings</span>
              <div className="font-medium text-slate-900 mt-0.5">{data.latest_job?.contradictions_found ?? "—"}</div>
            </div>
            <div>
              <span className="text-slate-500 text-xs uppercase tracking-wide font-medium">Daily monitoring</span>
              <div className={`font-medium mt-0.5 ${(data.profile?.monitoring_active ?? true) ? "text-emerald-700" : "text-slate-400"}`}>
                {(data.profile?.monitoring_active ?? true) ? "On" : "Off"}
              </div>
            </div>
            {Object.keys(data.findings_by_type || {}).length > 0 ? (
              <div>
                <span className="text-slate-500 text-xs uppercase tracking-wide font-medium">By type</span>
                <div className="flex gap-1.5 mt-0.5 flex-wrap">
                  {Object.entries(data.findings_by_type).map(([kind, count]) => {
                    const cls = { contradiction: "badge-red", confirmation: "badge-green", addition: "badge-indigo" }[kind] ?? "badge-slate";
                    return <span key={kind} className={cls}>{kind} {count}</span>;
                  })}
                </div>
              </div>
            ) : null}
          </div>

          {/* ── Main two-column ── */}
          <div className="grid md:grid-cols-3 gap-5 items-start">

            {/* ── Left sidebar: settings ── */}
            <div className="space-y-5">

              {/* Google Doc */}
              <section className="card p-5 space-y-3">
                <h2 className="section-title">Google Doc</h2>
                {googleConnected ? (
                  <div className="flex items-center gap-1.5 text-xs text-emerald-700 bg-emerald-50 border border-emerald-100 rounded-lg px-3 py-2">
                    <svg className="w-3.5 h-3.5 text-emerald-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    Google account connected
                  </div>
                ) : (
                  <>
                    {svcEmail ? (
                      <div className="bg-emerald-50 border border-emerald-100 rounded-lg px-3 py-2.5">
                        <p className="text-xs text-slate-500 mb-0.5">Share your doc with this address</p>
                        <p className="text-xs font-mono font-medium text-emerald-800 break-all select-all">{svcEmail}</p>
                      </div>
                    ) : null}
                    <a
                      href={`/api/auth/google?mode=connect&token=${getToken() || ""}`}
                      className="flex items-center justify-center gap-2 w-full py-2 px-3 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 transition-colors text-xs font-medium text-slate-600 shadow-sm"
                    >
                      <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                        <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                        <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05"/>
                        <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                      </svg>
                      Connect Google Account
                    </a>
                  </>
                )}
                <div>
                  <label className="label">Doc URL</label>
                  <input className="input" value={docUrl} onChange={(e) => setDocUrl(e.target.value)} placeholder="https://docs.google.com/document/d/..." />
                </div>
                <div>
                  <label className="label">Review date (optional)</label>
                  <input className="input w-auto" type="date" value={lastUpdated} onChange={(e) => setLastUpdated(e.target.value)} />
                </div>
                <button className="btn-primary w-full" disabled={busy || !docUrl} onClick={linkDoc}>
                  {busy ? "Linking..." : "Link & Analyze"}
                </button>

              </section>

              {/* Monitoring controls */}
              <section className="card p-5 space-y-3">
                <h2 className="section-title">Monitoring</h2>
                <div>
                  <label className="label">Run from date (optional)</label>
                  <input className="input w-auto" type="date" value={runFromDate} onChange={(e) => setRunFromDate(e.target.value)} />
                  <p className="text-xs text-slate-500 mt-1">Defaults to last checked date or last 24h.</p>
                </div>
                <div className="flex flex-col gap-2">
                  <button className="btn-secondary w-full text-left" onClick={() => setMonitoring(!(data.profile?.monitoring_active ?? true))}>
                    {(data.profile?.monitoring_active ?? true) ? "Disable daily monitoring" : "Enable daily monitoring"}
                  </button>
                  <button className="btn-secondary w-full text-left" onClick={() => setValidation(!(data.profile?.include_validation ?? true))}>
                    {(data.profile?.include_validation ?? true) ? "Disable validation findings" : "Enable validation findings"}
                  </button>
                </div>
                {data.profile?.keywords?.length ? (
                  <div>
                    <span className="text-xs text-slate-500 font-medium">Keywords: </span>
                    <span className="text-xs text-slate-700">{data.profile.keywords.join(", ")}</span>
                  </div>
                ) : null}
                {data.latest_job?.error_message ? (
                  <div className="alert-error text-xs">{data.latest_job.error_message}</div>
                ) : null}
              </section>

              {/* AI Revision */}
              <section className="card p-5 space-y-3">
                <h2 className="section-title">AI Revision Draft</h2>
                {data.profile?.ai_revision_tab_title ? (
                  <p className="text-xs text-slate-500">Tab: <span className="font-medium text-slate-700">{data.profile.ai_revision_tab_title}</span></p>
                ) : null}
                <div>
                  <label className="label">Tab title</label>
                  <input className="input" value={aiTabTitle} onChange={(e) => setAiTabTitle(e.target.value)} placeholder="AI-Revision" />
                </div>
                <div>
                  <label className="label">Citation style</label>
                  <input className="input" value={citationStyle} onChange={(e) => setCitationStyle(e.target.value)} placeholder="APA" />
                </div>
                <div>
                  <label className="label">Draft heading</label>
                  <input className="input" value={revisionHeading} onChange={(e) => setRevisionHeading(e.target.value)} placeholder="AI Revision Draft" />
                </div>
                <div className="flex flex-col gap-2">
                  <button className="btn-secondary w-full" disabled={tabBusy || !data.profile?.google_doc_url} onClick={ensureAiTab}>
                    {tabBusy ? "Preparing..." : "Create / Sync AI tab"}
                  </button>
                  <button className="btn-primary w-full" disabled={aiBusy || !data.profile?.google_doc_url} onClick={generateAiRevision}>
                    {aiBusy ? "Generating..." : "Generate AI revision draft"}
                  </button>
                </div>
                <p className="text-xs text-slate-500 leading-relaxed">Draft is written to the AI tab only. Review all claims before using.</p>
              </section>
            </div>

            {/* ── Right: findings ── */}
            <section className="md:col-span-2">
              <div className="flex items-center justify-between mb-3">
                <h2 className="section-title">Findings &amp; suggested updates</h2>
                <div className="flex items-center gap-2">
                  {(data.recent_findings || []).some((f) => f.status === "resolved" || f.status === "dismissed") ? (
                    <button
                      className="text-xs text-slate-500 hover:text-slate-800 underline"
                      onClick={() => setShowResolved((v) => !v)}
                    >
                      {showResolved ? "Hide resolved" : "Show resolved"}
                    </button>
                  ) : null}
                  {(() => {
                    const open = (data.recent_findings || []).filter((f) => !f.status || f.status === "pending").length;
                    return open > 0 ? <span className="badge-slate">{open} open</span> : null;
                  })()}
                </div>
              </div>
              {(data.recent_findings || []).filter((f) => showResolved || !f.status || f.status === "pending").length === 0 ? (
                <div className="card p-12 text-center">
                  <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center mx-auto mb-3">
                    <svg className="w-6 h-6 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                    </svg>
                  </div>
                  <p className="text-sm font-medium text-slate-700">{(data.recent_findings || []).length > 0 ? "All findings resolved" : "No findings yet"}</p>
                  <p className="text-xs text-slate-500 mt-1">{(data.recent_findings || []).length > 0 ? 'Toggle "Show resolved" above to review them.' : "Link your Google Doc and run a check to get started."}</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {(data.recent_findings || []).filter((f) => showResolved || !f.status || f.status === "pending").map((finding) => {
                    const kindBadge = { contradiction: "badge-red", confirmation: "badge-green", addition: "badge-indigo" }[finding.kind] ?? "badge-slate";
                    const sevBadge = { critical: "badge-red", major: "badge-red", minor: "badge-amber" }[finding.severity] ?? "badge-slate";
                    const isResolved = finding.status === "resolved" || finding.status === "dismissed";
                    return (
                      <div key={finding.id} className={`card p-4 text-sm transition-shadow ${isResolved ? "opacity-50" : "hover:shadow-md"}`}>
                        <div className="flex items-start justify-between gap-3 mb-2">
                          <div className="font-semibold text-slate-900 leading-snug">{finding.paper_title || "(untitled)"}</div>
                          <div className="flex gap-1.5 shrink-0 flex-wrap justify-end">
                            {finding.kind ? <span className={kindBadge}>{finding.kind}</span> : null}
                            {finding.severity ? <span className={sevBadge}>{finding.severity}</span> : null}
                            {isResolved ? <span className="badge-slate">{finding.status}</span> : null}
                          </div>
                        </div>
                        {(finding.paper_authors || finding.paper_date || finding.user_section) ? (
                          <div className="mb-2 space-y-0.5">
                            {finding.paper_authors ? (
                              <p className="text-xs text-slate-600">{finding.paper_authors}</p>
                            ) : null}
                            {(finding.paper_date || finding.user_section) ? (
                              <p className="text-xs text-slate-500">
                                {[finding.paper_date, finding.user_section ? `\u00a7 ${finding.user_section}` : null].filter(Boolean).join(" \u00b7 ")}
                              </p>
                            ) : null}
                          </div>
                        ) : null}
                        {finding.new_finding ? (
                          <div className="mt-2.5 pl-3 border-l-2 border-slate-200">
                            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">New info</span>
                            <p className="mt-0.5 text-slate-700 leading-relaxed">{finding.new_finding}</p>
                          </div>
                        ) : null}
                        {finding.suggested_update ? (
                          <div className="mt-2.5 pl-3 border-l-2 border-emerald-200">
                            <span className="text-xs font-semibold text-emerald-700 uppercase tracking-wide">Suggested update</span>
                            <p className="mt-0.5 text-slate-700 leading-relaxed">{finding.suggested_update}</p>
                          </div>
                        ) : null}
                        {finding.paper_doi ? (
                          <div className="mt-2.5">
                            <a className="text-xs text-emerald-600 hover:text-emerald-700 underline" href={`https://doi.org/${finding.paper_doi}`} target="_blank" rel="noreferrer">
                              doi:{finding.paper_doi} ↗
                            </a>
                          </div>
                        ) : null}
                        <div className="mt-3 pt-3 border-t border-slate-100 flex gap-2">
                          {!isResolved ? (
                            <>
                              <button
                                className="text-xs px-2.5 py-1 rounded-md bg-emerald-50 text-emerald-700 hover:bg-emerald-100 font-medium transition-colors"
                                onClick={() => setFindingStatus(finding.id, "resolved")}
                              >
                                Mark resolved
                              </button>
                              <button
                                className="text-xs px-2.5 py-1 rounded-md bg-slate-100 text-slate-600 hover:bg-slate-200 font-medium transition-colors"
                                onClick={() => setFindingStatus(finding.id, "dismissed")}
                              >
                                Dismiss
                              </button>
                            </>
                          ) : (
                            <button
                              className="text-xs px-2.5 py-1 rounded-md bg-slate-100 text-slate-600 hover:bg-slate-200 font-medium transition-colors"
                              onClick={() => setFindingStatus(finding.id, "pending")}
                            >
                              Reopen
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </section>

          </div>
        </div>
      ) : null}
    </Layout>
  );
}
