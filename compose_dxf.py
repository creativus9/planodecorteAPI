
import ezdxf
from google_drive import baixar_arquivo_drive

COORDENADAS = {
    1: (99.5, 113.9), 2: (253.0, 113.9), 3: (406.5, 113.9), 4: (560.0, 113.9),
    5: (713.5, 113.9), 6: (867.0, 113.9), 7: (99.5, 311.7), 8: (253.0, 311.7),
    9: (406.5, 311.7), 10: (560.0, 311.7), 11: (713.5, 311.7), 12: (867.0, 311.7),
    13: (99.5, 509.5), 14: (253.0, 509.5), 15: (406.5, 509.5), 16: (560.0, 509.5),
    17: (713.5, 509.5), 18: (867.0, 509.5),
}

def calcular_centro(msp):
    min_x, min_y, max_x, max_y = None, None, None, None
    for e in msp:
        try:
            bbox = e.bbox()
            if bbox.extmin and bbox.extmax:
                exmin = bbox.extmin
                exmax = bbox.extmax
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
        return (0, 0)
    centro_x = (min_x + max_x) / 2
    centro_y = (min_y + max_y) / 2
    return (centro_x, centro_y)

def adicionar_marca(msp, x, y, tamanho=5):
    msp.add_line((x - tamanho, y), (x + tamanho, y))
    msp.add_line((x, y - tamanho), (x, y + tamanho))

def compor_dxf_com_base(lista_arquivos, caminho_saida):
    base_path = baixar_arquivo_drive("BASE.DXF")
    doc_base = ezdxf.readfile(base_path)
    msp_base = doc_base.modelspace()

    base_min_x, base_min_y, base_max_x, base_max_y = None, None, None, None
    for e in msp_base:
        try:
            bbox = e.bbox()
            if bbox.extmin and bbox.extmax:
                exmin = bbox.extmin
                exmax = bbox.extmax
                if base_min_x is None:
                    base_min_x, base_min_y = exmin.x, exmin.y
                    base_max_x, base_max_y = exmax.x, exmax.y
                else:
                    base_min_x = min(base_min_x, exmin.x)
                    base_min_y = min(base_min_y, exmin.y)
                    base_max_x = max(base_max_x, exmax.x)
                    base_max_y = max(base_max_y, exmax.y)
        except Exception:
            continue

    if base_min_x is None:
        offset_x, offset_y = 0, 0
    else:
        offset_x = -base_min_x
        offset_y = -base_min_y

    for e in list(msp_base):
        try:
            e.translate(dx=offset_x, dy=offset_y, dz=0)
        except Exception:
            continue

    for x, y in COORDENADAS.values():
        adicionar_marca(msp_base, x, y)

    for item in lista_arquivos:
        arq_path = baixar_arquivo_drive(item.nome, subpasta="arquivos padronizados")
        doc_etiqueta = ezdxf.readfile(arq_path)
        msp_etiqueta = doc_etiqueta.modelspace()

        centro_x, centro_y = calcular_centro(msp_etiqueta)
        destino_x, destino_y = COORDENADAS[item.posicao]

        dx = destino_x - centro_x
        dy = destino_y - centro_y

        for entidade in msp_etiqueta:
            try:
                nova = entidade.copy()
                nova.translate(dx=dx, dy=dy, dz=0)
                msp_base.add_entity(nova)
            except Exception:
                continue

    doc_base.saveas(caminho_saida)
