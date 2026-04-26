import cv2
import mediapipe as mp
import numpy as np
import math
import time
import json
import os
from enum import Enum

# ==========================================
# CONFIGURAÇÕES INICIAIS E VARIÁVEIS GLOBAIS
# ==========================================

# Nova API de Tasks do MediaPipe
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (
    HandLandmarker,
    HandLandmarkerOptions,
    HandLandmarkerResult,
    RunningMode,
)

# Caminho do modelo (baixado previamente)
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hand_landmarker.task")

TAMANHO_MATRIZ = 10
LARGURA_BLOCO = 40  
ALTURA_BLOCO = 20   
ORIGEM_X = 640      # Centralizado horizontalmente (1280/2)
ORIGEM_Y = 370      # Centralizado verticalmente na tela

mapa_alturas = {} 
blocos = []       

# Paleta de Cores (BGR para o OpenCV)
CORES_MENU = [
    (0, 200, 0),   # Verde
    (0, 0, 200),   # Vermelho
    (200, 0, 0),   # Azul
    (0, 200, 200), # Amarelo
    (200, 0, 200), # Magenta
    (200, 200, 200)# Branco/Cinza
]
cor_atual = CORES_MENU[0]

# ==========================================
# MÁQUINA DE ESTADOS
# ==========================================
class AppState(Enum):
    IDLE = "IDLE"
    BUILDING = "BUILDING"
    ERASING = "ERASING"
    MOVING_MODEL = "MOVING_MODEL"

estado_atual = AppState.IDLE
estado_anterior = AppState.IDLE

# Variáveis para Construção Contínua
pinca_ativa_anterior = False
ultima_pos_construcao = None

# Variáveis para Grab & Move (Manipulação Global)
grab_ponto_medio_anterior = None
origem_x_dinamica = ORIGEM_X
origem_y_dinamica = ORIGEM_Y

# Mão Guia — eixo Z suavizado
cursor_z_suave = 0.0
EMA_ALPHA = 0.3  # Fator de suavização (0 = mais suave, 1 = sem filtro)

# Escala do bloco (1, 2, ou 3)
escala_bloco = 1

# Índice da cor atual na paleta
indice_cor_atual = 0

# Tela de ajuda
mostrar_ajuda = False

# Cooldowns para gestos de atalho
ultimo_tempo_escala = 0
ultimo_tempo_cor = 0

