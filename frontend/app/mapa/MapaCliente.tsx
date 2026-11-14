"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";

import { ErroCarga, FonteDados } from "@/components/Estados";
import MapaDinamico, { type Marcador } from "@/components/MapaDinamico";
import { useApi } from "@/lib/api";
import { dataBr, dataHoraBr, mesBr, numero, plural } from "@/lib/formato";
import { chave } from "@/lib/texto";
import type { DadosMapa, Envelope, RelatoPublico } from "@/lib/tipos";

const LIMITE_LISTA = 150;

export default function MapaCliente() {
  const parametros = useSearchParams();
  const [sub, setSub] = useState(parametros.get("subprefeitura") ?? "");
  const [mes, setMes] = useState(parametros.get("mes") ?? "");
  const [verHistorico, setVerHistorico] = useState(true);
  const [verRelatos, setVerRelatos] = useState(true);
  const [selecionado, setSelecionado] = useState<string | null>(null);

  const consulta = new URLSearchParams({ limit: "2000" });
  if (sub) consulta.set("subprefeitura", sub);
  if (mes) consulta.set("mes", mes);
  const mapa = useApi<Envelope<DadosMapa>>(`/alagamentos/mapa?${consulta.toString()}`);
  const relatos = useApi<Envelope<RelatoPublico[]>>("/relatos?limit=500");

  const dados = mapa.dados?.dados;
  const relatosFiltrados = useMemo(
    () =>
      (relatos.dados?.dados ?? []).filter(
        (r) => (!mes || r.ocorrido_em.startsWith(mes)) && (!sub || chave(r.subprefeitura) === chave(sub)),
      ),
    [relatos.dados, mes, sub],
  );

  const marcadores: Marcador[] = useMemo(() => {
    const lista: Marcador[] = [];
    if (verHistorico) {
      for (const p of dados?.pontos ?? []) {
        lista.push({
          id: `h-${p.id}`,
          latitude: p.latitude,
          longitude: p.longitude,
          tipo: "historico",
          titulo: `${p.tipo ? p.tipo.charAt(0) + p.tipo.slice(1).toLowerCase() : "Ocorrência"} em ${dataBr(p.data)}`,
          linhas: [`Subprefeitura: ${p.subprefeitura_exibicao}`],
          origem: "Registro histórico do GeoSampa/Defesa Civil",
        });
      }
    }
    if (verRelatos) {
      for (const r of relatosFiltrados) {
        lista.push({
          id: `r-${r.id}`,
          latitude: r.latitude,
          longitude: r.longitude,
          tipo: "relato",
          titulo: `${r.tipo_rotulo} em ${dataHoraBr(r.ocorrido_em)}`,
          linhas: [r.descricao],
          origem: "Relato de morador, aprovado pela moderação",
          fotoUrl: r.tem_foto ? `/api/relatos/${r.id}/foto` : undefined,
        });
      }
    }
    return lista;
  }, [dados, relatosFiltrados, verHistorico, verRelatos]);

  const semPontosHistoricos = mapa.dados && mapa.dados.meta.pontos_disponiveis === false;
  const totalVisivel = (verHistorico ? dados?.total_filtrado ?? 0 : 0) + (verRelatos ? relatosFiltrados.length : 0);

  return (
    <>
      <div className="titulo-pagina">
        <h1>Mapa de ocorrências</h1>
        <p>
          Pontos azuis são registros históricos de alagamento. Pontos laranja são relatos de moradores já revisados pela
          moderação.
        </p>
      </div>

      <div className="layout-mapa">
        <aside className="painel-filtros superficie" aria-label="Filtros do mapa">
          <div className="campo">
            <label htmlFor="filtro-sub">Subprefeitura</label>
            <select id="filtro-sub" value={sub} onChange={(e) => setSub(e.target.value)}>
              <option value="">Todas</option>
              {sub && !dados?.filtros.subprefeituras.includes(sub) && <option value={sub}>{sub}</option>}
              {(dados?.filtros.subprefeituras ?? []).map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
          <div className="campo">
            <label htmlFor="filtro-mes">Mês</label>
            <select id="filtro-mes" value={mes} onChange={(e) => setMes(e.target.value)}>
              <option value="">Todos os meses</option>
              {(dados?.filtros.meses ?? []).map((m) => (
                <option key={m} value={m}>
                  {mesBr(m)}
                </option>
              ))}
            </select>
          </div>
          <fieldset className="campo" style={{ border: 0, padding: 0, margin: "0 0 1rem" }}>
            <legend>Camadas</legend>
            <label className="caixa-marcar">
              <input type="checkbox" checked={verHistorico} onChange={(e) => setVerHistorico(e.target.checked)} />
              <span>Registros históricos</span>
            </label>
            <label className="caixa-marcar">
              <input type="checkbox" checked={verRelatos} onChange={(e) => setVerRelatos(e.target.checked)} />
              <span>Relatos da comunidade ({numero(relatosFiltrados.length)})</span>
            </label>
          </fieldset>

          <p role="status" aria-live="polite" style={{ margin: 0 }}>
            {mapa.carregando ? "Atualizando…" : `${plural(totalVisivel, "ponto", "pontos")} no mapa`}
          </p>
          {dados && dados.pontos.length > 0 && verHistorico && (
            <>
              <h2 style={{ fontSize: "1rem", margin: "1rem 0 0" }}>Registros mais recentes</h2>
              <ul className="lista-ocorrencias">
                {dados.pontos.slice(0, LIMITE_LISTA).map((p) => (
                  <li key={p.id}>
                    <button type="button" onClick={() => setSelecionado(`h-${p.id}`)}>
                      {dataBr(p.data)}
                      <small>{p.subprefeitura_exibicao}</small>
                    </button>
                  </li>
                ))}
              </ul>
            </>
          )}
        </aside>

        <div>
          {mapa.erro && <ErroCarga erro={mapa.erro} recarregar={mapa.recarregar} />}
          {semPontosHistoricos && (
            <div className="aviso aviso--neutro">
              <p>
                Os pontos históricos aparecem quando a API está conectada ao Databricks ou quando a tabela{" "}
                <code>prata_alagamentos</code> é exportada para o snapshot. Enquanto isso, o mapa mostra os relatos da
                comunidade. Os totais por região estão em <Link href="/regioes">Regiões</Link>.
              </p>
            </div>
          )}
          <MapaDinamico
            marcadores={marcadores}
            selecionado={selecionado}
            rotulo="Mapa de São Paulo com ocorrências de alagamento"
          />
          {mapa.dados && <FonteDados meta={mapa.dados.meta} extra="Relatos: banco da API, somente aprovados." />}
        </div>
      </div>
    </>
  );
}
