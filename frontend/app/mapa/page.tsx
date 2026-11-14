import type { Metadata } from "next";
import { Suspense } from "react";

import { Carregando } from "@/components/Estados";

import MapaCliente from "./MapaCliente";

export const metadata: Metadata = { title: "Mapa de ocorrências" };

export default function PaginaMapa() {
  return (
    <Suspense fallback={<Carregando texto="Carregando o mapa…" />}>
      <MapaCliente />
    </Suspense>
  );
}
