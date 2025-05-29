# -*- coding: utf-8 -*-
# Bibliotecas
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import numpy as np
import unicodedata
import re
import folium
import random
import time

# Def para normalização de texto
def normalizar(texto: str) -> str:
    if pd.isna(texto):
        return ""
    texto = str(texto).lower().strip()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join([c for c in texto if not unicodedata.combining(c)])
    texto = re.sub(r"\s+", " ", texto)
    return texto

# Função robusta para geocodificação com tentativas e tratamento de erros
def geocode_endereco(geolocator, endereco, tentativas=3, pausa=1):
    location = None
    for tentativa in range(tentativas):
        try:
            location = geolocator.geocode(endereco, timeout=10)
            if location:
                return location # Sucesso
            print(f"Tentativa {tentativa + 1}: Endereço \"{endereco}\" não encontrado.")
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            print(f"Tentativa {tentativa + 1}: Erro no serviço de geocodificação ({e}). Tentando novamente em {pausa}s...")
            time.sleep(pausa)
        except Exception as e:
            print(f"Tentativa {tentativa + 1}: Erro inesperado durante a geocodificação: {e}")
            break # Sai se for um erro diferente
    return None # Falhou após todas as tentativas

# --- Início da Adaptação ---

print("1° Etapa: Lendo tabelas de estabelecimentos e ratings sintéticos")

# Carregar estabelecimentos
try:
    caminho_estabelecimentos = "dataprod\mercados_lojas_brasilia.csv"
    estabelecimentos_df = pd.read_csv(caminho_estabelecimentos)
    print(f"Leitura OK! {len(estabelecimentos_df)} estabelecimentos carregados.")

    # Extrair localidades únicas para usar como palavras-chave no geocoding
    localidades_conhecidas = [normalizar(loc) for loc in estabelecimentos_df["localidade"].unique() if pd.notna(loc)]
    localidades_conhecidas.extend(["asa norte", "asa sul", "lago norte", "lago sul", "sudoeste", "noroeste", "guara", "taguatinga", "ceilandia", "samambaia", "recanto das emas", "gama", "santa maria", "sao sebastiao", "jardim botanico", "paranoa", "itapoa", "sobradinho", "planaltina", "brazlandia", "vicente pires", "aguas claras", "nucleo bandeirante", "candangolandia", "park way", "scia", "sia"])
    localidades_conhecidas = sorted(list(set(localidades_conhecidas)), key=len, reverse=True)

    # Verificar e limpar coordenadas dos estabelecimentos
    if "latitude" not in estabelecimentos_df.columns or "longitude" not in estabelecimentos_df.columns:
        print("Erro: Colunas 'latitude' ou 'longitude' não encontradas no CSV de estabelecimentos.")
        exit()
    estabelecimentos_df["latitude"] = pd.to_numeric(estabelecimentos_df["latitude"], errors="coerce")
    estabelecimentos_df["longitude"] = pd.to_numeric(estabelecimentos_df["longitude"], errors="coerce")
    estabelecimentos_df.dropna(subset=["latitude", "longitude"], inplace=True)
    print(f"{len(estabelecimentos_df)} estabelecimentos com coordenadas válidas.")

except FileNotFoundError:
    print(f"Erro: Arquivo {caminho_estabelecimentos} não encontrado.")
    exit()
except Exception as e:
    print(f"Erro ao ler ou processar o arquivo de estabelecimentos: {e}")
    exit()

# Carregar ratings sintéticos
try:
    caminho_ratings = "dataprod/synthetic_ratings.csv"
    ratings_df = pd.read_csv(caminho_ratings)
    print(f"Leitura OK! {len(ratings_df)} ratings sintéticos carregados.")
    # Normalizar nomes para facilitar junção/comparação
    ratings_df["establishment_id"] = ratings_df["establishment_id"].apply(normalizar)
    ratings_df["product_name"] = ratings_df["product_name"].apply(normalizar)
    estabelecimentos_df["nome_normalizado"] = estabelecimentos_df["nome"].apply(normalizar)

except FileNotFoundError:
    print(f"Erro: Arquivo {caminho_ratings} não encontrado. Execute gerar_matriz_sintetica.py primeiro.")
    exit()
