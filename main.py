import cv2
import mediapipe as mp
import numpy as np
import math
import time
import json
import os

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
# FUNÇÕES DE RENDERIZAÇÃO
# ==========================================
def grid_para_tela(gx, gy, gz):
    tela_x = ORIGEM_X + (gx - gy) * (LARGURA_BLOCO // 2)
    tela_y = ORIGEM_Y + (gx + gy) * (ALTURA_BLOCO // 2) - (gz * ALTURA_BLOCO)
    return tela_x, tela_y

def tela_para_grid(tela_x, tela_y):
    dx = tela_x - ORIGEM_X
    dy = tela_y - ORIGEM_Y
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

        # Desenhar Chão
        for gx in range(TAMANHO_MATRIZ):
            for gy in range(TAMANHO_MATRIZ):
                desenhar_cubo_solido(image, gx, gy, -1, (200, 200, 200))

        # Desenhar Menu Flutuante
        desenhar_menu_ui(image)

        acao_adicionar = False
        acao_remover = False

        # Processar resultados do HandLandmarker
        result = latest_result
        if result and result.hand_landmarks and result.handedness:
            for hand_landmarks, handedness in zip(result.hand_landmarks, result.handedness):
                label = handedness[0].category_name

                # Converter landmarks normalizados para coordenadas de tela
                if label == 'Left':
                    raw_x = int(hand_landmarks[8].x * w_tela)
                    raw_y = int(hand_landmarks[8].y * h_tela)
                    
                    # Filtro EMA (Anti-Jitter) para deixar a mira suave
                    if cursor_suave_x is None:
                        cursor_suave_x, cursor_suave_y = raw_x, raw_y
                    else:
                        cursor_suave_x = int(0.3 * raw_x + 0.7 * cursor_suave_x)
                        cursor_suave_y = int(0.3 * raw_y + 0.7 * cursor_suave_y)
                    
                    cv2.circle(image, (cursor_suave_x, cursor_suave_y), 6, (255, 255, 255), -1)
                    cv2.circle(image, (cursor_suave_x, cursor_suave_y), 4, cor_atual, -1)

                elif label == 'Right':
                    x_pol = int(hand_landmarks[4].x * w_tela)
                    y_pol = int(hand_landmarks[4].y * h_tela)
                    x_ind = int(hand_landmarks[8].x * w_tela)
                    y_ind = int(hand_landmarks[8].y * h_tela)
                    x_med = int(hand_landmarks[12].x * w_tela)
                    y_med = int(hand_landmarks[12].y * h_tela)
                    
                    if math.hypot(x_ind - x_pol, y_ind - y_pol) < 40:
                        acao_adicionar = True
                        cv2.putText(image, "Acao: ADICIONAR", (10, h_tela - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    elif math.hypot(x_med - x_pol, y_med - y_pol) < 40:
                        acao_remover = True
                        cv2.putText(image, "Acao: DELETAR", (10, h_tela - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        # Lógica do Tabuleiro e Menu
        if cursor_suave_x is not None and cursor_suave_y is not None:
            tempo_atual = time.time()
            
            # Checar se a mira está em cima do Menu de Cores
            if cursor_suave_y < 60 and cursor_suave_x < (len(CORES_MENU) * 50 + 15):
                indice_cor = (cursor_suave_x - 10) // 50
                if 0 <= indice_cor < len(CORES_MENU) and acao_adicionar and (tempo_atual - ultimo_tempo) > 0.5:
                    cor_atual = CORES_MENU[indice_cor]
                    ultimo_tempo = tempo_atual
            
            # Se não está no menu, checar Tabuleiro
            else:
                grid_x, grid_y = tela_para_grid(cursor_suave_x, cursor_suave_y)
                
                if 0 <= grid_x < TAMANHO_MATRIZ and 0 <= grid_y < TAMANHO_MATRIZ:
                    altura_atual = mapa_alturas.get((grid_x, grid_y), 0)
                    
                    # EFEITO DE FANTASMA TRANSPARENTE
                    overlay = image.copy()
                    if acao_remover and altura_atual > 0:
                        desenhar_cubo_solido(overlay, grid_x, grid_y, altura_atual - 1, (0, 0, 255)) # Destaca o bloco a ser deletado em vermelho
                    elif altura_atual < TAMANHO_MATRIZ:
                        desenhar_cubo_solido(overlay, grid_x, grid_y, altura_atual, cor_atual)
                    
                    cv2.addWeighted(overlay, 0.5, image, 0.5, 0, image) # Aplica 50% de opacidade
                    
                    # LOGICA DE CLIQUES
                    if (tempo_atual - ultimo_tempo) > 0.4:
                        if acao_adicionar and altura_atual < TAMANHO_MATRIZ:
                            blocos.append((grid_x, grid_y, altura_atual, cor_atual)) 
                            mapa_alturas[(grid_x, grid_y)] = altura_atual + 1
                            ultimo_tempo = tempo_atual
                        
                        elif acao_remover and altura_atual > 0:
                            z_alvo = altura_atual - 1
                            blocos = [b for b in blocos if not (b[0] == grid_x and b[1] == grid_y and b[2] == z_alvo)]
                            mapa_alturas[(grid_x, grid_y)] = z_alvo
                            ultimo_tempo = tempo_atual

        # Renderizar Blocos Salvos
        blocos_ordenados = sorted(blocos, key=lambda b: (b[2], b[0] + b[1]))
        for bloco in blocos_ordenados:
            desenhar_cubo_solido(image, bloco[0], bloco[1], bloco[2], bloco[3])

        cv2.imshow('Construtor de Voxel AR', image)
        
        # Mapeamento de Teclas
        tecla = cv2.waitKey(5) & 0xFF
        if tecla == 27: # ESC
            break
        elif tecla == ord('c') or tecla == ord('C'):
            blocos.clear()
            mapa_alturas.clear()
        elif tecla == ord('s') or tecla == ord('S'):
            salvar_projeto()
        elif tecla == ord('l') or tecla == ord('L'):
            carregar_projeto()
        elif tecla == ord('o') or tecla == ord('O'):
            exportar_obj()

cap.release()
cv2.destroyAllWindows()
