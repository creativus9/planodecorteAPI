import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import tempfile

import json
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Carrega credenciais direto da variável de ambiente (Render)
SERVICE_ACCOUNT_JSON = os.getenv("service_account.json")
if not SERVICE_ACCOUNT_JSON:
    raise Exception("Variável de ambiente 'service_account.json' não foi encontrada.")

info = json.loads(SERVICE_ACCOUNT_JSON)

creds = service_account.Credentials.from_service_account_info(
    info,
    scopes=["https://www.googleapis.com/auth/drive"]
)

drive_service = build('drive', 'v3', credentials=creds)


def baixar_arquivo_drive(nome_arquivo, subpasta=None):
    query = f"'{FOLDER_ID}' in parents and name = '{nome_arquivo}'"
    if subpasta:
        query += f" and '{FOLDER_ID}' in parents"

    response = drive_service.files().list(q=query, fields="files(id, name)").execute()
    arquivos = response.get("files", [])

    if not arquivos:
        raise FileNotFoundError(f"{nome_arquivo} não encontrado no Drive.")

    file_id = arquivos[0]["id"]
    request = drive_service.files().get_media(fileId=file_id)
    fh = tempfile.NamedTemporaryFile(delete=False, suffix=".dxf")
    downloader = MediaFileUpload(fh.name, resumable=False)
    data = drive_service.files().get_media(fileId=file_id).execute()
    with open(fh.name, 'wb') as f:
        f.write(data)
    return fh.name

def listar_arquivos_existentes():
    response = drive_service.files().list(q=f"'{FOLDER_ID}' in parents", fields="files(name)").execute()
    return [f["name"] for f in response.get("files", [])]

def upload_to_drive(caminho, nome):
    file_metadata = {
        "name": nome,
        "parents": [FOLDER_ID]
    }
    media = MediaFileUpload(caminho, mimetype="application/dxf")
    file = drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()
    file_id = file.get("id")
    drive_service.permissions().create(fileId=file_id, body={"role": "reader", "type": "anyone"}).execute()
    return f"https://drive.google.com/file/d/{file_id}/view"
