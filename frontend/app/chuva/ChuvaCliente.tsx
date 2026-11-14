"use client";

import { Carregando, ErroCarga, FonteDados } from "@/components/Estados";
import { GraficoChuva } from "@/components/Graficos";
import { useApi } from "@/lib/api";
import { dataBr, mm, numero } from "@/lib/formato";
import type { Clima, Envelope } from "@/lib/tipos";

/** Equivalência concreta: 1 mm de chuva = 1 litro por metro quadrado. */
function Equivalencia({ mmDia, data }: { mmDia: number; data: string }) {
  const litrosQuadra = mmDia * 100 * 100; // quadra típica de 100 m × 100 m
  const caixas = litrosQuadra / 1000; // caixas d'água de 1.000 litros
  return (
    <div className="grade-2">
      <div>
        <h3>O que significa {mm(mmDia)}</h3>
        <p>
          Um milímetro de chuva é 1 litro de água em cada metro quadrado de chão. No dia mais chuvoso da série,{" "}
          {dataBr(data)}, caíram cerca de <strong>{numero(mmDia, 1)} litros por metro quadrado</strong>.
        </p>
        <p>
          Numa quadra de 100 m por 100 m, isso dá uns <strong>{numero(litrosQuadra)} litros</strong>, o bastante para
          encher {numero(caixas)} caixas d’água de 1.000 litros. Quando essa água cai em pouco tempo sobre asfalto e
          concreto, os bueiros não dão conta e a rua alaga.
        </p>
      </div>
      <div>
        <h3>Por que o mesmo volume pode ou não alagar</h3>
        <p>
          O impacto depende de quanto tempo a chuva leva para cair. Vinte milímetros espalhados pelo dia passam quase
          despercebidos. Os mesmos vinte milímetros em meia hora causam transtorno. Os dados desta página são totais
          diários, então não mostram a intensidade de cada hora.
        </p>
        <p>Bueiros entupidos, córregos canalizados e ruas em baixada também pesam.</p>
      </div>
    </div>
  );
}

export default function ChuvaCliente() {
  const clima = useApi<Envelope<Clima>>("/clima/diario");
  const serie = clima.dados?.dados.serie ?? [];
  const maior = serie.reduce<(typeof serie)[number] | null>(
    (m, d) => (!m || (d.precipitacao_mm ?? 0) > (m.precipitacao_mm ?? 0) ? d : m),
    null,
  );
  const semChuva = serie.filter((d) => (d.precipitacao_mm ?? 0) === 0).length;
  const total = serie.length ? serie[serie.length - 1].precipitacao_acumulada_mm : null;

  return (
    <>
      <div className="titulo-pagina">
        <h1>Chuva e contexto</h1>
        <p>
          Quanto choveu, dia a dia, num ponto de referência da região central de São Paulo. Em um bairro distante, a
          chuva da mesma tarde pode ter sido bem diferente.
        </p>
      </div>

      <section className="superficie" aria-labelledby="titulo-serie">
        <h2 id="titulo-serie">Chuva por dia</h2>
        {clima.carregando && <Carregando />}
        {clima.erro && <ErroCarga erro={clima.erro} recarregar={clima.recarregar} />}
        {clima.dados && serie.length > 0 && (
          <>
            <p className="secao__intro">
              De {dataBr(serie[0].data)} a {dataBr(serie[serie.length - 1].data)} choveu {mm(total)} no total
              {maior ? `; o dia mais chuvoso foi ${dataBr(maior.data)}, com ${mm(maior.precipitacao_mm)}` : ""}.
              {semChuva > 0 && ` Em ${semChuva} ${semChuva === 1 ? "dia" : "dias"} não choveu.`}
            </p>
            <GraficoChuva serie={serie} destaque={maior?.data ?? null} />
            <details className="tabela-dados">
              <summary>Ver os dados em tabela</summary>
              <div className="tabela-rolagem">
                <table>
                  <thead>
                    <tr>
                      <th scope="col">Data</th>
                      <th scope="col" className="num">
                        Chuva no dia
                      </th>
                      <th scope="col" className="num">
                        Acumulado
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {serie.map((d) => (
                      <tr key={d.data}>
                        <td>{dataBr(d.data)}</td>
                        <td className="num">{mm(d.precipitacao_mm)}</td>
                        <td className="num">{mm(d.precipitacao_acumulada_mm)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
            <FonteDados
              meta={clima.dados.meta}
              extra={`Origem: ${clima.dados.dados.fonte_original}, coordenada ${numero(
                clima.dados.dados.ponto_referencia.latitude,
                2,
              )}, ${numero(clima.dados.dados.ponto_referencia.longitude, 2)}.`}
            />
          </>
        )}
      </section>

      {maior && maior.precipitacao_mm !== null && (
        <section className="secao superficie" aria-label="Como ler os milímetros">
          <Equivalencia mmDia={maior.precipitacao_mm} data={maior.data} />
        </section>
      )}

      <div className="aviso secao">
        <p>
          Esta série de chuva (fim de outubro e início de novembro) não coincide com o período dos registros de alagamento
          (janeiro a setembro). Por isso o AlertaBairro não afirma que uma coisa causou a outra.
        </p>
      </div>
    </>
  );
}
