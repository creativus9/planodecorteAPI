from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from compose_dxf import compor_dxf_com_base
from google_drive import upload_to_drive, listar_arquivos_existentes
from datetime import datetime
import os

app = FastAPI()

class Arquivo(BaseModel):
    nome: str
    posicao: int

class Entrada(BaseModel):
    arquivos: list[Arquivo]

@app.post("/compor")
def compor(entrada: Entrada):
    if len(entrada.arquivos) > 18:
        raise HTTPException(status_code=400, detail="Máximo de 18 arquivos permitidos.")

    # Compor o DXF
    nome_saida = gerar_nome_sequencial()
    path_saida = f"/tmp/{nome_saida}"
    compor_dxf_com_base(entrada.arquivos, path_saida)

    # Upload ao Drive
    url = upload_to_drive(path_saida, nome_saida)
    return {"url": url}

def gerar_nome_sequencial():
    hoje = datetime.now().strftime("%d-%m-%Y")
    prefixo = "Plano de corte"
    existentes = listar_arquivos_existentes()

    contador = 1
    while True:
        nome = f"{prefixo} {contador:02d} {hoje}.dxf"
        if nome not in existentes:
            return nome
        contador += 1
