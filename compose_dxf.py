import ezdxf
from google_drive import baixar_arquivo_drive

# Posições centrais para cada etiqueta (1 a 18)
COORDENADAS = {
    1: (99.5, 113.9), 2: (253.0, 113.9), 3: (406.5, 113.9), 4: (560.0, 113.9),
    5: (713.5, 113.9), 6: (867.0, 113.9), 7: (99.5, 311.7), 8: (253.0, 311.7),
    9: (406.5, 311.7), 10: (560.0, 311.7), 11: (713.5, 311.7), 12: (867.0, 311.7),
    13: (99.5, 509.5), 14: (253.0, 509.5), 15: (406.5, 509.5), 16: (560.0, 509.5),
    17: (713.5, 509.5), 18: (867.0, 509.5),
}

# Posições para as marcações de base
POSICOES_BASE = [
    (8.5, 8.5),
    (961.5, 8.5),
    (8.5, 771.5),
    (961.5, 771.5),
]

def calcular_centro(msp):
    """
    Calcula o centro do bounding box de todas as entidades em um Modelspace.
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
    Adiciona um quadrado amarelo de lado `tamanho` centrado em (x,y).
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
    Gera um novo arquivo DXF:
    1. Marcações de base (os quatro cantos definidores)
    2. Insere cada etiqueta nas posições centrais definidas por COORDENADAS
    """
    # Cria novo documento e modelspace
    doc = ezdxf.new()
    msp = doc.modelspace()

    # Adiciona marcações de base
    for (bx, by) in POSICOES_BASE:
        adicionar_marca(msp, bx, by)

    # Insere cada arquivo de etiqueta na ordem fornecida
    for item in lista_arquivos:
        nome_arq = item.nome
        pos = item.posicao
        destino = COORDENADAS.get(pos)
        if not destino:
            continue
        # Baixa e abre o DXF da etiqueta
        arq_path = baixar_arquivo_drive(nome_arq, subpasta="arquivos padronizados")
        doc_etiq = ezdxf.readfile(arq_path)
        msp_etiq = doc_etiq.modelspace()

        # Calcula o centro da etiqueta
        cx, cy = calcular_centro(msp_etiq)
        dx = destino[0] - cx
        dy = destino[1] - cy

        # Copia entidades para a posição correta
        for ent in msp_etiq:
            try:
                nova = ent.copy()
                nova.translate(dx=dx, dy=dy, dz=0)
                msp.add_entity(nova)
            except Exception:
                continue

    # Salva o DXF resultante
    doc.saveas(caminho_saida)
