import Link from "next/link";
import { BarChart3, FileSpreadsheet, MessageSquare, Share2, Sparkles, Zap } from "lucide-react";

const features = [
  { icon: Zap, title: "Dashboard < 10 detik", text: "Unggah file mentah; sistem membersihkan, memprofilkan, dan menyusun grafik terbaik otomatis." },
  { icon: BarChart3, title: "Smart Chart Recommender", text: "Aturan data science memilih Line, Donut, Bar, Scatter, atau Waterfall sesuai struktur data." },
  { icon: Sparkles, title: "Insight Bahasa Manusia", text: "Ringkasan eksekutif dan rekomendasi bisnis otomatis dari angka-angka Anda." },
  { icon: MessageSquare, title: "Ask My Data", text: "Tanya dengan bahasa natural, jawaban datang lengkap dengan grafiknya." },
  { icon: FileSpreadsheet, title: "Chart Studio Tanpa Kode", text: "Ganti tipe grafik, tukar sumbu, ubah agregasi, dan filter global dalam satu klik." },
  { icon: Share2, title: "Export & Bagikan", text: "PDF siap cetak, PNG/SVG resolusi tinggi, dan link read-only yang dapat dicabut." },
];

export default function Home() {
  return (
    <main>
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
        <span className="text-lg font-bold text-indigo-700">AutoAnalytica</span>
        <Link href="/login" className="btn-primary">Masuk</Link>
      </header>
      <section className="mx-auto max-w-4xl px-6 py-16 text-center">
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
          Dari file Excel mentah ke <span className="text-indigo-600">dashboard &amp; insight</span> — tanpa coding.
        </h1>
        <p className="mx-auto mt-5 max-w-2xl text-lg text-slate-600">
          Platform Self-Service BI berbasis AI untuk UMKM hingga profesional. Tanpa rumus, tanpa SQL, tanpa pivot.
        </p>
        <div className="mt-8 flex justify-center gap-3">
          <Link href="/login" className="btn-primary !px-5 !py-3 text-base">Mulai Gratis</Link>
        </div>
      </section>
      <section className="mx-auto grid max-w-6xl gap-4 px-6 pb-20 sm:grid-cols-2 lg:grid-cols-3">
        {features.map(({ icon: Icon, title, text }) => (
          <div key={title} className="card p-5">
            <span className="inline-flex rounded-lg bg-indigo-50 p-2 text-indigo-600"><Icon size={20} /></span>
            <h3 className="mt-3 font-semibold">{title}</h3>
            <p className="mt-1 text-sm text-slate-600">{text}</p>
          </div>
        ))}
      </section>
    </main>
  );
}
