import type { Metadata } from "next";

import RelatarCliente from "./RelatarCliente";

export const metadata: Metadata = { title: "Relatar ocorrência" };

export default function PaginaRelatar() {
  return <RelatarCliente />;
}
