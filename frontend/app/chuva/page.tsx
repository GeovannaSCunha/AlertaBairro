import type { Metadata } from "next";

import ChuvaCliente from "./ChuvaCliente";

export const metadata: Metadata = { title: "Chuva e contexto" };

export default function PaginaChuva() {
  return <ChuvaCliente />;
}