except Exception as e:
    print(f"Erro ao ler ou processar o arquivo de ratings: {e}")
    exit()

# --- Fim da Leitura de Dados ---

print("\n2° Etapa: Coletar localização e preferências do usuário")
geolocator = Nominatim(user_agent="recomendacao_brasilia_matriz_v1")
user_lat, user_lon = None, None

while user_lat is None:
    usar_endereco = input("Você quer digitar um endereço (ex: SQN 101 Bloco A, Asa Norte) ou usar coordenadas? (endereco/coords): ").strip().lower()

    if "endereco".startswith(usar_endereco):
        endereco_usuario = input("Digite seu endereço completo em Brasília: ")
        endereco_normalizado = normalizar(endereco_usuario)

        print(f"Tentando geocodificar: \"{endereco_usuario}, Brasília, DF\"...")
        location = geocode_endereco(geolocator, f"{endereco_usuario}, Brasília, DF")

        if location:
            user_lat = location.latitude
            user_lon = location.longitude
            print(f"Coordenadas encontradas: ({user_lat:.6f}, {user_lon:.6f})")
        else:
            print("Não foi possível encontrar o endereço exato. Tentando identificar a região...")
            regiao_encontrada = None
            for loc in localidades_conhecidas:
                if loc in endereco_normalizado:
                    regiao_encontrada = loc
                    print(f"Região identificada: \"{regiao_encontrada.title()}\"")
                    break

            if regiao_encontrada:
                endereco_regiao = f"{regiao_encontrada}, Brasília, DF"
                print(f"Tentando geocodificar pela região: \"{endereco_regiao}\"...")
                location_regiao = geocode_endereco(geolocator, endereco_regiao)
                if location_regiao:
                    user_lat = location_regiao.latitude
                    user_lon = location_regiao.longitude
                    print(f"Usando coordenadas aproximadas da região \"{regiao_encontrada.title()}\": ({user_lat:.6f}, {user_lon:.6f})")
                    print("Aviso: A localização é aproximada para a região informada.")
                else:
                    print(f"Não foi possível encontrar coordenadas nem para a região \"{regiao_encontrada.title()}\".")
            else:
                print("Nenhuma região conhecida foi identificada no endereço.")

            if user_lat is None:
                print("Falha ao obter coordenadas pelo endereço. Por favor, tente fornecer as coordenadas diretamente ou um endereço mais claro.")

    elif "coords".startswith(usar_endereco):
        try:
            user_lat_str = input("Digite sua latitude (ex: -15.78): ")
            user_lon_str = input("Digite sua longitude (ex: -47.92): ")
            user_lat = float(user_lat_str.replace(",", "."))
            user_lon = float(user_lon_str.replace(",", "."))
            print(f"Usando coordenadas: ({user_lat:.6f}, {user_lon:.6f})")
        except ValueError:
            print("Entrada inválida. Latitude e longitude devem ser números. Tente novamente.")
    else:
        print("Opção inválida. Por favor, digite \"endereco\" ou \"coords\".")

# Preferências de Produto
produtos_desejados_str = input("\nDigite os produtos que você procura, separados por vírgula (ex: Tomate, Alface): ").strip()
produtos_desejados = [normalizar(p) for p in produtos_desejados_str.split(",") if p.strip()]

if not produtos_desejados:
    print("Nenhum produto especificado. Saindo.")
    exit()

print(f"Procurando por: {produtos_desejados}")

dist_max_str = input("\nQual a distância máxima em km que você aceita? (ex: 5): ")
try:
    dist_max = float(dist_max_str.replace(",", "."))
except ValueError:
    print("Distância inválida. Usando padrão de 5 km.")
    dist_max = 5.0

print("\n3° Etapa: Calculando distâncias")
def calcular_distancia(row):
    try:
        if pd.notna(row["latitude"]) and pd.notna(row["longitude"]):
             return geodesic((user_lat, user_lon), (row["latitude"], row["longitude"])).km
        else:
             return np.inf
    except ValueError:
        return np.inf

estabelecimentos_df["dist_km"] = estabelecimentos_df.apply(calcular_distancia, axis=1)

print("\n4° Etapa: Filtrando e recomendando com base em produtos e notas")

