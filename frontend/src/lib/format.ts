const idCompact = new Intl.NumberFormat("id-ID", { notation: "compact", maximumFractionDigits: 1 });
const idNumber = new Intl.NumberFormat("id-ID", { maximumFractionDigits: 2 });
const idCurrency = new Intl.NumberFormat("id-ID", {
  style: "currency",
  currency: "IDR",
  maximumFractionDigits: 0,
});
const idPercent = new Intl.NumberFormat("id-ID", {
  style: "percent",
  maximumFractionDigits: 1,
  signDisplay: "exceptZero",
});

export const compact = (n: number | null | undefined) => (n == null ? "-" : idCompact.format(n));
export const formatNumber = (n: number | null | undefined) => (n == null ? "-" : idNumber.format(n));
export const formatCurrency = (n: number | null | undefined) => (n == null ? "-" : idCurrency.format(n));
export const formatPercent = (n: number | null | undefined) => (n == null ? "-" : idPercent.format(n));
