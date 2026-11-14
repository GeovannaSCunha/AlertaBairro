import type { Meta } from "@/lib/tipos";
import { dataBr, dataHoraBr } from "@/lib/formato";

export function Carregando({ texto = "Carregando os dados…" }: { texto?: string }) {
  return (
    <p className="carregando" role="status" aria-live="polite">
      {texto}
    </p>
  );
}

export function ErroCarga({ erro, recarregar }: { erro: string; recarregar?: () => void }) {
  return (
    <div className="erro-carga" role="alert">
      <p>{erro}</p>
      {recarregar && (
        <button type="button" className="botao botao--secundario" onClick={recarregar}>
          Tentar de novo
        </button>
      )}
    </div>
  );
}

/** Mostra de onde vem cada número: critério de aceite da proposta e item 08 da disciplina de Big Data. */
export function FonteDados({ meta, extra }: { meta: Meta; extra?: string }) {
  const snapshot = meta.origem === "snapshot";
  return (
    <p className="fonte-dados">
      <span className={snapshot ? "selo selo--snapshot" : "selo"}>
        {snapshot ? "Snapshot" : meta.origem === "comunidade" ? "Comunidade" : "Databricks"}
      </span>{" "}
      Fonte: tabela <code>{meta.tabela}</code>
      {meta.tabela_clima ? (
        <>
          {" "}
          e <code>{meta.tabela_clima}</code>
        </>
      ) : null}
      .{" "}
      {snapshot && meta.snapshot_validado_em
        ? `Valores validados em ${dataBr(meta.snapshot_validado_em)}. `
        : meta.consultado_em
          ? `Consultado em ${dataHoraBr(meta.consultado_em)}. `
          : ""}
      {meta.natureza === "historico" ? "Dados históricos, não em tempo real. " : ""}
      {extra}
      {meta.aviso ? <span className="sr-only"> {meta.aviso}</span> : null}
    </p>
  );
}

export function AvisoFonte({ meta }: { meta: Meta }) {
  if (!meta.aviso || meta.origem !== "snapshot") return null;
  return (
    <div className="aviso aviso--neutro">
      <p>{meta.aviso}</p>
    </div>
  );
}
