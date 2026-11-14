"use client";

import { useApi } from "@/lib/api";
import { dataBr, dataHoraBr } from "@/lib/formato";
import type { StatusApi } from "@/lib/tipos";

export default function StatusIntegracoes() {
  const status = useApi<StatusApi>("/status");
  if (status.erro) {
    return (
      <div className="erro-carga" role="alert">
        <p>A API não respondeu: {status.erro}</p>
      </div>
    );
  }
  if (!status.dados) return null;
  const d = status.dados.dados;
  const assistente = status.dados.assistente.modo === "llm" ? "modelo de linguagem" : "respostas montadas dos dados";
  return (
    <section className="superficie" aria-labelledby="t-status">
      <h2 id="t-status">Situação agora</h2>
      <p style={{ marginBottom: 0 }}>
        {d.modo === "databricks"
          ? `A API está lendo o catálogo ${d.catalogo} no Databricks.${
              d.ultima_consulta_ok ? ` Última consulta bem-sucedida: ${dataHoraBr(d.ultima_consulta_ok)}.` : ""
            }${d.falhas_consecutivas ? ` Falhas seguidas: ${d.falhas_consecutivas}.` : ""}`
          : `A API está usando o snapshot validado em ${dataBr(d.snapshot_validado_em)}, porque a conexão com o Databricks não está configurada neste ambiente.`}{" "}
        Assistente: {assistente}. Versão {status.dados.versao}.
      </p>
    </section>
  );
}
