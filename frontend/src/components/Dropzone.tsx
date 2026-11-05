"use client";

import { useCallback, useState } from "react";
import { useDropzone, type FileRejection } from "react-dropzone";
import { useRouter } from "next/navigation";
import { CheckCircle2, FileSpreadsheet, Loader2, UploadCloud } from "lucide-react";
import { api } from "@/lib/api";
import { BUCKET, getSupabase } from "@/lib/supabase";

const MAX_BYTES = 50 * 1024 * 1024;
type Step = "idle" | "uploading" | "analyzing" | "done";

export default function Dropzone({ onUploaded }: { onUploaded?: () => void }) {
  const router = useRouter();
  const [step, setStep] = useState<Step>("idle");
  const [error, setError] = useState<string | null>(null);
  const [fileName, setFileName] = useState("");

  const handle = useCallback(
    async (file: File) => {
      setError(null);
      setFileName(file.name);
      const sb = getSupabase();
      let datasetId: string | null = null;
      let path: string | null = null;
      try {
        const { data: u } = await sb.auth.getUser();
        if (!u.user) throw new Error("Sesi berakhir. Silakan login ulang.");

        setStep("uploading");
        const safe = file.name.replace(/[^\w.\-]+/g, "_");
        path = `${u.user.id}/${crypto.randomUUID()}-${safe}`;
        const up = await sb.storage.from(BUCKET).upload(path, file, { upsert: false });
        if (up.error) throw new Error(`Upload gagal: ${up.error.message}`);

        const ins = await sb
          .from("datasets")
          .insert({ user_id: u.user.id, file_name: file.name, file_path: path, file_size: file.size, status: "uploaded" })
          .select("id")
          .single();
        if (ins.error) throw new Error(`Gagal menyimpan dataset: ${ins.error.message}`);
        datasetId = ins.data.id as string;
        onUploaded?.();

        setStep("analyzing");
        const r = await api<{ dashboard_id: string }>(`/api/datasets/${datasetId}/analyze`, { method: "POST" });
        setStep("done");
        router.push(`/dashboard/${r.dashboard_id}`);
      } catch (e) {
        setStep("idle");
        setError(e instanceof Error ? e.message : "Terjadi kesalahan.");
        if (datasetId) onUploaded?.();
      }
    },
    [onUploaded, router],
  );

  const onDrop = useCallback(
    (accepted: File[], rejected: FileRejection[]) => {
      if (rejected.length) {
        const code = rejected[0].errors[0]?.code;
        setError(
          code === "file-too-large"
            ? "Ukuran file melebihi 50MB."
            : "Format tidak didukung. Gunakan .xlsx, .xls, atau .csv.",
        );
        return;
      }
      if (accepted[0]) void handle(accepted[0]);
    },
    [handle],
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: false,
    maxSize: MAX_BYTES,
    disabled: step === "uploading" || step === "analyzing",
    accept: {
      "text/csv": [".csv"],
      "application/vnd.ms-excel": [".xls", ".csv"],
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
    },
  });

  const busy = step === "uploading" || step === "analyzing";

  return (
    <div>
      <div
        {...getRootProps()}
        className={`card flex cursor-pointer flex-col items-center justify-center gap-2 border-2 border-dashed px-6 py-12 text-center transition ${
          isDragActive ? "border-indigo-500 bg-indigo-50" : "border-slate-300 hover:border-indigo-400"
        } ${busy ? "pointer-events-none opacity-80" : ""}`}
      >
        <input {...getInputProps()} />
        {busy ? (
          <>
            <Loader2 className="animate-spin text-indigo-600" size={36} />
            <p className="font-medium">{step === "uploading" ? "Mengunggah file…" : "Menganalisis data & membuat dashboard…"}</p>
            <p className="flex items-center gap-1 text-sm text-slate-500">
              <FileSpreadsheet size={14} /> {fileName}
            </p>
          </>
        ) : step === "done" ? (
          <>
            <CheckCircle2 className="text-emerald-600" size={36} />
            <p className="font-medium">Selesai! Membuka dashboard…</p>
          </>
        ) : (
          <>
            <UploadCloud className="text-indigo-600" size={36} />
            <p className="font-medium">Seret &amp; lepas file di sini, atau klik untuk memilih</p>
            <p className="text-sm text-slate-500">.xlsx, .xls, .csv — maksimal 50MB</p>
          </>
        )}
      </div>
      {error && <p className="mt-3 rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}
    </div>
  );
}
