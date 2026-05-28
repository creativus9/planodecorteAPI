import ezdxf
import logging
import unicodedata

# Configuração simples de log
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def contar_placas_no_dxf(caminho_arquivo: str) -> int:
    """
    Lê o arquivo DXF e identifica placas seguindo as regras rigorosas:
    - Entidade LWPOLYLINE
    - Cor Amarela (código 62 = 2)
    - Formato Retângulo (Fechada, 4 ou 5 pontos)
    - Dimensões: ~129mm de largura e ~187.8mm de altura
    """
    try:
        doc = ezdxf.readfile(caminho_arquivo)
        msp = doc.modelspace()
    except Exception as e:
        logger.error(f"Erro ao ler DXF {caminho_arquivo}: {e}")
        return 0

    count = 0
    for entity in msp.query('LWPOLYLINE'):
        # Regra 1: Ter a cor Amarela (62 = 2)
        if entity.dxf.color != 2:
            continue

        points = list(entity.get_points('xy'))
        
        # Regra 2: Formato Retângulo e ser fechada
        # Na prática do DXF, uma polilinha fechada pode ter 4 pontos (com flag closed=True) 
        # ou exatamente 5 pontos (onde o último se conecta ao primeiro).
        is_closed = entity.closed or (len(points) == 5 and points[0] == points[-1])
        if not is_closed:
            continue
        
        # Ignora se não formar a quantidade de cantos de um retângulo
        if len(points) not in (4, 5):
            continue

        # Dimensões e Coordenadas
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]

        largura = max(xs) - min(xs)
        altura = max(ys) - min(ys)

        # Tolerância de 0.5mm para garantir que vai detectar, pois o CAD pode salvar dízimas precisas
        tol = 0.5
        # Valida Exatos 129 x 187.8
        if abs(largura - 129.0) <= tol and abs(altura - 187.8) <= tol:
            count += 1
        # Valida caso a peça tenha sido desenhada deitada (rotacionada 90 graus)
        elif abs(largura - 187.8) <= tol and abs(altura - 129.0) <= tol:
            count += 1

    return count

def mapear_cor(cor_texto: str) -> str:
    """ Identifica a cor vinda do JSON ignorando acentos e maiúsculas/minúsculas """
    if not cor_texto:
        return "PRA" # Prata como padrão se vier vazio
    
    cor_limpa = ''.join(c for c in unicodedata.normalize('NFD', cor_texto) if unicodedata.category(c) != 'Mn').upper()
    
    if "DOU" in cor_limpa or "OUR" in cor_limpa:
        return "DOU"
    elif "ROS" in cor_limpa:
        return "ROS"
    elif "PRA" in cor_limpa:
        return "PRA"
        
    return "PRA"

def limpar_dxf_placas(caminho_entrada: str, caminho_saida: str) -> int:
    """
    Abre o DXF, localiza as placas amarelas de corte e APAGA todas as outras entidades
    que estejam fora desses retângulos (Lixo de desenho do cliente).
    Salva o arquivo limpo para ser usado no plano de corte.
    """
    from ezdxf import bbox
    
    try:
        doc = ezdxf.readfile(caminho_entrada)
        msp = doc.modelspace()
    except Exception as e:
        logger.error(f"Erro ao ler DXF para limpeza {caminho_entrada}: {e}")
        return 0
        
    placas_boxes = []
    # 1. Encontra os retângulos amarelos
    for entity in msp.query('LWPOLYLINE'):
        if entity.dxf.color == 2:
            points = list(entity.get_points('xy'))
            is_closed = entity.closed or (len(points) == 5 and points[0] == points[-1])
            if is_closed and len(points) in (4, 5):
                xs = [p[0] for p in points]
                ys = [p[1] for p in points]
                largura, altura = max(xs) - min(xs), max(ys) - min(ys)
                tol = 0.5
                if (abs(largura - 129.0) <= tol and abs(altura - 187.8) <= tol) or \
                   (abs(largura - 187.8) <= tol and abs(altura - 129.0) <= tol):
                    # Salva a "área" do retângulo com 1mm de folga
                    placas_boxes.append((min(xs)-1, min(ys)-1, max(xs)+1, max(ys)+1))
    
    qtd_placas = len(placas_boxes)
    if qtd_placas == 0:
        return 0
        
    cache = bbox.Cache()
    entities_to_delete = []
    
    # 2. Deleta o lixo (Tudo que não está 100% dentro da placa)
    for entity in msp:
        try:
            bb = bbox.extents([entity], cache=cache)
            if not bb.has_data:
                continue
            
            e_minx, e_miny = bb.extmin.x, bb.extmin.y
            e_maxx, e_maxy = bb.extmax.x, bb.extmax.y
            
            dentro = False
            for (px1, py1, px2, py2) in placas_boxes:
                if (e_minx >= px1 and e_maxx <= px2 and e_miny >= py1 and e_maxy <= py2):
                    dentro = True
                    break
            
            if not dentro:
                entities_to_delete.append(entity)
        except Exception:
            entities_to_delete.append(entity)
            
    for ent in entities_to_delete:
        try:
            msp.delete_entity(ent)
        except:
            pass
            
    # Salva o arquivo contendo APENAS a plaquinha limpa e o conteúdo dela
    doc.saveas(caminho_saida)
    return qtd_placas


def processar_ids_placas(ids: list) -> list:
    """
    Recebe os IDs da rota, aciona o download e retorna a contagem formatada.
    """
    from google_drive import buscar_dxf_personalizado
    resultados = []

    for target_id in ids:
        logger.info(f"Iniciando processamento para o ID: {target_id}")
        caminho_local, nome_arquivo = buscar_dxf_personalizado(target_id)
        
        if not caminho_local:
            logger.warning(f"ID {target_id}: Nenhum arquivo correspondente encontrado.")
            resultados.append({
                "id": target_id,
                "status": "nao_encontrado",
                "quantidade": 0,
                "arquivo": None
            })
            continue
            
        qtd_placas = contar_placas_no_dxf(caminho_local)
        
        # LOG SIMPLES REQUISITADO
        logger.info(f"RESULTADO -> ID: {target_id} | Placas Encontradas: {qtd_placas}")
        
        resultados.append({
            "id": target_id,
            "status": "sucesso",
            "quantidade": qtd_placas,
            "arquivo": nome_arquivo
        })

    return resultados