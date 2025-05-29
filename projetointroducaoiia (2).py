#Bibliotecas
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import numpy as np
import unicodedata
import re
import folium
import random
import time # Para adicionar pausa entre tentativas de geocodificação

# Def para normalização de texto
def normalizar(texto: str) -> str:
    if pd.isna(texto):
        return ""
    texto = str(texto).lower().strip()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join([c for c in texto if not unicodedata.combining(c)])
    texto = re.sub(r"\s+", " ", texto)
    return texto

# Lista de produtos conforme especificações
lista_produtos_base = [
    "Alface", "Mandioca", "Tomate", "Repolho", "Batata", "Cebola", "Couve", "Chuchu", "Morango", "Pimentão",
    "Brócolis", "Abóbora", "Berinjela", "Beterraba", "Pepino", "Cenoura", "Quiabo", "Agrião", "Jiló", "Gengibre",
    "Abacate", "Goiaba", "Banana", "Limão", "Tangerina", "Maracujá", "Manga", "Lichia", "Uva", "Atemóia", "Cajamanga",
    "Graviola", "Coco", "Pitaia", "Mamão"
]

# Categorias (exemplo)
produtos_frutas = ["Morango", "Abacate", "Goiaba", "Banana", "Limão", "Tangerina", "Maracujá", "Manga", "Lichia", "Uva", "Atemóia", "Cajamanga", "Graviola", "Coco", "Pitaia", "Mamão"]
produtos_olericolas = [p for p in lista_produtos_base if p not in produtos_frutas]

# Função para simular produtos, status orgânico e avaliação para cada estabelecimento
def simular_dados_loja(num_produtos_max=15):
    num_produtos = random.randint(5, num_produtos_max)
    produtos_disponiveis = random.sample(lista_produtos_base, num_produtos)
    tem_organicos = random.random() < 0.3
    avaliacao = random.randint(1, 5) # Simula avaliação de 1 a 5 estrelas
    return {
        "produtos": ", ".join(produtos_disponiveis),
        "organicos": tem_organicos,
        "avaliacao": avaliacao
    }

# Função robusta para geocodificação com tentativas e tratamento de erros
def geocode_endereco(geolocator, endereco, tentativas=3, pausa=1):
    location = None
    for tentativa in range(tentativas):
        try:
            location = geolocator.geocode(endereco, timeout=10)
            if location:
                return location # Sucesso
            print(f"Tentativa {tentativa + 1}: Endereço '{endereco}' não encontrado.")
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            print(f"Tentativa {tentativa + 1}: Erro no serviço de geocodificação ({e}). Tentando novamente em {pausa}s...")
            time.sleep(pausa)
        except Exception as e:
            print(f"Tentativa {tentativa + 1}: Erro inesperado durante a geocodificação: {e}")
            break # Sai se for um erro diferente
    return None # Falhou após todas as tentativas

# 1° Etapa: Ler a tabela de estabelecimentos
print("1° Etapa: Lendo a tabela de estabelecimentos de Brasília")
try:
    caminho_csv = "dataprod/mercados_lojas_brasilia.csv"
    dados = pd.read_csv(caminho_csv)
    print(f"Leitura OK! {len(dados)} estabelecimentos carregados.")

    # Extrair localidades únicas para usar como palavras-chave
    localidades_conhecidas = [normalizar(loc) for loc in dados['localidade'].unique() if pd.notna(loc)]
    # Adicionar algumas regiões administrativas comuns que podem não estar na coluna 'localidade'
    localidades_conhecidas.extend(["asa norte", "asa sul", "lago norte", "lago sul", "sudoeste", "noroeste", "guara", "taguatinga", "ceilandia", "samambaia", "recanto das emas", "gama", "santa maria", "sao sebastiao", "jardim botanico", "paranoa", "itapoa", "sobradinho", "planaltina", "brazlandia", "vicente pires", "aguas claras", "nucleo bandeirante", "candangolandia", "park way", "scia", "sia"])
    localidades_conhecidas = sorted(list(set(localidades_conhecidas)), key=len, reverse=True) # Ordena por comprimento para pegar nomes mais específicos primeiro

    # Verificar e limpar coordenadas
    if "latitude" not in dados.columns or "longitude" not in dados.columns:
        print("Erro: Colunas 'latitude' ou 'longitude' não encontradas no CSV.")
        exit()
    dados["latitude"] = pd.to_numeric(dados["latitude"], errors="coerce")
    dados["longitude"] = pd.to_numeric(dados["longitude"], errors="coerce")
    dados.dropna(subset=["latitude", "longitude"], inplace=True)
    print(f"{len(dados)} estabelecimentos com coordenadas válidas.")

    # Simular produtos, status orgânico e avaliação para cada linha
    simulacao = dados.apply(lambda row: simular_dados_loja(), axis=1, result_type='expand')
    dados = pd.concat([dados, simulacao], axis=1)
    print("Dados de produtos, status orgânico e avaliação simulados.")

