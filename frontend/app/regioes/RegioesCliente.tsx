"use client";

import { useState } from "react";

import { Carregando, ErroCarga, FonteDados } from "@/components/Estados";
import { ColunasMensais, RankingBarras } from "@/components/Graficos";
import { useApi } from "@/lib/api";
import { dataBr, mesBr, numero } from "@/lib/formato";
import type { Envelope, Mensal, Ranking } from "@/lib/tipos";

const capitalizar = (t: string) => t.charAt(0).toUpperCase() + t.slice(1);

export default function RegioesCliente() {
  const ranking = useApi<Envelope<Ranking>>("/alagamentos/subprefeituras?limit=50");
  const mensal = useApi<Envelope<Mensal>>("/alagamentos/mensal");
  const [destaque, setDestaque] = useState<string>("");

  const itens = ranking.dados?.dados.itens ?? [];
  const demais = ranking.dados?.dados.demais;
  const total = itens.reduce((s, i) => s + i.total_ocorrencias, 0) + (demais?.total_ocorrencias ?? 0);
  const serie = mensal.dados?.dados.serie ?? [];
  const pico = serie.reduce<(typeof serie)[number] | null>((m, x) => (!m || x.total_ocorrencias > m.total_ocorrencias ? x : m), null);

  return (
    <>
      <div className="titulo-pagina">
        <h1>Regiões e meses</h1>
        <p>
          Onde e quando estão os registros de alagamento da base. O ranking mostra quantos registros cada região tem,
          sem considerar população, área ou gravidade.
        </p>
      </div>

      <section className="superficie" aria-labelledby="titulo-ranking">
        <h2 id="titulo-ranking">Registros por subprefeitura</h2>
        {ranking.carregando && <Carregando />}
        {ranking.erro && <ErroCarga erro={ranking.erro} recarregar={ranking.recarregar} />}
        {ranking.dados && (
          <>
            <div className="campo" style={{ maxWidth: "24rem" }}>
              <label htmlFor="destaque">Destacar uma região</label>
              <select id="destaque" value={destaque} onChange={(e) => setDestaque(e.target.value)}>
                <option value="">Nenhuma</option>
                {itens.map((i) => (
                  <option key={i.chave} value={i.chave}>
                    {i.subprefeitura}
                  </option>
                ))}
              </select>
            </div>
            <RankingBarras
              itens={itens}
              destaque={destaque || null}
              descricao={`Ranking de registros por subprefeitura: ${itens
                .map((i) => `${i.subprefeitura} ${i.total_ocorrencias}`)
                .join(", ")}.`}
            />
            {itens[0] && total > 0 && (
              <p style={{ marginTop: "1rem" }}>
                {itens[0].subprefeitura} concentra {numero(itens[0].total_ocorrencias)} dos {numero(total)} registros (
                {numero((itens[0].total_ocorrencias / total) * 100, 0)}%).
                {demais
                  ? ` As outras ${demais.grupos} subprefeituras com registros somam ${numero(demais.total_ocorrencias)}; o snapshot não traz o número de cada uma.`
                  : ""}
              </p>
            )}
            <details className="tabela-dados">
              <summary>Ver os dados em tabela</summary>
              <div className="tabela-rolagem">
                <table>
                  <thead>
                    <tr>
                      <th scope="col">Posição</th>
                      <th scope="col">Subprefeitura</th>
                      <th scope="col" className="num">
                        Registros
                      </th>
                      <th scope="col">Primeiro</th>
                      <th scope="col">Último</th>
                    </tr>
                  </thead>
                  <tbody>
                    {itens.map((i, n) => (
                      <tr key={i.chave}>
                        <td>{n + 1}ª</td>
                        <td>{i.subprefeitura}</td>
                        <td className="num">{numero(i.total_ocorrencias)}</td>
                        <td>{dataBr(i.primeira_ocorrencia)}</td>
                        <td>{dataBr(i.ultima_ocorrencia)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
            <FonteDados meta={ranking.dados.meta} />
          </>
        )}
      </section>

      <section className="superficie secao" aria-labelledby="titulo-mensal">
        <h2 id="titulo-mensal">Registros por mês</h2>
        {mensal.carregando && <Carregando />}
        {mensal.erro && <ErroCarga erro={mensal.erro} recarregar={mensal.recarregar} />}
        {mensal.dados && (
          <>
            {pico && (
              <p className="secao__intro">
                O mês com mais registros foi {mesBr(pico.mes)}, com {numero(pico.total_ocorrencias)}.
                {mensal.dados.dados.lacunas.length > 0 &&
                  ` ${capitalizar(mensal.dados.dados.lacunas.map((l) => mesBr(l)).join(", "))} não ${
                    mensal.dados.dados.lacunas.length > 1 ? "têm" : "tem"
                  } linha na tabela: é uma lacuna da base, não prova de que não houve alagamento.`}
              </p>
            )}
            <ColunasMensais serie={serie} lacunas={mensal.dados.dados.lacunas} />
            <FonteDados meta={mensal.dados.meta} />
          </>
        )}
      </section>
    </>
  );
}
