/** Mesma regra do backend (app/texto.py): sem sigla inicial ("MP - "), sem acento, maiúsculas, só letras e números. */
export function chave(texto: string | null | undefined): string {
  if (!texto) return "";
  return texto
    .replace(/^\s*[A-Za-z]{1,3}\s*[-–]\s+/, "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toUpperCase()
    .replace(/[^A-Z0-9]/g, "");
}
