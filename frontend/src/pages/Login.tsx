import { lazy, Suspense, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/components/ui/Button";
import { Safeguard } from "@/components/layout/Safeguard";
import { DEMO_PASSWORD, DEMO_ROLES } from "@/lib/api";
import { loginAsDemo, useAuth } from "@/store/auth";
import { Fallback2D } from "@/3d/Fallback2D";
import { useUi } from "@/store/ui";

const LoginObject3D = lazy(() => import("@/3d/LoginObject3D"));

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(4),
});

export default function Login() {
  const login = useAuth((s) => s.login);
  const nav = useNavigate();
  const toast = useUi((s) => s.toast);
  const [tab, setTab] = useState("super_admin");
  const form = useForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema),
    defaultValues: { email: "super@approveflow.demo", password: DEMO_PASSWORD },
  });

  async function onSubmit(values: z.infer<typeof schema>) {
    try {
      await login(values.email, values.password);
      nav("/app");
    } catch (e) {
      toast((e as Error).message, "err");
    }
  }

  return (
    <div className="grid min-h-screen md:grid-cols-2">
      <div className="hidden items-center justify-center bg-gradient-to-b from-white to-canvas md:flex">
        <Suspense fallback={<Fallback2D variant="login" />}>
          <LoginObject3D />
        </Suspense>
      </div>
      <div className="flex items-center justify-center p-8">
        <form onSubmit={form.handleSubmit(onSubmit)} className="w-full max-w-md space-y-4">
          <h1 className="text-3xl font-extrabold">Sign in</h1>
          <p className="text-sm text-slate-500">Simulated demo. Password for every demo role is Demo@123.</p>
          <div className="flex flex-wrap gap-1 rounded-2xl bg-canvas p-1">
            {DEMO_ROLES.map((r) => (
              <button
                key={r.role}
                type="button"
                onClick={() => {
                  setTab(r.role);
                  form.setValue("email", r.email);
                }}
                className={`rounded-xl px-2 py-1 text-xs ${tab === r.role ? "bg-white font-semibold shadow-sm" : ""}`}
              >
                {r.label}
              </button>
            ))}
          </div>
          <input className="w-full rounded-xl border border-line p-3" {...form.register("email")} />
          <input type="password" className="w-full rounded-xl border border-line p-3" {...form.register("password")} />
          <Button className="w-full" type="submit">
            Continue
          </Button>
          <div className="grid gap-2">
            {DEMO_ROLES.map((r) => (
              <Button
                key={r.email}
                type="button"
                variant="outline"
                onClick={async () => {
                  await loginAsDemo(r.email);
                  nav("/app");
                }}
              >
                Login as {r.label}
              </Button>
            ))}
          </div>
          <button type="button" className="text-sm text-slate-500" onClick={() => toast("Password reset is mocked in this demo.", "warn")}>
            Forgot password
          </button>
          <Safeguard />
        </form>
      </div>
    </div>
  );
}
