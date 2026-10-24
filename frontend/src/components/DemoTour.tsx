import { useUi } from "@/store/ui";
import { Button } from "./ui/Button";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

const STEPS = [
  { title: "Role-based workbench", body: "Each demo role sees a different dashboard. Switch roles from the header.", to: "/app" },
  { title: "Stage pipeline", body: "The 3D pipeline summarises pendency. Click a node to filter applications.", to: "/app" },
  { title: "Human routing", body: "Forward and return are authorised human actions. Nothing auto-approves.", to: "/app/applications" },
  { title: "EVC calendar", body: "Schedule visits, detect double-booking, and record a recommendation only.", to: "/app/evc" },
  { title: "Alerts never decide", body: "Reminders and the escalation ladder support officers. Run jobs from Monitoring.", to: "/app/admin/monitor" },
];

export function DemoTour() {
  const open = useUi((s) => s.tourOpen);
  const setTour = useUi((s) => s.setTour);
  const [i, setI] = useState(0);
  const nav = useNavigate();
  if (!open) return null;
  const step = STEPS[i];
  return (
    <div className="fixed bottom-6 right-6 z-[55] w-80 rounded-card border border-line bg-white p-5 shadow-lift">
      <p className="text-xs uppercase tracking-wide text-slate-400">
        Demo tour {i + 1}/{STEPS.length}
      </p>
      <h3 className="mt-1 font-semibold">{step.title}</h3>
      <p className="mt-2 text-sm text-slate-600">{step.body}</p>
      <div className="mt-4 flex gap-2">
        <Button
          size="sm"
          onClick={() => {
            nav(step.to);
            if (i === STEPS.length - 1) setTour(false);
            else setI((x) => x + 1);
          }}
        >
          {i === STEPS.length - 1 ? "Finish" : "Next"}
        </Button>
        <Button variant="ghost" size="sm" onClick={() => setTour(false)}>
          Close
        </Button>
      </div>
    </div>
  );
}
