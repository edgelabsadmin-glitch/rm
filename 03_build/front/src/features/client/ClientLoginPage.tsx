import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2, Zap } from "lucide-react";
import { clientApi, setClientSession } from "@/lib/client-api";
import { cn } from "@/lib/utils";

export function ClientLoginPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState<"email" | "otp">("email");
  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleRequestOtp(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await clientApi.requestOtp(email.trim());
      setStep("otp");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send code. Try again.");
    } finally {
      setLoading(false);
    }
  }

  async function handleVerifyOtp(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const { session_id } = await clientApi.verifyOtp(email.trim(), otp.trim());
      setClientSession(session_id);
      navigate("/client/chat", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invalid code. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 p-4">
      <div className="w-full max-w-sm">
        {/* Brand */}
        <div className="mb-8 flex flex-col items-center gap-4">
          <div className="flex h-16 w-16 items-center justify-center rounded-3xl bg-brand text-ink-on-brand shadow-xl-brand">
            <Zap className="h-8 w-8" />
          </div>
          <div className="text-center">
            <h1 className="text-2xl font-semibold tracking-tight text-ink-primary">EDGE Pulse</h1>
            <p className="mt-1 text-sm text-ink-secondary">Client portal</p>
          </div>
        </div>

        <div className="rounded-3xl border border-line-subtle bg-white p-8 shadow-lg shadow-slate-200">
          {step === "email" ? (
            <form onSubmit={handleRequestOtp} className="space-y-4">
              <div>
                <h2 className="mb-1 text-center text-base font-semibold text-ink-primary">
                  Sign in
                </h2>
                <p className="mb-6 text-center text-xs text-ink-muted">
                  Enter your email and we&apos;ll send you a login code
                </p>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="your@email.com"
                  required
                  className="w-full rounded-xl border border-line-strong px-4 py-3 text-sm text-ink-primary placeholder:text-ink-muted focus:border-brand/40 focus:outline-none focus:ring-2 focus:ring-brand/10"
                />
              </div>
              {error && <p className="text-center text-xs text-red-500">{error}</p>}
              <button
                type="submit"
                disabled={loading || !email.trim()}
                className={cn(
                  "flex w-full items-center justify-center gap-2 rounded-xl bg-brand px-4 py-3 text-sm font-semibold text-ink-on-brand shadow-xl-brand transition hover:opacity-90",
                  "disabled:cursor-not-allowed disabled:opacity-50",
                )}
              >
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Send code"}
              </button>
            </form>
          ) : (
            <form onSubmit={handleVerifyOtp} className="space-y-4">
              <div>
                <h2 className="mb-1 text-center text-base font-semibold text-ink-primary">
                  Enter your code
                </h2>
                <p className="mb-6 text-center text-xs text-ink-muted">
                  We sent a 6-digit code to{" "}
                  <span className="font-medium text-ink-secondary">{email}</span>
                </p>
                <input
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]{6}"
                  maxLength={6}
                  value={otp}
                  onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))}
                  placeholder="123456"
                  required
                  className="w-full rounded-xl border border-line-strong px-4 py-3 text-center text-2xl tracking-widest text-ink-primary placeholder:text-ink-muted focus:border-brand/40 focus:outline-none focus:ring-2 focus:ring-brand/10"
                />
              </div>
              {error && <p className="text-center text-xs text-red-500">{error}</p>}
              <button
                type="submit"
                disabled={loading || otp.length !== 6}
                className={cn(
                  "flex w-full items-center justify-center gap-2 rounded-xl bg-brand px-4 py-3 text-sm font-semibold text-ink-on-brand shadow-xl-brand transition hover:opacity-90",
                  "disabled:cursor-not-allowed disabled:opacity-50",
                )}
              >
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Sign in"}
              </button>
              <button
                type="button"
                onClick={() => {
                  setStep("email");
                  setOtp("");
                  setError(null);
                }}
                className="w-full text-center text-xs text-ink-muted hover:text-brand"
              >
                Use a different email
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
