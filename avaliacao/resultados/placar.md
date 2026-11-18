| Métrica | sem_contexto (qwen2.5:3b-instruct) | rag (qwen2.5:3b-instruct) | lora_rag (alertabairro-lora) |
|---|---|---|---|
| Acerto geral (50 casos) | 24,0% | 78,0% | 88,0% |
| Acerto nas perguntas com resposta | 5,4% | 73,0% | 86,5% |
| Recusa correta ('não consta' e previsão) | 76,9% | 92,3% | 92,3% |
| Alucinação que chega ao usuário | 16,0% | 4,0% | 2,0% |
| Respostas barradas pela validação do JSON | 0,0% | 14,0% | 4,0% |
| Recusa indevida | 54,0% | 0,0% | 2,0% |
| JSON válido (chamadas ao modelo) | 100,0% | 83,3% | 95,2% |
| Citou o trecho correto | — | 69,4% | 91,4% |
| Chamadas ao modelo | 50 | 42 | 42 |
| Casos com correção manual | 10 | 1 | 2 |
| Latência média (s) | 0,6 | 0,6 | 0,9 |
