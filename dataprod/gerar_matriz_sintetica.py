# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import random

print("Iniciando geração da matriz sintética...")

# 1. Carregar dados base

try:
    estabelecimentos_df = pd.read_csv("mercados_lojas_brasilia.csv")
    lista_estabelecimentos = estabelecimentos_df["nome"].unique().tolist()
    print(f"{len(lista_estabelecimentos)} estabelecimentos carregados.")
except FileNotFoundError:
    print("Erro: Arquivo dataprod/mercados_lojas_brasilia.csv não encontrado.")
    exit()
except Exception as e:
    print(f"Erro ao carregar estabelecimentos: {e}")
    exit()

# Lista de produtos base (do código original)
lista_produtos_base = [
    "Alface", "Mandioca", "Tomate", "Repolho", "Batata", "Cebola", "Couve", "Chuchu", "Morango", "Pimentão",
    "Brócolis", "Abóbora", "Berinjela", "Beterraba", "Pepino", "Cenoura", "Quiabo", "Agrião", "Jiló", "Gengibre",
    "Abacate", "Goiaba", "Banana", "Limão", "Tangerina", "Maracujá", "Manga", "Lichia", "Uva", "Atemóia", "Cajamanga",
    "Graviola", "Coco", "Pitaia", "Mamão"
]
print(f"{len(lista_produtos_base)} produtos base definidos.")

# 2. Simular disponibilidade de produtos por estabelecimento

produtos_por_estabelecimento = {}
for est in lista_estabelecimentos:
    num_produtos = random.randint(15, 30) # Cada estabelecimento tem entre 15 e 30 produtos
    produtos_por_estabelecimento[est] = random.sample(lista_produtos_base, num_produtos)

print("Disponibilidade de produtos por estabelecimento simulada.")

# 3. Definir parâmetros da simulação

num_usuarios = 200
min_ratings_por_usuario = 25
max_ratings_por_usuario = 60
num_linhas_minimo = 5000

# Calcular número médio de ratings para garantir o mínimo
num_ratings_medio = (min_ratings_por_usuario + max_ratings_por_usuario) / 2
num_linhas_estimado = num_usuarios * num_ratings_medio

if num_linhas_estimado < num_linhas_minimo:
    # Ajustar número de usuários se a estimativa for baixa
    num_usuarios = int(np.ceil(num_linhas_minimo / num_ratings_medio)) + 1
    print(f"Ajustando número de usuários para {num_usuarios} para garantir >{num_linhas_minimo} linhas.")

# 4. Gerar dados sintéticos (ratings)

dados_sinteticos = []
linhas_geradas = 0

for user_id in range(1, num_usuarios + 1):
    num_ratings_usuario = random.randint(min_ratings_por_usuario, max_ratings_por_usuario)
    
    # Simular preferências do usuário (exemplo simples)
    prefere_frutas = random.random() < 0.5
    nota_base_usuario = random.uniform(2.5, 4.5) # Tendência geral de notas do usuário
    
    estabelecimentos_visitados = random.sample(lista_estabelecimentos, k=min(len(lista_estabelecimentos), num_ratings_usuario // 2 + 5)) # Usuário visita um subconjunto

    for _ in range(num_ratings_usuario):
        # Escolher estabelecimento
        estabelecimento_escolhido = random.choice(estabelecimentos_visitados)
        
        # Escolher produto disponível
        produtos_disponiveis = produtos_por_estabelecimento[estabelecimento_escolhido]
        if not produtos_disponiveis:
            continue # Pula se o estabelecimento não tiver produtos (improvável)
        produto_escolhido = random.choice(produtos_disponiveis)
        
        # Gerar nota (exemplo simples)
        nota = nota_base_usuario
        # Ajuste baseado na preferência (ex: nota maior se for fruta e usuário prefere frutas)
        if prefere_frutas and produto_escolhido in ["Morango", "Abacate", "Goiaba", "Banana", "Limão", "Tangerina", "Maracujá", "Manga", "Lichia", "Uva", "Atemóia", "Cajamanga", "Graviola", "Coco", "Pitaia", "Mamão"]:
            nota += random.uniform(0, 0.8)
        elif not prefere_frutas and produto_escolhido not in ["Morango", "Abacate", "Goiaba", "Banana", "Limão", "Tangerina", "Maracujá", "Manga", "Lichia", "Uva", "Atemóia", "Cajamanga", "Graviola", "Coco", "Pitaia", "Mamão"]:
             nota += random.uniform(0, 0.5)
        else:
             nota -= random.uniform(0, 0.3)

        # Adicionar ruído
        nota += random.gauss(0, 0.5) 
        
        # Limitar nota entre 1 e 5 e arredondar para inteiro
        nota_final = max(1, min(5, round(nota)))
        
        dados_sinteticos.append({
            "user_id": user_id,
            "establishment_id": estabelecimento_escolhido,
            "product_name": produto_escolhido,
            "rating": nota_final
        })
        linhas_geradas += 1

print(f"{linhas_geradas} linhas de ratings geradas.")

# 5. Criar DataFrame e salvar

ratings_df = pd.DataFrame(dados_sinteticos)

# Garantir que temos pelo menos 5000 linhas (caso a geração aleatória tenha ficado abaixo)
while len(ratings_df) < num_linhas_minimo:
    print(f"Ainda faltam {num_linhas_minimo - len(ratings_df)} linhas. Gerando mais algumas...")
    user_id = random.randint(1, num_usuarios)
    estabelecimento_escolhido = random.choice(lista_estabelecimentos)
    produtos_disponiveis = produtos_por_estabelecimento[estabelecimento_escolhido]
    if not produtos_disponiveis:
        continue
    produto_escolhido = random.choice(produtos_disponiveis)
    nota_final = random.randint(1, 5)
    ratings_df = pd.concat([ratings_df, pd.DataFrame([{
            "user_id": user_id,
            "establishment_id": estabelecimento_escolhido,
            "product_name": produto_escolhido,
            "rating": nota_final
        }])], ignore_index=True)

# Embaralhar o resultado final
ratings_df = ratings_df.sample(frac=1).reset_index(drop=True)
output_path = "synthetic_ratings.csv"
try:
    ratings_df.to_csv(output_path, index=False)
    print(f"Matriz sintética com {len(ratings_df)} linhas salva em: {output_path}")
except Exception as e:
    print(f"Erro ao salvar o arquivo CSV: {e}")

print("\nExemplo dos dados gerados:")
print(ratings_df.head())

