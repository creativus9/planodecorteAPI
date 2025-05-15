import os
import json
import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Carrega credenciais direto da variável de ambiente
SERVICE_ACCOUNT_JSON = os.getenv("service_account.json")
if not SERVICE_ACCOUNT_JSON:
    raise Exception("Variável de ambiente 'service_account.json' não foi encontrada.")
info = json.loads(SERVICE_ACCOUNT_JSON)

creds = service_account.Credentials.from_service_account_info(
    info,
    scopes=["https://www.googleapis.com/auth/drive"]
)

drive_service = build('drive', 'v3', credentials=creds)
FOLDER_ID = "18RIUiRS7SugpUeGOIAxu3gVj9D6-MD2G"


def baixar_arquivo_drive(nome_arquivo, subpasta=None):
    """Baixa e retorna caminho local de um arquivo no Drive"""
    if subpasta:
        sub_query = f"'{FOLDER_ID}' in parents and name='{subpasta}' and mimeType='application/vnd.google-apps.folder'"
        sub_result = drive_service.files().list(q=sub_query, fields="files(id)").execute().get('files', [])
        if not sub_result:
            raise FileNotFoundError(f"Subpasta '{subpasta}' não encontrada no Drive.")
        sub_id = sub_result[0]['id']
        query = f"'{sub_id}' in parents and name='{nome_arquivo}'"
    else:
        query = f"'{FOLDER_ID}' in parents and name='{nome_arquivo}'"

    response = drive_service.files().list(q=query, fields="files(id,name)").execute()
    arquivos = response.get('files', [])
    if not arquivos:
        raise FileNotFoundError(f"{nome_arquivo} não encontrado no Drive.")
    file_id = arquivos[0]['id']
    local_path = f"/tmp/{nome_arquivo}"
    data = drive_service.files().get_media(fileId=file_id).execute()
    with open(local_path, 'wb') as f:
        f.write(data)
    return local_path


def listar_arquivos_existentes():
    """Retorna lista de nomes de arquivos na pasta principal"""
    response = drive_service.files().list(q=f"'{FOLDER_ID}' in parents", fields="files(name)").execute()
    return [f['name'] for f in response.get('files', [])]


def upload_to_drive(caminho, nome):
    """Faz upload de arquivo e retorna URL pública"""
    file_metadata = {'name': nome, 'parents': [FOLDER_ID]}
    media = MediaFileUpload(caminho, mimetype="application/dxf")
    file = drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()
    drive_service.permissions().create(
        fileId=file.get('id'), body={'role':'reader','type':'anyone'}
    ).execute()
    return f"https://drive.google.com/file/d/{file.get('id')}/view"


def mover_arquivos_antigos():
    """
    Move arquivos .dxf e .png com data diferente da atual para subpasta 'arquivo morto'.
    Retorna quantidade movida.
    """
    hoje = datetime.datetime.now().strftime("%d-%m-%Y")
    # garantir subpasta 'arquivo morto'
    query = f"'{FOLDER_ID}' in parents and name='arquivo morto' and mimeType='application/vnd.google-apps.folder'"
    res = drive_service.files().list(q=query, fields="files(id)").execute().get('files', [])
    if res:
        dest_id = res[0]['id']
    else:
        meta = {'name':'arquivo morto','mimeType':'application/vnd.google-apps.folder','parents':[FOLDER_ID]}
        folder = drive_service.files().create(body=meta, fields='id').execute()
        dest_id = folder.get('id')
    # listar arquivos na pasta principal
    resp = drive_service.files().list(q=f"'{FOLDER_ID}' in parents", fields="files(id,name,parents)").execute()
    files = resp.get('files', [])
    moved = 0
    for f in files:
        name = f.get('name', '')
        if name.startswith('Plano de corte '):
            # extrair data antes de extensão
            parts = name.rsplit(' ', 1)
            if len(parts)==2:
                date_part = parts[1].replace('.dxf','').replace('.png','')
                if date_part != hoje:
                    drive_service.files().update(
                        fileId=f['id'],
                        addParents=dest_id,
                        removeParents=FOLDER_ID,
                        fields='id, parents'
                    ).execute()
                    moved += 1
    return moved
