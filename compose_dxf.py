import ezdxf
from google_drive import baixar_arquivo_drive
from collections import defaultdict

# Coordenadas definidas para etiquetas e posições de base
COORDENADAS = {
    1: (99.5, 113.9), 2: (253.0, 113.9), 3: (406.5, 113.9), 4: (560.0, 113.9),
    5: (713.5, 113.9), 6: (867.0, 113.9), 7: (99.5, 311.7), 8: (253.0, 311.7),
    9: (406.5, 311.7), 10: (560.0, 311.7), 11: (713.5, 311.7), 12: (867.0, 311.7),
    13: (99.5, 509.5), 14: (253.0, 509.5), 15: (406.5, 509.5), 16: (560.0, 509.5),
    17: (713.5, 509.5), 18: (867.0, 509.5),
}

# Pontos onde adicionar marcações de base
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
    return (min_x + max_x) / 2, (min_y + max_y) / 2

def adicionar_marca(msp, x, y, tamanho=17):
    """
    Adiciona um quadrado de lado `tamanho` pontilhado no ponto (x,y).
    """
    half = tamanho / 2
    msp.add_lwpolyline(
        [(x-half, y-half), (x+half, y-half), (x+half, y+half), (x-half, y+half), (x-half, y-half)],
        dxfattribs={"color": 2, "closed": True}
    )

def compor_dxf_com_base(lista_arquivos, caminho_saida):
    """
    Cria um novo DXF com:
    - Marcações de base em POSICOES_BASE.
    - Importação eficiente de etiquetas via blocos para cada arquivo.
    """
    # Cria novo documento
    doc_saida = ezdxf.new()
    msp_saida = doc_saida.modelspace()

    # Adiciona marcações de base
    for x, y in POSICOES_BASE:
        adicionar_marca(msp_saida, x, y)

    # Agrupa por nome de arquivo para otimizar múltiplas inserções
    grupos = defaultdict(list)
    for item in lista_arquivos:
        grupos[item.nome].append(item.posicao)

    # Para cada arquivo único, cria um bloco e inserções
    for nome_arq, posicoes in grupos.items():
        arq_path = baixar_arquivo_drive(nome_arq, subpasta="arquivos padronizados")
        doc_etiq = ezdxf.readfile(arq_path)
        msp_etiq = doc_etiq.modelspace()

        # Calcula centro e cria bloco
        cx, cy = calcular_centro(msp_etiq)
        block_name = f"BLK_{nome_arq.replace('.', '_')}"
        blk = doc_saida.blocks.new(name=block_name)

        # Copia entidades para o bloco, deslocadas para origem
        for e in list(msp_etiq):
            try:
                e_blk = e.copy()
                e_blk.translate(dx=-cx, dy=-cy, dz=0)
                blk.add_entity(e_blk)
            except Exception:
                continue

        # Insere o bloco em cada posição desejada
        for pos in posicoes:
            destino_x, destino_y = COORDENADAS.get(pos, (0, 0))
            msp_saida.add_blockref(block_name, insert=(destino_x, destino_y))

    # Salva arquivo de saída
    doc_saida.saveas(caminho_saida)
