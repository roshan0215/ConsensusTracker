import { useEffect, useState } from "react";
import Layout from "../components/Layout";
import { apiFetch } from "../lib/api";

export default function Verify() {
  const [status, setStatus] = useState("Verifying...");

  useEffect(() => {
    const token = new URLSearchParams(window.location.search).get("token");
    if (!token) {
      setStatus("Missing token.");
      return;
    }
    apiFetch(`/api/auth/verify?token=${encodeURIComponent(token)}`, { auth: false })
      .then(() => setStatus("Email verified. You can sign in now."))
      .catch((e) => setStatus(String(e.message || e)));
  }, []);

  return (
    <Layout title="Verify email" maxWidth="max-w-lg">
      <div className="text-sm">{status}</div>
      <div className="mt-4">
        <a className="underline text-sm" href="/signin">Go to sign in</a>
      </div>
    </Layout>
  );
}