# ==========================================
# FUNÇÕES DE RENDERIZAÇÃO
# ==========================================
def grid_para_tela(gx, gy, gz):
    tela_x = origem_x_dinamica + (gx - gy) * (LARGURA_BLOCO // 2)
    tela_y = origem_y_dinamica + (gx + gy) * (ALTURA_BLOCO // 2) - (gz * ALTURA_BLOCO)
    return tela_x, tela_y

def tela_para_grid(tela_x, tela_y):
    dx = tela_x - origem_x_dinamica
    dy = tela_y - origem_y_dinamica
    gx = (dx / (LARGURA_BLOCO / 2) + dy / (ALTURA_BLOCO / 2)) / 2
    gy = (dy / (ALTURA_BLOCO / 2) - dx / (LARGURA_BLOCO / 2)) / 2
    return int(round(gx)), int(round(gy))

def desenhar_cubo_solido(img, gx, gy, gz, cor_base):
    cx, cy = grid_para_tela(gx, gy, gz)
    w, h = LARGURA_BLOCO, ALTURA_BLOCO
    
    topo_pts = np.array([[cx, cy - h], [cx + w//2, cy - h//2], [cx, cy], [cx - w//2, cy - h//2]], np.int32)
    esq_pts = np.array([[cx - w//2, cy - h//2], [cx, cy], [cx, cy + h], [cx - w//2, cy + h - h//2]], np.int32)
    dir_pts = np.array([[cx, cy], [cx + w//2, cy - h//2], [cx + w//2, cy + h - h//2], [cx, cy + h]], np.int32)
    
    b, g, r = cor_base
    cor_topo = (min(255, b+50), min(255, g+50), min(255, r+50))
    cor_esq = (b, g, r)
    cor_dir = (max(0, b-50), max(0, g-50), max(0, r-50))
    
    cv2.fillPoly(img, [topo_pts], cor_topo)
    cv2.fillPoly(img, [esq_pts], cor_esq)
    cv2.fillPoly(img, [dir_pts], cor_dir)
    
    contorno_cor = (50, 50, 50)
    cv2.polylines(img, [topo_pts], True, contorno_cor, 1)
    cv2.polylines(img, [esq_pts], True, contorno_cor, 1)
    cv2.polylines(img, [dir_pts], True, contorno_cor, 1)

def desenhar_menu_ui(img):
    """Desenha a paleta de cores no topo da tela"""
    cv2.rectangle(img, (5, 5), (len(CORES_MENU) * 50 + 15, 60), (40, 40, 40), -1)
    cv2.putText(img, "Paleta de Cores", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    
    for i, cor in enumerate(CORES_MENU):
        cx, cy = 10 + i * 50, 25
        # Destaque se for a cor atual
        espessura = -1 if cor == cor_atual else 2
        if cor == cor_atual:
            cv2.rectangle(img, (cx-2, cy-2), (cx + 42, cy + 32), (255, 255, 255), 2)
        cv2.rectangle(img, (cx, cy), (cx + 40, cy + 30), cor, -1)

def desenhar_hud_estado(img, estado, w_tela):
    """Renderiza o estado atual da Máquina de Estados no canto superior direito."""
    cores_estado = {
        AppState.IDLE: ((180, 180, 180), "IDLE"),
        AppState.BUILDING: ((0, 255, 0), "CONSTRUINDO"),
        AppState.ERASING: ((0, 0, 255), "APAGANDO"),
        AppState.MOVING_MODEL: ((255, 200, 0), "MOVENDO MODELO"),
    }
    cor, texto = cores_estado.get(estado, ((255, 255, 255), "???"))
    pos_x = w_tela - 250
    cv2.rectangle(img, (pos_x - 5, 5), (w_tela - 5, 40), (30, 30, 30), -1)
    cv2.putText(img, f"Estado: {texto}", (pos_x, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.5, cor, 2)

# ==========================================
# FUNÇÕES DE DETECÇÃO DE GESTOS
# ==========================================
def detectar_pinca(hand_landmarks, w, h):
    """Retorna True se polegar e indicador estão juntos (pinça)."""
    x_pol = hand_landmarks[4].x * w
    y_pol = hand_landmarks[4].y * h
    x_ind = hand_landmarks[8].x * w
    y_ind = hand_landmarks[8].y * h
    return math.hypot(x_ind - x_pol, y_ind - y_pol) < 40

def detectar_mao_espalmada(hand_landmarks, w, h):
    """Retorna True se todos os 5 dedos estão estendidos (mão espalmada).
    Verifica se a ponta de cada dedo está acima (menor Y) do PIP correspondente.
    Para o polegar, usa a coordenada X relativa ao pulso."""
    # Pares: (tip, pip) para indicador, médio, anelar, mindinho
    pares_dedos = [(8, 6), (12, 10), (16, 14), (20, 18)]
    dedos_abertos = 0
    for tip_id, pip_id in pares_dedos:
        if hand_landmarks[tip_id].y < hand_landmarks[pip_id].y:
            dedos_abertos += 1
    # Polegar: tip (4) mais afastado lateralmente que IP (3) em relação ao pulso (0)
    pulso_x = hand_landmarks[0].x
    pol_tip_x = hand_landmarks[4].x
    pol_ip_x = hand_landmarks[3].x
    if abs(pol_tip_x - pulso_x) > abs(pol_ip_x - pulso_x):
        dedos_abertos += 1
    return dedos_abertos == 5

def detectar_punho_fechado(hand_landmarks, w, h):
    """Retorna True se todos os dedos estão fechados (punho).
    Verifica se a ponta de cada dedo está abaixo (maior Y) do MCP correspondente."""
    # Pares: (tip, mcp) para indicador, médio, anelar, mindinho
    pares_dedos = [(8, 5), (12, 9), (16, 13), (20, 17)]
    dedos_fechados = 0
    for tip_id, mcp_id in pares_dedos:
        if hand_landmarks[tip_id].y > hand_landmarks[mcp_id].y:
            dedos_fechados += 1
    # Polegar: tip (4) mais perto do pulso que IP (3)
    pulso_x = hand_landmarks[0].x
    pol_tip_x = hand_landmarks[4].x
    pol_ip_x = hand_landmarks[3].x
    if abs(pol_tip_x - pulso_x) < abs(pol_ip_x - pulso_x):
        dedos_fechados += 1
    return dedos_fechados >= 4  # Tolerância: 4 de 5

def interpolar_linha_2d(x0, y0, x1, y1):
    """Bresenham simplificado: retorna lista de (x, y) entre dois pontos da grade."""
    pontos = []
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    while True:
        pontos.append((x0, y0))
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy
    return pontos

def detectar_polegar_mindinho(hand_landmarks, w, h):
    """Retorna True se polegar e mindinho estão juntos (atalho de escala)."""
    x_pol = hand_landmarks[4].x * w
    y_pol = hand_landmarks[4].y * h
    x_min = hand_landmarks[20].x * w
    y_min = hand_landmarks[20].y * h
    return math.hypot(x_min - x_pol, y_min - y_pol) < 50

def detectar_polegar_anelar(hand_landmarks, w, h):
    """Retorna True se polegar e anelar estão juntos (atalho de cor)."""
    x_pol = hand_landmarks[4].x * w
    y_pol = hand_landmarks[4].y * h
    x_ane = hand_landmarks[16].x * w
    y_ane = hand_landmarks[16].y * h
    return math.hypot(x_ane - x_pol, y_ane - y_pol) < 40

def encontrar_posicao_fantasma(cursor_sx, cursor_sy, blocos_lista):
    """Encontra a posição do fantasma baseado na face mais próxima de um bloco existente.
    Retorna (gx, gy, gz) para o fantasma, ou None se não houver posição válida.
    
    Se não houver blocos, retorna a posição da grade no Z=0.
    Se houver blocos, encontra a face visível mais próxima do cursor e retorna
    a posição adjacente àquela face.
    """
    if not blocos_lista:
        # Sem blocos — posicionar no grid Z=0
        gx, gy = tela_para_grid(cursor_sx, cursor_sy)
        return (gx, gy, 0)
    
    # Posições de vizinhança e centros de face correspondentes (em tela)
    # Para cada bloco, as 3 faces visíveis apontam para estas direções:
    melhor_dist = float('inf')
    melhor_pos = None
    
    # Construir um set para lookup rápido de posições ocupadas
    posicoes_ocupadas = set()
    for b in blocos_lista:
        posicoes_ocupadas.add((b[0], b[1], b[2]))
    
    for bloco in blocos_lista:
        bx, by, bz = bloco[0], bloco[1], bloco[2]
        cx, cy = grid_para_tela(bx, by, bz)
        w, h = LARGURA_BLOCO, ALTURA_BLOCO
        
        # Centro de cada face visível e sua posição adjacente
        faces = [
            # (centro_tela_x, centro_tela_y, vizinho_gx, vizinho_gy, vizinho_gz)
            (cx, cy - h,            bx, by, bz + 1),       # Topo → bloco acima
            (cx - w//4, cy + h//4,  bx - 1, by, bz),       # Face esquerda → bloco atrás-esquerda
            (cx + w//4, cy + h//4,  bx, by - 1, bz),       # Face direita → bloco atrás-direita
        ]
        
        # Também verificar faces ocultas (para colocar blocos atrás/embaixo)
        faces += [
            (cx + w//4, cy - h//4,  bx + 1, by, bz),       # Face traseira-direita
            (cx - w//4, cy - h//4,  bx, by + 1, bz),       # Face traseira-esquerda
            (cx, cy + h,            bx, by, bz - 1),       # Embaixo
        ]
        
        for fcx, fcy, nx, ny, nz in faces:
            # Ignorar posições já ocupadas
            if (nx, ny, nz) in posicoes_ocupadas:
                continue
            # Ignorar posições com Z negativo
            if nz < 0:
                continue
                
            dist = math.hypot(cursor_sx - fcx, cursor_sy - fcy)
            if dist < melhor_dist:
                melhor_dist = dist
                melhor_pos = (nx, ny, nz)
    
    # Se todos os vizinhos estão ocupados, fallback para posição na grade Z=0
    if melhor_pos is None:
        gx, gy = tela_para_grid(cursor_sx, cursor_sy)
        return (gx, gy, 0)
    
    return melhor_pos

def colocar_bloco_com_escala(gx, gy, gz, cor, escala):
    """Instancia um bloco (ou grupo de blocos se escala > 1) na posição dada.
    Escala 2 = cubo 2×2×2, Escala 3 = cubo 3×3×3, etc."""
    global blocos, mapa_alturas
    novos = []
    for dx in range(escala):
        for dy in range(escala):
            for dz in range(escala):
                nx, ny, nz = gx + dx, gy + dy, gz + dz
                # Verificar se posição já está ocupada
                ocupado = any(b[0] == nx and b[1] == ny and b[2] == nz for b in blocos)
                if not ocupado:
                    blocos.append((nx, ny, nz, cor))
                    mapa_alturas[(nx, ny)] = max(mapa_alturas.get((nx, ny), 0), nz + 1)
                    novos.append((nx, ny, nz))
    return novos

def desenhar_tela_ajuda(img, w_tela, h_tela):
    """Renderiza a tela de ajuda com fundo preto e lista de atalhos."""
    # Fundo preto semi-transparente
    overlay = np.zeros_like(img)
    cv2.addWeighted(overlay, 0.85, img, 0.15, 0, img)
    
    titulo = "ATALHOS E CONTROLES"
    cv2.putText(img, titulo, (w_tela // 2 - 200, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
    cv2.line(img, (w_tela // 2 - 200, 60), (w_tela // 2 + 200, 60), (255, 255, 255), 1)
    
    atalhos = [
        ("", "--- GESTOS (Mao Direita) ---"),
        ("Polegar + Indicador", "Pinca: Colocar bloco"),
        ("Pinca mantida + mover", "Construcao continua"),
        ("Mao espalmada (5 dedos)", "Apagar bloco"),
        ("Polegar + Anelar", "Trocar cor (ciclar)"),
        ("Polegar + Mindinho", "Mudar escala (1x/2x/3x)"),
        ("", ""),
        ("", "--- GESTOS (Duas Maos) ---"),
        ("Dois punhos fechados", "Grab & Move (mover tudo)"),
        ("", ""),
        ("", "--- TECLADO ---"),
        ("H", "Abrir/Fechar esta tela"),
        ("ESC", "Sair da aplicacao"),
        ("C", "Limpar todos os blocos"),
        ("S", "Salvar projeto (JSON)"),
        ("L", "Carregar projeto (JSON)"),
        ("O", "Exportar malha 3D (.OBJ)"),
        ("R", "Resetar posicao da camera"),
        ("+/-", "Aumentar/diminuir escala"),
    ]
    
    y = 100
    for tecla, descricao in atalhos:
        if tecla == "":
            # Seção título
            cv2.putText(img, descricao, (w_tela // 2 - 180, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 1)
        else:
            cv2.putText(img, f"[{tecla}]", (w_tela // 2 - 250, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 200), 1)
            cv2.putText(img, descricao, (w_tela // 2 - 20, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
        y += 28
    
    cv2.putText(img, "Pressione H para fechar", (w_tela // 2 - 130, h_tela - 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)

# ==========================================
# FUNÇÕES DE SAVE, LOAD E EXPORT
# ==========================================
def salvar_projeto():
    with open('mundo_voxel.json', 'w') as f:
        json.dump(blocos, f)
    print("Projeto Salvo em mundo_voxel.json!")

def carregar_projeto():
    global blocos, mapa_alturas
    try:
        with open('mundo_voxel.json', 'r') as f:
            blocos_lidos = json.load(f)
        blocos.clear()
        mapa_alturas.clear()
        for b in blocos_lidos:
            gx, gy, gz, cor = b[0], b[1], b[2], tuple(b[3])
            blocos.append((gx, gy, gz, cor))
            # Atualiza a altura do mapa (Z máximo daquela célula + 1)
            mapa_alturas[(gx, gy)] = max(mapa_alturas.get((gx, gy), -1), gz)
        for k in mapa_alturas:
            mapa_alturas[k] += 1
        print("Projeto Carregado!")
    except FileNotFoundError:
        print("Nenhum save encontrado.")

def exportar_obj():
    filename = "voxel_art.obj"
    with open(filename, 'w') as f:
        f.write("# Exportado do Motor Voxel AR em Python\n")
        v_offset = 1
        for bloco in blocos:
            bx, by, bz, _ = bloco
            # 8 Vértices de um cubo (Tamanho 1x1x1)
            vertices = [
                (bx, by, bz), (bx+1, by, bz), (bx+1, by+1, bz), (bx, by+1, bz),
                (bx, by, bz+1), (bx+1, by, bz+1), (bx+1, by+1, bz+1), (bx, by+1, bz+1)
            ]
            for v in vertices:
                f.write(f"v {v[0]} {v[1]} {v[2]}\n")
            
            # 6 Faces do cubo (Padrão OBJ)
            faces = [
                (1, 2, 3, 4), (5, 6, 7, 8), (1, 2, 6, 5),
                (2, 3, 7, 6), (3, 4, 8, 7), (4, 1, 5, 8)
            ]
            for face in faces:
                f.write(f"f {face[0]+v_offset-1} {face[1]+v_offset-1} {face[2]+v_offset-1} {face[3]+v_offset-1}\n")
            v_offset += 8
    print(f"Malha 3D exportada para: {os.path.abspath(filename)}")

# ==========================================
# LOOP PRINCIPAL
# ==========================================
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 960)

ultimo_tempo = 0
cursor_suave_x, cursor_suave_y = None, None # Variáveis para o Anti-Jitter

# Variável compartilhada para receber resultados assíncronos
latest_result: HandLandmarkerResult | None = None

def on_result(result: HandLandmarkerResult, output_image: mp.Image, timestamp_ms: int):
    """Callback chamado pelo HandLandmarker em modo LIVE_STREAM"""
    global latest_result
    latest_result = result

# Configurar o HandLandmarker com a nova API Tasks
options = HandLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=MODEL_PATH),
    running_mode=RunningMode.LIVE_STREAM,
    num_hands=2,
    min_hand_detection_confidence=0.7,
    min_hand_presence_confidence=0.7,
    min_tracking_confidence=0.7,
    result_callback=on_result,
)

with HandLandmarker.create_from_options(options) as landmarker:
    frame_timestamp_ms = 0

    while cap.isOpened():
        success, image = cap.read()
        if not success:
            break

        image = cv2.flip(image, 1)
        h_tela, w_tela, _ = image.shape

        # Converter para RGB e criar mp.Image
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)

        # Enviar frame para processamento assíncrono
        frame_timestamp_ms += 33  # ~30 FPS
        landmarker.detect_async(mp_image, frame_timestamp_ms)

        # Desenhar Menu Flutuante
        desenhar_menu_ui(image)

        # --- Detecção de gestos por mão ---
        pinca_detectada = False
        espalmada_detectada = False
        punhos_fechados = 0  # Conta quantas mãos estão com punho fechado
        mao_guia_landmarks = None
        mao_acao_landmarks = None
        todos_landmarks = []  # Para grab & move (precisa dos pulsos)

        result = latest_result
        if result and result.hand_landmarks and result.handedness:
            for hand_landmarks, handedness in zip(result.hand_landmarks, result.handedness):
                label = handedness[0].category_name
                todos_landmarks.append((label, hand_landmarks))

                if label == 'Left':
                    mao_guia_landmarks = hand_landmarks

                    # --- Mão Guia: Cursor suave X, Y ---
                    raw_x = int(hand_landmarks[8].x * w_tela)
                    raw_y = int(hand_landmarks[8].y * h_tela)

                    if cursor_suave_x is None:
                        cursor_suave_x, cursor_suave_y = raw_x, raw_y
                    else:
                        cursor_suave_x = int(EMA_ALPHA * raw_x + (1 - EMA_ALPHA) * cursor_suave_x)
                        cursor_suave_y = int(EMA_ALPHA * raw_y + (1 - EMA_ALPHA) * cursor_suave_y)

                    # Verificar se a mão guia também faz punho (para grab & move)
                    if detectar_punho_fechado(hand_landmarks, w_tela, h_tela):
                        punhos_fechados += 1

                elif label == 'Right':
                    mao_acao_landmarks = hand_landmarks

                    # Detectar gestos na mão de ação (prioridade)
                    if detectar_punho_fechado(hand_landmarks, w_tela, h_tela):
                        punhos_fechados += 1
                    elif detectar_pinca(hand_landmarks, w_tela, h_tela):
                        pinca_detectada = True
                    elif detectar_mao_espalmada(hand_landmarks, w_tela, h_tela):
                        espalmada_detectada = True
                    elif detectar_polegar_mindinho(hand_landmarks, w_tela, h_tela):
                        # Atalho: mudar escala do bloco
                        tempo_agora = time.time()
                        if (tempo_agora - ultimo_tempo_escala) > 0.6:
                            escala_bloco = (escala_bloco % 3) + 1
                            ultimo_tempo_escala = tempo_agora
                            print(f"[Escala] Bloco: {escala_bloco}x{escala_bloco}x{escala_bloco}")
                    elif detectar_polegar_anelar(hand_landmarks, w_tela, h_tela):
                        # Atalho: trocar cor
                        tempo_agora = time.time()
                        if (tempo_agora - ultimo_tempo_cor) > 0.5:
                            indice_cor_atual = (indice_cor_atual + 1) % len(CORES_MENU)
                            cor_atual = CORES_MENU[indice_cor_atual]
                            ultimo_tempo_cor = tempo_agora
                            print(f"[Cor] Ciclada para: {cor_atual}")

        # --- Máquina de Estados: Transições ---
        estado_anterior = estado_atual

        if punhos_fechados >= 2:
            estado_atual = AppState.MOVING_MODEL
        elif pinca_detectada:
            estado_atual = AppState.BUILDING
        elif espalmada_detectada:
            estado_atual = AppState.ERASING
        else:
            estado_atual = AppState.IDLE

        # Log de transição de estado
        if estado_atual != estado_anterior:
            print(f"[Estado] {estado_anterior.value} -> {estado_atual.value}")

        # Reset de construção contínua ao sair do estado BUILDING
        if estado_atual != AppState.BUILDING:
            pinca_ativa_anterior = False
            ultima_pos_construcao = None

        # --- HUD: Estado atual + escala + dica ---
        desenhar_hud_estado(image, estado_atual, w_tela)
        cv2.putText(image, f"Escala: {escala_bloco}x", (w_tela - 250, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
        cv2.putText(image, "Pressione H para ajuda", (w_tela // 2 - 100, h_tela - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (150, 150, 150), 1)

        # --- Cursor visual com cor dependente do estado ---
        if cursor_suave_x is not None and cursor_suave_y is not None:
            cores_cursor = {
                AppState.IDLE: (255, 255, 255),
                AppState.BUILDING: (0, 255, 0),
                AppState.ERASING: (0, 0, 255),
                AppState.MOVING_MODEL: (255, 200, 0),
            }
            cor_cursor = cores_cursor.get(estado_atual, (255, 255, 255))
            cv2.circle(image, (cursor_suave_x, cursor_suave_y), 8, cor_cursor, 2)
            cv2.circle(image, (cursor_suave_x, cursor_suave_y), 4, cor_atual, -1)

        # =============================================
        # LÓGICA POR ESTADO
        # =============================================

        # --- ESTADO: MOVING_MODEL (Grab & Move) ---
        if estado_atual == AppState.MOVING_MODEL and len(todos_landmarks) >= 2:
            # Calcular ponto médio entre os pulsos das duas mãos
            pulso_coords = []
            for _, lms in todos_landmarks:
                px = int(lms[0].x * w_tela)
                py = int(lms[0].y * h_tela)
                pulso_coords.append((px, py))

            if len(pulso_coords) >= 2:
                medio_x = (pulso_coords[0][0] + pulso_coords[1][0]) // 2
                medio_y = (pulso_coords[0][1] + pulso_coords[1][1]) // 2

                if grab_ponto_medio_anterior is not None:
                    delta_x = medio_x - grab_ponto_medio_anterior[0]
                    delta_y = medio_y - grab_ponto_medio_anterior[1]
                    origem_x_dinamica += delta_x
                    origem_y_dinamica += delta_y

                grab_ponto_medio_anterior = (medio_x, medio_y)

                # Feedback visual: linha entre os punhos
                cv2.line(image, pulso_coords[0], pulso_coords[1], (255, 200, 0), 2)
                cv2.circle(image, (medio_x, medio_y), 8, (255, 200, 0), -1)
                cv2.putText(image, "GRAB & MOVE", (10, h_tela - 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 200, 0), 2)
        else:
            grab_ponto_medio_anterior = None

        # --- ESTADOS: BUILDING / ERASING / IDLE (interação com tabuleiro) ---
        if not mostrar_ajuda and estado_atual != AppState.MOVING_MODEL and cursor_suave_x is not None and cursor_suave_y is not None:
            tempo_atual = time.time()

            # Checar se a mira está em cima do Menu de Cores
            if cursor_suave_y < 60 and cursor_suave_x < (len(CORES_MENU) * 50 + 15):
                indice_cor = (cursor_suave_x - 10) // 50
                if 0 <= indice_cor < len(CORES_MENU) and estado_atual == AppState.BUILDING and (tempo_atual - ultimo_tempo) > 0.5:
                    indice_cor_atual = indice_cor
                    cor_atual = CORES_MENU[indice_cor_atual]
                    ultimo_tempo = tempo_atual
                    print(f"[Cor] Selecionada: {cor_atual}")

            # Fantasma na face adjacente + construção/exclusão
            else:
                # Encontrar posição do fantasma baseado na face mais próxima
                fantasma_pos = encontrar_posicao_fantasma(cursor_suave_x, cursor_suave_y, blocos)
                gfx, gfy, gfz = fantasma_pos

                # EFEITO DE FANTASMA TRANSPARENTE (preview na face adjacente)
                overlay = image.copy()
                if estado_atual == AppState.ERASING and blocos:
                    # Encontrar bloco mais próximo do cursor para deletar
                    melhor_bloco = None
                    melhor_dist = float('inf')
                    for b in blocos:
                        bsx, bsy = grid_para_tela(b[0], b[1], b[2])
                        d = math.hypot(cursor_suave_x - bsx, cursor_suave_y - bsy)
                        if d < melhor_dist:
                            melhor_dist = d
                            melhor_bloco = b
                    if melhor_bloco:
                        desenhar_cubo_solido(overlay, melhor_bloco[0], melhor_bloco[1], melhor_bloco[2], (0, 0, 255))
                else:
                    # Preview do bloco (com escala) a ser colocado
                    for dx in range(escala_bloco):
                        for dy in range(escala_bloco):
                            for dz in range(escala_bloco):
                                desenhar_cubo_solido(overlay, gfx + dx, gfy + dy, gfz + dz, cor_atual)

                cv2.addWeighted(overlay, 0.5, image, 0.5, 0, image)

                # --- ESTADO: BUILDING (Construção + Construção Contínua) ---
                if estado_atual == AppState.BUILDING:
                    pos_atual = (gfx, gfy, gfz)

                    if not pinca_ativa_anterior:
                        # Primeiro frame da pinça: colocar UM bloco
                        if (tempo_atual - ultimo_tempo) > 0.3:
                            colocar_bloco_com_escala(gfx, gfy, gfz, cor_atual, escala_bloco)
                            ultimo_tempo = tempo_atual
                            ultima_pos_construcao = pos_atual

                    elif ultima_pos_construcao is not None and ultima_pos_construcao != pos_atual:
                        # Construção Contínua: só ao MOVER para nova posição
                        if (tempo_atual - ultimo_tempo) > 0.15:
                            z_fixo = ultima_pos_construcao[2]
                            caminho = interpolar_linha_2d(
                                ultima_pos_construcao[0], ultima_pos_construcao[1],
                                gfx, gfy
                            )
                            for cx, cy in caminho:
                                colocar_bloco_com_escala(cx, cy, z_fixo, cor_atual, escala_bloco)
                            ultima_pos_construcao = pos_atual
                            ultimo_tempo = tempo_atual

                    # Se pinça mantida sem mover, NÃO coloca mais blocos
                    pinca_ativa_anterior = True

                # --- ESTADO: ERASING (Exclusão com mão espalmada) ---
                elif estado_atual == AppState.ERASING:
                    if (tempo_atual - ultimo_tempo) > 0.3 and blocos:
                        # Encontrar bloco mais próximo do cursor
                        melhor_bloco = None
                        melhor_dist = float('inf')
                        for b in blocos:
                            bsx, bsy = grid_para_tela(b[0], b[1], b[2])
                            d = math.hypot(cursor_suave_x - bsx, cursor_suave_y - bsy)
                            if d < melhor_dist:
                                melhor_dist = d
                                melhor_bloco = b
                        if melhor_bloco and melhor_dist < 60:
                            bx, by, bz = melhor_bloco[0], melhor_bloco[1], melhor_bloco[2]
                            blocos = [b for b in blocos if not (b[0] == bx and b[1] == by and b[2] == bz)]
                            # Atualizar mapa de alturas
                            max_z = -1
                            for b in blocos:
                                if b[0] == bx and b[1] == by:
                                    max_z = max(max_z, b[2])
                            mapa_alturas[(bx, by)] = max_z + 1 if max_z >= 0 else 0
                            ultimo_tempo = tempo_atual
                            print(f"[Apagar] Bloco ({bx}, {by}, {bz}) removido")

                    cv2.putText(image, "MAO ESPALMADA: APAGANDO", (10, h_tela - 20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        # Renderizar Blocos Salvos
        blocos_ordenados = sorted(blocos, key=lambda b: (b[2], b[0] + b[1]))
        for bloco in blocos_ordenados:
            desenhar_cubo_solido(image, bloco[0], bloco[1], bloco[2], bloco[3])

        # Tela de ajuda (por cima de tudo)
        if mostrar_ajuda:
            desenhar_tela_ajuda(image, w_tela, h_tela)

        cv2.imshow('Construtor de Voxel AR', image)
        
        # Mapeamento de Teclas
        tecla = cv2.waitKey(5) & 0xFF
        if tecla == 27: # ESC
            break
        elif tecla == ord('h') or tecla == ord('H'):
            mostrar_ajuda = not mostrar_ajuda
            print(f"[Ajuda] {'Aberta' if mostrar_ajuda else 'Fechada'}")
        elif tecla == ord('c') or tecla == ord('C'):
            blocos.clear()
            mapa_alturas.clear()
            print("[Limpar] Todos os blocos removidos")
        elif tecla == ord('s') or tecla == ord('S'):
            salvar_projeto()
        elif tecla == ord('l') or tecla == ord('L'):
            carregar_projeto()
        elif tecla == ord('o') or tecla == ord('O'):
            exportar_obj()
        elif tecla == ord('r') or tecla == ord('R'):
            origem_x_dinamica = ORIGEM_X
            origem_y_dinamica = ORIGEM_Y
            print("[Reset] Posição da câmera restaurada")
        elif tecla == ord('+') or tecla == ord('='):
            escala_bloco = min(3, escala_bloco + 1)
            print(f"[Escala] Bloco: {escala_bloco}x")
        elif tecla == ord('-') or tecla == ord('_'):
            escala_bloco = max(1, escala_bloco - 1)
            print(f"[Escala] Bloco: {escala_bloco}x")

cap.release()
cv2.destroyAllWindows()
