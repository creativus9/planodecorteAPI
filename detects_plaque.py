import ezdxf
import logging

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