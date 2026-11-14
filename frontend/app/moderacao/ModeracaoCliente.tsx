"use client";

import { type FormEvent, useCallback, useEffect, useState } from "react";

import { api, ErroApi, postarJson } from "@/lib/api";
import { dataHoraBr, numero } from "@/lib/formato";
import type { RelatoModeracao } from "@/lib/tipos";

const CHAVE_SESSAO = "alertabairro-token-moderacao";
type Status = "pendente" | "aprovado" | "rejeitado";

function FotoProtegida({ id, token }: { id: string; token: string }) {
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    let ativo = true;
    let criada: string | null = null;
    fetch(`/api/moderacao/relatos/${id}/foto`, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => (r.ok ? r.blob() : null))
      .then((b) => {
        if (b && ativo) {
          criada = URL.createObjectURL(b);
          setUrl(criada);
        }
      })
      .catch(() => undefined);
    return () => {
      ativo = false;
      if (criada) URL.revokeObjectURL(criada);
    };
  }, [id, token]);
  return url ? <img src={url} alt="Foto enviada com o relato" /> : null;
}

export default function ModeracaoCliente() {
  const [token, setToken] = useState("");
  const [entrada, setEntrada] = useState("");
  const [status, setStatus] = useState<Status>("pendente");
  const [itens, setItens] = useState<RelatoModeracao[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [motivos, setMotivos] = useState<Record<string, string>>({});
  const [processando, setProcessando] = useState<string | null>(null);

  useEffect(() => {
    try {
      const salvo = sessionStorage.getItem(CHAVE_SESSAO);
      if (salvo) setToken(salvo);
    } catch {
      // sessionStorage indisponível: pede o token a cada visita
    }
  }, []);

  const carregar = useCallback(async () => {
    if (!token) return;
    setErro(null);
    try {
      const r = await api<{ dados: RelatoModeracao[] }>(`/moderacao/relatos?status=${status}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setItens(r.dados);
    } catch (e) {
      setItens(null);
      if (e instanceof ErroApi && e.status === 401) {
        setToken("");
        try {
          sessionStorage.removeItem(CHAVE_SESSAO);
        } catch {
          /* ignora */
        }
        setErro("Token inválido. Confira e tente de novo.");
      } else {
        setErro(e instanceof Error ? e.message : "Erro ao carregar a fila.");
      }
    }
  }, [token, status]);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  function entrar(e: FormEvent) {
    e.preventDefault();
    const t = entrada.trim();
    setToken(t);
    setEntrada("");
    try {
      sessionStorage.setItem(CHAVE_SESSAO, t);
    } catch {
      /* ignora */
    }
  }

  function sair() {
    setToken("");
    setItens(null);
    try {
      sessionStorage.removeItem(CHAVE_SESSAO);
    } catch {
      /* ignora */
    }
  }

  async function decidir(id: string, acao: "aprovar" | "rejeitar") {
    setProcessando(id);
    setErro(null);
    try {
      await postarJson(`/moderacao/relatos/${id}`, { acao, motivo: motivos[id] || null }, { Authorization: `Bearer ${token}` });
      setItens((lista) => (lista ?? []).filter((i) => i.id !== id));
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro ao registrar a decisão.");
    } finally {
      setProcessando(null);
    }
  }

  if (!token) {
    return (
      <>
        <div className="titulo-pagina">
          <h1>Moderação</h1>
          <p>Área para a equipe revisar os relatos antes da publicação.</p>
        </div>
        <form className="superficie" onSubmit={entrar} style={{ maxWidth: "28rem" }}>
          <div className="campo">
            <label htmlFor="token">Token de moderação</label>
            <input
              id="token"
              type="password"
              value={entrada}
              onChange={(e) => setEntrada(e.target.value)}
              autoComplete="current-password"
            />
            <p className="campo__ajuda">É o valor de ADMIN_TOKEN configurado no servidor da API. Fica salvo só nesta aba.</p>
          </div>
          {erro && <p className="campo__erro">{erro}</p>}
          <button type="submit" className="botao" disabled={entrada.trim().length < 16}>
            Entrar na moderação
          </button>
        </form>
      </>
    );
  }

  return (
    <>
      <div className="titulo-pagina" style={{ display: "flex", justifyContent: "space-between", gap: "1rem", flexWrap: "wrap" }}>
        <div>
          <h1>Moderação</h1>
          <p>Aprove relatos coerentes e sem dados pessoais. Ao rejeitar, a foto é apagada na hora.</p>
        </div>
        <button type="button" className="botao botao--secundario" onClick={sair}>
          Sair da moderação
        </button>
      </div>

      <fieldset className="opcoes-radio" style={{ marginBottom: "1.25rem" }}>
        <legend className="sr-only">Mostrar relatos</legend>
        {(["pendente", "aprovado", "rejeitado"] as Status[]).map((s) => (
          <label key={s}>
            <input type="radio" name="status" checked={status === s} onChange={() => setStatus(s)} />
            <span>{s === "pendente" ? "Pendentes" : s === "aprovado" ? "Aprovados" : "Rejeitados"}</span>
          </label>
        ))}
      </fieldset>

      {erro && (
        <div className="erro-carga" role="alert">
          <p>{erro}</p>
        </div>
      )}
      {itens && itens.length === 0 && <p className="vazio">Nenhum relato nesta lista.</p>}
      {itens && itens.length > 0 && (
        <p role="status">{numero(itens.length)} relato(s).</p>
      )}

      <div className="fila-moderacao">
        {(itens ?? []).map((r) => (
          <article key={r.id} className="superficie item-moderacao" aria-labelledby={`t-${r.id}`}>
            <div>
              <h2 id={`t-${r.id}`} style={{ fontSize: "1.1rem" }}>
                {r.tipo_rotulo} em {dataHoraBr(r.ocorrido_em)}
              </h2>
              <p>{r.descricao}</p>
              <p className="campo__ajuda">
                Protocolo {r.protocolo}. Enviado em {dataHoraBr(r.criado_em)}. Local {numero(r.latitude, 3)},{" "}
                {numero(r.longitude, 3)}
                {r.subprefeitura ? ` (${r.subprefeitura})` : ""}.{" "}
                <a
                  href={`https://www.openstreetmap.org/?mlat=${r.latitude}&mlon=${r.longitude}#map=17/${r.latitude}/${r.longitude}`}
                  target="_blank"
                  rel="noreferrer noopener"
                >
                  Conferir o local no OpenStreetMap
                </a>
              </p>
              {r.motivo_moderacao && <p className="campo__ajuda">Motivo registrado: {r.motivo_moderacao}</p>}
              {status === "pendente" && (
                <>
                  <div className="campo" style={{ marginBottom: 0, maxWidth: "30rem" }}>
                    <label htmlFor={`motivo-${r.id}`}>Motivo (opcional, aparece para quem enviou)</label>
                    <input
                      id={`motivo-${r.id}`}
                      type="text"
                      maxLength={200}
                      value={motivos[r.id] ?? ""}
                      onChange={(e) => setMotivos((m) => ({ ...m, [r.id]: e.target.value }))}
                    />
                  </div>
                  <div className="item-moderacao__acoes">
                    <button type="button" className="botao" disabled={processando === r.id} onClick={() => void decidir(r.id, "aprovar")}>
                      Aprovar e publicar
                    </button>
                    <button
                      type="button"
                      className="botao botao--secundario"
                      disabled={processando === r.id}
                      onClick={() => void decidir(r.id, "rejeitar")}
                    >
                      Rejeitar
                    </button>
                  </div>
                </>
              )}
            </div>
            {r.tem_foto && <FotoProtegida id={r.id} token={token} />}
          </article>
        ))}
      </div>
    </>
  );
}
