const MESES = [
  "janeiro",
  "fevereiro",
  "março",
  "abril",
  "maio",
  "junho",
  "julho",
  "agosto",
  "setembro",
  "outubro",
  "novembro",
  "dezembro",
];
const MESES_CURTOS = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];

export function numero(n: number | null | undefined, casas = 0): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "–";
  return n.toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });
}

export function mm(n: number | null | undefined): string {
  return n === null || n === undefined ? "–" : `${numero(n, 1)} mm`;
}

/** "2026-10-29" → "29/10/2026" (sem conversão de fuso: a data já é local). */
export function dataBr(iso: string | null | undefined): string {
  if (!iso) return "–";
  const [a, m, d] = iso.slice(0, 10).split("-");
  return d && m && a ? `${d}/${m}/${a}` : iso;
}

export function diaMes(iso: string): string {
  const [, m, d] = iso.slice(0, 10).split("-");
  return `${d}/${m}`;
}

/** "2026-01" ou "2026-01-01" → "janeiro de 2026" */
export function mesBr(iso: string | null | undefined): string {
  if (!iso) return "–";
  const ano = iso.slice(0, 4);
  const mes = Number(iso.slice(5, 7));
  return `${MESES[mes - 1] ?? iso} de ${ano}`;
}

export function mesCurto(iso: string): string {
  return MESES_CURTOS[Number(iso.slice(5, 7)) - 1] ?? iso;
}

export function periodoMeses(inicio: string | null, fim: string | null): string {
  if (!inicio || !fim) return "–";
  if (inicio.slice(0, 4) === fim.slice(0, 4)) {
    return `${MESES[Number(inicio.slice(5, 7)) - 1]} a ${mesBr(fim)}`;
  }
  return `${mesBr(inicio)} a ${mesBr(fim)}`;
}

export function dataHoraBr(iso: string | null | undefined): string {
  if (!iso) return "–";
  const data = new Date(iso);
  if (Number.isNaN(data.getTime())) return iso;
  return data.toLocaleString("pt-BR", {
    timeZone: "America/Sao_Paulo",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function plural(n: number, singular: string, pluralForma: string): string {
  return `${numero(n)} ${n === 1 ? singular : pluralForma}`;
}
