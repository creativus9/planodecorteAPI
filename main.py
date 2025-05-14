from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from compose_dxf import compor_dxf_com_base
from google_drive import upload_to_drive, listar_arquivos_existentes, drive_service, FOLDER_ID
from googleapiclient.errors import HttpError
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

    nome_saida = gerar_nome_sequencial()
    path_saida = f"/tmp/{nome_saida}"
    compor_dxf_com_base(entrada.arquivos, path_saida)

    url = upload_to_drive(path_saida, nome_saida)
    return {"url": url}

@app.post("/mover-antigos")
def mover_antigos():
    hoje = datetime.now().strftime("%d-%m-%Y")
    # Buscar ou criar subpasta "arquivo morto"
    q_folder = (
        f"'{FOLDER_ID}' in parents and name = 'arquivo morto'"
        " and mimeType = 'application/vnd.google-apps.folder'"
    )
    resp = drive_service.files().list(q=q_folder, fields="files(id)").execute()
    files_folders = resp.get("files", [])
    if files_folders:
        morto_id = files_folders[0]["id"]
    else:
        folder_metadata = {
            "name": "arquivo morto",
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [FOLDER_ID]
        }
        morto_id = drive_service.files().create(body=folder_metadata, fields="id").execute()["id"]

    # Listar arquivos 'Plano de corte' na pasta principal
    q_files = f"'{FOLDER_ID}' in parents and name contains 'Plano de corte'"
    resp_files = drive_service.files().list(q=q_files, fields="files(id,name,parents)").execute()
    files_to_move = resp_files.get("files", [])

    moved = 0
    for f in files_to_move:
        name = f["name"]
        # Extrair data no formato dd-MM-YYYY
        data = name[-14:-4]
        if data != hoje:
            try:
                drive_service.files().update(
                    fileId=f["id"],
                    addParents=morto_id,
                    removeParents=FOLDER_ID,
                    fields="id, parents"
                ).execute()
                moved += 1
            except HttpError:
                continue
    return {"moved": moved}

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
