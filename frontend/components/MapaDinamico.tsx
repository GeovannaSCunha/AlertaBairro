"use client";

import dynamic from "next/dynamic";

// O Leaflet usa `window` ao ser importado; por isso o mapa só é carregado no navegador.
const MapaDinamico = dynamic(() => import("./Mapa"), {
  ssr: false,
  loading: () => (
    <div className="mapa mapa-vazio" role="status">
      Carregando o mapa…
    </div>
  ),
});

export default MapaDinamico;
export type { Marcador } from "./Mapa";
