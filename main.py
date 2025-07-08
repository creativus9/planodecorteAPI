from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from compose_dxf import compor_dxf_com_base as compor_dxf_com_base_18
from compose_dxf_32 import compor_dxf_com_base_32
from google_drive import upload_to_drive, listar_arquivos_existentes, baixar_arquivo_drive
from datetime import datetime
from types import SimpleNamespace
import os

app = FastAPI()

class Entrada(BaseModel):
    arquivos: list[str]
    nome_arquivo: str = None
    maquina: str = "18"

# Função utilitária para checar existência de arquivos no Google Drive
def arquivo_existe_drive(nome_arquivo, subpasta="arquivos padronizados"):
    try:
        baixar_arquivo_drive(nome_arquivo, subpasta=subpasta)
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False

@app.post("/compor")
def compor(entrada: Entrada):
    total = len(entrada.arquivos)
    if total == 0:
        raise HTTPException(status_code=400, detail="Nenhum arquivo fornecido.")

    # --- NOVA VALIDAÇÃO DE EXISTÊNCIA ---
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
        url = upload_to_drive(path_saida, nome_saida_livre)
        planos.append({"nome": nome_saida_livre, "url": url})

    return {"plans": planos}
