import type { Metadata } from "next";

import RegioesCliente from "./RegioesCliente";

export const metadata: Metadata = { title: "Regiões e meses" };

export default function PaginaRegioes() {
  return <RegioesCliente />;
}
