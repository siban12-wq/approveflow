import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowLeft, CheckCircle2, Lock } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { api } from "@/lib/api";
import { useUi } from "@/store/ui";

const schema = z
  .object({
    password: z
      .string()
      .min(8, "Password must be at least 8 characters")
      .regex(/[A-Z]/, "Must include at least one uppercase letter")
      .regex(/[0-9]/, "Must include at least one number")
      .regex(/[^A-Za-z0-9]/, "Must include at least one special character"),
    confirm_password: z.string(),
  })
  .refine((d) => d.password === d.confirm_password, {
    message: "Passwords do not match",
    path: ["confirm_password"],
  });

type FormValues = z.infer<typeof schema>;

export default function ResetPassword() {
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const nav = useNavigate();
  const toast = useUi((s) => s.toast);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { password: "", confirm_password: "" },
  });

  async function onSubmit(values: FormValues) {
    if (!token) {
      toast("Invalid or missing reset token", "err");
      return;
    }
    setLoading(true);
    try {
      await api.post("/api/v1/auth/reset-password", {
        token,
        password: values.password,
        confirm_password: values.confirm_password,
      });
      setSuccess(true);
      toast("Password successfully reset", "ok");
    } catch (err) {
      toast((err as Error).message || "Reset failed", "err");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-canvas flex items-center justify-center p-4">
      <div className="w-full max-w-md rounded-3xl border border-line bg-white p-8 shadow-card">
        <div className="mb-6 flex items-center justify-between">
          <Link to="/login" className="inline-flex items-center text-xs font-semibold text-brand-600 hover:text-brand-700">
            <ArrowLeft className="mr-1.5 h-4 w-4" /> Back to Sign In
          </Link>
          <img src={`${import.meta.env.BASE_URL}logo.png`} alt="ApproveFlow" className="h-6 w-auto" />
        </div>

        {success ? (
          <div className="py-6 text-center space-y-4">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600 border border-emerald-200">
              <CheckCircle2 className="h-6 w-6" />
            </div>
            <h2 className="text-xl font-bold text-ink">Password Updated</h2>
            <p className="text-xs text-slate-500">
              Your password has been securely reset. All previous sessions have been invalidated.
            </p>
            <Button className="w-full" onClick={() => nav("/login")}>
              Sign In with New Password
            </Button>
          </div>
        ) : (
          <div>
            <h1 className="text-2xl font-extrabold text-ink">Set New Password</h1>
            <p className="mt-1 text-xs text-slate-500">
              Create a new secure password for your ApproveFlow account.
            </p>

            {!token ? (
              <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs text-rose-700">
                Invalid or missing reset token. Please request a new password reset link from the login page.
              </div>
            ) : (
              <form onSubmit={form.handleSubmit(onSubmit)} className="mt-6 space-y-4">
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1">
                    New Password
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-3 h-4 w-4 text-slate-400" />
                    <input
                      type="password"
                      placeholder="Min 8 chars, uppercase, number, symbol"
                      className="w-full rounded-xl border border-line p-2.5 pl-10 text-sm"
                      {...form.register("password")}
                    />
                  </div>
                  {form.formState.errors.password && (
                    <p className="mt-1 text-xs text-rose-500">{form.formState.errors.password.message}</p>
                  )}
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1">
                    Confirm New Password
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-3 h-4 w-4 text-slate-400" />
                    <input
                      type="password"
                      placeholder="Re-enter new password"
                      className="w-full rounded-xl border border-line p-2.5 pl-10 text-sm"
                      {...form.register("confirm_password")}
                    />
                  </div>
                  {form.formState.errors.confirm_password && (
                    <p className="mt-1 text-xs text-rose-500">{form.formState.errors.confirm_password.message}</p>
                  )}
                </div>

                <Button type="submit" disabled={loading} className="w-full">
                  {loading ? "Updating Password…" : "Update Password"}
                </Button>
              </form>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
