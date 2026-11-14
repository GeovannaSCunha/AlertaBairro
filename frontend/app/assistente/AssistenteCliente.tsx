"use client";

import { type FormEvent, useEffect, useRef, useState } from "react";

import { postarJson, useApi } from "@/lib/api";
import type { InfoAssistente, RespostaAssistente } from "@/lib/tipos";

type Mensagem = { id: number; autor: "pessoa" | "assistente"; texto: string; resposta?: RespostaAssistente };

function descreverModo(modo: string): string {
  if (modo.startsWith("llm:")) return `Gerado pelo modelo ${modo.slice(4)} com base nos trechos citados.`;
  if (modo === "guardrail") return "Resposta de segurança: o assistente não faz previsões.";
  return "Resposta montada a partir dos dados, sem modelo de linguagem.";
}

export default function AssistenteCliente() {
  const info = useApi<InfoAssistente>("/assistente/info");
  const [mensagens, setMensagens] = useState<Mensagem[]>([]);
  const [pergunta, setPergunta] = useState("");
  const [enviando, setEnviando] = useState(false);
  const fim = useRef<HTMLDivElement>(null);
  const contador = useRef(0);

  useEffect(() => {
    fim.current?.scrollIntoView({ block: "end" });
  }, [mensagens]);

  async function perguntar(texto: string) {
    const limpo = texto.trim();
    if (!limpo || enviando) return;
    setPergunta("");
    setEnviando(true);
    setMensagens((m) => [...m, { id: ++contador.current, autor: "pessoa", texto: limpo }]);
    try {
      const r = await postarJson<RespostaAssistente>("/assistente", { pergunta: limpo.slice(0, 500) });
      setMensagens((m) => [...m, { id: ++contador.current, autor: "assistente", texto: r.resposta, resposta: r }]);
    } catch (e) {
      setMensagens((m) => [
        ...m,
        {
          id: ++contador.current,
          autor: "assistente",
          texto: e instanceof Error ? e.message : "Não consegui responder agora. Tente de novo.",
        },
      ]);
    } finally {
      setEnviando(false);
    }
  }

  function enviar(e: FormEvent) {
    e.preventDefault();
    void perguntar(pergunta);
  }

  return (
    <>
      <div className="titulo-pagina">
        <h1>Assistente</h1>
        <p>
          Pergunte sobre os registros de alagamento, a chuva e o índice. As respostas vêm só da base do AlertaBairro e
          indicam a fonte. O assistente não faz previsão.
        </p>
      </div>

      <div className="chat">
        <div className="chat__mensagens" aria-live="polite" aria-relevant="additions">
          {mensagens.length === 0 && (
            <div>
              <p style={{ color: "var(--concreto)" }}>Experimente uma destas perguntas:</p>
              <div className="sugestoes">
                {(info.dados?.exemplos ?? []).map((ex) => (
                  <button key={ex} type="button" onClick={() => void perguntar(ex)}>
                    {ex}
                  </button>
                ))}
              </div>
            </div>
          )}
          {mensagens.map((m) =>
            m.autor === "pessoa" ? (
              <div key={m.id} className="msg msg--pessoa">
                <span className="sr-only">Você perguntou: </span>
                <p>{m.texto}</p>
              </div>
            ) : (
              <div key={m.id} className={m.resposta?.recusou ? "msg msg--assistente msg--recusa" : "msg msg--assistente"}>
                <span className="sr-only">Assistente: </span>
                <p>{m.texto}</p>
                {m.resposta && m.resposta.fontes.length > 0 && (
                  <div className="msg__fontes">
                    Fontes:
                    <ul>
                      {m.resposta.fontes.map((f) => (
                        <li key={f.id}>
                          {f.titulo} ({f.fonte})
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {m.resposta && <p className="msg__modo">{descreverModo(m.resposta.modo)}</p>}
              </div>
            ),
          )}
          {enviando && (
            <p className="carregando" role="status">
              Consultando a base…
            </p>
          )}
          <div ref={fim} />
        </div>

        <form className="chat__entrada" onSubmit={enviar}>
          <label htmlFor="pergunta" className="sr-only">
            Sua pergunta
          </label>
          <input
            id="pergunta"
            type="text"
            value={pergunta}
            onChange={(e) => setPergunta(e.target.value)}
            maxLength={500}
            placeholder="Ex.: Quantos alagamentos tem no Butantã?"
            autoComplete="off"
          />
          <button type="submit" className="botao" disabled={enviando || !pergunta.trim()}>
            Perguntar
          </button>
        </form>
      </div>
    </>
  );
}
