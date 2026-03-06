import { useEffect, useState } from "react";
import Layout from "../components/Layout";
import { apiFetch, setToken } from "../lib/api";

export default function Magic() {
  const [status, setStatus] = useState("Signing you in...");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get("token");
    if (!token) {
      setStatus("Missing token.");
      return;
    }
    // Google OAuth login flow redirects here with ?google=1&token=<already_issued_jwt>
    // In that case the token is already a valid bearer JWT — skip the magic-link exchange.
    if (params.get("google") === "1") {
      setToken(token);
      window.location.href = "/projects";
      return;
    }
    apiFetch(`/api/auth/magic?token=${encodeURIComponent(token)}`, { auth: false })
      .then((out) => {
        setToken(out.access_token);
        window.location.href = "/projects";
      })
      .catch((e) => setStatus(String(e.message || e)));
  }, []);

  return (
    <Layout title="Magic link" maxWidth="max-w-lg">
      <div className="text-sm">{status}</div>
    </Layout>
  );
}
