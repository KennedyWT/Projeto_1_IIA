#Bibliotecas
import pandas as pd
from geopy.geocoders import Nominatim
import time

#1° Etapa: processar e ler os dados
print("1° Etapa: processando e leitura dos dados")
print("Importação OK!")
dados = pd.read_excel("dataprod/produtores.xlsx")
print("Leitura OK!")
print(dados.head(10))
print()


#2° Etapa: refinamento dos dados
print("2° Etapa: refinando os dados")

# remover linhas com valores vazios
dados = dados.dropna(subset=["location_x", "location_y", "location_address", "location_desc", "location_site"])

# renomear colunas para facilitar a leitura
dados = dados.rename(columns={
    "location_x": "longitude",
    "location_y": "latitude",
    "location_adress": "endereco",
    "location_d": "referencia",
    "location_site": "localizacao",
    "location_site_otherdesc": "complemento"
})

# transformar tipos de dados em float
dados["latitude"] = dados["latitude"].astype(float)
dados["longitude"] = dados["longitude"].astype(float)
print("Dados organizados")

#Revisar os dados
print(dados.head(10))
print()


#3° Etapa: Geocoordenadas
print("3° Etapa: Refinando coordenadas geoespaciais")
#Verificar se os dados tem coordenadas NUMERICAS
dados["latitude"] = pd.to_numeric(dados["latitude"], errors='coerce')
dados["longitude"] = pd.to_numeric(dados["longitude"], errors='coerce')


#Remove linhas com coordenadas vazias
dados = dados.dropna(subset=["latitude", "longitude"])
print("Coordenadas refinadas")


#Confere as linhas com coordenadas numericas
print(dados[["latitude", "longitude"]].head(10))

