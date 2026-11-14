"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

const LINKS = [
  { href: "/", rotulo: "Início" },
  { href: "/mapa", rotulo: "Mapa" },
  { href: "/regioes", rotulo: "Regiões" },
  { href: "/chuva", rotulo: "Chuva" },
  { href: "/indice", rotulo: "Índice" },
  { href: "/assistente", rotulo: "Assistente" },
  { href: "/sobre", rotulo: "Sobre os dados" },
];

export function Logo({ tamanho = 28 }: { tamanho?: number }) {
  // Nuvem com três gotas: céu encoberto sobre o bairro.
  return (
    <svg width={tamanho} height={tamanho} viewBox="0 0 32 32" aria-hidden="true">
      <path
        d="M9 18.5a5.5 5.5 0 0 1 .9-10.93A7 7 0 0 1 23.4 9.6 4.5 4.5 0 0 1 23 18.5Z"
        fill="var(--garoa)"
      />
      <path d="M11 22.5l-1.4 3M16.5 22.5l-1.4 3M22 22.5l-1.4 3" stroke="var(--agua)" strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  );
}

type Tema = "claro" | "escuro";

function lerTema(): Tema {
  if (typeof document === "undefined") return "claro";
  return document.documentElement.dataset.tema === "escuro" ? "escuro" : "claro";
}

export default function Cabecalho() {
  const caminho = usePathname();
  const [tema, setTema] = useState<Tema>("claro");

  useEffect(() => setTema(lerTema()), []);

  function alternarTema() {
    const novo: Tema = tema === "escuro" ? "claro" : "escuro";
    document.documentElement.dataset.tema = novo;
    try {
      localStorage.setItem("alertabairro-tema", novo);
    } catch {
      // armazenamento indisponível (modo privado): o tema vale só nesta visita
    }
    setTema(novo);
    window.dispatchEvent(new CustomEvent("alertabairro:tema", { detail: novo }));
  }

  const ativo = (href: string) => (href === "/" ? caminho === "/" : caminho?.startsWith(href));

  return (
    <header className="cabecalho">
      <div className="cabecalho__interno">
        <Link href="/" className="marca">
          <Logo />
          AlertaBairro
        </Link>
        <nav className="navegacao" aria-label="Seções do AlertaBairro">
          {LINKS.map((l) => (
            <Link key={l.href} href={l.href} aria-current={ativo(l.href) ? "page" : undefined}>
              {l.rotulo}
            </Link>
          ))}
        </nav>
        <div className="cabecalho__acoes">
          <button
            type="button"
            className="botao-tema"
            onClick={alternarTema}
            aria-label={tema === "escuro" ? "Usar tema claro" : "Usar tema escuro"}
            title={tema === "escuro" ? "Usar tema claro" : "Usar tema escuro"}
          >
            {tema === "escuro" ? (
              <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true">
                <circle cx="12" cy="12" r="4.5" fill="currentColor" />
                <path
                  d="M12 2v2.5M12 19.5V22M2 12h2.5M19.5 12H22M4.9 4.9l1.8 1.8M17.3 17.3l1.8 1.8M4.9 19.1l1.8-1.8M17.3 6.7l1.8-1.8"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                />
              </svg>
            ) : (
              <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5Z" fill="currentColor" />
              </svg>
            )}
          </button>
          <Link href="/relatar" className="botao botao--relatar">
            Relatar ocorrência
          </Link>
        </div>
      </div>
    </header>
  );
}
