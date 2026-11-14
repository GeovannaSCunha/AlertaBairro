// Contratos da API AlertaBairro (backend/app/rotas). Mantenha em sincronia com o backend.

export type Meta = {
  origem: "databricks" | "snapshot" | "comunidade" | string;
  tabela: string;
  natureza?: string;
  consultado_em?: string | null;
  snapshot_validado_em?: string | null;
  aviso?: string | null;
  simulacao?: boolean;
  tabela_clima?: string;
  pontos_disponiveis?: boolean;
  moderado?: boolean;
};

export type Envelope<T> = { dados: T; meta: Meta };

export type Kpis = {
  alagamentos: { total: number; periodo_inicio: string | null; periodo_fim: string | null };
  subprefeituras_com_registros: number;
  clima: {
    chuva_acumulada_mm: number | null;
    maior_chuva_diaria_mm: number | null;
    data_maior_chuva: string | null;
    periodo_inicio: string | null;
    periodo_fim: string | null;
    ponto_referencia: { latitude: number; longitude: number; descricao: string };
  };
};

export type Subprefeitura = {
  codigo: string | null;
  subprefeitura: string;
  chave: string;
  total_ocorrencias: number;
  primeira_ocorrencia: string | null;
  ultima_ocorrencia: string | null;
};

export type Ranking = {
  itens: Subprefeitura[];
  demais: { grupos: number; total_ocorrencias: number } | null;
};

export type PontoMensal = { mes: string; total_ocorrencias: number };
export type Mensal = { serie: PontoMensal[]; lacunas: string[] };

export type DiaChuva = { data: string; precipitacao_mm: number | null; precipitacao_acumulada_mm: number | null };
export type Clima = {
  serie: DiaChuva[];
  ponto_referencia: { latitude: number; longitude: number; descricao: string };
  fonte_original: string;
};

export type Ponto = {
  id: string;
  data: string | null;
  tipo: string | null;
  subprefeitura: string | null;
  subprefeitura_exibicao: string;
  latitude: number;
  longitude: number;
};

export type DadosMapa = {
  pontos: Ponto[];
  total_filtrado: number;
  total: number;
  filtros: { subprefeituras: string[]; meses: string[] };
};

export type NivelCodigo = "baixa" | "moderada" | "elevada";

export type RegiaoIndice = {
  subprefeitura: string;
  chave: string;
  total_ocorrencias: number;
  componente_historico: number;
  componente_chuva: number;
  pontuacao: number;
  nivel: NivelCodigo;
  rotulo: string;
  explicacao: string;
};

export type Indice = {
  data_referencia: string;
  chuva: {
    considerada: boolean;
    mm_72h: number | null;
    janela_inicio: string | null;
    janela_fim: string | null;
    motivo: string;
    pontos: number;
  };
  regioes: RegiaoIndice[];
  regras: string[];
  aviso: string;
  demais: { grupos: number; total_ocorrencias: number } | null;
};

export type Participacao = {
  total: number;
  pendente: number;
  aprovado: number;
  rejeitado: number;
  taxa_aprovacao: number | null;
  ultimo_relato_em: string | null;
};

export type Indicadores = {
  cobertura: { ocorrencias_mapeadas: number; subprefeituras_com_registros: number; total_subprefeituras_sp: number };
  qualidade: { origem_dados: string; consultado_em: string | null; snapshot_validado_em: string | null };
  participacao: Participacao;
};

export type TipoRelato = { codigo: string; rotulo: string };

export type RelatoPublico = {
  id: string;
  tipo: string;
  tipo_rotulo: string;
  descricao: string;
  ocorrido_em: string;
  latitude: number;
  longitude: number;
  subprefeitura: string | null;
  tem_foto: boolean;
};

export type RelatoModeracao = RelatoPublico & {
  protocolo: string;
  status: "pendente" | "aprovado" | "rejeitado";
  criado_em: string;
  motivo_moderacao: string | null;
};

export type RelatoCriado = { id: string; protocolo: string; status: string; mensagem: string };

export type FonteResposta = { id: string; titulo: string; fonte: string };

export type RespostaAssistente = {
  resposta: string;
  fontes: FonteResposta[];
  recusou: boolean;
  motivo_recusa: string | null;
  modo: string;
  ferramentas: string[];
  categoria: string;
};

export type InfoAssistente = {
  modo: string;
  modelo: string | null;
  limiar_relevancia: number;
  cobertura_minima: number;
  exemplos: string[];
};

export type StatusApi = {
  versao: string;
  dados: {
    modo: "databricks" | "snapshot";
    databricks_configurado: boolean;
    ultima_consulta_ok: string | null;
    ultima_falha: string | null;
    falhas_consecutivas: number;
    snapshot_validado_em: string;
    catalogo: string;
  };
  assistente: { modo: string };
  moderacao_habilitada: boolean;
};
