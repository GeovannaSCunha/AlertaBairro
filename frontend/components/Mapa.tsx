"use client";

import "leaflet/dist/leaflet.css";

import L from "leaflet";
import { useEffect, useRef } from "react";

export type Marcador = {
  id: string;
  latitude: number;
  longitude: number;
  tipo: "historico" | "relato";
  titulo: string;
  linhas: string[];
  origem: string;
  fotoUrl?: string;
};

export type PropsMapa = {
  marcadores: Marcador[];
  rotulo: string;
  selecionado?: string | null;
  aoClicarMapa?: (latitude: number, longitude: number) => void;
  pino?: { latitude: number; longitude: number } | null;
  compacto?: boolean;
  ajustarAosMarcadores?: boolean;
};

const CENTRO_SP: L.LatLngTuple = [-23.55, -46.63];
const LIMITES_SP = L.latLngBounds([-24.1, -47.0], [-23.25, -46.2]);

function urlTiles(): string {
  const escuro = document.documentElement.dataset.tema === "escuro";
  return `https://{s}.basemaps.cartocdn.com/${escuro ? "dark_all" : "light_all"}/{z}/{x}/{y}{r}.png`;
}

/** Conteúdo do popup montado com textContent: relatos vêm de moradores, então nada é interpretado como HTML. */
function conteudoPopup(m: Marcador): HTMLElement {
  const raiz = document.createElement("div");
  const titulo = document.createElement("strong");
  titulo.className = "popup-titulo";
  titulo.textContent = m.titulo;
  raiz.appendChild(titulo);
  for (const linha of m.linhas) {
    const p = document.createElement("span");
    p.style.display = "block";
    p.textContent = linha;
    raiz.appendChild(p);
  }
  if (m.fotoUrl) {
    const img = document.createElement("img");
    img.src = m.fotoUrl;
    img.alt = "Foto enviada junto com o relato";
    img.loading = "lazy";
    img.style.maxWidth = "220px";
    img.style.marginTop = "0.4rem";
    img.style.borderRadius = "4px";
    raiz.appendChild(img);
  }
  const origem = document.createElement("span");
  origem.className = "popup-origem";
  origem.textContent = m.origem;
  raiz.appendChild(origem);
  return raiz;
}

export default function Mapa({
  marcadores,
  rotulo,
  selecionado,
  aoClicarMapa,
  pino,
  compacto = false,
  ajustarAosMarcadores = true,
}: PropsMapa) {
  const elemento = useRef<HTMLDivElement>(null);
  const mapa = useRef<L.Map | null>(null);
  const camada = useRef<L.LayerGroup | null>(null);
  const tiles = useRef<L.TileLayer | null>(null);
  const pinoRef = useRef<L.CircleMarker | null>(null);
  const porId = useRef(new Map<string, L.CircleMarker>());
  const aoClicar = useRef(aoClicarMapa);
  aoClicar.current = aoClicarMapa;

  // Cria o mapa uma única vez
  useEffect(() => {
    if (!elemento.current || mapa.current) return;
    const m = L.map(elemento.current, {
      center: CENTRO_SP,
      zoom: 11,
      minZoom: 9,
      maxBounds: LIMITES_SP,
      maxBoundsViscosity: 0.8,
      preferCanvas: false,
    });
    tiles.current = L.tileLayer(urlTiles(), {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
      subdomains: "abcd",
      maxZoom: 19,
    }).addTo(m);
    camada.current = L.layerGroup().addTo(m);
    m.on("click", (e: L.LeafletMouseEvent) => aoClicar.current?.(e.latlng.lat, e.latlng.lng));
    mapa.current = m;

    const trocarTema = () => tiles.current?.setUrl(urlTiles());
    window.addEventListener("alertabairro:tema", trocarTema);
    return () => {
      window.removeEventListener("alertabairro:tema", trocarTema);
      m.remove();
      mapa.current = null;
    };
  }, []);

  // Marcadores
  useEffect(() => {
    const m = mapa.current;
    const grupo = camada.current;
    if (!m || !grupo) return;
    grupo.clearLayers();
    porId.current.clear();
    for (const item of marcadores) {
      const marcador = L.circleMarker([item.latitude, item.longitude], {
        radius: item.tipo === "relato" ? 8 : 6,
        weight: 1.5,
        fillOpacity: 0.85,
        className: item.tipo === "relato" ? "marcador-relato" : "marcador-historico",
        bubblingMouseEvents: false,
      });
      marcador.bindPopup(() => conteudoPopup(item), { maxWidth: 260 });
      marcador.bindTooltip(item.titulo, { direction: "top", offset: [0, -6] });
      marcador.addTo(grupo);
      porId.current.set(item.id, marcador);
    }
    if (ajustarAosMarcadores && marcadores.length > 0) {
      const limites = L.latLngBounds(marcadores.map((x) => [x.latitude, x.longitude] as L.LatLngTuple));
      m.fitBounds(limites, { padding: [36, 36], maxZoom: 15 });
    }
  }, [marcadores, ajustarAosMarcadores]);

  // Destaque vindo da lista lateral
  useEffect(() => {
    if (!selecionado || !mapa.current) return;
    const marcador = porId.current.get(selecionado);
    if (marcador) {
      mapa.current.setView(marcador.getLatLng(), Math.max(mapa.current.getZoom(), 14));
      marcador.openPopup();
    }
  }, [selecionado]);

  // Pino do formulário de relato
  useEffect(() => {
    const m = mapa.current;
    if (!m) return;
    pinoRef.current?.remove();
    pinoRef.current = null;
    if (pino) {
      pinoRef.current = L.circleMarker([pino.latitude, pino.longitude], {
        radius: 11,
        weight: 3,
        fillOpacity: 0.9,
        className: "marcador-pino",
      }).addTo(m);
      if (!m.getBounds().contains([pino.latitude, pino.longitude])) {
        m.setView([pino.latitude, pino.longitude], 15);
      }
    }
  }, [pino]);

  return (
    <div
      ref={elemento}
      className={compacto ? "mapa mapa--compacto" : "mapa"}
      role="region"
      aria-label={rotulo}
    />
  );
}
