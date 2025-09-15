from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware # Importado para permitir requisições de diferentes origens

# Importações das funções de composição DXF e de interação com o Google Drive
from compose_dxf import compor_dxf_com_base as compor_dxf_com_base_18
from compose_dxf_32 import compor_dxf_com_base_32
# Agora importamos 'mover_arquivos_antigos' corretamente
from google_drive import upload_to_drive, listar_arquivos_existentes, baixar_arquivo_drive, arquivo_existe_drive, mover_arquivos_antigos

from datetime import datetime
from types import SimpleNamespace
import os

app = FastAPI()

# --- Configuração CORS ---
# Esta seção permite que o seu frontend (por exemplo, uma aplicação React)
# faça requisições para esta API, mesmo que estejam em domínios/portas diferentes.
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,          # Lista de origens permitidas
    allow_credentials=True,         # Permite o envio de cookies de credenciais
    allow_methods=["*"],            # Permite todos os métodos HTTP (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],            # Permite todos os cabeçalhos nas requisições
)
# --- Fim da Configuração CORS ---


class Entrada(BaseModel):
    """
    Define o modelo de dados para a entrada da requisição POST.
    - arquivos: Lista de nomes de arquivos DXF a serem compostos.
    - nome_arquivo: Nome base para o arquivo DXF de saída (opcional, será gerado se não fornecido).
    - maquina: Tipo de máquina ("18" ou "32") para determinar o número máximo de arquivos por plano.
    """
    arquivos: list[str]
    nome_arquivo: str = None
    maquina: str = "18"

@app.post("/compor")
def compor(entrada: Entrada):
    """
    Endpoint principal para compor arquivos DXF.
    Recebe uma lista de nomes de arquivos e os compõe em um ou mais planos DXF,
    baseado no tipo de máquina selecionado.
    Também gera e faz upload de imagens PNG correspondentes.
    """
    total = len(entrada.arquivos)
    if total == 0:
        # Retorna um erro HTTP 400 se nenhum arquivo for fornecido
        raise HTTPException(status_code=400, detail="Nenhum arquivo fornecido.")

    # --- VALIDAÇÃO DE EXISTÊNCIA DOS ARQUIVOS NO GOOGLE DRIVE ---
    # Verifica se todos os arquivos DXF listados na entrada existem na subpasta
    # "arquivos padronizados" do Google Drive.
    arquivos_faltando = []
    for nome in entrada.arquivos:
        if not arquivo_existe_drive(nome, subpasta="arquivos padronizados"):
            arquivos_faltando.append(nome)
    if arquivos_faltando:
        # Se houver arquivos faltando, retorna um erro HTTP 404 com a lista de arquivos não encontrados.
        raise HTTPException(
            status_code=404,
            detail=f"Os arquivos DXF abaixo NÃO foram encontrados no Google Drive:\n" + "\n".join(arquivos_faltando)
        )
    # --- FIM DA VALIDAÇÃO ---

    # Lista os arquivos já existentes no Google Drive para evitar sobrescrever nomes.
    existentes = listar_arquivos_existentes()
    nome_base = entrada.nome_arquivo  # O nome base para o arquivo de saída, ex: Plano de corte 13 16-06-2025.dxf

    # Define o número máximo de arquivos por plano e a função de composição baseada na máquina.
    if entrada.maquina == "32":
        max_por_plano = 32
        compor_fn = compor_dxf_com_base_32
    else:
        max_por_plano = 18
        compor_fn = compor_dxf_com_base_18

    planos = [] # Lista para armazenar os detalhes dos planos gerados
    # Calcula o número de planos necessários
    num_planos = (total + max_por_plano - 1) // max_por_plano

    for i in range(num_planos):
        # Seleciona o "pedaço" de arquivos para o plano atual
        chunk_names = entrada.arquivos[i*max_por_plano : (i+1)*max_por_plano]
        # Converte os nomes dos arquivos em objetos SimpleNamespace para a função de composição
        chunk_objs = [
            SimpleNamespace(nome=name, posicao=index + 1)
            for index, name in enumerate(chunk_names)
        ]

        # Define o nome de saída para o plano atual
        if i == 0:
            nome_saida = nome_base
        else:
            # Adiciona um sufixo numérico (ex: _02, _03) antes da extensão .dxf para planos subsequentes.
            nome_saida = nome_base.replace('.dxf', f'_{i+1:02d}.dxf')

        # Evita sobrescrever arquivos existentes no Google Drive, adicionando sufixos extras se necessário.
        nome_saida_livre = nome_saida
        contador_extra = 2
        while nome_saida_livre in existentes:
            # Tenta um novo nome com sufixo incremental se o nome já existir
            nome_saida_livre = nome_base.replace('.dxf', f'_{i+contador_extra:02d}.dxf')
            contador_extra += 1

        # Define o caminho temporário para salvar o arquivo DXF gerado localmente.
        path_saida = f"/tmp/{nome_saida_livre}"
        
        # Chama a função de composição DXF para gerar o arquivo.
        # Assume-se que `compor_fn` também chama `gerar_imagem_plano` internamente,
        # que por sua vez já faz o upload do PNG para o Google Drive.
        compor_fn(chunk_objs, path_saida)

        # Upload do arquivo DXF gerado para o Google Drive.
        url_dxf = upload_to_drive(path_saida, nome_saida_livre)
        
        # O nome do PNG será o mesmo do DXF, mas com extensão .png.
        nome_png = nome_saida_livre.replace('.dxf', '.png')
        
        # --- Lógica para o URL do PNG ---
        # ATENÇÃO: A forma mais robusta seria ter a função `compor_fn` (ou `gerar_imagem_plano`
        # dentro dela) retornando o URL real do PNG após o upload.
        # Por enquanto, estamos simulando o URL do PNG com base no URL do DXF.
        # Você precisará ajustar suas funções `compose_dxf.py` e `compose_dxf_32.py`
        # para que `gerar_imagem_plano` retorne o URL do PNG e este seja propagado até aqui.
        url_png_simulado = url_dxf.replace('.dxf', '.png').replace('/view', '') # Simulação: remove '/view' para um URL mais "direto"

        # Adiciona os detalhes do plano (nome, URL do DXF e URL simulado do PNG) à lista de planos.
        # O Apps Script espera a chave 'url', então estamos usando 'url_dxf' para isso.
        planos.append({"nome": nome_saida_livre, "url": url_dxf, "url_png": url_png_simulado})

    # Retorna a lista de planos gerados como resposta da API.
    return {"plans": planos}

@app.post("/mover-antigos")
def mover_antigos():
    """
    Endpoint para mover arquivos DXF antigos para uma subpasta de "arquivos antigos".
    Esta função agora chama a lógica implementada em google_drive.py.
    """
    try:
        moved_count = mover_arquivos_antigos() # Chama a função do google_drive.py
        return {"moved": moved_count}
    except Exception as e:
        print(f"Erro ao mover arquivos: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao mover arquivos: {e}")
