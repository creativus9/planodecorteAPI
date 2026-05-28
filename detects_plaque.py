import ezdxf
from ezdxf import bbox
from ezdxf.math import Matrix44
import logging
import unicodedata
import os

# Configuração simples de log
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def contar_placas_no_dxf(caminho_arquivo: str) -> int:
    """
    Lê o arquivo DXF e identifica placas seguindo as regras rigorosas.
    """
    try:
        doc = ezdxf.readfile(caminho_arquivo)
        msp = doc.modelspace()
    except Exception as e:
        logger.error(f"Erro ao ler DXF {caminho_arquivo}: {e}")
        return 0

    count = 0
    for entity in msp.query('LWPOLYLINE'):
        if entity.dxf.color != 2:
            continue

        points = list(entity.get_points('xy'))
        is_closed = entity.closed or (len(points) == 5 and points[0] == points[-1])
        if not is_closed or len(points) not in (4, 5):
            continue

        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        largura, altura = max(xs) - min(xs), max(ys) - min(ys)

        tol = 0.5
        if abs(largura - 129.0) <= tol and abs(altura - 187.8) <= tol:
            count += 1
        elif abs(largura - 187.8) <= tol and abs(altura - 129.0) <= tol:
            count += 1

    return count

def mapear_cor(cor_texto: str) -> str:
    """ Identifica a cor vinda do JSON ignorando acentos e maiúsculas/minúsculas """
    if not cor_texto:
        return "PRA" 
    
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
    Abre o DXF, localiza as placas amarelas de corte e APAGA o lixo.
    Em seguida, ESPELHA a placa limpa e ADICIONA o arquivo Placa_Sobrepor.dxf
    sem espelhar por cima da área da placa.
    """
    try:
        doc = ezdxf.readfile(caminho_entrada)
        msp = doc.modelspace()
    except Exception as e:
        logger.error(f"Erro ao ler DXF para limpeza {caminho_entrada}: {e}")
        return 0
        
    placas_boxes = []
    centros_placas = []
    
    # 1. Encontra os retângulos amarelos e o CENTRO EXATO
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
                    
                    # Salva a "área" de proteção
                    placas_boxes.append((min(xs)-1, min(ys)-1, max(xs)+1, max(ys)+1))
                    
                    # Salva o centro matemático real do retângulo amarelo
                    centros_placas.append(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2))
    
    qtd_placas = len(placas_boxes)
    if qtd_placas == 0:
        return 0
        
    # 2. Deleta o lixo (Tudo que não está dentro da placa)
    cache = bbox.Cache()
    entities_to_delete = []
    
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
            
    # ========================================================
    # 3. ESPELHAR E SOBREPOR A PLACA
    # ========================================================
    if centros_placas:
        # Pega o centro global da placa para servir de pivô no espelho
        cx_global = sum(c[0] for c in centros_placas) / len(centros_placas)
        
        # Matriz que Inverte o Eixo X
        m_mirror = Matrix44.chain(
            Matrix44.translate(-cx_global, 0, 0),
            Matrix44.scale(-1, 1, 1),
            Matrix44.translate(cx_global, 0, 0)
        )
        
        # Espelha o conteúdo
        for ent in msp:
            try:
                ent.transform(m_mirror)
            except AttributeError:
                pass # Algumas entidades antigas podem não aceitar cálculo de matriz, são ignoradas
                
        # Calcula onde foram parar os centros após o espelho
        novos_centros = [(2 * cx_global - c[0], c[1]) for c in centros_placas]

        # 4. Inserir a Placa_Sobrepor (SEM espelhar)
        pasta_base = os.path.dirname(os.path.abspath(__file__))
        caminho_sobrepor = os.path.join(pasta_base, "DXF Arquivos", "Placa_Sobrepor.dxf")
        
        if os.path.exists(caminho_sobrepor):
            try:
                doc_sobrepor = ezdxf.readfile(caminho_sobrepor)
                msp_sobrepor = doc_sobrepor.modelspace()
                
                # Acha o centro da placa de sobreposição
                cache_sob = bbox.Cache()
                bb_sob = bbox.extents(msp_sobrepor, cache=cache_sob)
                
                if bb_sob.has_data:
                    cx_sob = bb_sob.center.x
                    cy_sob = bb_sob.center.y
                    
                    # Se tiver mais de uma placa no mesmo arquivo, cola em todas elas
                    for (nx, ny) in novos_centros:
                        dx = nx - cx_sob
                        dy = ny - cy_sob
                        
                        for ent in msp_sobrepor:
                            try:
                                novo_ent = ent.copy()
                                novo_ent.translate(dx, dy, 0)
                                msp.add_entity(novo_ent)
                            except Exception:
                                pass
            except Exception as e:
                logger.error(f"Erro ao inserir Placa_Sobrepor.dxf: {e}")
        else:
            logger.warning(f"Aviso: Arquivo de sobreposição não encontrado em {caminho_sobrepor}")

    # Salva o arquivo final
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
        
        logger.info(f"RESULTADO -> ID: {target_id} | Placas Encontradas: {qtd_placas}")
        
        resultados.append({
            "id": target_id,
            "status": "sucesso",
            "quantidade": qtd_placas,
            "arquivo": nome_arquivo
        })

    return resultados