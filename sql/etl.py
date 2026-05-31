import sqlite3
import pandas as pd


caminho_dadosbrutos = r".\data\producao_citros_bruto (1).csv"
caminho_municipios = r".\extraction\municipios_api.csv"

caminho_saida_fato = r".\data\fato_producao.csv"
caminho_saida_dim = r".\data\dim_municipio.csv"
caminho_saida_produto = r".\data\dim_produto.csv"

con = sqlite3.connect(":memory:")

pd.read_csv(caminho_dadosbrutos).to_sql("view_producao", con, if_exists="replace", index=False)
pd.read_csv(caminho_municipios).to_sql("view_municipios", con, if_exists="replace", index=False)

# Realizei uma análise prévia nos dados de produção e vi que as colunas estavam sujas, com "-", optei por transformar em null, até porque esses dados não vão para a análise final
# Estou utilizando UPPER para fazer o join, pois existem diferenças entre os nomes do município entre as duas tabelas, como por exemplo "São Paulo" e "SÃO PAULO".
# Os nomes de município da tabela fato não foram ajustados para a inicial maiuscula porque não encontrei uma função nativa para fazer com sqlite, e como vou usar a informação da tabela dimensão no BI, não tem necessidade.
# Join com municipio e UF porque tem mais de um município com o mesmo nome em estados diferentes, como por exemplo "São José" que existe em vários estados. E Petrolina classificado como BA no dataset, precisei ajustar no join para PE
query_fato_dadosbrutos = """
    WITH dados_higienizados AS (
        SELECT 
            m.id AS cod_municipio_ibge,
            b.cod_produto,
            b.ano,
                 
            CASE WHEN b.qtd_produzida_ton IN ('-', '') THEN NULL 
                 ELSE CAST(b.qtd_produzida_ton AS REAL) 
            END AS qtd_produzida_ton,
            
            CASE WHEN b.area_colhida_ha IN ('-', '') THEN NULL 
                 ELSE CAST(b.area_colhida_ha AS REAL) 
            END AS area_colhida_ha,
            
            CASE WHEN b.valor_producao_reais IN ('-', '') THEN NULL 
                 ELSE CAST(b.valor_producao_reais AS REAL) 
            END AS valor_producao_reais
            
        FROM view_producao b
        JOIN view_municipios m 
          ON UPPER(TRIM(b.municipio)) = UPPER(TRIM(m.nome))
          AND UPPER(TRIM(CASE WHEN UPPER(TRIM(b.municipio)) = 'PETROLINA' THEN 'PE' ELSE b.uf END)) = UPPER(TRIM(m.uf))
    )
    SELECT 
        cod_municipio_ibge,
        cod_produto,
        ano,
        qtd_produzida_ton,
        area_colhida_ha,
        valor_producao_reais,
        (qtd_produzida_ton / area_colhida_ha) AS produtividade_ton_ha
    FROM dados_higienizados
    WHERE qtd_produzida_ton IS NOT NULL AND qtd_produzida_ton > 0
      AND area_colhida_ha IS NOT NULL AND area_colhida_ha > 0
"""

query_dim_municipio = """
    SELECT DISTINCT
        id AS cod_municipio_ibge,
       nome AS nome_municipio,
        uf,
        estado,
        mesorregiao,
        regiao_brasil,
        regiao_imediata,
        regiao_intermediaria
    FROM view_municipios
"""

query_dim_produto = """
    SELECT DISTINCT
        cod_produto,
        produto AS nome_produto
    FROM view_producao
    WHERE cod_produto IS NOT NULL AND cod_produto != ''
"""

df_fato = pd.read_sql_query(query_fato_dadosbrutos, con)
df_dim = pd.read_sql_query(query_dim_municipio, con)
df_produto = pd.read_sql_query(query_dim_produto, con)

df_fato.to_csv(caminho_saida_fato, index=False)
df_dim.to_csv(caminho_saida_dim, index=False)
df_produto.to_csv(caminho_saida_produto, index=False)

con.close()

print("Processamento concluído com sucesso!")