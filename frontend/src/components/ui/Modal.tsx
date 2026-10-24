import { Button } from "./Button";

export function Modal({
  open,
  title,
  children,
  onClose,
  onConfirm,
  confirmLabel = "Confirm",
  danger,
}: {
  open: boolean;
  title: string;
  children: React.ReactNode;
  onClose: () => void;
  onConfirm?: () => void;
  confirmLabel?: string;
  danger?: boolean;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/30 p-4 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-card border border-line bg-white p-6 shadow-lift">
        <h3 className="text-lg font-semibold">{title}</h3>
        <div className="mt-3 text-sm text-slate-600">{children}</div>
        <div className="mt-5 flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          {onConfirm && (
            <Button variant={danger ? "danger" : "primary"} onClick={onConfirm}>
              {confirmLabel}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
