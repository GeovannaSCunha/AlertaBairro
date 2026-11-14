import Link from "next/link";

export default function NaoEncontrada() {
  return (
    <div className="titulo-pagina">
      <h1>Página não encontrada</h1>
      <p>Esse endereço não existe no AlertaBairro.</p>
      <Link className="botao" href="/">
        Voltar para o início
      </Link>
    </div>
  );
}
