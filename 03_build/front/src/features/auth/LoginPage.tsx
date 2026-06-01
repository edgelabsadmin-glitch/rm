import { useEffect, useState } from "react";
import { Zap } from "lucide-react";

// Read the error/unauthorized state from the URL Google OAuth puts there.
function useOAuthError() {
  const params = new URLSearchParams(window.location.search);
  const status = params.get("google");
  if (status === "error") return "Something went wrong during sign-in. Please try again.";
  if (status === "unauthorized")
    return "Your Google account is not authorized to access Pulse. Use your onedge.co or edgeonline.co account.";
  return null;
}

export function LoginPage() {
  const [loading, setLoading] = useState(false);
  const error = useOAuthError();

  // Clean the error param from the URL so a refresh doesn't re-show it.
  useEffect(() => {
    if (error) {
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, [error]);

  function handleGoogleSignIn() {
    setLoading(true);
    // Full page navigation — Vite proxies /api → FastAPI which redirects to Google.
    window.location.href = "/api/auth/google/start";
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 p-4">
      <div className="w-full max-w-sm">
        {/* Brand mark */}
        <div className="mb-8 flex flex-col items-center gap-4">
          <div className="flex h-16 w-16 items-center justify-center rounded-3xl bg-brand text-ink-on-brand shadow-xl-brand">
            <Zap className="h-8 w-8" />
          </div>
          <div className="text-center">
            <h1 className="text-2xl font-semibold tracking-tight text-ink-primary">Pulse</h1>
            <p className="mt-1 text-sm text-ink-secondary">Relationship intelligence for RMs</p>
          </div>
        </div>

        {/* Login card */}
        <div className="rounded-3xl border border-line-subtle bg-white p-8 shadow-lg shadow-slate-200">
          <h2 className="mb-1 text-center text-base font-semibold text-ink-primary">
            Sign in to continue
          </h2>
          <p className="mb-6 text-center text-xs text-ink-muted">
            Use your Edge team Google account
          </p>

          {/* Error message */}
          {error && (
            <div className="mb-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-xs text-red-700">
              {error}
            </div>
          )}

          {/* Google Sign-In button — follows Google's brand guidelines */}
          <button
            type="button"
            onClick={handleGoogleSignIn}
            disabled={loading}
            className="flex w-full items-center justify-center gap-3 rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 hover:shadow disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading ? (
              <svg className="h-4 w-4 animate-spin text-slate-400" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            ) : (
              /* Google "G" logo — official colours */
              <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden>
                <path fill="#4285F4" d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844a4.14 4.14 0 0 1-1.796 2.717v2.258h2.908c1.702-1.567 2.684-3.874 2.684-6.615z" />
                <path fill="#34A853" d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18z" />
                <path fill="#FBBC05" d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332z" />
                <path fill="#EA4335" d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58z" />
              </svg>
            )}
            {loading ? "Redirecting…" : "Sign in with Google"}
          </button>
        </div>

        <p className="mt-6 text-center text-xs text-ink-muted">
          Access is limited to authorized onedge.co and edgeonline.co team members.
        </p>
      </div>
    </div>
  );
}
