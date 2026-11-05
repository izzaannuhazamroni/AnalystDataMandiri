"use client";

function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export const safeName = (s: string) => s.replace(/[^\w\-]+/g, "_").slice(0, 60) || "chart";

function serializeSvg(svg: SVGSVGElement): { xml: string; width: number; height: number } {
  const rect = svg.getBoundingClientRect();
  const width = Math.max(1, Math.round(rect.width));
  const height = Math.max(1, Math.round(rect.height));
  const clone = svg.cloneNode(true) as SVGSVGElement;
  clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  clone.setAttribute("width", String(width));
  clone.setAttribute("height", String(height));
  clone.setAttribute("viewBox", `0 0 ${width} ${height}`);
  const bg = document.createElementNS("http://www.w3.org/2000/svg", "rect");
  bg.setAttribute("width", "100%");
  bg.setAttribute("height", "100%");
  bg.setAttribute("fill", "#ffffff");
  clone.insertBefore(bg, clone.firstChild);
  return { xml: new XMLSerializer().serializeToString(clone), width, height };
}

export function downloadSvg(root: HTMLElement, filename: string) {
  const svg = root.querySelector("svg");
  if (!svg) throw new Error("Grafik belum siap.");
  const { xml } = serializeSvg(svg as SVGSVGElement);
  saveBlob(new Blob([xml], { type: "image/svg+xml;charset=utf-8" }), `${safeName(filename)}.svg`);
}

/** PNG resolusi tinggi (default 3x). */
export async function downloadPng(root: HTMLElement, filename: string, scale = 3) {
  const svg = root.querySelector("svg");
  if (!svg) throw new Error("Grafik belum siap.");
  const { xml, width, height } = serializeSvg(svg as SVGSVGElement);
  const url = URL.createObjectURL(new Blob([xml], { type: "image/svg+xml;charset=utf-8" }));
  const img = new Image();
  await new Promise<void>((resolve, reject) => {
    img.onload = () => resolve();
    img.onerror = () => reject(new Error("Gagal merender grafik."));
    img.src = url;
  });
  const canvas = document.createElement("canvas");
  canvas.width = width * scale;
  canvas.height = height * scale;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Canvas tidak tersedia.");
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
  URL.revokeObjectURL(url);
  await new Promise<void>((resolve) =>
    canvas.toBlob((b) => {
      if (b) saveBlob(b, `${safeName(filename)}.png`);
      resolve();
    }, "image/png"),
  );
}

/** Export seluruh dashboard ke PDF A4 siap cetak (elemen ber-atribut data-html2canvas-ignore dilewati). */
export async function exportDashboardPdf(el: HTMLElement, title: string) {
  const [{ default: html2canvas }, { jsPDF }] = await Promise.all([import("html2canvas"), import("jspdf")]);
  const canvas = await html2canvas(el, { scale: 2, backgroundColor: "#ffffff", useCORS: true, logging: false });
  const pdf = new jsPDF({ orientation: "portrait", unit: "mm", format: "a4" });
  const pageW = pdf.internal.pageSize.getWidth();
  const pageH = pdf.internal.pageSize.getHeight();
  const margin = 10;
  const imgW = pageW - margin * 2;
  const imgH = (canvas.height * imgW) / canvas.width;
  const contentH = pageH - margin * 2;
  const data = canvas.toDataURL("image/jpeg", 0.92);

  let offset = 0;
  let page = 0;
  while (offset < imgH - 0.5) {
    if (page > 0) pdf.addPage();
    pdf.addImage(data, "JPEG", margin, margin - offset, imgW, imgH);
    // tutup sisa gambar di luar area konten agar margin bersih
    pdf.setFillColor(255, 255, 255);
    pdf.rect(0, 0, pageW, margin, "F");
    pdf.rect(0, pageH - margin, pageW, margin, "F");
    offset += contentH;
    page += 1;
  }
  pdf.save(`${safeName(title)}.pdf`);
}
