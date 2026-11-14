import type { Metadata } from "next";

import ModeracaoCliente from "./ModeracaoCliente";

export const metadata: Metadata = { title: "Moderação", robots: { index: false, follow: false } };

export default function PaginaModeracao() {
  return <ModeracaoCliente />;
}
