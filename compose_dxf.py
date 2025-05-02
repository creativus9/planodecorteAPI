import ezdxf
from ezdxf.addons.importer import Importer
from google_drive import baixar_arquivo_drive

# Posições fixas
posicoes = [
    (99.5, 113.9), (253.0, 113.9), (406.5, 113.9), (560.0, 113.9), (713.5, 113.9), (867.0, 113.9),
    (99.5, 311.7), (253.0, 311.7), (406.5, 311.7), (560.0, 311.7), (713.5, 311.7), (867.0, 311.7),
    (99.5, 509.5), (253.0, 509.5), (406.5, 509.5), (560.0, 509.5), (713.5, 509.5), (867.0, 509.5),
]

def compor_dxf_com_base(lista, output_path):
    base_path = baixar_arquivo_drive("BASE.DXF")
    doc_final = ezdxf.readfile(base_path)
    msp_final = doc_final.modelspace()

    for item in lista:
        if item.posicao < 1 or item.posicao > 18:
            continue

        x, y = posicoes[item.posicao - 1]
        arq_path = baixar_arquivo_drive(item.nome, subpasta="arquivos padronizados")
        doc = ezdxf.readfile(arq_path)
        msp = doc.modelspace()

        importer = Importer(doc, doc_final)
        importer.import_modelspace()
        importer.finalize()

        for e in msp_final:
            try:
                if e.dxf.owner == msp_final.dxf.handle:
                    e.translate(x, y)
            except Exception:
                continue

    doc_final.saveas(output_path)