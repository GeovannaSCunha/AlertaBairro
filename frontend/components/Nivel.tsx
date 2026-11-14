import type { NivelCodigo } from "@/lib/tipos";

export function Nivel({ nivel, rotulo }: { nivel: NivelCodigo; rotulo: string }) {
  return <span className={`nivel nivel--${nivel}`}>{rotulo}</span>;
}

export function PontosIndice({ h, c }: { h: number; c: number }) {
  const total = 5;
  return (
    <span className="pontos-indice" aria-label={`${h} ponto(s) de histórico e ${c} de chuva, de 5 possíveis`}>
      {Array.from({ length: total }, (_, i) => (
        <i key={i} className={i < h ? "h" : i < h + c ? "c" : undefined} />
      ))}
    </span>
  );
}
