import { useMemo, useState } from "react";
import { Button } from "./Button";

export type Column<T> = { key: keyof T | string; header: string; render?: (row: T) => React.ReactNode };

export function DataTable<T extends Record<string, unknown>>({
  rows,
  columns,
  onRow,
}: {
  rows: T[];
  columns: Column<T>[];
  onRow?: (row: T) => void;
}) {
  const [q, setQ] = useState("");
  const [sort, setSort] = useState<string>(String(columns[0]?.key ?? ""));
  const [dir, setDir] = useState<1 | -1>(1);
  const [page, setPage] = useState(1);
  const [hidden, setHidden] = useState<string[]>([]);
  const size = 12;

  const filtered = useMemo(() => {
    const needle = q.toLowerCase();
    const list = rows.filter((r) => JSON.stringify(r).toLowerCase().includes(needle));
    list.sort((a, b) => {
      const av = String(a[sort] ?? "");
      const bv = String(b[sort] ?? "");
      return av.localeCompare(bv) * dir;
    });
    return list;
  }, [rows, q, sort, dir]);

  const slice = filtered.slice((page - 1) * size, page * size);
  const pages = Math.max(1, Math.ceil(filtered.length / size));
  const visible = columns.filter((c) => !hidden.includes(String(c.key)));

  function exportCsv() {
    const headers = visible.map((c) => c.header);
    const body = filtered.map((r) => visible.map((c) => JSON.stringify(r[String(c.key)] ?? "")).join(","));
    const blob = new Blob([[headers.join(","), ...body].join("\n")], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "approveflow-export.csv";
    a.click();
  }

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <input
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setPage(1);
          }}
          placeholder="Filter rows"
          className="rounded-xl border border-line px-3 py-2 text-sm"
        />
        <Button variant="outline" size="sm" onClick={exportCsv}>
          Export CSV
        </Button>
        <div className="ml-auto flex flex-wrap gap-2 text-xs text-slate-500">
          {columns.map((c) => (
            <label key={String(c.key)} className="flex items-center gap-1">
              <input
                type="checkbox"
                checked={!hidden.includes(String(c.key))}
                onChange={(e) =>
                  setHidden((h) => (e.target.checked ? h.filter((x) => x !== String(c.key)) : [...h, String(c.key)]))
                }
              />
              {c.header}
            </label>
          ))}
        </div>
      </div>
      <div className="overflow-x-auto rounded-card border border-line">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-canvas text-xs uppercase text-slate-500">
            <tr>
              {visible.map((c) => (
                <th key={String(c.key)} className="cursor-pointer px-3 py-2" onClick={() => {
                  setSort(String(c.key));
                  setDir((d) => (sort === String(c.key) ? (d === 1 ? -1 : 1) : 1));
                }}>
                  {c.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {slice.map((row, i) => (
              <tr
                key={i}
                onClick={() => onRow?.(row)}
                className="cursor-pointer border-t border-line hover:bg-canvas/80"
              >
                {visible.map((c) => (
                  <td key={String(c.key)} className="px-3 py-2">
                    {c.render ? c.render(row) : String(row[String(c.key)] ?? "")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mt-3 flex items-center justify-between text-sm text-slate-500">
        <span>
          {filtered.length} rows · page {page}/{pages}
        </span>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" disabled={page === 1} onClick={() => setPage((p) => p - 1)}>
            Prev
          </Button>
          <Button variant="outline" size="sm" disabled={page === pages} onClick={() => setPage((p) => p + 1)}>
            Next
          </Button>
        </div>
      </div>
    </div>
  );
}