# Filtrar estabelecimentos por distância
estabelecimentos_proximos = estabelecimentos_df[estabelecimentos_df["dist_km"] <= dist_max].copy()

if estabelecimentos_proximos.empty:
    print(f"Nenhum estabelecimento encontrado dentro de {dist_max} km.")
    exit()

print(f"{len(estabelecimentos_proximos)} estabelecimentos encontrados dentro de {dist_max} km. Verificando notas...")

# Filtrar ratings para os produtos desejados e estabelecimentos próximos
estab_proximos_norm = estabelecimentos_proximos["nome_normalizado"].tolist()
ratings_filtrados = ratings_df[
    (ratings_df["establishment_id"].isin(estab_proximos_norm)) &
    (ratings_df["product_name"].isin(produtos_desejados))
].copy()

if ratings_filtrados.empty:
    print(f"Nenhum rating encontrado para os produtos {produtos_desejados} nos estabelecimentos próximos.")
    exit()

# Calcular nota média por estabelecimento para os produtos desejados
notas_medias = ratings_filtrados.groupby("establishment_id")["rating"].agg(["mean", "count"])
notas_medias.rename(columns={"mean": "nota_media_produto", "count": "num_avaliacoes_produto"}, inplace=True)

# Juntar notas médias com os dados dos estabelecimentos próximos
recomendados = estabelecimentos_proximos.merge(
    notas_medias,
    left_on="nome_normalizado",
    right_index=True,
    how="inner" # Apenas estabelecimentos com notas para os produtos desejados
)

if recomendados.empty:
    print(f"Nenhum estabelecimento próximo possui avaliações para os produtos: {produtos_desejados}")
    exit()

# Ordenar por nota média (descendente) e distância (ascendente)
recomendados.sort_values(by=["nota_media_produto", "dist_km"], ascending=[False, True], inplace=True)

print(f"\nEstabelecimentos recomendados para {produtos_desejados} (até {dist_max} km):")
colunas_exibir = ["nome", "tipo", "endereco", "dist_km", "nota_media_produto", "num_avaliacoes_produto"]
print(recomendados[colunas_exibir].head(10).to_string(index=False))

print("\n5° Etapa: Gerando mapa")
mapa = folium.Map(location=[user_lat, user_lon], zoom_start=13)

folium.Marker(
    location=[user_lat, user_lon],
    tooltip="Sua Localização (Pode ser aproximada)",
    popup="Você está aqui",
    icon=folium.Icon(color="blue", icon="user")
).add_to(mapa)

for _, row in recomendados.head(20).iterrows():
    if pd.notna(row["latitude"]) and pd.notna(row["longitude"]):
        cor_icone = "green"
        icone_tipo = "shopping-cart"
        tipo_norm = normalizar(row["tipo"])
        if "feira" in tipo_norm:
            cor_icone = "orange"
            icone_tipo = "leaf"
        elif "supermercado" in tipo_norm:
            cor_icone = "red"
        elif "associação" in tipo_norm or "cooperativa" in tipo_norm:
            cor_icone = "darkgreen"
            icone_tipo = "home"

        popup_html = (
            f'<b>{row["nome"]}</b><br>'
            f'Tipo: {row["tipo"]}<br>'
            f'Endereço: {row["endereco"]}<br>'
            f'Distância: {row["dist_km"]:.1f} km<br>'
            f'Nota Média ({", ".join(produtos_desejados)}): {row["nota_media_produto"]:.1f}/5<br>'           f'({row["num_avaliacoes_produto"]} avaliações)'
        )

        folium.Marker(
            location=[row["latitude"], row["longitude"]],
            tooltip=f'{row["nome"]} ({row["tipo"]}) - Nota Média: {row["nota_media_produto"]:.1f}/5',
            popup=popup_html,
            icon=folium.Icon(color=cor_icone, icon=icone_tipo, prefix="fa")
        ).add_to(mapa)

mapa_path = "mapa_recomendacoes_matriz.html"
mapa.save(mapa_path)
print(f"\nMapa salvo como \"{mapa_path}\"")
print("Abra este arquivo em um navegador para ver o mapa interativo.")

# --- Fim da Adaptação ---

