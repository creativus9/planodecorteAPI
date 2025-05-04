
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import List
from compose_dxf import compor_dxf_com_base
from google_drive import upload_to_drive, listar_arquivos_existentes

app = FastAPI()

class Arquivo(BaseModel):
    nome: str
    posicao: int

class Entrada(BaseModel):
    arquivos: List[Arquivo]

@app.post("/compor")
async def compor(entrada: Entrada, background: BackgroundTasks):
    if len(entrada.arquivos) > 18:
        raise HTTPException(status_code=400, detail="Máximo de 18 arquivos permitidos.")

    nome_saida = gerar_nome_sequencial()
    path_saida = f"/tmp/{nome_saida}"

    background.add_task(gerar_e_enviar_arquivo, entrada.arquivos, path_saida, nome_saida)

    return {
        "mensagem": "Arquivo sendo gerado em segundo plano.",
        "nome_arquivo": nome_saida
    }

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

def gerar_e_enviar_arquivo(lista_arquivos, caminho_saida, nome_saida):
    try:
        compor_dxf_com_base(lista_arquivos, caminho_saida)
        upload_to_drive(caminho_saida, nome_saida)
        print(f"[OK] Arquivo gerado e enviado ao Drive: {nome_saida}")
    except Exception as e:
        print(f"[ERRO] Erro durante geração ou envio: {e}")
