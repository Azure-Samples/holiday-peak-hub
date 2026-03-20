export function random(min: number, max: number): number {
  return Math.floor(Math.random() * (max - min)) + min;
}

function formatDecimal(value: number, minimumFractionDigits: number, maximumFractionDigits: number): string {
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits,
    maximumFractionDigits,
  }).format(value);
}

export function formatPercent(percent: number): string {
  return `${formatDecimal(percent, 1, 1)}%`;
}

export function formatCurrency(value: number): string {
  return `$${formatDecimal(value, 2, 2).replace(/\.00$/g, "")}`;
}

export function formatNumber(value: number): string {
  return formatDecimal(value, 2, 2).replace(/\.00$/g, "");
}
