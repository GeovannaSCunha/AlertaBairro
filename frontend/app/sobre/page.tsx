import type { Metadata } from "next";
import Link from "next/link";

import StatusIntegracoes from "./StatusIntegracoes";

export const metadata: Metadata = { title: "Fontes, método e privacidade" };

export default function PaginaSobre() {
  return (
    <>
      <div className="titulo-pagina">
        <h1>Fontes, método e privacidade</h1>
        <p>
          De onde vêm os números, como eles são tratados, o que o AlertaBairro não faz e como cuidamos dos dados de quem
          envia um relato.
        </p>
      </div>

      <StatusIntegracoes />

      <section className="secao" aria-labelledby="t-fontes">
        <h2 id="t-fontes">Fontes de dados</h2>
        <div className="tabela-rolagem superficie">
          <table>
            <thead>
              <tr>
                <th scope="col">Fonte</th>
                <th scope="col">O que fornece</th>
                <th scope="col">Período no MVP</th>
                <th scope="col">Tabela usada pelo app</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>GeoSampa / Defesa Civil</td>
                <td>Ocorrências de alagamento com coordenadas e subprefeitura</td>
                <td>janeiro a setembro de 2026 (292 registros únicos)</td>
                <td>
                  <code>prata_alagamentos</code>, <code>ouro_alagamentos_subprefeitura</code>,{" "}
                  <code>ouro_alagamentos_mensal</code>
                </td>
              </tr>
              <tr>
                <td>Open-Meteo</td>
                <td>Precipitação diária numa coordenada da região central (-23,55; -46,63)</td>
                <td>28/10 a 06/11/2026 (10 dias)</td>
                <td>
                  <code>ouro_clima_diario</code>
                </td>
              </tr>
              <tr>
                <td>Moradores</td>
                <td>Relatos com tipo, descrição, local aproximado e foto opcional</td>
                <td>contínuo, após moderação</td>
                <td>
                  <code>relatos</code> (banco da API)
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section className="secao" aria-labelledby="t-pipeline">
        <h2 id="t-pipeline">Do dado bruto à tela</h2>
        <ol className="regras">
          <li>Um DAG do Airflow coleta as duas fontes em paralelo e grava um arquivo por coleta, com a data no nome.</li>
          <li>Os lotes são enviados a um Volume do Unity Catalog no Databricks (por enquanto, manualmente).</li>
          <li>A camada Bronze guarda o dado bruto; a Prata remove duplicidades e corrige tipos; a Ouro agrega por região, mês e dia.</li>
          <li>
            A API do AlertaBairro lê a Prata e a Ouro pela SQL Statement Execution API, sempre com SQL fixo e somente leitura.
            O navegador nunca recebe credenciais do Databricks.
          </li>
          <li>Se o Databricks não responde, a API usa o snapshot validado em 13/11/2026 e a tela avisa.</li>
        </ol>
      </section>

      <section className="secao grade-2" aria-label="Limites e inteligência artificial">
        <div>
          <h2>O que o AlertaBairro não faz</h2>
          <ul className="regras">
            <li>Não é monitoramento em tempo real nem sistema oficial de alerta.</li>
            <li>Não faz previsão: o índice é uma classificação ilustrativa com regras abertas.</li>
            <li>Não afirma que a chuva causou os alagamentos: os dois períodos não se sobrepõem.</li>
            <li>O ranking conta registros; não mede gravidade nem considera população ou área.</li>
            <li>Julho de 2026 não tem linha na tabela mensal, o que não significa zero alagamentos.</li>
          </ul>
        </div>
        <div>
          <h2>Como a IA entra</h2>
          <p>
            O <Link href="/indice">índice experimental</Link> é a primeira etapa: regras explicáveis. O{" "}
            <Link href="/assistente">assistente</Link> busca trechos numa base de conhecimento com fonte e responde só com
            base neles. Ele recusa perguntas que pedem previsão e cita de onde tirou cada número. Pode funcionar com um
            modelo de linguagem local (por exemplo, via Ollama) ou, sem modelo, com respostas montadas a partir dos dados.
          </p>
        </div>
      </section>

      <section className="secao superficie" aria-labelledby="t-lgpd">
        <h2 id="t-lgpd">Privacidade (LGPD)</h2>
        <ul className="regras">
          <li>Não pedimos nome, e-mail, telefone nem cadastro para enviar um relato.</li>
          <li>A descrição é recusada se contiver e-mail, CPF ou telefone.</li>
          <li>O local do relato é arredondado para cerca de 110 metros antes de ser gravado.</li>
          <li>A foto é regravada no seu aparelho e de novo no servidor, sem metadados como a localização GPS da câmera.</li>
          <li>Fotos de relatos rejeitados são apagadas na hora; as demais, depois de 90 dias.</li>
          <li>Só relatos aprovados pela moderação ficam públicos.</li>
          <li>Os dados públicos de alagamento não contêm informações pessoais.</li>
        </ul>
      </section>

      <section className="secao" aria-labelledby="t-ods">
        <h2 id="t-ods">Objetivos de Desenvolvimento Sustentável</h2>
        <p>
          <strong>ODS 11, Cidades e comunidades sustentáveis:</strong> torna o histórico de alagamentos compreensível para
          quem mora no bairro e cria um canal estruturado de participação.
        </p>
        <p>
          <strong>ODS 13, Ação contra a mudança global do clima:</strong> amplia o acesso a informação sobre chuva e
          alagamento, apoiando a adaptação a eventos climáticos.
        </p>
      </section>
    </>
  );
}
