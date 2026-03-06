import { useEffect, useState } from "react";
import { clearToken, getToken } from "../lib/api";

export default function Layout({ title, children, maxWidth = "max-w-5xl", variant = "default" }) {
  const [hasToken, setHasToken] = useState(false);

  useEffect(() => {
    setHasToken(Boolean(getToken()));
  }, []);

  const logout = () => {
    clearToken();
    window.location.href = "/signin";
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* ── Navigation ── */}
      <header className="sticky top-0 z-50 bg-emerald-50 border-b border-emerald-200">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <a href="/" className="flex items-center text-lg font-bold tracking-tight select-none">
            <span className="text-slate-900">Consensus</span>
            <span className="text-emerald-600">Tracker</span>
          </a>
          <nav className="flex items-center gap-1">
            {hasToken ? (
              <>
                <a
                  href="/projects"
                  className="px-3 py-1.5 rounded-md text-sm font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors"
                >
                  Projects
                </a>
                <button
                  onClick={logout}
                  className="ml-1 px-3 py-1.5 rounded-md text-sm font-medium border border-slate-300 text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors"
                >
                  Log out
                </button>
              </>
            ) : (
              <>
                <a
                  href="/signin"
                  className="px-3 py-1.5 rounded-md text-sm font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors"
                >
                  Sign in
                </a>
                <a
                  href="/register"
                  className="ml-1 px-4 py-1.5 rounded-md text-sm font-medium bg-emerald-600 hover:bg-emerald-700 text-white transition-colors"
                >
                  Get started
                </a>
              </>
            )}
          </nav>
        </div>
      </header>

      {/* ── Body ── */}
      {variant === "centered" ? (
        <main className="flex-1 flex items-center justify-center px-6 py-16">
          {children}
        </main>
      ) : (
        <main className={`flex-1 ${maxWidth} mx-auto w-full px-6 py-8`}>
          {title ? (
            <h1 className="text-2xl font-bold text-slate-900 mb-6">{title}</h1>
          ) : null}
          {children}
        </main>
      )}

      {/* ── Footer ── */}
      <footer className="border-t border-slate-200 bg-white py-5 mt-auto">
        <div className="max-w-6xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-slate-500">
          <div>
            <span className="font-semibold text-slate-700">ConsensusTracker</span>
            {" "}— keep your review aligned with the evidence.
          </div>
          <div>Built for researchers, by researchers.</div>
        </div>
      </footer>
    </div>
  );
}

