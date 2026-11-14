"use client";

import { useEffect, useState } from "react";

import { Carregando, ErroCarga, FonteDados } from "@/components/Estados";
import { Nivel, PontosIndice } from "@/components/Nivel";
import { useApi } from "@/lib/api";
import { dataBr, mm, numero } from "@/lib/formato";
import type { Clima, Envelope, Indice } from "@/lib/tipos";

export default function IndiceCliente() {
  const [modo, setModo] = useState<"hoje" | "simular">("hoje");
  const [data, setData] = useState("");
  const clima = useApi<Envelope<Clima>>("/clima/diario");
  const serie = clima.dados?.dados.serie ?? [];
  const inicioSerie = serie[0]?.data ?? "";
  const fimSerie = serie[serie.length - 1]?.data ?? "";

  useEffect(() => {
    if (modo === "simular" && !data && fimSerie) setData(fimSerie);
  }, [modo, data, fimSerie]);

  const caminho = modo === "simular" && data ? `/indice?data_referencia=${data}` : "/indice";
  const indice = useApi<Envelope<Indice>>(caminho);
  const d = indice.dados?.dados;

  // Rola até a região indicada no endereço (ex.: /indice#CAMPOLIMPO, vindo da página inicial)
  useEffect(() => {
    if (!d || typeof window === "undefined" || !window.location.hash) return;
    document.getElementById(window.location.hash.slice(1))?.scrollIntoView({ block: "center" });
  }, [d]);

  return (
    <>
      <div className="titulo-pagina">
        <h1>Índice experimental de atenção</h1>
        <p>
          Uma classificação ilustrativa que soma o histórico de registros de cada região com a chuva recente. As regras
          estão nesta página, para qualquer pessoa conferir o cálculo.
        </p>
      </div>

      <div className="aviso">
        <p>
          Não é previsão nem medida de risco, e não substitui a Defesa Civil (199) ou os Bombeiros (193).
        </p>
      </div>

      <section className="superficie" aria-labelledby="titulo-referencia">
        <h2 id="titulo-referencia">Data de referência</h2>
        <fieldset className="opcoes-radio" style={{ marginBottom: "1rem" }}>
          <legend className="sr-only">Escolha a data de referência</legend>
          <label>
            <input type="radio" name="modo" checked={modo === "hoje"} onChange={() => setModo("hoje")} />
            <span>Hoje</span>
          </label>
          <label>
            <input type="radio" name="modo" checked={modo === "simular"} onChange={() => setModo("simular")} />
            <span>Simular outra data</span>
          </label>
        </fieldset>
        {modo === "simular" && (
          <div className="campo" style={{ maxWidth: "18rem" }}>
            <label htmlFor="data-ref">Data simulada</label>
            <input
              id="data-ref"
              type="date"
              value={data}
              min={inicioSerie || undefined}
              max={new Date().toISOString().slice(0, 10)}
              onChange={(e) => setData(e.target.value)}
            />
            <p className="campo__ajuda">
              A simulação mostra como o índice ficaria nessa data, com a chuva disponível na série ({dataBr(inicioSerie)} a{" "}
              {dataBr(fimSerie)}).
            </p>
          </div>
        )}
        {d && (
          <div className={d.chuva.considerada ? "aviso aviso--neutro" : "aviso"}>
            <p>
              <strong>{d.chuva.considerada ? `Chuva considerada: ${mm(d.chuva.mm_72h)} em 3 dias.` : "Chuva não considerada."}</strong>{" "}
              {d.chuva.motivo}
            </p>
          </div>
        )}
      </section>

      <section className="superficie secao" aria-labelledby="titulo-tabela-indice">
        <h2 id="titulo-tabela-indice">
          Resultado em {d ? dataBr(d.data_referencia) : "…"}
          {indice.dados?.meta.simulacao ? " (simulação)" : ""}
        </h2>
        {indice.carregando && <Carregando texto="Calculando o índice…" />}
        {indice.erro && <ErroCarga erro={indice.erro} recarregar={indice.recarregar} />}
        {d && indice.dados && (
          <>
            <div className="tabela-rolagem">
              <table>
                <caption className="sr-only">Índice de atenção por subprefeitura</caption>
                <thead>
                  <tr>
                    <th scope="col">Subprefeitura</th>
                    <th scope="col">Nível</th>
                    <th scope="col">Pontos</th>
                    <th scope="col">Como foi calculado</th>
                  </tr>
                </thead>
                <tbody>
                  {d.regioes.map((r) => (
                    <tr key={r.chave} id={r.chave} tabIndex={-1}>
                      <th scope="row" style={{ color: "var(--asfalto)" }}>
                        {r.subprefeitura}
                      </th>
                      <td>
                        <Nivel nivel={r.nivel} rotulo={r.rotulo} />
                      </td>
                      <td className="pontos-celula">
                        <PontosIndice h={r.componente_historico} c={r.componente_chuva} /> {r.pontuacao}/5
                      </td>
                      <td style={{ color: "var(--concreto)" }}>{r.explicacao}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {d.demais && (
              <p style={{ marginTop: "1rem" }}>
                As outras {d.demais.grupos} subprefeituras com registros ({numero(d.demais.total_ocorrencias)} no total)
                não aparecem porque o snapshot não traz o número de cada uma.
              </p>
            )}
            <ul className="legenda">
              <li>
                <i style={{ background: "var(--garoa)" }} />
                Pontos de histórico
              </li>
              <li>
                <i style={{ background: "var(--agua)" }} />
                Pontos de chuva
              </li>
            </ul>
            <FonteDados meta={indice.dados.meta} />
          </>
        )}
      </section>

      {d && (
        <section className="secao" aria-labelledby="titulo-regras">
          <h2 id="titulo-regras">Como o índice é calculado</h2>
          <ul className="regras">
            {d.regras.map((regra) => (
              <li key={regra}>{regra}</li>
            ))}
          </ul>
          <p className="secao__intro">
            Esta é a primeira etapa da proposta: regras explicáveis. Um modelo de aprendizado de máquina só entra se houver
            dados rotulados e validação temporal suficientes.
          </p>
        </section>
      )}
    </>
  );
}
