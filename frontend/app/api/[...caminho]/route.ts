// Proxy do navegador para a API FastAPI.
// O navegador chama /api/<rota>; aqui encaminhamos para ${API_URL}/api/v1/<rota>.
// Vantagens: sem CORS, URL da API privada à rede interna e variável lida em tempo de execução.

import type { NextRequest } from "next/server";

export const dynamic = "force-dynamic";

const API_URL = (process.env.API_URL ?? "http://localhost:8000").replace(/\/$/, "");
const SEGMENTO_VALIDO = /^[A-Za-z0-9._-]+$/;
const CABECALHOS_REPASSADOS = ["content-type", "authorization", "accept"];
const TEMPO_LIMITE_MS = 60_000;

type Contexto = { params: Promise<{ caminho: string[] }> };

async function encaminhar(req: NextRequest, ctx: Contexto): Promise<Response> {
  const { caminho } = await ctx.params;
  if (!caminho.length || caminho.some((s) => !SEGMENTO_VALIDO.test(s) || s === "..")) {
    return Response.json({ detail: "Caminho inválido" }, { status: 400 });
  }

  const destino = `${API_URL}/api/v1/${caminho.join("/")}${req.nextUrl.search}`;
  const cabecalhos = new Headers();
  for (const nome of CABECALHOS_REPASSADOS) {
    const valor = req.headers.get(nome);
    if (valor) cabecalhos.set(nome, valor);
  }
  // Usa o ÚLTIMO IP da cadeia (o que o balanceador da nuvem viu); o primeiro pode ser forjado pelo cliente.
  const ipCliente =
    req.headers.get("x-forwarded-for")?.split(",").pop()?.trim() || req.headers.get("x-real-ip") || null;
  if (ipCliente) cabecalhos.set("x-forwarded-for", ipCliente);

  const comCorpo = req.method !== "GET" && req.method !== "HEAD";
  let resposta: Response;
  try {
    resposta = await fetch(destino, {
      method: req.method,
      headers: cabecalhos,
      body: comCorpo ? req.body : undefined,
      cache: "no-store",
      redirect: "manual",
      signal: AbortSignal.timeout(TEMPO_LIMITE_MS),
      // Necessário no Node para enviar o corpo como stream (upload de foto)
      ...(comCorpo ? { duplex: "half" } : {}),
    } as RequestInit);
  } catch {
    return Response.json(
      { detail: "A API do AlertaBairro não respondeu. Tente de novo em instantes." },
      { status: 502 },
    );
  }

  const saida = new Headers();
  for (const nome of ["content-type", "cache-control", "retry-after", "www-authenticate"]) {
    const valor = resposta.headers.get(nome);
    if (valor) saida.set(nome, valor);
  }
  return new Response(resposta.body, { status: resposta.status, headers: saida });
}

export const GET = encaminhar;
export const POST = encaminhar;
