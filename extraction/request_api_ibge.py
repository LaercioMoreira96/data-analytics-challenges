import logging
from typing import Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import pandas as pd
from pydantic import BaseModel, Field



# Configuração do log


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Configuração do pydantic

class Regiao(BaseModel):
    nome: str

class UF(BaseModel):
    sigla: str
    nome: str
    regiao: Optional[Regiao] = None

class RegiaoIntermediaria(BaseModel):
    id: int
    nome: str
    UF: UF

class RegiaoImediata(BaseModel):
    id: int
    nome: str
    regiao_intermediaria: Optional[RegiaoIntermediaria] = Field(None, alias="regiao-intermediaria")

class Mesorregiao(BaseModel):
    nome: str
    UF: UF

class Microrregiao(BaseModel):
    mesorregiao: Optional[Mesorregiao] = None



class Municipio(BaseModel):
    id: int
    nome: str
    microrregiao: Optional[Microrregiao] = None
    regiao_imediata: Optional[RegiaoImediata] = Field(None, alias="regiao-imediata")


# Configuração do retry
sessao = requests.Session()

config_tentativas = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[500, 502, 503, 504],
    raise_on_status=False
)

adaptador = HTTPAdapter(max_retries=config_tentativas)
sessao.mount('https://', adaptador)

# Lista de ufs 26 + DF
ufs = ['ac', 'al', 'ap', 'am', 'ba', 'ce', 'df', 'es', 'go', 'ma', 'mt', 'ms', 'mg', 'pa', 'pb', 'pr', 'pe', 'pi', 'rj', 'rn', 'rs', 'ro', 'rr', 'sc', 'sp', 'se', 'to']
nome_regioes = {
    'SP': 'Sudeste', 'RJ': 'Sudeste', 'MG': 'Sudeste', 'ES': 'Sudeste',
    'RS': 'Sul', 'SC': 'Sul', 'PR': 'Sul',
    'MT': 'Centro-Oeste', 'MS': 'Centro-Oeste', 'GO': 'Centro-Oeste', 'DF': 'Centro-Oeste',
    'BA': 'Nordeste', 'PE': 'Nordeste', 'CE': 'Nordeste', 'MA': 'Nordeste', 'PI': 'Nordeste', 
    'RN': 'Nordeste', 'PB': 'Nordeste', 'AL': 'Nordeste', 'SE': 'Nordeste',
    'AM': 'Norte', 'PA': 'Norte', 'RO': 'Norte', 'RR': 'Norte', 'AC': 'Norte', 'TO': 'Norte', 'AP': 'Norte'
}

tabela_municipios = []

# Requisição com laço de repetição, para puxar municipios de acordo com cada uf. 
for uf in ufs:
    try:
        logging.info(f"Tentando coleta dos municípios da UF '{uf.upper()}'...")
        resposta = sessao.get(
            f'https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf}/municipios',
            timeout=10
        )
        resposta.raise_for_status()

        municipios_uf = resposta.json()
        logging.info(f"UF '{uf.upper()}' — {len(municipios_uf)} municípios recebidos.")

        for item in municipios_uf:
            try:
                municipio = Municipio.model_validate(item)
                mesorregiao = municipio.microrregiao.mesorregiao if municipio.microrregiao else None
                regiao_imediata = municipio.regiao_imediata
                regiao_intermediaria = regiao_imediata.regiao_intermediaria if regiao_imediata else None

                if not mesorregiao:
                    logging.warning(f"Município sem mesorregião: {municipio.nome} ({uf.upper()})")

                tabela_municipios.append({
                    'id': municipio.id,
                    'nome': municipio.nome,
                    'uf': uf.upper(),
                    # Aqui esta olhando para região para garantir que tenha um estado, porque nem todos os municipios tem mesorregiao
                    'estado': mesorregiao.UF.nome if mesorregiao else (regiao_imediata.regiao_intermediaria.UF.nome if regiao_imediata else "Não Mapeado"),
                    'mesorregiao':  mesorregiao.nome  if mesorregiao else "Não Mapeado",
                    'regiao_brasil': mesorregiao.UF.regiao.nome   if mesorregiao and mesorregiao.UF.regiao else nome_regioes.get(uf.upper(), "Não mapeada"),
                    'regiao_imediata': municipio.regiao_imediata.nome if municipio.regiao_imediata else "Não Mapeada",
                    'regiao_intermediaria': regiao_intermediaria.nome if regiao_intermediaria else "Não Mapeada"
                })
            except Exception as e:
                logging.warning(f"Município ignorado em {uf.upper()} ({item.get('nome')}): {e}")

        logging.info(f"UF '{uf.upper()}' processada — {len(tabela_municipios)} municípios acumulados.")

    except requests.exceptions.HTTPError as e:
        logging.error(f"Erro HTTP {e.response.status_code} na UF '{uf}' após tentativas.")
    except requests.exceptions.ConnectionError as e:
        logging.error(f"Erro de conexão na UF '{uf}' (Rede fora do ar): {e}")
    except Exception as e:
        logging.error(f"Erro inesperado na UF '{uf}': {e}")

tabela_municipios_df = pd.DataFrame(tabela_municipios)
# Verificação para entender se houve alguma mudança no formato do ID dos municípios, que deve ser um número inteiro de 7 dígitos
if (tabela_municipios_df['id'].astype(str).str.len() != 7).any():
    logging.warning("Existem IDs que não seguem a regra de 7 dígitos. Verifique os dados.")
# Para entender se teve alguma mudança igual o ocorrido no mesorregião
if (tabela_municipios_df['regiao_intermediaria'] == "Não Mapeada").any() or (tabela_municipios_df['regiao_imediata'] == "Não Mapeada").any():
    logging.warning("Existem municípios com regiões geográficas (imediata ou intermediária) não mapeadas pelo IBGE. Verifique os dados.")
tabela_municipios_df.to_csv('municipios_api.csv', index=False, encoding='utf-8-sig')