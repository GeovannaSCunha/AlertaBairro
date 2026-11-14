"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { AvisoFonte, Carregando, ErroCarga, FonteDados } from "@/components/Estados";
import { ChuvaDeFundo } from "@/components/Graficos";
import { useApi } from "@/lib/api";
import { dataBr, mm, numero, periodoMeses, plural } from "@/lib/formato";
import type { Clima, Envelope, Indicadores, Kpis, Ranking } from "@/lib/tipos";

export default function Inicio() {
  const kpis = useApi<Envelope<Kpis>>("/kpis");
  const ranking = useApi<Envelope<Ranking>>("/alagamentos/subprefeituras?limit=50");
  const clima = useApi<Envelope<Clima>>("/clima/diario");
  const indicadores = useApi<Envelope<Indicadores>>("/indicadores");
  const [escolhida, setEscolhida] = useState<string>("");

  const itens = ranking.dados?.dados.itens ?? [];
  const ordenadas = useMemo(
    () => [...itens].sort((a, b) => a.subprefeitura.localeCompare(b.subprefeitura, "pt-BR")),
    [itens],
  );
  const posicao = itens.findIndex((i) => i.chave === escolhida);
  const regiao = posicao >= 0 ? itens[posicao] : null;
  const k = kpis.dados?.dados;
  const demais = ranking.dados?.dados.demais;

  return (
    <>
      <section className="heroi" aria-labelledby="titulo-inicio">
        <div className="heroi__texto">
          <h1 id="titulo-inicio">Como é o histórico de alagamentos da sua região?</h1>
          <p>
            O AlertaBairro reúne registros públicos de alagamento e de chuva em São Paulo e os relatos dos moradores.
            Escolha uma subprefeitura para ver o que a base mostra.
          </p>
          <div className="seletor-regiao">
            <label htmlFor="regiao">Sua região</label>
            {ranking.erro ? (
              <ErroCarga erro={ranking.erro} recarregar={ranking.recarregar} />
            ) : (
              <select
                id="regiao"
                value={escolhida}
                onChange={(e) => setEscolhida(e.target.value)}
                disabled={ranking.carregando}
              >
                <option value="">{ranking.carregando ? "Carregando regiões…" : "Escolha uma subprefeitura"}</option>
                {ordenadas.map((s) => (
                  <option key={s.chave} value={s.chave}>
                    {s.subprefeitura}
                  </option>
                ))}
              </select>
            )}
            {demais && (
              <p className="campo__ajuda" style={{ marginTop: "0.5rem" }}>
                A lista mostra as {itens.length} subprefeituras com mais registros no snapshot. Outras {demais.grupos}{" "}
                somam {numero(demais.total_ocorrencias)} registros.
              </p>
            )}
          </div>
        </div>

        <div className="ficha-regiao" aria-live="polite">
          <ChuvaDeFundo serie={clima.dados?.dados.serie ?? []} />
          <div style={{ position: "relative" }}>
            {regiao && k ? (
              <>
                <h2>{regiao.subprefeitura}</h2>
                <div className="ficha-regiao__numero">
                  {numero(regiao.total_ocorrencias)}
                  <small>{regiao.total_ocorrencias === 1 ? "registro" : "registros"} de alagamento</small>
                </div>
                <dl>
                  <dt>Posição na base</dt>
                  <dd>
                    {posicao + 1}ª de {k.subprefeituras_com_registros} subprefeituras
                  </dd>
                  <dt>Parte do total</dt>
                  <dd>{numero((regiao.total_ocorrencias / Math.max(1, k.alagamentos.total)) * 100, 1)}%</dd>
                  <dt>Período</dt>
                  <dd>
                    {regiao.primeira_ocorrencia && regiao.ultima_ocorrencia
                      ? `${dataBr(regiao.primeira_ocorrencia)} a ${dataBr(regiao.ultima_ocorrencia)}`
                      : periodoMeses(k.alagamentos.periodo_inicio, k.alagamentos.periodo_fim)}
                  </dd>
                </dl>
                <div className="ficha-regiao__acoes">
                  <Link className="botao" href={`/mapa?subprefeitura=${encodeURIComponent(regiao.subprefeitura)}`}>
                    Ver no mapa
                  </Link>
                  <Link className="botao botao--secundario" href={`/indice#${regiao.chave}`}>
                    Ver índice de atenção
                  </Link>
                </div>
              </>
            ) : (
              <>
                <h2>Toda a base histórica</h2>
                <div className="ficha-regiao__numero">
                  {k ? numero(k.alagamentos.total) : "–"}
                  <small>registros de alagamento</small>
                </div>
                <p style={{ marginTop: "1rem" }}>
                  {k
                    ? `De ${periodoMeses(k.alagamentos.periodo_inicio, k.alagamentos.periodo_fim)}, em ${plural(
                        k.subprefeituras_com_registros,
                        "subprefeitura",
                        "subprefeituras",
                      )}.`
                    : "Carregando os números da base…"}{" "}
                  O ranking mostra onde estão os registros, não o risco de cada lugar.
                </p>
                <div className="ficha-regiao__acoes">
                  <Link className="botao" href="/mapa">
                    Abrir o mapa
                  </Link>
                  <Link className="botao botao--secundario" href="/regioes">
                    Comparar regiões
                  </Link>
                </div>
              </>
            )}
          </div>
        </div>
      </section>

      {kpis.erro && <ErroCarga erro={kpis.erro} recarregar={kpis.recarregar} />}
      {kpis.carregando && <Carregando />}
      {k && kpis.dados && (
        <section aria-label="O que a base mostra">
          <div className="fatos">
            <div className="fato">
              <strong>{numero(k.alagamentos.total)}</strong>
              <span>ocorrências únicas de alagamento, {periodoMeses(k.alagamentos.periodo_inicio, k.alagamentos.periodo_fim)}</span>
            </div>
            <div className="fato">
              <strong>{numero(k.subprefeituras_com_registros)}</strong>
              <span>das 32 subprefeituras de São Paulo têm registros</span>
            </div>
            <div className="fato">
              <strong>{mm(k.clima.chuva_acumulada_mm)}</strong>
              <span>
                de chuva de {dataBr(k.clima.periodo_inicio)} a {dataBr(k.clima.periodo_fim)}, na região central
              </span>
            </div>
            <div className="fato">
              <strong>{mm(k.clima.maior_chuva_diaria_mm)}</strong>
              <span>no dia mais chuvoso, {dataBr(k.clima.data_maior_chuva)}</span>
            </div>
          </div>
          <FonteDados
            meta={kpis.dados.meta}
            extra="A chuva e os alagamentos cobrem períodos diferentes; por isso não comparamos um com o outro."
          />
          <AvisoFonte meta={kpis.dados.meta} />
        </section>
      )}

      <section className="secao" aria-labelledby="titulo-passos">
        <h2 id="titulo-passos">Como usar</h2>
        <p className="secao__intro">Cinco passos, sem cadastro.</p>
        <ol className="passos">
          <li>
            <Link href="/">Escolha a região</Link>
            <p>No seletor acima, veja quantos registros a sua subprefeitura tem.</p>
          </li>
          <li>
            <Link href="/mapa">Consulte o mapa</Link>
            <p>Filtre as ocorrências por região e por mês e veja cada ponto.</p>
          </li>
          <li>
            <Link href="/chuva">Entenda a chuva</Link>
            <p>Veja quanto choveu e o que os milímetros significam.</p>
          </li>
          <li>
            <Link href="/relatar">Relate uma ocorrência</Link>
            <p>Marque no mapa o que você viu. Um moderador revisa antes de publicar.</p>
          </li>
          <li>
            <Link href="/indice">Veja os indicadores</Link>
            <p>Confira o índice experimental e como ele é calculado.</p>
          </li>
        </ol>
      </section>

      {indicadores.dados && (
        <section className="secao" aria-labelledby="titulo-participacao">
          <h2 id="titulo-participacao">Participação da comunidade</h2>
          <p className="secao__intro">
            {indicadores.dados.dados.participacao.total === 0
              ? "Nenhum relato enviado ainda. O primeiro pode ser o seu."
              : `${plural(indicadores.dados.dados.participacao.total, "relato recebido", "relatos recebidos")}: ${plural(
                  indicadores.dados.dados.participacao.aprovado,
                  "publicado",
                  "publicados",
                )}, ${plural(indicadores.dados.dados.participacao.pendente, "aguardando", "aguardando")} moderação.`}
          </p>
          <Link className="botao botao--relatar" href="/relatar">
            Relatar ocorrência
          </Link>
        </section>
      )}
    </>
  );
}
