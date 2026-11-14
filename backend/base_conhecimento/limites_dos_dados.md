# Limites dos dados do AlertaBairro
Fonte: Relatório técnico AlertaBairro — Databricks (13/11/2026)

## Os dados são históricos
Os alagamentos vêm do GeoSampa/Defesa Civil e cobrem de janeiro a setembro de 2026. A chuva vem do Open-Meteo e cobre de 28 de outubro a 6 de novembro de 2026. Os dois períodos não se sobrepõem, então não é possível afirmar correlação entre chuva e alagamento com esta base. O AlertaBairro não faz monitoramento em tempo real nem previsão.

## O ranking não é um índice de risco
O ranking de subprefeituras mostra quantos registros de alagamento estão na base para cada região. Ele não mede gravidade, não considera população nem área e não indica a probabilidade de um novo alagamento.

## Como funciona o índice experimental
O índice experimental soma dois componentes. O histórico (H) dá de 0 a 3 pontos conforme a quantidade de registros da subprefeitura: até 4 registros, 0 ponto; de 5 a 14, 1; de 15 a 49, 2; 50 ou mais, 3. A chuva recente (C) dá de 0 a 2 pontos conforme a soma dos últimos 3 dias no ponto de referência: menos de 10 mm, 0; de 10 a 29,9 mm, 1; 30 mm ou mais, 2. A chuva só conta quando o dado climático tem no máximo 3 dias. De 0 a 1 ponto, a atenção é baixa; de 2 a 3, moderada; de 4 a 5, elevada. O índice é ilustrativo e não substitui a Defesa Civil.

## Julho sem dados
Julho de 2026 não tem linha na tabela mensal de alagamentos. Isso é uma lacuna da base e não comprova que não houve alagamentos nesse mês.

## Chuva medida em um único ponto
A chuva usada pelo AlertaBairro é a de uma coordenada de referência na região central de São Paulo (latitude -23,55 e longitude -46,63). Ela não representa a chuva de cada bairro, que pode variar muito numa mesma tarde.

## Atualização dos dados
Os lotes de dados são coletados por um DAG do Airflow e enviados ao Databricks, onde passam pelas camadas Bronze, Prata e Ouro. Na versão atual, o envio ao Databricks é manual. Por isso, o AlertaBairro mostra em cada tela a origem e a data dos dados.
