import { Lightbulb, Sparkles } from "lucide-react";

export default function NarrativeCard({ text }: { text: string | null }) {
  if (!text) return null;
  const lines = text.split("\n").map((l) => l.trim()).filter(Boolean);
  const bullets = lines.filter((l) => l.startsWith("- ")).map((l) => l.slice(2));
  const rec = lines.find((l) => l.startsWith("> "))?.slice(2);
  const other = lines.filter((l) => !l.startsWith("- ") && !l.startsWith("> "));

  return (
    <section className="card p-5">
      <h2 className="mb-3 flex items-center gap-2 text-base font-semibold">
        <Sparkles size={18} className="text-indigo-600" /> Ringkasan Eksekutif
      </h2>
      <ul className="space-y-1.5 text-sm text-slate-700">
        {[...bullets, ...other].map((b, i) => (
          <li key={i} className="flex gap-2">
            <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-indigo-400" />
            <span>{b}</span>
          </li>
        ))}
      </ul>
      {rec && (
        <div className="mt-4 flex gap-2 rounded-xl bg-amber-50 p-3 text-sm text-amber-900">
          <Lightbulb size={16} className="mt-0.5 shrink-0" />
          <span>{rec}</span>
        </div>
      )}
    </section>
  );
}
