"use client";

import { type FormEvent, useEffect, useState } from "react";

import MapaDinamico from "@/components/MapaDinamico";
import { api, ErroApi, useApi } from "@/lib/api";
import { dataHoraBr, numero } from "@/lib/formato";
import { SUBPREFEITURAS_SP } from "@/lib/subprefeituras";
import type { RelatoCriado, TipoRelato } from "@/lib/tipos";

const DESCRICAO_MAX = 500;
const FOTO_MAX_MB = 3;
const LIMITES = { latMin: -24.01, latMax: -23.35, lonMin: -46.83, lonMax: -46.36 };

type Local = { latitude: number; longitude: number };

function agoraLocal(): string {
  const d = new Date();
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 16);
}

/** Regrava a foto no navegador: reduz o tamanho e descarta metadados (EXIF/GPS). O servidor repete a limpeza. */
async function prepararFoto(arquivo: File): Promise<Blob> {
  try {
    const bitmap = await createImageBitmap(arquivo, { imageOrientation: "from-image" });
    const escala = Math.min(1, 1600 / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(bitmap.width * escala);
    canvas.height = Math.round(bitmap.height * escala);
    canvas.getContext("2d")?.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    bitmap.close();
    const blob = await new Promise<Blob | null>((ok) => canvas.toBlob(ok, "image/jpeg", 0.85));
    return blob ?? arquivo;
  } catch {
    return arquivo;
  }
}

function dentroDeSP(l: Local): boolean {
  return (
    l.latitude >= LIMITES.latMin && l.latitude <= LIMITES.latMax && l.longitude >= LIMITES.lonMin && l.longitude <= LIMITES.lonMax
  );
}

function Erro({ id, texto }: { id: string; texto?: string }) {
  if (!texto) return null;
  return (
    <p className="campo__erro" id={id}>
      {texto}
    </p>
  );
}

function Acompanhar() {
  const [protocolo, setProtocolo] = useState("");
  const [resultado, setResultado] = useState<string | null>(null);
  const [buscando, setBuscando] = useState(false);
  const rotulos: Record<string, string> = {
    pendente: "aguardando moderação",
    aprovado: "aprovado e publicado no mapa",
    rejeitado: "não aprovado",
  };

  async function consultar(e: FormEvent) {
    e.preventDefault();
    setBuscando(true);
    setResultado(null);
    try {
      const r = await api<{ status: string; criado_em: string; motivo_moderacao: string | null }>(
        `/relatos/protocolo/${encodeURIComponent(protocolo.trim().toUpperCase())}`,
      );
      setResultado(
        `Relato enviado em ${dataHoraBr(r.criado_em)}: ${rotulos[r.status] ?? r.status}.` +
          (r.motivo_moderacao ? ` Motivo: ${r.motivo_moderacao}` : ""),
      );
    } catch (erro) {
      setResultado(erro instanceof ErroApi && erro.status === 404 ? "Não encontramos esse protocolo. Confira as letras e os números." : erro instanceof Error ? erro.message : "Erro ao consultar.");
    } finally {
      setBuscando(false);
    }
  }

  return (
    <section id="acompanhar" className="secao superficie" aria-labelledby="titulo-acompanhar">
      <h2 id="titulo-acompanhar">Acompanhar um relato</h2>
      <form onSubmit={consultar} style={{ display: "flex", gap: "0.6rem", flexWrap: "wrap", alignItems: "end" }}>
        <div className="campo" style={{ marginBottom: 0, flex: "1 1 14rem" }}>
          <label htmlFor="protocolo">Protocolo</label>
          <input
            id="protocolo"
            type="text"
            value={protocolo}
            onChange={(e) => setProtocolo(e.target.value)}
            placeholder="AB-XXXXXX"
            autoComplete="off"
            maxLength={9}
          />
        </div>
        <button type="submit" className="botao botao--secundario" disabled={buscando || protocolo.trim().length < 9}>
          Consultar protocolo
        </button>
      </form>
      {resultado && (
        <p role="status" style={{ marginTop: "1rem" }}>
          {resultado}
        </p>
      )}
    </section>
  );
}

export default function RelatarCliente() {
  const tipos = useApi<{ dados: TipoRelato[] }>("/relatos/tipos");
  const [tipo, setTipo] = useState("alagamento");
  const [quando, setQuando] = useState("");
  const [maximo, setMaximo] = useState("");
  const [descricao, setDescricao] = useState("");
  const [subprefeitura, setSubprefeitura] = useState("");
  const [local, setLocal] = useState<Local | null>(null);
  const [foto, setFoto] = useState<File | null>(null);
  const [aceite, setAceite] = useState(false);
  const [erros, setErros] = useState<Record<string, string>>({});
  const [erroGeral, setErroGeral] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [criado, setCriado] = useState<RelatoCriado | null>(null);
  const [localizando, setLocalizando] = useState(false);

  useEffect(() => {
    const agora = agoraLocal();
    setQuando(agora);
    setMaximo(agora);
  }, []);

  function marcar(latitude: number, longitude: number) {
    const l = { latitude, longitude };
    setLocal(l);
    setErros((e) => {
      const { localizacao: _removido, ...resto } = e;
      return dentroDeSP(l) ? resto : { ...resto, localizacao: "Esse ponto fica fora do município de São Paulo." };
    });
  }

  function usarMinhaLocalizacao() {
    if (!("geolocation" in navigator)) {
      setErros((e) => ({ ...e, localizacao: "Seu navegador não informa a localização. Marque o ponto no mapa." }));
      return;
    }
    setLocalizando(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        marcar(pos.coords.latitude, pos.coords.longitude);
        setLocalizando(false);
      },
      () => {
        setErros((e) => ({ ...e, localizacao: "Não foi possível obter sua localização. Marque o ponto no mapa." }));
        setLocalizando(false);
      },
      { enableHighAccuracy: false, timeout: 10_000, maximumAge: 60_000 },
    );
  }

  function validarLocal(): Record<string, string> {
    // Mesma ordem dos campos na tela: o foco vai para o primeiro erro que a pessoa encontraria.
    const e: Record<string, string> = {};
    if (!quando) e.ocorrido_em = "Informe a data e a hora da ocorrência.";
    if (descricao.trim().length < 15) e.descricao = "Descreva a ocorrência com pelo menos 15 caracteres.";
    if (foto && foto.size > FOTO_MAX_MB * 4 * 1024 * 1024) e.foto = "Essa foto é grande demais. Escolha outra.";
    if (!aceite) e.aceite_termos = "É preciso concordar com o uso das informações para publicar o relato.";
    if (!local) e.localizacao = "Marque o local da ocorrência no mapa.";
    else if (!dentroDeSP(local)) e.localizacao = "Esse ponto fica fora do município de São Paulo.";
    return e;
  }

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    setErroGeral(null);
    const locais = validarLocal();
    setErros(locais);
    if (Object.keys(locais).length) {
      document.getElementById(`campo-${Object.keys(locais)[0]}`)?.focus();
      return;
    }
    setEnviando(true);
    try {
      const corpo = new FormData();
      corpo.set("tipo", tipo);
      corpo.set("descricao", descricao.trim());
      corpo.set("ocorrido_em", quando);
      corpo.set("latitude", String(local?.latitude));
      corpo.set("longitude", String(local?.longitude));
      corpo.set("aceite_termos", String(aceite));
      if (subprefeitura) corpo.set("subprefeitura", subprefeitura);
      if (foto) {
        const limpa = await prepararFoto(foto);
        if (limpa.size > FOTO_MAX_MB * 1024 * 1024) {
          setErros({ foto: `Mesmo reduzida, a foto passou de ${FOTO_MAX_MB} MB. Escolha outra.` });
          return;
        }
        corpo.set("foto", limpa, "foto.jpg");
      }
      const r = await api<RelatoCriado>("/relatos", { method: "POST", body: corpo });
      setCriado(r);
      window.scrollTo({ top: 0 });
    } catch (e) {
      if (e instanceof ErroApi && Object.keys(e.campos).length) {
        setErros(e.campos);
        setErroGeral(e.message);
      } else {
        setErroGeral(e instanceof Error ? e.message : "Não foi possível enviar. Tente de novo.");
      }
    } finally {
      setEnviando(false);
    }
  }

  function novoRelato() {
    setCriado(null);
    setDescricao("");
    setFoto(null);
    setLocal(null);
    setAceite(false);
    setErros({});
    const agora = agoraLocal();
    setQuando(agora);
    setMaximo(agora);
  }

  if (criado) {
    return (
      <>
        <div className="titulo-pagina">
          <h1>Relato recebido</h1>
        </div>
        <div className="confirmacao" role="status">
          <p>Guarde este protocolo para acompanhar a moderação:</p>
          <p className="protocolo">{criado.protocolo}</p>
          <p>{criado.mensagem}</p>
          <div style={{ display: "flex", gap: "0.6rem", flexWrap: "wrap" }}>
            <button type="button" className="botao" onClick={novoRelato}>
              Relatar outra ocorrência
            </button>
            <a className="botao botao--secundario" href="/mapa">
              Abrir o mapa
            </a>
          </div>
        </div>
        <Acompanhar />
      </>
    );
  }

  const prop = (campo: string) =>
    erros[campo] ? { "aria-invalid": true as const, "aria-describedby": `erro-${campo}` } : {};

  return (
    <>
      <div className="titulo-pagina">
        <h1>Relatar ocorrência</h1>
        <p>
          Viu um alagamento, uma via intransitável ou uma boca de lobo entupida? Conte aqui. Um moderador revisa o relato
          antes de ele aparecer no mapa.
        </p>
      </div>

      {erroGeral && (
        <div className="erro-carga" role="alert" style={{ marginBottom: "1rem" }}>
          <p>{erroGeral}</p>
        </div>
      )}

      <form className="layout-relato" onSubmit={enviar} noValidate>
        <div className="superficie">
          <fieldset className="campo" style={{ border: 0, padding: 0 }}>
            <legend>O que aconteceu</legend>
            <div className="opcoes-radio" id="campo-tipo">
              {(tipos.dados?.dados ?? [{ codigo: "alagamento", rotulo: "Alagamento" }]).map((t) => (
                <label key={t.codigo}>
                  <input type="radio" name="tipo" value={t.codigo} checked={tipo === t.codigo} onChange={() => setTipo(t.codigo)} />
                  <span>{t.rotulo}</span>
                </label>
              ))}
            </div>
            <Erro id="erro-tipo" texto={erros.tipo} />
          </fieldset>

          <div className="campo">
            <label htmlFor="campo-ocorrido_em">Quando</label>
            <input
              id="campo-ocorrido_em"
              type="datetime-local"
              value={quando}
              max={maximo || undefined}
              onChange={(e) => setQuando(e.target.value)}
              {...prop("ocorrido_em")}
            />
            <p className="campo__ajuda">Aceitamos ocorrências dos últimos 7 dias.</p>
            <Erro id="erro-ocorrido_em" texto={erros.ocorrido_em} />
          </div>

          <div className="campo">
            <label htmlFor="campo-descricao">Descrição</label>
            <textarea
              id="campo-descricao"
              value={descricao}
              maxLength={DESCRICAO_MAX}
              onChange={(e) => setDescricao(e.target.value)}
              placeholder="Ex.: Água acima da calçada na esquina da escola, carros desviando pela contramão."
              {...prop("descricao")}
            />
            <p className="campo__ajuda">
              {numero(descricao.length)}/{DESCRICAO_MAX}. Não escreva nome, telefone, e-mail ou CPF.
            </p>
            <Erro id="erro-descricao" texto={erros.descricao} />
          </div>

          <div className="campo">
            <label htmlFor="campo-subprefeitura">Subprefeitura (opcional)</label>
            <select id="campo-subprefeitura" value={subprefeitura} onChange={(e) => setSubprefeitura(e.target.value)}>
              <option value="">Não sei</option>
              {SUBPREFEITURAS_SP.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>

          <div className="campo">
            <label htmlFor="campo-foto">Foto (opcional)</label>
            <input
              id="campo-foto"
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={(e) => setFoto(e.target.files?.[0] ?? null)}
              {...prop("foto")}
            />
            <p className="campo__ajuda">
              Evite rostos e placas de carro. A foto perde a localização da câmera ao ser enviada e é apagada em 90 dias.
            </p>
            <Erro id="erro-foto" texto={erros.foto} />
          </div>

          <div className="campo">
            <label className="caixa-marcar" htmlFor="campo-aceite_termos">
              <input
                id="campo-aceite_termos"
                type="checkbox"
                checked={aceite}
                onChange={(e) => setAceite(e.target.checked)}
                {...prop("aceite_termos")}
              />
              <span style={{ fontWeight: 400 }}>
                Concordo que o tipo, a descrição, a foto e o local aproximado (cerca de 110 m) sejam publicados no mapa
                depois da moderação. Não guardamos meu nome nem meus contatos.
              </span>
            </label>
            <Erro id="erro-aceite_termos" texto={erros.aceite_termos} />
          </div>

          <button type="submit" className="botao botao--relatar" disabled={enviando}>
            {enviando ? "Enviando relato…" : "Enviar relato"}
          </button>
        </div>

        <div>
          <div className="campo">
            <span id="rotulo-local" style={{ fontWeight: 700 }}>
              Onde
            </span>
            <p className="campo__ajuda">Toque no mapa para marcar o local ou use a localização do aparelho.</p>
          </div>
          <MapaDinamico
            marcadores={[]}
            pino={local}
            aoClicarMapa={marcar}
            compacto
            ajustarAosMarcadores={false}
            rotulo="Mapa para marcar o local da ocorrência"
          />
          <div style={{ display: "flex", gap: "0.6rem", flexWrap: "wrap", alignItems: "center", marginTop: "0.75rem" }}>
            <button
              type="button"
              id="campo-localizacao"
              className="botao botao--secundario"
              onClick={usarMinhaLocalizacao}
              disabled={localizando}
              aria-describedby={erros.localizacao ? "erro-localizacao" : undefined}
            >
              {localizando ? "Obtendo localização…" : "Usar minha localização"}
            </button>
            <span role="status" style={{ color: "var(--concreto)" }}>
              {local
                ? `Ponto marcado: ${numero(local.latitude, 3)}, ${numero(local.longitude, 3)}`
                : "Nenhum ponto marcado ainda."}
            </span>
          </div>
          <Erro id="erro-localizacao" texto={erros.localizacao} />
        </div>
      </form>

      <Acompanhar />
    </>
  );
}
