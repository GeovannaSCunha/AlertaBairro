/** Mesma regra do backend (app/texto.py): sem acento, maiúsculas, só letras e números. */
export function chave(texto: string | null | undefined): string {
  if (!texto) return "";
  return texto
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toUpperCase()
    .replace(/[^A-Z0-9]/g, "");
}
