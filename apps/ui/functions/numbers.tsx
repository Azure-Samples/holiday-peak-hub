import accounting from "accounting";

export function random(min: number, max: number): number {
  return Math.floor(Math.random() * (max - min)) + min;
}

export function formatPercent(percent: number): string {
  return `${accounting
    .formatMoney(percent, "", 1, ",", ".")
    .replace(/\.00$/g, "")}%`;
}

export function formatCurrency(value: number): string {
  return accounting.formatMoney(value, "$", 2, ",", ".").replace(/\.00$/g, "");
}

export function formatNumber(value: number): string {
  return accounting.formatMoney(value, "", 2, ",", ".").replace(/\.00$/g, "");
}
