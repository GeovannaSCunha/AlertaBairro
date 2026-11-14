import type { Metadata } from "next";

import AssistenteCliente from "./AssistenteCliente";

export const metadata: Metadata = { title: "Assistente" };

export default function PaginaAssistente() {
  return <AssistenteCliente />;
}
