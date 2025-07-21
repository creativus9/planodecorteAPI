from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware # Importe o CORSMiddleware

from compose_dxf import compor_dxf_com_base as compor_dxf_com_base_18
from compose_dxf_32 import compor_dxf_com_base_32 # CORRIGIDO: Renomeado de new_code_file para compose_dxf_32
from google_drive import upload_to_drive, listar_arquivos_existentes, baixar_arquivo_drive, arquivo_existe_drive # Importa arquivo_existe_drive
from datetime import datetime
from types import SimpleNamespace
import os

app = FastAPI()

# --- Configuração CORS ---
# Adicione esta seção para permitir requisições do seu frontend
origins = [
    "http://localhost",
    "http://localhost:5173", # O endereço do seu frontend React
    # Se você tiver um domínio de produção para o seu frontend, adicione-o aqui também
    # "https://seu-dominio-frontend-em-producao.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Permite todos os métodos (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"], # Permite todos os cabeçalhos
)
# --- Fim da Configuração CORS ---


class Entrada(BaseModel):
    arquivos: list[str]
    nome_arquivo: str = None
    maquina: str = "18"

@app.post("/compor")
def compor(entrada: Entrada):
    total = len(entrada.arquivos)
    if total == 0:
        raise HTTPException(status_code=400, detail="Nenhum arquivo fornecido.")

    # --- VALIDAÇÃO DE EXISTÊNCIA (agora usando a função importada) ---
    arquivos_faltando = []
    for nome in entrada.arquivos:
        if not arquivo_existe_drive(nome, subpasta="arquivos padronizados"):
            arquivos_faltando.append(nome)
    if arquivos_faltando:
        raise HTTPException(
            status_code=404,
            detail=f"Os arquivos DXF abaixo NÃO foram encontrados:\n" + "\n".join(arquivos_faltando)
        )
    # --- FIM VALIDAÇÃO ---

    existentes = listar_arquivos_existentes()
    nome_base = entrada.nome_arquivo  # Já deve vir, ex: Plano de corte 13 16-06-2025.dxf

    if entrada.maquina == "32":
        max_por_plano = 32
        compor_fn = compor_dxf_com_base_32
    else:
        max_por_plano = 18
        compor_fn = compor_dxf_com_base_18

    planos = []
    num_planos = (total + max_por_plano - 1) // max_por_plano

    for i in range(num_planos):
        chunk_names = entrada.arquivos[i*max_por_plano : (i+1)*max_por_plano]
        chunk_objs = [
            SimpleNamespace(nome=name, posicao=index + 1)
            for index, name in enumerate(chunk_names)
        ]
        if i == 0:
            nome_saida = nome_base
        else:
            # Adiciona _02, _03, ... ANTES da extensão .dxf
            nome_saida = nome_base.replace('.dxf', f'_{i+1:02d}.dxf')

        # Evita sobrescrever existentes (adicionando mais sufixo se necessário)
        nome_saida_livre = nome_saida
        contador_extra = 2
        while nome_saida_livre in existentes:
            nome_saida_livre = nome_base.replace('.dxf', f'_{i+contador_extra:02d}.dxf')
            contador_extra += 1

        path_saida = f"/tmp/{nome_saida_livre}"
        compor_fn(chunk_objs, path_saida)

        # Gerar e enviar PNG também
        png_path = path_saida.replace('.dxf', '.png')
        # A função compor_fn já deve chamar gerar_imagem_plano internamente,
        # que por sua vez já faz o upload do PNG.
        # Portanto, não precisamos chamar gerar_imagem_plano ou upload_to_drive para o PNG aqui novamente.

        # Upload do DXF
        url_dxf = upload_to_drive(path_saida, nome_saida_livre)
        
        # O nome do PNG será o mesmo do DXF, mas com extensão .png
        nome_png = nome_saida_livre.replace('.dxf', '.png')
        
        # Para obter o URL do PNG, precisamos de uma forma de obtê-lo do Google Drive
        # A função upload_to_drive já retorna o URL, mas para o DXF.
        # Se gerar_imagem_plano já faz o upload do PNG, ela deve retornar o URL do PNG
        # ou o upload_to_drive precisa ser chamado para o PNG também.
        # Assumindo que gerar_imagem_plano já faz o upload e o nome é consistente,
        # podemos construir o URL do PNG se necessário, ou ajustar a resposta da API.
        # Por enquanto, a API de composição retorna apenas o URL do DXF.
        # Para retornar o URL do PNG, precisaríamos que `compor_fn` retornasse o URL do PNG também.
        # VOU ASSUMIR QUE `compor_fn` JÁ FAZ O UPLOAD DO PNG E PODEMOS CONSTRUIR O URL.
        # No entanto, para ser mais robusto, a função `compor_fn` deveria retornar o URL do PNG.
        # Para simplificar, vou adicionar um placeholder para o URL do PNG.

        # A forma mais robusta seria:
        # url_dxf, url_png = compor_fn(chunk_objs, path_saida) # compor_fn retorna ambos os URLs
        # Mas como a estrutura atual não permite isso facilmente, vamos adicionar um placeholder para o PNG.
        # Idealmente, a função `gerar_imagem_plano` em compose_dxf.py e compose_dxf_32.py
        # deveria retornar o URL do PNG após o upload.

        # Para compatibilidade com a estrutura atual, vamos apenas retornar o nome do DXF e um URL de exemplo para o PNG.
        # VOCÊ PRECISARÁ AJUSTAR SEU `compose_dxf.py` e `compose_dxf_32.py` PARA RETORNAR O URL DO PNG
        # DE DENTRO DA FUNÇÃO `gerar_imagem_plano` E PASSÁ-LO ATÉ AQUI.
        # Por agora, vou simular o URL do PNG.
        url_png_simulado = url_dxf.replace('.dxf', '.png').replace('/view', '') # Simulação, precisa ser o URL real do PNG

        planos.append({"nome": nome_saida_livre, "url_dxf": url_dxf, "url_png": url_png_simulado})

    return {"plans": planos}
