from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from compose_dxf import compor_dxf_com_base as compor_dxf_com_base_18
from compose_dxf_32 import compor_dxf_com_base as compor_dxf_com_base_32
from google_drive import upload_to_drive, listar_arquivos_existentes
from datetime import datetime
from types import SimpleNamespace

app = FastAPI()

class Entrada(BaseModel):
    arquivos: list[str]                # lista de nomes de arquivos DXF
    nome_arquivo: str = None           # nome personalizado do plano (opcional)
    maquina: str = "18"                # "18" ou "32" (padrão: 18 posições)

@app.post("/compor")
def compor(entrada: Entrada):
    total = len(entrada.arquivos)
    if total == 0:
        raise HTTPException(status_code=400, detail="Nenhum arquivo fornecido.")

    existentes = listar_arquivos_existentes()
    hoje = datetime.now().strftime("%d-%m-%Y")
    prefixo = entrada.nome_arquivo if entrada.nome_arquivo else "Plano de corte"
    planos = []

    if entrada.maquina == "32":
        max_por_plano = 32
        compor_fn = compor_dxf_com_base_32
    else:
        max_por_plano = 18
        compor_fn = compor_dxf_com_base_18

    # encontra o primeiro contador livre para evitar sobrescrever arquivos existentes
    contador = 1
    while True:
        nome_teste = f"{prefixo} {contador:02d} {hoje}.dxf"
        if nome_teste not in existentes:
            break
        contador += 1

    num_planos = (total + max_por_plano - 1) // max_por_plano
    for i in range(num_planos):
        chunk_names = entrada.arquivos[i*max_por_plano : (i+1)*max_por_plano]
        chunk_objs = [
            SimpleNamespace(nome=name, posicao=index + 1)
            for index, name in enumerate(chunk_names)
        ]

        nome_saida = f"{prefixo} {contador:02d} {hoje}.dxf"
        existentes.append(nome_saida)
        contador += 1

        path_saida = f"/tmp/{nome_saida}"
        compor_fn(chunk_objs, path_saida)
        url = upload_to_drive(path_saida, nome_saida)
        planos.append({"nome": nome_saida, "url": url})

    return {"plans": planos}
