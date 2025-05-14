import ezdxf
from google_drive import baixar_arquivo_drive
import copy

# Coordenadas definidas para etiquetas
COORDENADAS = {
    1: (99.5, 113.9), 2: (253.0, 113.9), 3: (406.5, 113.9), 4: (560.0, 113.9),
    5: (713.5, 113.9), 6: (867.0, 113.9), 7: (99.5, 311.7), 8: (253.0, 311.7),
    9: (406.5, 311.7), 10: (560.0, 311.7), 11: (713.5, 311.7), 12: (867.0, 311.7),
    13: (99.5, 509.5), 14: (253.0, 509.5), 15: (406.5, 509.5), 16: (560.0, 509.5),
    17: (713.5, 509.5), 18: (867.0, 509.5),
}

# Posições de marcação de base
POSICOES_BASE = [
    (8.5, 8.5),
    (961.5, 8.5),
    (8.5, 771.5),
    (961.5, 771.5),
]

def calcular_centro(msp):
    """
    Calcula o centro do bounding box de todas as entidades em modelspace.
    """
    min_x = min_y = max_x = max_y = None
    for e in msp:
        try:
            bbox = e.bbox()
            if bbox.extmin and bbox.extmax:
                exmin, exmax = bbox.extmin, bbox.extmax
                if min_x is None:
                    min_x, min_y = exmin.x, exmin.y
                    max_x, max_y = exmax.x, exmax.y
                else:
                    min_x = min(min_x, exmin.x)
                    min_y = min(min_y, exmin.y)
                    max_x = max(max_x, exmax.x)
                    max_y = max(max_y, exmax.y)
        except Exception:
            continue
    if min_x is None:
        return 0, 0
    return ((min_x + max_x) / 2, (min_y + max_y) / 2)

def adicionar_marca(msp, x, y, tamanho=17):
    """
    Adiciona um quadrado amarelo de lado `tamanho` no ponto (x,y).
    """
    half = tamanho / 2
    msp.add_lwpolyline([
        (x-half, y-half),
        (x+half, y-half),
        (x+half, y+half),
        (x-half, y+half),
        (x-half, y-half)
    ], dxfattribs={"color": 2, "closed": True})

def compor_dxf_com_base(lista_arquivos, caminho_saida):
    """
    Gera um novo DXF contendo:
    - Marcações de base
    - Inserções centralizadas de etiquetas usando blocos
    """
    # Cria documento de saída
    doc_saida = ezdxf.new()
    msp_saida = doc_saida.modelspace()

    # Adiciona marcações de base
    for x, y in POSICOES_BASE:
        adicionar_marca(msp_saida, x, y)

    # Cache de blocos para cada arquivo, evitando recriações
    block_cache = {}

    # Insere cada etiqueta na ordem recebida
    for item in lista_arquivos:
        nome_arq = item.nome
        posicao = item.posicao

        # Cria bloco se ainda não existir
        if nome_arq not in block_cache:
            arq_path = baixar_arquivo_drive(nome_arq, subpasta="arquivos padronizados")
            doc_etiq = ezdxf.readfile(arq_path)
            msp_etiq = doc_etiq.modelspace()

            # Calcula centro para alinhar
            centro_x, centro_y = calcular_centro(msp_etiq)
            block_name = f"BLK_{nome_arq.replace('.', '_')}"
            blk = doc_saida.blocks.new(name=block_name)

            # Copia entidades para o bloco, centralizando
            for e in msp_etiq:
                try:
                    e_copia = copy.deepcopy(e)
                    e_copia.translate(dx=-centro_x, dy=-centro_y, dz=0)
                    blk.add_entity(e_copia)
                except Exception:
                    continue

            block_cache[nome_arq] = block_name

        # Insere o bloco na posição desejada
        bloco = block_cache[nome_arq]
        destino_x, destino_y = COORDENADAS.get(posicao, (0, 0))
        msp_saida.add_blockref(bloco, insert=(destino_x, destino_y))

    # Salva DXF final
    doc_saida.saveas(caminho_saida)
