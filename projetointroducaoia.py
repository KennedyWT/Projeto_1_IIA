#Bibliotecas
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import numpy as np
import unicodedata
import re
import folium


#Def para normalização de texto
def normalizar(texto: str) -> str:
    if pd.isna(texto):
        return ""
    texto = str(texto).lower().strip()
    texto = unicodedata.normalize('NFKD', texto)
    texto = "".join([c for c in texto if not unicodedata.combining(c)])
    texto = re.sub(r"\s+", " ", texto)
    return texto

LISTA_PRODUTOS_35 = [
    "Alface", "Mandioca", "Tomate", "Repolho", "Batata", "Cebola", "Couve", "Chuchu",
    "Morango", "Pimentão", "Brócolis", "Abóbora", "Berinjela", "Beterraba", "Pepino",
    "Cenoura", "Quiabo", "Agrião", "Jiló", "Gengibre", "Abacate", "Goiaba", "Banana",
    "Limão", "Tangerina", "Maracujá", "Manga", "Lichia", "Uva", "Atemóia", "Cajamanga",
    "Graviola", "Coco", "Pitaia", "Mamão"]


LOCALIDADES_EMATER = [
    "alexandre gusmao", "brazlandia", "ceilandia", "gama", "jardim",
    "pad-df", "paranoa", "pipiripau", "planaltina", "sao sebastiao",
    "sobradinho", "tabatinga", "taquara", "vargem bonita" 
]

LOCALIDADES_EMATER = [normalizar(loc) for loc in LOCALIDADES_EMATER]


#1° Etapa: processar e ler os dados
print("1° Etapa: processando e leitura dos dados")
print("Importação OK!")
culturas = pd.read_excel("dataprod/culturas.xlsx")
localidades = pd.read_excel("dataprod/localidades.up.xlsx")
print("Leitura OK!")
print()
print(culturas.head(15))
print("culturas OK!")
print()
print(localidades.head(15))
print("localidades OK!")
print()

print("\n2° Etapa: preenchendo localidade nas culturas com ffill()")
culturas["Localidade / Cultura"] = culturas["Localidade / Cultura"].ffill()

culturas = culturas[~culturas["Localidade / Cultura"].str.contains("subtotal", case=False, na=False)]

print(culturas["Localidade / Cultura"].isna().sum())
#print(culturas[["Localidade / Cultura", "Localidade / Cultura (ffil)"]].head(20))

#3° Etapa: refinamento dos dados
print("2° Etapa: refinando os dados da cultura")

# remover linhas com valores vazios
culturas = culturas.dropna(subset=["Localidade / Cultura", "Área Plantada (hectares)", "Produção (toneladas)"])

#Aplicação da função normalizar
culturas["regiao_norm"] = culturas["Localidade / Cultura"].apply(normalizar)
localidades["regiao_norm"] = localidades["Região"].apply(normalizar)

# 4º Merge das coordenadas
dados = pd.merge(
    culturas,
    localidades[["regiao_norm", "latitude", "longitude"]],
    on="regiao_norm",
    how="left"
)

#Verificar e transforma os dados em coordenadas NUMERICAS
dados["latitude"] = pd.to_numeric(dados["latitude"], errors='coerce')
dados["longitude"] = pd.to_numeric(dados["longitude"], errors='coerce')

#Remove linhas com coordenadas vazias
dados = dados.dropna(subset=["latitude", "longitude"])
print("Coordenadas refinadas")
print()

#Confere as linhas com coordenadas numericas
print("Linhas com coordenadas númericas:\n")
print(dados[["Localidade / Cultura", "latitude", "longitude"]].head(10))
#--------------------------------------------------------------------------------
# Inicializa o geolocalizador
geolocator = Nominatim(user_agent="produtores_app")

# Coleta dados do usuário
usar_endereco = input("Você quer digitar um endereço? (s/n): ").strip().lower()

if usar_endereco == 's':
    endereco = input("Digite seu endereço: ")
    location = geolocator.geocode(endereco)

    if location:
        user_lat = location.latitude
        user_lon = location.longitude
        print(f"Coordenadas encontradas: ({user_lat}, {user_lon})")
    else:
        print("Endereço não encontrado. Tente novamente.")
        exit()
else:
    user_lat = float(input("Digite sua latitude: "))
    user_lon = float(input("Digite sua longitude: "))

# Preferências
preferencia = input("Qual tipo de produto você procura? (ex: frutas, orgânicos): ").lower()
dist_max = float(input("Qual a distância máxima em km?: "))

#------------------------------------------------------------------------------------------------

# Função para calcular distância entre o usuário e cada produtor
def calcular_distancia(row):
    return geodesic((user_lat, user_lon), (row["latitude"], row["longitude"])).km

# Aplica o cálculo de distância
dados["dist_km"] = dados.apply(calcular_distancia, axis=1)

# Adiciona avaliação simulada
dados["avaliacao"] = np.random.uniform(3.0, 5.0, size=len(dados))

# Filtra dados com base na distância e na preferência (em dois campos)
recomendados = dados[
    (dados["dist_km"] <= dist_max) &
    (
        dados["referencia"].str.lower().str.contains(preferencia, na=False) |
        dados["specialproductionmethods"].str.lower().str.contains(preferencia, na=False)
    )
].sort_values(by=["avaliacao", "dist_km"], ascending=[False, True])

# Mostra os resultados
if recomendados.empty:
    print("\nNenhum mercado encontrado com esses critérios.")
else:
    print("\nMercados recomendados:")
    print(recomendados[["referencia", "dist_km", "avaliacao"]].head(10))

#-------------------------------------------------------------------------------------------------


# Cria o mapa centralizado na localização do usuário
mapa = folium.Map(location=[user_lat, user_lon], zoom_start=12)

# Marcador do usuário
folium.Marker(
    location=[user_lat, user_lon],
    tooltip="Sua localização",
    icon=folium.Icon(color="blue", icon="user")
).add_to(mapa)

# Adiciona cada produtor recomendado no mapa
for _, row in recomendados.iterrows():
    folium.Marker(
        location=[row["latitude"], row["longitude"]],
        tooltip=row["referencia"],
        popup=f"{row['referencia']}<br>Distância: {row['dist_km']:.1f} km<br>Avaliação: {row['avaliacao']:.1f}",
        icon=folium.Icon(color="green", icon="leaf")
    ).add_to(mapa)

# Salva o mapa em um arquivo HTML
mapa.save("mapa_recomendacoes.html")
print("\nMapa salvo como 'mapa_recomendacoes.html'")
print(dados[["referencia", "specialproductionmethods"]].head(10))
