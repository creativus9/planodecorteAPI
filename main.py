from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from compose_dxf import compor_dxf_com_base
from google_drive import upload_to_drive, listar_arquivos_existentes, mover_arquivos_antigos
from datetime import datetime
from types import SimpleNamespace

app = FastAPI()

class Entrada(BaseModel):
    arquivos: list[str]  # agora só nomes

@app.post("/compor")
def compor(entrada: Entrada):
    total = len(entrada.arquivos)
    if total == 0:
        raise HTTPException(status_code=400, detail="Nenhum arquivo fornecido.")

    existentes = listar_arquivos_existentes()
    hoje = datetime.now().strftime("%d-%m-%Y")
    prefixo = "Plano de corte"
    planos: list[dict] = []  # lista de dicts {nome, url}

    # encontra o primeiro contador livre
    contador = 1
    while True:
        nome_teste = f"{prefixo} {contador:02d} {hoje}.dxf"
        if nome_teste not in existentes:
            break
        contador += 1

    # processa em blocos de até 18 entradas
    for i in range(0, total, 18):
        chunk_names = entrada.arquivos[i : i + 18]
        # converte em objetos com posicao = índice + 1 dentro do plano
        chunk_objs = [
            SimpleNamespace(nome=name, posicao=index + 1)
            for index, name in enumerate(chunk_names)
        ]

        nome_saida = f"{prefixo} {contador:02d} {hoje}.dxf"
        existentes.append(nome_saida)
        contador += 1

        path_saida = f"/tmp/{nome_saida}"
        compor_dxf_com_base(chunk_objs, path_saida)

        url = upload_to_drive(path_saida, nome_saida)
        planos.append({"nome": nome_saida, "url": url})

    return {"plans": planos}

@app.post("/mover-antigos")
def mover_antigos():
    """Move arquivos de planos de corte antigos para a subpasta 'arquivo morto'."""
    moved = mover_arquivos_antigos()
    return {"moved": moved}
