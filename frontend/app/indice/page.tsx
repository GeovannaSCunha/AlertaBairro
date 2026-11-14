import type { Metadata } from "next";

import IndiceCliente from "./IndiceCliente";

export const metadata: Metadata = { title: "Índice experimental de atenção" };

export default function PaginaIndice() {
  return <IndiceCliente />;
}
