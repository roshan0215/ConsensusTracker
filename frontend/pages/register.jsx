import { useState, useEffect } from "react";
import Layout from "../components/Layout";
import { apiFetch } from "../lib/api";

const GOOGLE_ERROR_MAP = {
  google_denied: "Google sign-in was cancelled.",
  already_linked: "This Google account is linked to a different user.",
  google_error: "An error occurred with Google sign-in. Please try again.",
};

export default function Register() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const err = new URLSearchParams(window.location.search).get("error");
    if (err) setError(GOOGLE_ERROR_MAP[err] || "Sign-in error. Please try again.");
  }, []);

  const submit = async () => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await apiFetch("/api/auth/register", { method: "POST", body: { email, password }, auth: false });
      setMessage("Check your email for a verification link.");
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Layout variant="centered">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <a href="/" className="inline-flex items-center text-2xl font-bold tracking-tight">
            <span className="text-slate-900">Consensus</span>
            <span className="text-emerald-600">Tracker</span>
          </a>
          <h1 className="mt-3 text-xl font-semibold text-slate-900">Create your account</h1>
          <p className="mt-1 text-sm text-slate-500">Start monitoring your literature review</p>
        </div>

        <div className="card p-8">
          {error ? <div className="alert-error mb-5">{error}</div> : null}
          {message ? <div className="alert-success mb-5">{message}</div> : null}

          {/* Google OAuth */}
          <a
            href="/api/auth/google?mode=login"
            className="flex items-center justify-center gap-2.5 w-full py-2.5 px-4 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 transition-colors text-sm font-medium text-slate-700 shadow-sm"
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05"/>
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
            </svg>
            Continue with Google
          </a>

          <div className="flex items-center gap-3 my-5">
            <div className="flex-1 h-px bg-slate-200" />
            <span className="text-xs text-slate-400">or</span>
            <div className="flex-1 h-px bg-slate-200" />
          </div>

          <div className="space-y-4">
            <div>
              <label className="label">Email</label>
              <input className="input" value={email} onChange={(e) => setEmail(e.target.value)} type="email" placeholder="you@university.edu" />
            </div>
            <div>
              <label className="label">Password</label>
              <input className="input" value={password} onChange={(e) => setPassword(e.target.value)} type="password" placeholder="Min. 8 characters" />
            </div>
            <button className="btn-primary w-full py-3" disabled={busy} onClick={submit}>
              {busy ? "Creating account..." : "Create free account"}
            </button>
          </div>
        </div>

        <p className="mt-5 text-center text-sm text-slate-500">
          Already have an account?{" "}
          <a className="font-medium text-emerald-600 hover:text-emerald-700" href="/signin">Sign in</a>
        </p>
      </div>
    </Layout>
  );
}
