from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from compose_dxf import compor_dxf_com_base
from google_drive import upload_to_drive, listar_arquivos_existentes
from datetime import datetime
from types import SimpleNamespace

app = FastAPI()

class Entrada(BaseModel):
    arquivos: list[str]  # só nomes
    nome_arquivo: str = None  # novo campo opcional

@app.post("/compor")
def compor(entrada: Entrada):
    total = len(entrada.arquivos)
    if total == 0:
        raise HTTPException(status_code=400, detail="Nenhum arquivo fornecido.")

    existentes = listar_arquivos_existentes()
    hoje = datetime.now().strftime("%d-%m-%Y")
    prefixo = "Plano de corte"
    planos = []

    # base para nomes de arquivo
    nome_base = entrada.nome_arquivo
    if not nome_base:
        # fallback para formato antigo
        contador = 1
        while True:
            nome_teste = f"{prefixo} {contador:02d} {hoje}.dxf"
            if nome_teste not in existentes:
                nome_base = nome_teste
                break
            contador += 1
    else:
        # Garante extensão
        if not nome_base.lower().endswith('.dxf'):
            nome_base = nome_base.strip() + ".dxf"

    # Quantos planos de corte vão ser criados?
    num_planos = (total + 17) // 18  # inteiro para cima

    for i in range(num_planos):
        chunk_names = entrada.arquivos[i*18 : (i+1)*18]
        chunk_objs = [
            SimpleNamespace(nome=name, posicao=index + 1)
            for index, name in enumerate(chunk_names)
        ]
        # Para mais de um plano, adiciona _2, _3...
        if i == 0:
            nome_saida = nome_base
        else:
            nome_saida = nome_base.replace(".dxf", f"_{i+1:02d}.dxf")

        # Garante não sobrescrever nada existente
        contador_extra = 1
        nome_saida_livre = nome_saida
        while nome_saida_livre in existentes:
            nome_saida_livre = nome_saida.replace(".dxf", f"_{contador_extra+1:02d}.dxf")
            contador_extra += 1

        path_saida = f"/tmp/{nome_saida_livre}"
        compor_dxf_com_base(chunk_objs, path_saida)

        url = upload_to_drive(path_saida, nome_saida_livre)
        planos.append({"nome": nome_saida_livre, "url": url})

    return {"plans": planos}
