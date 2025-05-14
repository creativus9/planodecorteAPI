import os
import ezdxf
from google_drive import baixar_arquivo_drive, upload_to_drive
from collections import defaultdict
from PIL import Image, ImageDraw, ImageFont

# Coordenadas em cm
COORDENADAS = {
    1: (99.5, 113.9), 2: (253.0, 113.9), 3: (406.5, 113.9), 4: (560.0, 113.9),
    5: (713.5, 113.9), 6: (867.0, 113.9), 7: (99.5, 311.7), 8: (253.0, 311.7),
    9: (406.5, 311.7), 10: (560.0, 311.7), 11: (713.5, 311.7), 12: (867.0, 311.7),
    13: (99.5, 509.5), 14: (253.0, 509.5), 15: (406.5, 509.5), 16: (560.0, 509.5),
    17: (713.5, 509.5), 18: (867.0, 509.5),
}
POSICOES_BASE = [(8.5, 8.5), (961.5, 8.5), (8.5, 771.5), (961.5, 771.5)]
COLOR_MAP = {'DOU':'#FFD700','ROS':'#B76E79','PRA':'#C0C0C0'}
LETTER_MAP = {'DOU':'D','ROS':'R','PRA':'P'}
PLANO_LX, PLANO_LY = 97, 78  # cm
ETIQ_LX, ETIQ_LY = 13, 19    # cm


def gerar_imagem_plano(caminho_dxf, lista_arquivos):
    png_path = caminho_dxf.replace('.dxf', '.png')
    largura_mm = PLANO_LX * 10
    altura_mm = PLANO_LY * 10
    scale = 1000 / largura_mm
    w_px = int(round(largura_mm * scale))
    h_px = int(round(altura_mm * scale))
    margin = 40
    img = Image.new('RGB', (w_px, h_px + margin), 'white')
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    # título
    title = os.path.basename(caminho_dxf)
    bbox = draw.textbbox((0, 0), title, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((w_px - tw) / 2, (margin - th) / 2), title, fill='black', font=font)
    # retângulos e letras
    half_w = (ETIQ_LX * 10 / 2) * scale
    half_h = (ETIQ_LY * 10 / 2) * scale
    for item in lista_arquivos:
        pos = item.posicao; name = item.nome
        key = os.path.splitext(name)[0][-3:].upper()
        color = COLOR_MAP.get(key, '#CCCCCC')
        letter = LETTER_MAP.get(key, '?')
        xm, ym = COORDENADAS.get(pos, (0, 0))
        cx = xm * 10 * scale
        cy = h_px - ym * 10 * scale + margin
        left, top = cx - half_w, cy - half_h
        right, bottom = cx + half_w, cy + half_h
        draw.rectangle([left, top, right, bottom], fill=color)
        bbox2 = draw.textbbox((0, 0), letter, font=font)
        lw, lh = bbox2[2] - bbox2[0], bbox2[3] - bbox2[1]
        draw.text((cx - lw / 2, cy - lh / 2), letter, fill='black', font=font)
    # salvar PNG
    os.makedirs(os.path.dirname(png_path) or '.', exist_ok=True)
    img.save(png_path)
    print(f"[INFO] PNG salvo: {png_path}")
    # enviar ao Drive
    try:
        url_png = upload_to_drive(png_path, os.path.basename(png_path))
        print(f"[INFO] PNG enviado ao Drive: {url_png}")
    except Exception as e:
        print(f"[ERROR] Falha ao enviar PNG: {e}")
    return png_path


def calcular_centro(msp):
    min_x = min_y = max_x = max_y = None
    for e in msp:
        try:
            bb = e.bbox()
            if bb.extmin and bb.extmax:
                exmin, exmax = bb.extmin, bb.extmax
                if min_x is None:
                    min_x, min_y = exmin.x, exmin.y
                    max_x, max_y = exmax.x, exmax.y
                else:
                    min_x = min(min_x, exmin.x)
                    min_y = min(min_y, exmin.y)
                    max_x = max(max_x, exmax.x)
                    max_y = max(max_y, exmax.y)
        except Exception:
            pass
    if min_x is None:
        return 0, 0
    return ((min_x + max_x) / 2, (min_y + max_y) / 2)


def adicionar_marca(msp, x, y, tamanho=17):
    h = tamanho / 2
    msp.add_lwpolyline(
        [(x - h, y - h), (x + h, y - h), (x + h, y + h), (x - h, y + h), (x - h, y - h)],
        dxfattribs={'color': 2, 'closed': True}
    )


def compor_dxf_com_base(lista_arquivos, caminho_saida):
    # gerar DXF
    doc = ezdxf.new()
    msp = doc.modelspace()
    for x, y in POSICOES_BASE:
        adicionar_marca(msp, x, y)
    first = next((it for it in lista_arquivos if it.posicao == 1), None)
    if first:
        path = baixar_arquivo_drive(first.nome, subpasta='arquivos padronizados')
        eb = ezdxf.readfile(path).modelspace()
        cx, cy = calcular_centro(eb)
        dx, dy = COORDENADAS[1][0] - cx, COORDENADAS[1][1] - cy
        for ent in eb:
            try:
                ne = ent.copy()
                ne.translate(dx, dy, 0)
                msp.add_entity(ne)
            except:
                pass
    grupos = defaultdict(list)
    for it in lista_arquivos:
        if it.posicao != 1:
            grupos[it.nome].append(it.posicao)
    for nome, poses in grupos.items():
        path = baixar_arquivo_drive(nome, subpasta='arquivos padronizados')
        eb = ezdxf.readfile(path).modelspace()
        cx, cy = calcular_centro(eb)
        blk = doc.blocks.new(name=f"BLK_{nome.replace('.', '_')}")
        for ent in eb:
            try:
                ne = ent.copy()
                ne.translate(-cx, -cy, 0)
                blk.add_entity(ne)
            except:
                pass
        for pos in poses:
            msp.add_blockref(blk.name, insert=COORDENADAS[pos])
    # salvar DXF e gerar PNG
    os.makedirs(os.path.dirname(caminho_saida) or '.', exist_ok=True)
    doc.saveas(caminho_saida)
    gerar_imagem_plano(caminho_saida, lista_arquivos)
