import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/components/ui/Button";
import { api } from "@/lib/api";
import { useNavigate } from "react-router-dom";
import { useUi } from "@/store/ui";
import { useState } from "react";

const schema = z.object({
  application_type: z.string(),
  programme: z.string().min(3),
  intake: z.string().min(1),
  declaration: z.boolean(),
});

export default function NewApplication() {
  const [step, setStep] = useState(0);
  const nav = useNavigate();
  const toast = useUi((s) => s.toast);
  const form = useForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema),
    defaultValues: { application_type: "Extension", programme: "B.Tech Computer Science", intake: "60", declaration: true },
  });

  async function submit(values: z.infer<typeof schema>) {
    try {
      const res = await api.post<{ id: number; app_id: string }>("/api/v1/applications", { application_type: values.application_type });
      toast(`Submitted ${res.app_id}`);
      nav(`/app/applications/${res.id}`);
    } catch (e) {
      toast((e as Error).message, "err");
    }
  }

  return (
    <form onSubmit={form.handleSubmit(submit)} className="mx-auto max-w-xl space-y-4 rounded-card border border-line bg-white p-6 shadow-card">
      <h1 className="text-2xl font-extrabold">New application</h1>
      <p className="text-sm text-slate-500">Multi-step intake. Routing is selected from the application type; humans still decide later stages.</p>
      {step === 0 && (
        <>
          <label className="block text-sm">Type</label>
          <select className="w-full rounded-xl border border-line p-3" {...form.register("application_type")}>
            <option>New</option>
            <option>Extension</option>
            <option>Closure</option>
            <option>Increase in Intake</option>
            <option>New Campus</option>
          </select>
          <Button type="button" onClick={() => setStep(1)}>
            Continue
          </Button>
        </>
      )}
      {step === 1 && (
        <>
          <input className="w-full rounded-xl border border-line p-3" {...form.register("programme")} />
          <input className="w-full rounded-xl border border-line p-3" {...form.register("intake")} />
          <label className="flex gap-2 text-sm">
            <input type="checkbox" {...form.register("declaration")} /> I confirm this is simulated demo data.
          </label>
          <div className="flex gap-2">
            <Button type="button" variant="ghost" onClick={() => setStep(0)}>
              Back
            </Button>
            <Button type="submit">Submit for routing</Button>
          </div>
        </>
      )}
    </form>
  );
}