except FileNotFoundError:
    print(f"Erro: Arquivo '{caminho_csv}' não encontrado.")
    exit()
except Exception as e:
    print(f"Erro ao ler ou processar o arquivo CSV: {e}")
    exit()

print("\n2° Etapa: Coletar localização e preferências do usuário")
geolocator = Nominatim(user_agent="recomendacao_brasilia_app_v2") # User agent diferente
user_lat, user_lon = None, None

while user_lat is None:
    usar_endereco = input("Você quer digitar um endereço (ex: SQN 101 Bloco A, Asa Norte) ou usar coordenadas? (endereco/coords): ").strip().lower()

    if "endereco".startswith(usar_endereco):
        endereco_usuario = input("Digite seu endereço completo em Brasília: ")
        endereco_normalizado = normalizar(endereco_usuario)

        # Tentativa 1: Endereço completo + Brasília, DF
        print(f"Tentando geocodificar: '{endereco_usuario}, Brasília, DF'...")
        location = geocode_endereco(geolocator, f"{endereco_usuario}, Brasília, DF")

        if location:
            user_lat = location.latitude
            user_lon = location.longitude
            print(f"Coordenadas encontradas (Tentativa 1): ({user_lat:.6f}, {user_lon:.6f})")
        else:
            print("Não foi possível encontrar o endereço exato. Tentando identificar a região...")
            regiao_encontrada = None
            for loc in localidades_conhecidas:
                if loc in endereco_normalizado:
                    regiao_encontrada = loc
                    print(f"Região identificada: '{regiao_encontrada.title()}'")
                    break

            if regiao_encontrada:
                # Tentativa 2: Usar apenas a região identificada
                endereco_regiao = f"{regiao_encontrada}, Brasília, DF"
                print(f"Tentando geocodificar pela região: '{endereco_regiao}'...")
                location_regiao = geocode_endereco(geolocator, endereco_regiao)
                if location_regiao:
                    user_lat = location_regiao.latitude
                    user_lon = location_regiao.longitude
                    print(f"Usando coordenadas aproximadas da região '{regiao_encontrada.title()}': ({user_lat:.6f}, {user_lon:.6f})")
                    print("Aviso: A localização é aproximada para a região informada.")
                else:
                    print(f"Não foi possível encontrar coordenadas nem para a região '{regiao_encontrada.title()}'.")
            else:
                print("Nenhuma região conhecida foi identificada no endereço.")

            if user_lat is None:
                print("Falha ao obter coordenadas pelo endereço. Por favor, tente fornecer as coordenadas diretamente ou um endereço mais claro.")
                # Volta para o início do loop para pedir novamente

    elif "coords".startswith(usar_endereco):
        try:
            user_lat_str = input("Digite sua latitude (ex: -15.78): ")
            user_lon_str = input("Digite sua longitude (ex: -47.92): ")
            user_lat = float(user_lat_str.replace(',', '.')) # Aceita vírgula como separador decimal
            user_lon = float(user_lon_str.replace(',', '.'))
            print(f"Usando coordenadas: ({user_lat:.6f}, {user_lon:.6f})")
        except ValueError:
            print("Entrada inválida. Latitude e longitude devem ser números. Tente novamente.")
            # user_lat continua None, volta para o início do loop
    else:
        print("Opção inválida. Por favor, digite 'endereco' ou 'coords'.")
        # Volta para o início do loop


print("\nPreferências de Produtos:")
pref_organicos = input("Prefere produtos orgânicos? (s/n/tanto faz): ").strip().lower()
pref_tipo_produto = input(f"Prefere algum tipo específico? (frutas/olericolas/deixe em branco): ").strip().lower()
pref_produto_especifico = input(f"Procura algum produto específico? Digite o nome (ex: Tomate) ou deixe em branco: ").strip()

dist_max_str = input("\nQual a distância máxima em km que você aceita? (ex: 5): ")
try:
    dist_max = float(dist_max_str.replace(',', '.'))
except ValueError:
    print("Distância inválida. Usando padrão de 5 km.")
    dist_max = 5.0

