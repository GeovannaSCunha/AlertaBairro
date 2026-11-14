// Gráficos em SVG puro: leves (bom para celulares de entrada), acessíveis e sem dependências.
import { diaMes, mesBr, mesCurto, mm, numero } from "@/lib/formato";
import type { DiaChuva, PontoMensal, Subprefeitura } from "@/lib/tipos";

/* ---------------------------------------------------------------- ranking horizontal */
export function RankingBarras({
  itens,
  destaque,
  descricao,
}: {
  itens: Subprefeitura[];
  destaque?: string | null;
  descricao: string;
}) {
  const largura = 640;
  const alturaLinha = 34;
  const margemEsq = 200;
  const margemDir = 52;
  const altura = itens.length * alturaLinha + 8;
  const maximo = Math.max(1, ...itens.map((i) => i.total_ocorrencias));
  const escala = (v: number) => (v / maximo) * (largura - margemEsq - margemDir);

  return (
    <figure style={{ margin: 0 }}>
      <svg className="grafico" viewBox={`0 0 ${largura} ${altura}`} role="img" aria-label={descricao}>
        {itens.map((item, i) => {
          const y = i * alturaLinha + 4;
          const w = Math.max(2, escala(item.total_ocorrencias));
          const ehDestaque = destaque === item.chave;
          return (
            <g key={item.chave || item.subprefeitura}>
              <text x={margemEsq - 10} y={y + 19} textAnchor="end" className={ehDestaque ? "rotulo-valor" : undefined}>
                {item.subprefeitura.length > 26 ? `${item.subprefeitura.slice(0, 25)}…` : item.subprefeitura}
              </text>
              <rect
                x={margemEsq}
                y={y + 5}
                width={w}
                height={alturaLinha - 12}
                rx={3}
                className={ehDestaque ? "barra barra--destaque" : "barra"}
              />
              <text x={margemEsq + w + 8} y={y + 19} className="rotulo-valor">
                {numero(item.total_ocorrencias)}
              </text>
            </g>
          );
        })}
      </svg>
    </figure>
  );
}

/* ---------------------------------------------------------------- série mensal com lacunas */
export function ColunasMensais({ serie, lacunas }: { serie: PontoMensal[]; lacunas: string[] }) {
  const meses = [...serie.map((s) => ({ mes: s.mes.slice(0, 7), valor: s.total_ocorrencias as number | null })),
    ...lacunas.map((l) => ({ mes: l, valor: null as number | null }))].sort((a, b) => a.mes.localeCompare(b.mes));
  const largura = 640;
  const altura = 260;
  const base = 220;
  const topo = 24;
  const passo = (largura - 20) / Math.max(1, meses.length);
  const larguraBarra = Math.min(48, passo * 0.62);
  const maximo = Math.max(1, ...meses.map((m) => m.valor ?? 0));
  const h = (v: number) => (v / maximo) * (base - topo);
  const resumo = meses
    .map((m) => `${mesBr(m.mes)}: ${m.valor === null ? "sem linha na tabela" : `${m.valor} registros`}`)
    .join("; ");

  return (
    <figure style={{ margin: 0 }}>
      <svg className="grafico" viewBox={`0 0 ${largura} ${altura}`} role="img" aria-label={`Registros de alagamento por mês. ${resumo}.`}>
        <defs>
          <pattern id="hachura" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <line x1="0" y1="0" x2="0" y2="6" stroke="var(--linha)" strokeWidth="2" />
          </pattern>
        </defs>
        <line x1={10} x2={largura - 10} y1={base} y2={base} className="eixo" />
        {meses.map((m, i) => {
          const cx = 10 + passo * i + passo / 2;
          if (m.valor === null) {
            return (
              <g key={m.mes}>
                <rect x={cx - larguraBarra / 2} y={base - 46} width={larguraBarra} height={46} className="lacuna" rx={3} />
                <text x={cx} y={base - 54} textAnchor="middle">
                  sem dado
                </text>
                <text x={cx} y={base + 22} textAnchor="middle">
                  {mesCurto(m.mes)}
                </text>
              </g>
            );
          }
          const altBarra = Math.max(2, h(m.valor));
          return (
            <g key={m.mes}>
              <rect x={cx - larguraBarra / 2} y={base - altBarra} width={larguraBarra} height={altBarra} rx={3} className="barra" />
              <text x={cx} y={base - altBarra - 7} textAnchor="middle" className="rotulo-valor">
                {numero(m.valor)}
              </text>
              <text x={cx} y={base + 22} textAnchor="middle">
                {mesCurto(m.mes)}
              </text>
            </g>
          );
        })}
      </svg>
      <ul className="legenda">
        <li>
          <i style={{ background: "var(--garoa)" }} />
          Registros no mês
        </li>
        {lacunas.length > 0 && (
          <li>
            <i style={{ background: "var(--nuvem-2)", border: "1px dashed var(--concreto)" }} />
            Mês sem linha na tabela (não significa zero)
          </li>
        )}
      </ul>
    </figure>
  );
}

