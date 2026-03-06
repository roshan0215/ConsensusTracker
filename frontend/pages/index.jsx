import { useEffect, useState } from "react";
import Layout from "../components/Layout";
import { apiFetch, getToken } from "../lib/api";

function StatCard({ label, value, loading }) {
  return (
    <div className="text-center px-4">
      <div className="text-3xl md:text-4xl font-extrabold text-emerald-700 tabular-nums">
        {loading ? "—" : value.toLocaleString()}
      </div>
      <div className="text-sm text-slate-500 mt-1.5 leading-tight">{label}</div>
    </div>
  );
}

const features = [
  {
    icon: (
      <svg className="w-6 h-6 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
    title: "Google Docs native",
    desc: "Link your existing literature review — we extract your topic, claims, and methodology automatically. No reformatting required.",
  },
  {
    icon: (
      <svg className="w-6 h-6 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
      </svg>
    ),
    title: "Daily PubMed monitoring",
    desc: "We query PubMed every day with your review's keywords and surface papers that confirm, contradict, or extend your claims.",
  },
  {
    icon: (
      <svg className="w-6 h-6 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
      </svg>
    ),
    title: "AI revision drafts",
    desc: "Generate an evidence-grounded revision draft straight into a dedicated tab in your Google Doc — with proper citations.",
  },
];

const bullets = [
  "Automatic extraction of claims and methodology",
  "Weighted PubMed queries tailored to your topic",
  "Color-coded findings: confirmations, contradictions & additions",
  "Evidence-grounded AI revision drafts in APA, MLA, or Vancouver",
];

export default function Home() {
  const [hasToken, setHasToken] = useState(false);
  const [stats, setStats] = useState(null);
  const [statsLoading, setStatsLoading] = useState(true);

  useEffect(() => {
    setHasToken(Boolean(getToken()));
    apiFetch("/api/stats", { auth: false })
      .then((s) => setStats(s))
      .catch(() => {})
      .finally(() => setStatsLoading(false));
  }, []);

  return (
    <Layout title={null} maxWidth="max-w-6xl">
      {/* ── Hero ── */}
      <section className="py-16 md:py-24">
        <div className="grid md:grid-cols-2 gap-12 items-center">
          <div>
            <span className="inline-block mb-5 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-100 text-emerald-700 text-xs font-semibold tracking-widest uppercase">
              For researchers &amp; academics
            </span>
            <h1 className="text-4xl md:text-5xl font-extrabold text-slate-900 leading-tight">
              Keep your review<br />in sync{" "}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-600 to-teal-500">
                with the evidence.
              </span>
            </h1>
            <p className="mt-5 text-lg text-slate-600 leading-relaxed max-w-lg">
              ConsensusTracker monitors PubMed daily and alerts you when new papers confirm, contradict, or extend the claims in your Google Doc literature review.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              {hasToken ? (
                <a className="btn-primary px-7 py-3 text-base" href="/projects">
                  Go to my projects →
                </a>
              ) : (
                <>
                  <a className="btn-primary px-7 py-3 text-base" href="/register">
                    Start for free →
                  </a>
                  <a className="btn-secondary px-7 py-3 text-base" href="/signin">
                    Sign in
                  </a>
                </>
              )}
            </div>
            <p className="mt-4 text-xs text-slate-400">No credit card required.</p>
          </div>
          <div className="relative hidden md:flex items-center justify-center">
            <div className="absolute inset-0 -m-6 rounded-3xl bg-gradient-to-br from-emerald-50 via-teal-50 to-cyan-50" />
            <img
              src="https://images.unsplash.com/photo-1576091160550-2173dba999ef?w=720&q=80"
              alt="Researcher analyzing data"
              className="relative rounded-2xl shadow-2xl w-full object-cover aspect-[4/3]"
            />
            {/* Floating badge */}
            <div className="absolute bottom-4 left-4 bg-white rounded-xl shadow-lg border border-slate-100 px-4 py-3 flex items-center gap-3">
              <div className="w-9 h-9 rounded-full bg-emerald-100 flex items-center justify-center">
                <svg className="w-5 h-5 text-emerald-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
              </div>
              <div>
                <div className="text-xs font-semibold text-slate-900">New finding detected</div>
                <div className="text-xs text-slate-500">2 papers contradict §3.2</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Live stats ── */}
      <section className="rounded-2xl bg-emerald-50 border border-emerald-100 px-8 py-12 mb-2">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 divide-x divide-emerald-200">
          <StatCard label="Researchers using CT" value={stats?.researchers ?? 0} loading={statsLoading} />
          <StatCard label="Research projects tracked" value={stats?.projects ?? 0} loading={statsLoading} />
          <StatCard label="Papers analyzed" value={stats?.papers_analyzed ?? 0} loading={statsLoading} />
          <StatCard label="Findings surfaced" value={stats?.findings_generated ?? 0} loading={statsLoading} />
        </div>
      </section>

      {/* ── How it works ── */}
      <section className="py-16">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold text-slate-900">How it works</h2>
          <p className="mt-3 text-slate-500 text-base">Three steps to never miss a contradicting paper again.</p>
        </div>
        <div className="grid md:grid-cols-3 gap-6">
          {features.map((f, i) => (
            <div key={i} className="card p-6 flex flex-col gap-4 hover:shadow-md hover:-translate-y-0.5 transition-all">
              <div className="w-12 h-12 rounded-xl bg-emerald-50 flex items-center justify-center shrink-0">
                {f.icon}
              </div>
              <div>
                <h3 className="font-semibold text-slate-900">{f.title}</h3>
                <p className="mt-1.5 text-sm text-slate-600 leading-relaxed">{f.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Workflow visual ── */}
      <section className="pb-16">
        <div className="card overflow-hidden">
          <div className="grid md:grid-cols-2">
            <div className="p-8 md:p-12 flex flex-col justify-center">
              <h2 className="text-2xl font-bold text-slate-900">Built for the modern literature review</h2>
              <p className="mt-4 text-slate-600 leading-relaxed">
                Your Google Doc stays at the center of your workflow. ConsensusTracker reads it, understands your claims, and writes new evidence directly back into a dedicated revision tab — keeping everything in one place.
              </p>
              <ul className="mt-6 space-y-2.5">
                {bullets.map((item) => (
                  <li key={item} className="flex items-start gap-2.5 text-sm text-slate-700">
                    <svg className="w-4 h-4 text-emerald-500 mt-0.5 shrink-0" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                    {item}
                  </li>
                ))}
              </ul>
              <div className="mt-8">
                <a className="btn-primary" href={hasToken ? "/projects" : "/register"}>
                  {hasToken ? "Open my projects →" : "Create free account →"}
                </a>
              </div>
            </div>
            <div className="relative hidden md:block min-h-[320px]">
              <img
                src="https://images.unsplash.com/photo-1532187863486-abf9dbad1b69?w=720&q=80"
                alt="Scientific research"
                className="absolute inset-0 w-full h-full object-cover"
              />
              <div className="absolute inset-0 bg-gradient-to-r from-white/10 to-transparent" />
            </div>
          </div>
        </div>
      </section>


    </Layout>
  );
}


