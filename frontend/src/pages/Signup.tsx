import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowLeft, Building, CheckCircle2, Lock, Mail, Phone, ShieldAlert, UserCheck } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Safeguard } from "@/components/layout/Safeguard";
import { api } from "@/lib/api";
import { useUi } from "@/store/ui";

const schema = z
  .object({
    full_name: z.string().min(2, "Full name must be at least 2 characters"),
    email: z.string().email("Enter a valid official email address"),
    mobile: z.string().min(10, "Enter a valid 10-digit mobile number").max(15),
    institution_name: z.string().min(3, "Institution name must be at least 3 characters"),
    institution_code: z.string().min(2, "Enter institution code or identifier"),
    region_id: z.coerce.number().min(1, "Please select an applicable AICTE region"),
    requested_role: z.literal("institution_user"),
    password: z
      .string()
      .min(8, "Password must be at least 8 characters")
      .regex(/[A-Z]/, "Must include at least one uppercase letter")
      .regex(/[0-9]/, "Must include at least one number")
      .regex(/[^A-Za-z0-9]/, "Must include at least one special character"),
    confirm_password: z.string(),
    accept_terms: z.literal(true, {
      errorMap: () => ({ message: "You must accept the statutory compliance terms" }),
    }),
  })
  .refine((data) => data.password === data.confirm_password, {
    message: "Passwords do not match",
    path: ["confirm_password"],
  });

type FormValues = z.infer<typeof schema>;