/* ---------------------------------------------------------------- chuva diária + acumulado */
export function GraficoChuva({ serie, destaque }: { serie: DiaChuva[]; destaque?: string | null }) {
  const largura = 640;
  const altura = 280;
  const base = 236;
  const topo = 28;
  const passo = (largura - 60) / Math.max(1, serie.length);
  const larguraBarra = Math.min(40, passo * 0.6);
  const maxDia = Math.max(1, ...serie.map((d) => d.precipitacao_mm ?? 0));
  const maxAcum = Math.max(1, ...serie.map((d) => d.precipitacao_acumulada_mm ?? 0));
  const hDia = (v: number) => (v / maxDia) * (base - topo) * 0.78;
  const yAcum = (v: number) => base - (v / maxAcum) * (base - topo);
  const pontosLinha = serie
    .map((d, i) => `${30 + passo * i + passo / 2},${yAcum(d.precipitacao_acumulada_mm ?? 0)}`)
    .join(" ");
  const resumo = serie.map((d) => `${diaMes(d.data)}: ${mm(d.precipitacao_mm)}`).join("; ");

  return (
    <figure style={{ margin: 0 }}>
      <svg className="grafico" viewBox={`0 0 ${largura} ${altura}`} role="img" aria-label={`Chuva diária no ponto de referência. ${resumo}.`}>
        <line x1={20} x2={largura - 20} y1={base} y2={base} className="eixo" />
        {serie.map((d, i) => {
          const v = d.precipitacao_mm ?? 0;
          const cx = 30 + passo * i + passo / 2;
          const a = Math.max(v > 0 ? 2 : 0, hDia(v));
          return (
            <g key={d.data}>
              <rect
                x={cx - larguraBarra / 2}
                y={base - a}
                width={larguraBarra}
                height={a}
                rx={3}
                className={destaque === d.data ? "barra barra--destaque" : "barra barra--chuva"}
              />
              <text x={cx} y={base + 22} textAnchor="middle">
                {diaMes(d.data)}
              </text>
            </g>
          );
        })}
        <polyline points={pontosLinha} className="linha-acumulada" />
        {serie.map((d, i) => {
          const v = d.precipitacao_mm ?? 0;
          const cx = 30 + passo * i + passo / 2;
          const a = Math.max(v > 0 ? 2 : 0, hDia(v));
          return (
            <text key={`r-${d.data}`} x={cx} y={base - a - 7} textAnchor="middle" className="rotulo-valor">
              {numero(v, 1)}
            </text>
          );
        })}
        {serie.length > 0 && (
          <text
            x={30 + passo * (serie.length - 1) + passo / 2}
            y={yAcum(serie[serie.length - 1].precipitacao_acumulada_mm ?? 0) - 10}
            textAnchor="end"
            className="rotulo-valor"
          >
            {mm(serie[serie.length - 1].precipitacao_acumulada_mm)} acumulados
          </text>
        )}
      </svg>
      <ul className="legenda">
        <li>
          <i style={{ background: "var(--agua)" }} />
          Chuva no dia (mm)
        </li>
        <li>
          <i style={{ background: "var(--asfalto)", height: "3px", verticalAlign: "0.2rem" }} />
          Acumulado no período
        </li>
        {destaque && (
          <li>
            <i style={{ background: "var(--sinal)" }} />
            Dia mais chuvoso
          </li>
        )}
      </ul>
    </figure>
  );
}

/** Gotas decorativas de fundo, desenhadas a partir da chuva real (uma coluna por dia). */
export function ChuvaDeFundo({ serie }: { serie: DiaChuva[] }) {
  if (!serie.length) return null;
  const maximo = Math.max(1, ...serie.map((d) => d.precipitacao_mm ?? 0));
  return (
    <svg className="chuva-de-fundo" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
      {serie.map((d, i) => {
        const gotas = Math.round(((d.precipitacao_mm ?? 0) / maximo) * 9);
        const x = 4 + (92 / serie.length) * i + 46 / serie.length;
        return Array.from({ length: gotas }, (_, j) => (
          <line
            key={`${d.data}-${j}`}
            x1={x + (j % 2) * 2.4}
            x2={x + (j % 2) * 2.4 - 1.2}
            y1={6 + j * 10}
            y2={11 + j * 10}
            stroke="var(--agua-suave)"
            strokeWidth="0.9"
            strokeLinecap="round"
          />
        ));
      })}
    </svg>
  );
}
