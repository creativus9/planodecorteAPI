import os
import ezdxf
from google_drive import baixar_arquivo_drive
from collections import defaultdict
from PIL import Image, ImageDraw, ImageFont

# Coordenadas definidas para etiquetas e posições de base (em cm)
COORDENADAS = {
    1: (99.5, 113.9), 2: (253.0, 113.9), 3: (406.5, 113.9), 4: (560.0, 113.9),
    5: (713.5, 113.9), 6: (867.0, 113.9), 7: (99.5, 311.7), 8: (253.0, 311.7),
    9: (406.5, 311.7), 10: (560.0, 311.7), 11: (713.5, 311.7), 12: (867.0, 311.7),
    13: (99.5, 509.5), 14: (253.0, 509.5), 15: (406.5, 509.5), 16: (560.0, 509.5),
    17: (713.5, 509.5), 18: (867.0, 509.5),
}

# Pontos onde adicionar marcações de base (em cm)
POSICOES_BASE = [
    (8.5, 8.5),
    (961.5, 8.5),
    (8.5, 771.5),
    (961.5, 771.5),
]

# Mapeamento de cores pelas três últimas letras
COLOR_MAP = {
    'DOU': '#FFD700',  # dourado
    'ROS': '#B76E79',  # rosê
    'PRA': '#C0C0C0',  # prata
}
LETTER_MAP = {
    'DOU': 'D',
    'ROS': 'R',
    'PRA': 'P',
}

# Tamanho real do plano (cm)
PLANO_LARGURA_CM = 97
PLANO_ALTURA_CM = 78
# Tamanho real da etiqueta (cm)
ETIQ_LARGURA_CM = 13
ETIQ_ALTURA_CM = 19

# Gera imagem ilustrativa do plano de corte
def gerar_imagem_plano(nome_saida, lista_arquivos):
    # converter cm para mm e escalar para px (1000px de largura)
    largura_mm = PLANO_LARGURA_CM * 10
    altura_mm = PLANO_ALTURA_CM * 10
    factor = 1000 / largura_mm
    largura_px = int(round(largura_mm * factor))
    altura_px = int(round(altura_mm * factor))
    margin = 40  # espaço para título
    total_h = altura_px + margin

    image = Image.new('RGB', (largura_px, total_h), 'white')
    draw = ImageDraw.Draw(image)
    # Fonte padrão
    font = ImageFont.load_default()

    # Desenhar título
    title = nome_saida
    w, h = draw.textsize(title, font=font)
    draw.text(((largura_px - w) / 2, (margin - h) / 2), title, fill='black', font=font)

    # Desenhar retângulos e letras
    half_w = (ETIQ_LARGURA_CM * 10 / 2) * factor
    half_h = (ETIQ_ALTURA_CM * 10 / 2) * factor
    for item in lista_arquivos:
        pos = item.posicao
        nome_arq = item.nome
        # cor e letra
        key = os.path.splitext(nome_arq)[0][-3:].upper()
        color = COLOR_MAP.get(key, '#CCCCCC')
        letter = LETTER_MAP.get(key, '?')
        # posição central em px
        x_mm, y_mm = COORDENADAS.get(pos, (0, 0))
        cx = x_mm * 10 * factor
        cy = altura_px - (y_mm * 10 * factor) + margin
        # retângulo
        left = cx - half_w
        right = cx + half_w
        top = cy - half_h
        bottom = cy + half_h
        draw.rectangle([left, top, right, bottom], fill=color)
        # letra central
        lw, lh = draw.textsize(letter, font=font)
        draw.text((cx - lw / 2, cy - lh / 2), letter, fill='black', font=font)

    # salvar PNG
    png_path = nome_saida.replace('.dxf', '.png')
    image.save(png_path)
    return png_path


def calcular_centro(msp):
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
    half = tamanho / 2
    msp.add_lwpolyline(
        [(x-half, y-half), (x+half, y-half), (x+half, y+half), (x-half, y+half), (x-half, y-half)],
        dxfattribs={'color': 2, 'closed': True}
    )


def compor_dxf_com_base(lista_arquivos, caminho_saida):
    # Cria o DXF
    doc_saida = ezdxf.new()
    msp_saida = doc_saida.modelspace()

    # Marcações de base no DXF
    for x, y in POSICOES_BASE:
        adicionar_marca(msp_saida, x, y)

    # Inserção garantida para posição 1
    first_item = next((item for item in lista_arquivos if item.posicao == 1), None)
    if first_item:
        arq_path = baixar_arquivo_drive(first_item.nome, subpasta='arquivos padronizados')
        doc_etiq = ezdxf.readfile(arq_path)
        msp_etiq = doc_etiq.modelspace()
        cx, cy = calcular_centro(msp_etiq)
        destino_x, destino_y = COORDENADAS[1]
        dx = destino_x - cx
        dy = destino_y - cy
        for ent in msp_etiq:
            try:
                nova = ent.copy()
                nova.translate(dx=dx, dy=dy, dz=0)
                msp_saida.add_entity(nova)
            except Exception:
                continue

    # Agrupar demais posições e inserir via blocos
    grupos = defaultdict(list)
    for item in lista_arquivos:
        if item.posicao == 1:
            continue
        grupos[item.nome].append(item.posicao)

    for nome_arq, posicoes in grupos.items():
        arq_path = baixar_arquivo_drive(nome_arq, subpasta='arquivos padronizados')
        doc_etiq = ezdxf.readfile(arq_path)
        msp_etiq = doc_etiq.modelspace()
        cx, cy = calcular_centro(msp_etiq)
        block_name = f"BLK_{nome_arq.replace('.', '_')}"
        blk = doc_saida.blocks.new(name=block_name)
        for e in msp_etiq:
            try:
                e_blk = e.copy()
                e_blk.translate(dx=-cx, dy=-cy, dz=0)
                blk.add_entity(e_blk)
            except Exception:
                continue
        for pos in posicoes:
            destino_x, destino_y = COORDENADAS.get(pos, (0, 0))
            msp_saida.add_blockref(block_name, insert=(destino_x, destino_y))

    # Salvar DXF
    doc_saida.saveas(caminho_saida)
    # Gerar imagem PNG correspondente
    nome_arquivo = os.path.basename(caminho_saida)
    gerar_imagem_plano(nome_arquivo, lista_arquivos)