export default function Signup() {
  const nav = useNavigate();
  const toast = useUi((s) => s.toast);
  const [regions, setRegions] = useState<{ id: number; name: string; code: string }[]>([]);
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState<string | null>(null);

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      full_name: "",
      email: "",
      mobile: "",
      institution_name: "",
      institution_code: "",
      region_id: 1,
      requested_role: "institution_user",
      password: "",
      confirm_password: "",
      accept_terms: true as unknown as undefined,
    },
  });

  useEffect(() => {
    api
      .get<{ regions: { id: number; name: string; code: string }[] }>("/api/v1/auth/catalog")
      .then((res) => {
        if (res.regions) setRegions(res.regions);
      })
      .catch(() => {
        // Fallback default regions if offline
        setRegions([
          { id: 1, name: "Northern Region", code: "NR" },
          { id: 2, name: "Southern Region", code: "SR" },
          { id: 3, name: "Western Region", code: "WR" },
          { id: 4, name: "Eastern Region", code: "ER" },
          { id: 5, name: "Central Region", code: "CR" },
          { id: 6, name: "North-Western Region", code: "NWR" },
          { id: 7, name: "South-Western Region", code: "SWR" },
        ]);
      });
  }, []);

  async function onSubmit(values: FormValues) {
    setLoading(true);
    try {
      const res = await api.post<{ ok: boolean; message: string; status: string }>("/api/v1/auth/register", values);
      setSubmitted(res.message);
      toast("Registration submitted successfully", "ok");
    } catch (err) {
      toast((err as Error).message || "Registration failed", "err");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-canvas py-12 px-4 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-2xl">
        <div className="mb-6 flex items-center justify-between">
          <Link to="/login" className="inline-flex items-center text-xs font-semibold text-brand-600 hover:text-brand-700">
            <ArrowLeft className="mr-1.5 h-4 w-4" /> Back to Sign In
          </Link>
          <div className="flex items-center gap-2">
            <img src={`${import.meta.env.BASE_URL}logo.png`} alt="ApproveFlow" className="h-6 w-auto" />
            <span className="font-extrabold text-sm text-ink">ApproveFlow AICTE</span>
          </div>
        </div>

        <div className="rounded-3xl border border-line bg-white p-6 sm:p-10 shadow-card">
          {submitted ? (
            <div className="py-8 text-center space-y-4">
              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600 border border-emerald-200">
                <CheckCircle2 className="h-8 w-8" />
              </div>
              <h2 className="text-2xl font-extrabold text-ink">Registration Received</h2>
              <p className="max-w-md mx-auto text-sm text-slate-600">{submitted}</p>

              <div className="rounded-2xl border border-sky-100 bg-sky-50/60 p-4 text-xs text-sky-900 text-left max-w-lg mx-auto">
                <p className="font-semibold mb-1 flex items-center gap-1.5">
                  <ShieldAlert className="h-4 w-4 text-sky-600" /> Administrative Identity Verification
                </p>
                <p>
                  As an anti-fraud statutory safeguard, public registration accounts remain in <strong>Pending</strong> state until verified against the AICTE Institution Master Register by an authorized officer.
                </p>
              </div>

              <div className="pt-4 flex justify-center gap-3">
                <Button onClick={() => nav("/login")}>Proceed to Sign In</Button>
              </div>
            </div>
          ) : (
            <div>
              <div className="mb-8">
                <span className="rounded-md bg-brand-50 px-2.5 py-1 text-xs font-semibold text-brand-700 border border-brand-200">
                  Institution Registration
                </span>
                <h1 className="mt-3 text-2xl sm:text-3xl font-extrabold tracking-tight text-ink">
                  Register Your Institution
                </h1>
                <p className="mt-1.5 text-sm text-slate-500">
                  Submit principal or institutional administrator credentials for portal access and compliance filing.
                </p>
              </div>

              {/* Informative Security Banner */}
              <div className="mb-6 rounded-2xl border border-amber-200 bg-amber-50/70 p-4 text-xs text-amber-900">
                <p className="font-semibold mb-0.5">Statutory Authorization Requirement</p>
                <p>
                  Privileged roles (Regional Officers, Bureau Officers, Scrutiny Officers, EVC Members, Competent Authorities) cannot self-register. They are provisioned by AICTE System Administrators.
                </p>
              </div>

              <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                <div className="grid sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
                      Full Name (Principal / Registrar)
                    </label>
                    <input
                      placeholder="Dr. S. K. Narayanan"
                      className="w-full rounded-xl border border-line p-2.5 text-sm text-ink focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                      {...form.register("full_name")}
                    />
                    {form.formState.errors.full_name && (
                      <p className="mt-1 text-xs text-rose-500">{form.formState.errors.full_name.message}</p>
                    )}
                  </div>

                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
                      Official Email Address
                    </label>
                    <input
                      type="email"
                      placeholder="principal@college.edu.in"
                      className="w-full rounded-xl border border-line p-2.5 text-sm text-ink focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                      {...form.register("email")}
                    />
                    {form.formState.errors.email && (
                      <p className="mt-1 text-xs text-rose-500">{form.formState.errors.email.message}</p>
                    )}
                  </div>
                </div>

                <div className="grid sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
                      Mobile Number
                    </label>
                    <input
                      type="tel"
                      placeholder="9876543210"
                      className="w-full rounded-xl border border-line p-2.5 text-sm text-ink focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                      {...form.register("mobile")}
                    />
                    {form.formState.errors.mobile && (
                      <p className="mt-1 text-xs text-rose-500">{form.formState.errors.mobile.message}</p>
                    )}
                  </div>

                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
                      AICTE Region
                    </label>
                    <select
                      className="w-full rounded-xl border border-line p-2.5 text-sm text-ink bg-white focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                      {...form.register("region_id")}
                    >
                      {regions.map((r) => (
                        <option key={r.id} value={r.id}>
                          {r.name} ({r.code})
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="grid sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
                      Institution Name
                    </label>
                    <input
                      placeholder="e.g. Nalanda Institute of Technology"
                      className="w-full rounded-xl border border-line p-2.5 text-sm text-ink focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                      {...form.register("institution_name")}
                    />
                    {form.formState.errors.institution_name && (
                      <p className="mt-1 text-xs text-rose-500">{form.formState.errors.institution_name.message}</p>
                    )}
                  </div>

                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
                      Institution Code / Permanent ID
                    </label>
                    <input
                      placeholder="e.g. 1-12345678 or INS-101"
                      className="w-full rounded-xl border border-line p-2.5 text-sm text-ink focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                      {...form.register("institution_code")}
                    />
                    {form.formState.errors.institution_code && (
                      <p className="mt-1 text-xs text-rose-500">{form.formState.errors.institution_code.message}</p>
                    )}
                  </div>
                </div>

                <div className="grid sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
                      Account Password
                    </label>
                    <input
                      type="password"
                      placeholder="Min 8 chars, uppercase, number, symbol"
                      className="w-full rounded-xl border border-line p-2.5 text-sm text-ink focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                      {...form.register("password")}
                    />
                    {form.formState.errors.password && (
                      <p className="mt-1 text-xs text-rose-500">{form.formState.errors.password.message}</p>
                    )}
                  </div>

                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
                      Confirm Password
                    </label>
                    <input
                      type="password"
                      placeholder="Re-enter your password"
                      className="w-full rounded-xl border border-line p-2.5 text-sm text-ink focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                      {...form.register("confirm_password")}
                    />
                    {form.formState.errors.confirm_password && (
                      <p className="mt-1 text-xs text-rose-500">{form.formState.errors.confirm_password.message}</p>
                    )}
                  </div>
                </div>

                <div className="pt-2">
                  <div className="flex items-start">
                    <input
                      id="accept_terms"
                      type="checkbox"
                      className="mt-1 h-4 w-4 rounded border-line text-brand-600 focus:ring-brand-500"
                      {...form.register("accept_terms")}
                    />
                    <label htmlFor="accept_terms" className="ml-2 block text-xs text-slate-600 leading-relaxed">
                      I declare that I am the authorized representative of this technical institution. I agree to comply with the AICTE Approval Process Handbook (2024–2027) regulations, maintain true land lease & compliance documentation, and understand that submission of false data invites penal action under AICTE Act.
                    </label>
                  </div>
                  {form.formState.errors.accept_terms && (
                    <p className="mt-1 text-xs text-rose-500">{form.formState.errors.accept_terms.message}</p>
                  )}
                </div>

                <div className="pt-4">
                  <Button type="submit" disabled={loading} className="w-full py-3">
                    {loading ? "Submitting Registration…" : "Register Institution Account"}
                  </Button>
                </div>
              </form>
            </div>
          )}
        </div>

        <div className="mt-8">
          <Safeguard />
        </div>
      </div>
    </div>
  );
}
