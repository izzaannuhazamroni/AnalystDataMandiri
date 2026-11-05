import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AutoAnalytica — AI Data Analyst & BI Dashboard",
  description: "Unggah Excel/CSV, dapatkan dashboard interaktif dan insight bisnis otomatis dalam hitungan detik.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="id">
      <body className="min-h-screen font-sans antialiased">{children}</body>
    </html>
  );
}
