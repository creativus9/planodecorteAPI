import ezdxf
import os
from google_drive import baixar_arquivo_drive

# posições fixas definidas pelo usuário
COORDENADAS = {
    1: (99.5, 113.9),
    2: (253.0, 113.9),
    3: (406.5, 113.9),
    4: (560.0, 113.9),
    5: (713.5, 113.9),
    6: (867.0, 113.9),
    7: (99.5, 311.7),
    8: (253.0, 311.7),
    9: (406.5, 311.7),
    10: (560.0, 311.7),
    11: (713.5, 311.7),
    12: (867.0, 311.7),
    13: (99.5, 509.5),
    14: (253.0, 509.5),
    15: (406.5, 509.5),
    16: (560.0, 509.5),
    17: (713.5, 509.5),
    18: (867.0, 509.5),
}

def compor_dxf_com_base(lista_arquivos, caminho_saida):
    base_path = baixar_arquivo_drive("BASE.DXF")
    doc_base = ezdxf.readfile(base_path)
    msp_base = doc_base.modelspace()

    for item in lista_arquivos:
        arq_path = baixar_arquivo_drive(item.nome, subpasta="arquivos padronizados")
        doc_insert = ezdxf.readfile(arq_path)
        msp_insert = doc_insert.modelspace()

        bbox = msp_insert.bbox()
        largura = bbox.size.x
        altura = bbox.size.y

        centro_x = bbox.center.x
        centro_y = bbox.center.y

        destino_x, destino_y = COORDENADAS[item.posicao]

        deslocamento_x = destino_x - centro_x
        deslocamento_y = destino_y - centro_y

        # copia as entidades com deslocamento calculado
        for e in msp_insert:
            nova_entidade = e.copy()
            nova_entidade.translate(dx=deslocamento_x, dy=deslocamento_y)
            msp_base.add_entity(nova_entidade)

    doc_base.saveas(caminho_saida)
