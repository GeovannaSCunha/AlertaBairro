import type { Metadata, Viewport } from "next";
import { Atkinson_Hyperlegible } from "next/font/google";
import Link from "next/link";
import Script from "next/script";

import Cabecalho from "@/components/Cabecalho";

import "./globals.css";

// Atkinson Hyperlegible: criada pelo Braille Institute para leitura por pessoas com baixa visão.
const atkinson = Atkinson_Hyperlegible({
  subsets: ["latin"],
  weight: ["400", "700"],
  display: "swap",
  variable: "--fonte-atkinson",
});

export const metadata: Metadata = {
  title: { default: "AlertaBairro", template: "%s | AlertaBairro" },
  description:
    "Histórico de alagamentos e chuva em São Paulo num mapa simples e colaborativo. Projeto CitizenTech — Global Solution FIAP 2026.2.",
  applicationName: "AlertaBairro",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#e6ecf0" },
    { media: "(prefers-color-scheme: dark)", color: "#121a20" },
  ],
};

// Aplica o tema antes da pintura para evitar o "piscar" entre claro e escuro.
const scriptTema = `(function(){try{var t=localStorage.getItem('alertabairro-tema');if(!t){t=window.matchMedia('(prefers-color-scheme: dark)').matches?'escuro':'claro'}document.documentElement.dataset.tema=t}catch(e){document.documentElement.dataset.tema='claro'}})();`;

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" className={atkinson.variable} suppressHydrationWarning>
      <body>
        <Script id="tema-inicial" strategy="beforeInteractive">
          {scriptTema}
        </Script>
        <a className="pular" href="#conteudo">
          Pular para o conteúdo
        </a>
        <div className="faixa-emergencia" role="note">
          O AlertaBairro mostra dados históricos e não é um serviço de alerta. Em perigo, ligue{" "}
          <strong>193</strong> (Bombeiros) ou <strong>199</strong> (Defesa Civil).
        </div>
        <Cabecalho />
        <main id="conteudo" className="conteudo" tabIndex={-1}>
          {children}
        </main>
        <footer className="rodape">
          <div className="rodape__interno">
            <div>
              <p>
                <strong>AlertaBairro</strong>: projeto acadêmico CitizenTech da Global Solution FIAP 2026.2, conectado
                aos ODS 11 (cidades sustentáveis) e 13 (ação climática).
              </p>
              <p>
                Dados de alagamento: GeoSampa/Defesa Civil. Chuva: Open-Meteo. Tratamento no Databricks (camadas
                Bronze, Prata e Ouro).
              </p>
            </div>
            <div>
              <p>
                <Link href="/sobre">Fontes, método e privacidade</Link>
              </p>
              <p>
                <Link href="/relatar#acompanhar">Acompanhar um relato</Link>
              </p>
              <p>
                <Link href="/moderacao">Área de moderação</Link>
              </p>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
