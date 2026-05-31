##  📊 Visualização do Painel

<p align="center">
  <img src="./dashboard/screenshot.png" alt="Painel de Produção Citrícola Brasil" width="100%">
</p>

Decisões Técnicas do Projeto

Correção de NoneType (Mesorregião vs. Região Intermediária): Tive erros de NoneType em Mesorregião e, pesquisando, descobri que o IBGE substituiu essa divisão em 2017 pelas Regiões Intermediárias. Incluí essa nova divisão na extração e no BI. Na Mesorregião antiga, configurei para substituir o null por "Não Mapeado" para evitar "Em Branco" no power bi.

Tratamento de Municípios Novos : Observei falhas em municípios novos/não configurados na API (como Boa Esperança do Norte, que vinha sem dados de região). Optei por inseri-lo no DataFrame e inserir a região de acordo com a sigla do uf

Validação com Pydantic: Usei o Pydantic para validar os campos, evitando de qualquer alteração na api impacte na extração

Logging e Retry: Implementei um sistema de reentativas (retry) focado apenas em erros por instabilidade do servidor. O logging foi estruturado para facilitar o mapeamento de falhas, pensando no funcionamento do script dentro de um container.

Realizei uma validação nos ids para garantir que os dados estão retornando corretamente da api, caso mude dados da coluna, vamos conseguir mapear.

Realizei validações nas regiões para entender se existem regiões não mapeadas,  para entender quando ocorreu. A ideia é ter qualidade nos dados, optei por não restringir a geração do csv por não encontrar nenhum caso.

No case não solicitava para trazer da api o UF e o Estado, mas como é necessário para gerar a dim_municipio, eu já inclui essa info do ibge que é confiável

O Desafio pede para  ter uma linha por municipio, produto, ano. Como os dados já estão nessa granularidade, não houve necessidade de realizar qualquer tratamento, mas caso houvessem duplicatas seriam removidas, ou mais de uma linha diferente por combinação, eu iria soma-las.

Realizei a modelagem dos dados com Sqlite e salvei em csv pela portabilidade, por poder rodar em qualquer maquina sem instalar nada extra.
Salvei em csv pelo mesmo motivo, para carrega-lo direto no power bi  ao inves de conexão com sql

Encontrei uma inconsistencia no dataset enviado onde Petrolina estava como estado bahia, precisei fazer o join utilizando PE para fazer a classificação corretamente


Produto não é mencionado no case para ser incluido na tabela de produção, entretando é utilizado no dashboard. Optei por criar uma nova tabela dimensão para seguir o starschema

Optei por manter uma tabela calendário no BI apenas para manter a estrutura, mas não está sendo utilizada, dado que a análise é apenas por ano

