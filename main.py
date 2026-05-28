from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

# Importações das funções de composição DXF e de interação com o Google Drive
from compose_dxf import compor_dxf_com_base as compor_dxf_com_base_18
from compose_dxf_32 import compor_dxf_com_base_32
from compose_dxf_32_2 import compor_dxf_com_base_32_2

# Importações para a rota de Placas Personalizadas
from detects_plaque import processar_ids_placas

from google_drive import upload_to_drive, listar_arquivos_existentes, baixar_arquivo_drive, arquivo_existe_drive, mover_arquivos_antigos

from datetime import datetime
from types import SimpleNamespace
import os

app = FastAPI()

# --- Configuração CORS ---
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Entrada(BaseModel):
    arquivos: list[str]
    nome_arquivo: str = None
    maquina: str = "18"
    coordenadas_customizadas: dict[int, list[float]] = None
    tamanho_chapa: list[float] = None

class EntradaPlacas(BaseModel):
    ids: list[str]

@app.post("/compor")
def compor(entrada: Entrada):
    """ Endpoint principal para compor arquivos DXF. """
    total = len(entrada.arquivos)
    if total == 0:
        raise HTTPException(status_code=400, detail="Nenhum arquivo fornecido.")

    entrada.arquivos.sort(key=lambda x: x.lower())

    arquivos_faltando = []
    for nome in entrada.arquivos:
        if not arquivo_existe_drive(nome, subpasta="arquivos padronizados"):
            arquivos_faltando.append(nome)
    if arquivos_faltando:
        raise HTTPException(
            status_code=404,
            detail=f"Os arquivos DXF abaixo NÃO foram encontrados no Google Drive:\n" + "\n".join(arquivos_faltando)
        )

    existentes = listar_arquivos_existentes()
    nome_base = entrada.nome_arquivo

    is_custom = entrada.coordenadas_customizadas is not None and entrada.tamanho_chapa is not None

    if is_custom:
        max_por_plano = len(entrada.coordenadas_customizadas)
        def compor_fn(objs, path_saida):
            compor_dxf_com_base_18(
                objs, 
                path_saida, 
                custom_coords=entrada.coordenadas_customizadas, 
                custom_chapa=entrada.tamanho_chapa
            )
    else:
        if entrada.maquina == "32":
            max_por_plano = 32
            compor_fn = compor_dxf_com_base_32
        elif entrada.maquina == "32-2":
            max_por_plano = 32
            compor_fn = compor_dxf_com_base_32_2
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
            nome_saida = nome_base.replace('.dxf', f'_{i+1:02d}.dxf')

        nome_saida_livre = nome_saida
        contador_extra = 2
        while nome_saida_livre in existentes:
            nome_saida_livre = nome_base.replace('.dxf', f'_{i+contador_extra:02d}.dxf')
            contador_extra += 1

        path_saida = f"/tmp/{nome_saida_livre}"
        compor_fn(chunk_objs, path_saida)

        url_dxf = upload_to_drive(path_saida, nome_saida_livre)
        nome_png = nome_saida_livre.replace('.dxf', '.png')
        url_png_simulado = url_dxf.replace('.dxf', '.png').replace('/view', '')

        planos.append({"nome": nome_saida_livre, "url": url_dxf, "url_png": url_png_simulado})

    return {"plans": planos}


@app.post("/engraved_plaque")
def engraved_plaque(entrada: EntradaPlacas):
    """
    Recebe uma lista de IDs, busca o DXF correspondente no Google Drive (com base em Regex),
    e conta quantas placas amarelas existem usando o novo motor em detects_plaque.py.
    """
    if not entrada.ids:
        raise HTTPException(status_code=400, detail="A lista de IDs não pode estar vazia.")
    
    resultados = processar_ids_placas(entrada.ids)
    return {"resultados": resultados}


@app.post("/mover-antigos")
def mover_antigos():
    """ Endpoint para mover arquivos DXF antigos. """
    try:
        moved_count = mover_arquivos_antigos()
        return {"moved": moved_count}
    except Exception as e:
        print(f"Erro ao mover arquivos: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao mover arquivos: {e}")