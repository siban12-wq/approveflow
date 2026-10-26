import { lazy, Suspense, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Eye, EyeOff, Lock, Mail, ShieldCheck, ArrowRight, Building2, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Safeguard } from "@/components/layout/Safeguard";
import { api, DEMO_PASSWORD, DEMO_ROLES, ROLE_LABELS } from "@/lib/api";
import { loginAsDemo, useAuth } from "@/store/auth";
import { Fallback2D } from "@/3d/Fallback2D";
import { useUi } from "@/store/ui";

const LogoMark3D = lazy(() => import("@/3d/LogoMark3D"));

const schema = z.object({
  email: z.string().min(3, "Please enter your official email address"),
  password: z.string().min(4, "Password must be at least 4 characters"),
  rememberMe: z.boolean().default(false),
});

export default function Login() {
  const login = useAuth((s) => s.login);
  const nav = useNavigate();
  const toast = useUi((s) => s.toast);
  const [selectedRole, setSelectedRole] = useState("super_admin");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [forgotOpen, setForgotOpen] = useState(false);
  const [forgotEmail, setForgotEmail] = useState("");
  const [forgotLoading, setForgotLoading] = useState(false);
  const [forgotSuccess, setForgotSuccess] = useState<string | null>(null);

  const form = useForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema),
    defaultValues: { email: "super@approveflow.demo", password: DEMO_PASSWORD, rememberMe: true },
  });

  async function onSubmit(values: z.infer<typeof schema>) {
    setLoading(true);
    try {
      await login(values.email, values.password);
      toast("Welcome back to ApproveFlow", "ok");
      nav("/app");
    } catch (e) {
      toast((e as Error).message || "Invalid credentials", "err");
    } finally {
      setLoading(false);
    }
  }

  async function handleForgotSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!forgotEmail) return;
    setForgotLoading(true);
    try {
      const res = await api.post<{ message: string }>("/api/v1/auth/forgot-password", { email: forgotEmail });
      setForgotSuccess(res.message);
      toast("Password reset instructions dispatched", "ok");
    } catch (err) {
      toast((err as Error).message, "err");
    } finally {
      setForgotLoading(false);
    }
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-12 bg-canvas selection:bg-brand-500 selection:text-white">
      {/* Left Column: 3D Emblem & Institutional Credentials */}
      <div className="relative hidden lg:flex lg:col-span-5 xl:col-span-6 flex-col justify-between overflow-hidden bg-gradient-to-br from-[#06122C] via-[#0B1B3A] to-[#0A2540] p-12 text-white">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-blue-600/15 via-transparent to-transparent pointer-events-none" />

        <div className="relative z-10 flex items-center gap-3">
          <img
            src={`${import.meta.env.BASE_URL}logo.png`}
            alt="ApproveFlow Logo"
            className="h-10 w-auto rounded-lg shadow-md"
          />
          <div>
            <span className="text-xl font-extrabold tracking-tight text-white flex items-center gap-1.5">
              ApproveFlow
              <span className="rounded bg-sky-500/20 px-1.5 py-0.5 text-[10px] font-semibold text-sky-300">
                AICTE
              </span>
            </span>
            <p className="text-[11px] text-slate-400">Integrated Compliance & Workflow Automation</p>
          </div>
        </div>

        {/* 3D Visual Centerpiece */}
        <div className="relative z-10 my-auto flex flex-col items-center justify-center">
          <Suspense fallback={<Fallback2D variant="login" />}>
            <LogoMark3D />
          </Suspense>

          <div className="mt-6 max-w-md text-center">
            <h2 className="text-2xl font-bold tracking-tight text-white">
              Transparent Statutory Governance
            </h2>
            <p className="mt-2 text-sm text-slate-300">
              One unified platform for scrutiny, EVC committee inspection, land lease tracking, and SLA deadline compliance.
            </p>
          </div>

          {/* Key Trust Signals */}
          <div className="mt-8 grid grid-cols-2 gap-3 w-full max-w-md text-xs">
            <div className="rounded-xl border border-white/10 bg-white/5 p-3 backdrop-blur-sm">
              <div className="font-semibold text-sky-300 flex items-center gap-1.5">
                <ShieldCheck className="h-4 w-4" /> 100% Human Invariant
              </div>
              <p className="mt-1 text-slate-400">No AI or automated job ever grants or denies approval.</p>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/5 p-3 backdrop-blur-sm">
              <div className="font-semibold text-sky-300 flex items-center gap-1.5">
                <CheckCircle2 className="h-4 w-4" /> 4 Unified Streams
              </div>
              <p className="mt-1 text-slate-400">SLA, EVC scheduling, undertakings, and lease validity.</p>
            </div>
          </div>
        </div>

        <div className="relative z-10 flex items-center justify-between text-xs text-slate-400">
          <span>AICTE Regulation Bureau Prototype</span>
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            Backend Active
          </span>
        </div>
      </div>

      {/* Right Column: Sign In Form & Demo Roles */}
      <div className="lg:col-span-7 xl:col-span-6 flex flex-col justify-between p-6 sm:p-12 lg:p-16">
        <div className="flex items-center justify-between">
          <div className="flex lg:hidden items-center gap-2">
            <img src={`${import.meta.env.BASE_URL}logo.png`} alt="ApproveFlow" className="h-8 w-auto" />
            <span className="font-bold text-lg text-ink">ApproveFlow</span>
          </div>
          <div className="text-xs text-slate-500 ml-auto">
            Need an institution account?{" "}
            <Link to="/signup" className="font-semibold text-brand-600 hover:text-brand-700 underline">
              Register now
            </Link>
          </div>
        </div>

        <div className="mx-auto w-full max-w-md my-auto py-8">
          <div className="mb-6">
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-ink">
              Sign in to your portal
            </h1>
            <p className="mt-1.5 text-sm text-slate-500">
              Access role-specific queues, verify submissions, and track regulatory milestones.
            </p>
          </div>

          {/* Quick Demo Switcher */}
          <div className="mb-6 rounded-2xl border border-line bg-white p-3 shadow-sm">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Demo Accounts (Click to load)
              </span>
              <span className="text-[11px] font-mono text-slate-400">Password: Demo@123</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {DEMO_ROLES.map((r) => (
                <button
                  key={r.role}
                  type="button"
                  onClick={() => {
                    setSelectedRole(r.role);
                    form.setValue("email", r.email);
                    form.setValue("password", DEMO_PASSWORD);
                  }}
                  className={`rounded-lg px-2.5 py-1 text-xs transition-all ${
                    selectedRole === r.role
                      ? "bg-brand-600 font-semibold text-white shadow"
                      : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                  }`}
                >
                  {r.label}
                </button>
              ))}
            </div>
          </div>

          {/* Main Login Form */}
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
                Official Email Address
              </label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-3.5 h-4 w-4 text-slate-400" />
                <input
                  type="email"
                  autoComplete="email"
                  placeholder="name@approveflow.demo"
                  className="w-full rounded-xl border border-line bg-white py-2.5 pl-10 pr-3 text-sm text-ink placeholder:text-slate-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                  {...form.register("email")}
                />
              </div>
              {form.formState.errors.email && (
                <p className="mt-1 text-xs text-rose-500">{form.formState.errors.email.message}</p>
              )}
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600">
                  Password
                </label>
                <button
                  type="button"
                  onClick={() => setForgotOpen(true)}
                  className="text-xs font-medium text-brand-600 hover:text-brand-700"
                >
                  Forgot password?
                </button>
              </div>
              <div className="relative">
                <Lock className="absolute left-3.5 top-3.5 h-4 w-4 text-slate-400" />
                <input
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  placeholder="••••••••"
                  className="w-full rounded-xl border border-line bg-white py-2.5 pl-10 pr-10 text-sm text-ink placeholder:text-slate-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                  {...form.register("password")}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-3 text-slate-400 hover:text-slate-600"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              {form.formState.errors.password && (
                <p className="mt-1 text-xs text-rose-500">{form.formState.errors.password.message}</p>
              )}
            </div>

            <div className="flex items-center">
              <input
                id="rememberMe"
                type="checkbox"
                className="h-4 w-4 rounded border-line text-brand-600 focus:ring-brand-500"
                {...form.register("rememberMe")}
              />
              <label htmlFor="rememberMe" className="ml-2 block text-xs text-slate-600">
                Remember this session on this trusted computer
              </label>
            </div>

            <Button type="submit" disabled={loading} className="w-full flex items-center justify-center gap-2">
              {loading ? "Authenticating…" : "Sign In to ApproveFlow"}
              {!loading && <ArrowRight className="h-4 w-4" />}
            </Button>
          </form>

          {/* Quick Instant Login Buttons */}
          <div className="mt-6 pt-5 border-t border-line">
            <p className="text-xs text-slate-500 mb-2.5 text-center">Or launch directly with demo credentials:</p>
            <div className="grid grid-cols-2 gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="justify-start text-xs"
                onClick={async () => {
                  await loginAsDemo("super@approveflow.demo");
                  nav("/app");
                }}
              >
                <ShieldCheck className="h-3.5 w-3.5 mr-1.5 text-brand-600" />
                Super Admin
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="justify-start text-xs"
                onClick={async () => {
                  await loginAsDemo("institution@approveflow.demo");
                  nav("/app");
                }}
              >
                <Building2 className="h-3.5 w-3.5 mr-1.5 text-emerald-600" />
                Institution User
              </Button>
            </div>
          </div>

          <div className="mt-8">
            <Safeguard />
          </div>
        </div>

        {/* Footer Links */}
        <div className="flex flex-wrap items-center justify-between gap-4 text-xs text-slate-400 pt-6 border-t border-line">
          <span>&copy; {new Date().getFullYear()} AICTE ApproveFlow Prototype.</span>
          <div className="flex gap-4">
            <span className="hover:text-slate-600 cursor-pointer">Regulatory Guidelines</span>
            <span className="hover:text-slate-600 cursor-pointer">Security Safeguards</span>
            <span className="hover:text-slate-600 cursor-pointer">Audit Logging</span>
          </div>
        </div>
      </div>

      {/* Forgot Password Modal */}
      {forgotOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
            <h3 className="text-lg font-bold text-ink">Reset Your Password</h3>
            <p className="mt-1 text-xs text-slate-500">
              Enter your registered official email address. A secure single-use reset link will be generated.
            </p>

            {forgotSuccess ? (
              <div className="mt-4 rounded-xl bg-emerald-50 p-4 border border-emerald-200 text-xs text-emerald-800">
                <p className="font-semibold mb-1">Check Development Email Sink</p>
                <p>{forgotSuccess}</p>
                <Button className="mt-3 w-full" size="sm" onClick={() => { setForgotOpen(false); setForgotSuccess(null); }}>
                  Back to Sign In
                </Button>
              </div>
            ) : (
              <form onSubmit={handleForgotSubmit} className="mt-4 space-y-4">
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1">
                    Email Address
                  </label>
                  <input
                    type="email"
                    required
                    value={forgotEmail}
                    onChange={(e) => setForgotEmail(e.target.value)}
                    placeholder="official@institution.edu"
                    className="w-full rounded-xl border border-line p-2.5 text-sm"
                  />
                </div>
                <div className="flex gap-2 justify-end">
                  <Button type="button" variant="outline" size="sm" onClick={() => setForgotOpen(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" size="sm" disabled={forgotLoading}>
                    {forgotLoading ? "Issuing Link…" : "Generate Reset Link"}
                  </Button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
