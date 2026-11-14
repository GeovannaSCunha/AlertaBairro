"use client";

import { useCallback, useEffect, useState } from "react";

// O navegador fala apenas com o próprio frontend (/api/*); o proxy em app/api/[...caminho]
// encaminha para a API FastAPI. Nenhum segredo do Databricks chega ao navegador.
const BASE = "/api";

export class ErroApi extends Error {
  status: number;
  campos: Record<string, string>;

  constructor(mensagem: string, status: number, campos: Record<string, string> = {}) {
    super(mensagem);
    this.status = status;
    this.campos = campos;
  }
}

async function lerErro(resposta: Response): Promise<ErroApi> {
  let mensagem = "Não foi possível falar com o servidor do AlertaBairro.";
  let campos: Record<string, string> = {};
  try {
    const corpo = (await resposta.json()) as { detail?: unknown; campos?: Record<string, string> };
    if (typeof corpo.detail === "string") mensagem = corpo.detail;
    if (corpo.campos) campos = corpo.campos;
  } catch {
    // resposta sem JSON: mantém a mensagem padrão
  }
  if (resposta.status === 429 && mensagem.startsWith("Não foi")) {
    mensagem = "Muitas solicitações em pouco tempo. Aguarde alguns minutos e tente de novo.";
  }
  return new ErroApi(mensagem, resposta.status, campos);
}

export async function api<T>(caminho: string, init?: RequestInit): Promise<T> {
  let resposta: Response;
  try {
    resposta = await fetch(`${BASE}${caminho}`, { cache: "no-store", ...init });
  } catch {
    throw new ErroApi("Sem conexão com o servidor. Verifique sua internet e tente de novo.", 0);
  }
  if (!resposta.ok) throw await lerErro(resposta);
  return (await resposta.json()) as T;
}

export function postarJson<T>(caminho: string, corpo: unknown, cabecalhos: Record<string, string> = {}): Promise<T> {
  return api<T>(caminho, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...cabecalhos },
    body: JSON.stringify(corpo),
  });
}

export type EstadoApi<T> = {
  dados: T | null;
  erro: string | null;
  carregando: boolean;
  recarregar: () => void;
};

export function useApi<T>(caminho: string | null): EstadoApi<T> {
  const [dados, setDados] = useState<T | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState<boolean>(caminho !== null);
  const [versao, setVersao] = useState(0);

  useEffect(() => {
    if (caminho === null) {
      setCarregando(false);
      return;
    }
    let ativo = true;
    setCarregando(true);
    setErro(null);
    api<T>(caminho)
      .then((r) => {
        if (ativo) setDados(r);
      })
      .catch((e: unknown) => {
        if (ativo) setErro(e instanceof Error ? e.message : "Erro inesperado.");
      })
      .finally(() => {
        if (ativo) setCarregando(false);
      });
    return () => {
      ativo = false;
    };
  }, [caminho, versao]);

  const recarregar = useCallback(() => setVersao((v) => v + 1), []);
  return { dados, erro, carregando, recarregar };
}
