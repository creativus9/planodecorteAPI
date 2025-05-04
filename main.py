
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from compose_dxf import compor_dxf_com_base
from google_drive import upload_arquivo_drive, gerar_nome_arquivo

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class Arquivo(BaseModel):
    nome: str
    posicao: int

class EntradaArquivos(BaseModel):
    arquivos: List[Arquivo]

@app.post("/compor")
async def compor(entrada: EntradaArquivos, background: BackgroundTasks):
    nome_arquivo = gerar_nome_arquivo()
    caminho_saida = f"/tmp/{nome_arquivo}"
    background.add_task(gerar_arquivo_em_fundo, entrada.arquivos, caminho_saida, nome_arquivo)
    return {"mensagem": "Arquivo sendo gerado em segundo plano", "nome": nome_arquivo}

def gerar_arquivo_em_fundo(lista_arquivos, caminho_saida, nome_arquivo):
    try:
        compor_dxf_com_base(lista_arquivos, caminho_saida)
        upload_arquivo_drive(caminho_saida, nome_arquivo)
        print(f"[OK] Arquivo gerado e enviado ao Drive: {nome_arquivo}")
    except Exception as e:
        print(f"[ERRO] Durante geração/envio: {e}")