print("\n3° Etapa: Calculando distâncias")
def calcular_distancia(row):
    try:
        # Verifica se as coordenadas são válidas antes de calcular
        if pd.notna(row["latitude"]) and pd.notna(row["longitude"]):
             return geodesic((user_lat, user_lon), (row["latitude"], row["longitude"])).km
        else:
             return np.inf
    except ValueError:
        return np.inf

dados["dist_km"] = dados.apply(calcular_distancia, axis=1)

print("\n4° Etapa: Filtrando e recomendando")
recomendados = dados[dados["dist_km"] <= dist_max].copy()

if pref_organicos == 's':
    recomendados = recomendados[recomendados["organicos"] == True]
elif pref_organicos == 'n':
    recomendados = recomendados[recomendados["organicos"] == False]

if 'produtos' in recomendados.columns:
    if pref_tipo_produto == 'frutas':
        recomendados = recomendados[recomendados['produtos'].apply(lambda p: isinstance(p, str) and any(f in p for f in produtos_frutas))]
    elif pref_tipo_produto == 'olericolas':
        recomendados = recomendados[recomendados['produtos'].apply(lambda p: isinstance(p, str) and any(o in p for o in produtos_olericolas))]

else:
    print("Aviso: Coluna 'produtos' não encontrada para filtragem.")

if pref_produto_especifico and 'produtos' in recomendados.columns:
    produto_normalizado = normalizar(pref_produto_especifico)
    #print(recomendados.columns)
    recomendados = recomendados[recomendados['produtos'].apply(lambda p_str: isinstance(p_str, str) and produto_normalizado in normalizar(p_str))]



recomendados.sort_values(by=["dist_km", "avaliacao"], ascending=[True, False], inplace=True)

if recomendados.empty:
    print(f"\nNenhum estabelecimento encontrado com seus critérios dentro de {dist_max} km.")
else:
    print(f"\nEstabelecimentos recomendados (até {dist_max} km):")
    colunas_exibir = ["nome", "tipo", "endereco", "dist_km", "avaliacao"]
    if 'organicos' in recomendados.columns:
        colunas_exibir.append("organicos")
    # Verifica se a coluna 'produtos' existe antes de criar 'produtos_preview'
    if 'produtos' in recomendados.columns:
        recomendados['produtos_preview'] = recomendados['produtos'].apply(
            lambda x: ', '.join(x.split(',')[:5]) + ('...' if isinstance(x, str) and len(x.split(',')) > 5 else '') if isinstance(x, str) else ''
        )
        colunas_exibir.append("produtos_preview")
    else:
        print("Aviso: Coluna 'produtos' não encontrada para exibição.")

    # Garante que apenas colunas existentes sejam selecionadas
    colunas_exibir_validas = [col for col in colunas_exibir if col in recomendados.columns]
    print(recomendados[colunas_exibir_validas].head(10).to_string(index=False))

print("\n5° Etapa: Gerando mapa")
# Centraliza o mapa mesmo que as coordenadas sejam aproximadas
mapa = folium.Map(location=[user_lat, user_lon], zoom_start=13)

folium.Marker(
    location=[user_lat, user_lon],
    tooltip="Sua Localização (Pode ser aproximada)",
    popup="Você está aqui",
    icon=folium.Icon(color="blue", icon="user")
).add_to(mapa)

for _, row in recomendados.head(20).iterrows():
    # Verifica se as coordenadas da linha são válidas
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

        popup_html = f"<b>{row['nome']}</b><br>Tipo: {row['tipo']}<br>Endereço: {row['endereco']}<br>Distância: {row['dist_km']:.1f} km<br>Avaliação: {row['avaliacao']}/5"
        if 'organicos' in row and row['organicos']:
            popup_html += "<br><i>Oferece Orgânicos</i>"
        if 'produtos' in row and isinstance(row['produtos'], str):
             popup_html += f"<br>Produtos (amostra): {', '.join(row['produtos'].split(',')[:3])}..."

        folium.Marker(
            location=[row["latitude"], row["longitude"]],
            tooltip=f"{row['nome']} ({row['tipo']}) - Avaliação: {row['avaliacao']}/5",
            popup=popup_html,
            icon=folium.Icon(color=cor_icone, icon=icone_tipo, prefix='fa')
        ).add_to(mapa)

mapa_path = "mapa_recomendacoes_brasilia.html"
mapa.save(mapa_path)
print(f"\nMapa salvo como '{mapa_path}'")
print("Abra este arquivo em um navegador para ver o mapa interativo.")

