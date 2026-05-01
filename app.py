"""
AR Voxel Builder — Versão Web (Streamlit + WebRTC)
Deploy: Hugging Face Spaces (Streamlit SDK)
"""
import streamlit as st
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, WebRtcMode
import av
import cv2
import numpy as np
import math
import json
import os
import urllib.request
import threading
import logging
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (
    HandLandmarker, HandLandmarkerOptions, RunningMode,
)

# ==========================================
# CONFIGURAÇÕES
# ==========================================
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hand_landmarker.task")

LARGURA_BLOCO = 40
ALTURA_BLOCO = 20
ORIGEM_X = 320
ORIGEM_Y = 280

CORES_MENU = [
    (0, 200, 0), (0, 0, 200), (200, 0, 0),
    (0, 200, 200), (200, 0, 200), (200, 200, 200)
]
NOMES_CORES = ["Verde", "Vermelho", "Azul", "Amarelo", "Magenta", "Branco"]

def ensure_model():
    if not os.path.exists(MODEL_PATH):
        st.info("Baixando modelo MediaPipe Hand Landmarker (~7MB)...")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)

def get_ice_servers():
    """Busca servidores ICE (TURN+STUN) do Twilio para WebRTC.
    Configure os secrets TWILIO_ACCOUNT_SID e TWILIO_AUTH_TOKEN
    nas configurações do HuggingFace Space (Settings > Secrets).
    """
    try:
        account_sid = st.secrets["TWILIO_ACCOUNT_SID"]
        auth_token = st.secrets["TWILIO_AUTH_TOKEN"]
        from twilio.rest import Client
        client = Client(account_sid, auth_token)
        token = client.tokens.create()
        return token.ice_servers
    except Exception as e:
        st.warning(f"⚠️ TURN não configurado ({e}). Usando apenas STUN — a conexão pode falhar.")
        return [{"urls": ["stun:stun.l.google.com:19302"]}]

# ==========================================
# FUNÇÕES DE RENDERIZAÇÃO (mesmo do main.py)
# ==========================================
def grid_para_tela(gx, gy, gz, ox, oy):
    tx = ox + (gx - gy) * (LARGURA_BLOCO // 2)
    ty = oy + (gx + gy) * (ALTURA_BLOCO // 2) - (gz * ALTURA_BLOCO)
    return tx, ty

def tela_para_grid(tx, ty, ox, oy):
    dx = tx - ox
    dy = ty - oy
    gx = (dx / (LARGURA_BLOCO / 2) + dy / (ALTURA_BLOCO / 2)) / 2
    gy = (dy / (ALTURA_BLOCO / 2) - dx / (LARGURA_BLOCO / 2)) / 2
    return int(round(gx)), int(round(gy))

def desenhar_cubo(img, gx, gy, gz, cor, ox, oy):
    cx, cy = grid_para_tela(gx, gy, gz, ox, oy)
    w, h = LARGURA_BLOCO, ALTURA_BLOCO
    topo = np.array([[cx,cy-h],[cx+w//2,cy-h//2],[cx,cy],[cx-w//2,cy-h//2]], np.int32)
    esq = np.array([[cx-w//2,cy-h//2],[cx,cy],[cx,cy+h],[cx-w//2,cy+h-h//2]], np.int32)
    dir_ = np.array([[cx,cy],[cx+w//2,cy-h//2],[cx+w//2,cy+h-h//2],[cx,cy+h]], np.int32)
    b, g, r = cor
    cv2.fillPoly(img, [topo], (min(255,b+50),min(255,g+50),min(255,r+50)))
    cv2.fillPoly(img, [esq], cor)
    cv2.fillPoly(img, [dir_], (max(0,b-50),max(0,g-50),max(0,r-50)))
    cv2.polylines(img, [topo,esq,dir_], True, (50,50,50), 1)

# ==========================================
# DETECÇÃO DE GESTOS
# ==========================================
def detectar_pinca(lm, w, h):
    return math.hypot(lm[8].x*w - lm[4].x*w, lm[8].y*h - lm[4].y*h) < 40

def detectar_espalmada(lm, w, h):
    pares = [(8,6),(12,10),(16,14),(20,18)]
    abertos = sum(1 for t,p in pares if lm[t].y < lm[p].y)
    if abs(lm[4].x - lm[0].x) > abs(lm[3].x - lm[0].x):
        abertos += 1
    return abertos == 5

def detectar_punho(lm, w, h):
    pares = [(8,5),(12,9),(16,13),(20,17)]
    fechados = sum(1 for t,m in pares if lm[t].y > lm[m].y)
    if abs(lm[4].x - lm[0].x) < abs(lm[3].x - lm[0].x):
        fechados += 1
    return fechados >= 4

def encontrar_fantasma(cx, cy, blocos, ox, oy):
    if not blocos:
        gx, gy = tela_para_grid(cx, cy, ox, oy)
        return (gx, gy, 0)
    ocupadas = {(b[0],b[1],b[2]) for b in blocos}
    melhor_d, melhor_p = float('inf'), None
    for b in blocos:
        bx, by, bz = b[0], b[1], b[2]
        scx, scy = grid_para_tela(bx, by, bz, ox, oy)
        w, h = LARGURA_BLOCO, ALTURA_BLOCO
        for fcx,fcy,nx,ny,nz in [
            (scx, scy-h, bx, by, bz+1),
            (scx-w//4, scy+h//4, bx-1, by, bz),
            (scx+w//4, scy+h//4, bx, by-1, bz),
            (scx+w//4, scy-h//4, bx+1, by, bz),
            (scx-w//4, scy-h//4, bx, by+1, bz),
        ]:
            if (nx,ny,nz) in ocupadas or nz < 0:
                continue
            d = math.hypot(cx-fcx, cy-fcy)
            if d < melhor_d:
                melhor_d, melhor_p = d, (nx,ny,nz)
    if melhor_p is None:
        gx, gy = tela_para_grid(cx, cy, ox, oy)
        return (gx, gy, 0)
    return melhor_p

# ==========================================
# PROCESSADOR DE VÍDEO
# ==========================================
class VoxelProcessor(VideoProcessorBase):
    def __init__(self):
        self.blocos = []
        self.mapa_alturas = {}
        self.cor_atual = CORES_MENU[0]
        self.escala = 1
        self.ox = ORIGEM_X
        self.oy = ORIGEM_Y
        self.cursor_x = None
        self.cursor_y = None
        self.pinca_anterior = False
        self.ultima_pos = None
        self.EMA = 0.3
        self._lock = threading.Lock()
        self._clear_flag = False
        self._reset_flag = False

        opts = HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=MODEL_PATH),
            running_mode=RunningMode.IMAGE,
            num_hands=2,
            min_hand_detection_confidence=0.6,
            min_hand_presence_confidence=0.6,
            min_tracking_confidence=0.6,
        )
        self.landmarker = HandLandmarker.create_from_options(opts)

    def _colocar(self, gx, gy, gz):
        with self._lock:
            for dx in range(self.escala):
                for dy in range(self.escala):
                    for dz in range(self.escala):
                        nx, ny, nz = gx+dx, gy+dy, gz+dz
                        if not any(b[0]==nx and b[1]==ny and b[2]==nz for b in self.blocos):
                            self.blocos.append((nx,ny,nz,self.cor_atual))
                            self.mapa_alturas[(nx,ny)] = max(self.mapa_alturas.get((nx,ny),0), nz+1)

    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        img = frame.to_ndarray(format="bgr24")
        img = cv2.flip(img, 1)
        ht, wt, _ = img.shape

        # Flags de controle
        if self._clear_flag:
            with self._lock:
                self.blocos.clear()
                self.mapa_alturas.clear()
            self._clear_flag = False
        if self._reset_flag:
            self.ox, self.oy = ORIGEM_X, ORIGEM_Y
            self._reset_flag = False

        # MediaPipe
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self.landmarker.detect(mp_img)

        pinca = False
        espalm = False
        punhos = 0

        if result.hand_landmarks and result.handedness:
            all_lm = []
            for lm, hd in zip(result.hand_landmarks, result.handedness):
                label = hd[0].category_name
                all_lm.append((label, lm))
                if label == 'Left':
                    rx = int(lm[8].x * wt)
                    ry = int(lm[8].y * ht)
                    if self.cursor_x is None:
                        self.cursor_x, self.cursor_y = rx, ry
                    else:
                        self.cursor_x = int(self.EMA*rx + (1-self.EMA)*self.cursor_x)
                        self.cursor_y = int(self.EMA*ry + (1-self.EMA)*self.cursor_y)
                    if detectar_punho(lm, wt, ht):
                        punhos += 1
                elif label == 'Right':
                    if detectar_punho(lm, wt, ht):
                        punhos += 1
                    elif detectar_pinca(lm, wt, ht):
                        pinca = True
                    elif detectar_espalmada(lm, wt, ht):
                        espalm = True

            # Grab & Move
            if punhos >= 2 and len(all_lm) >= 2:
                coords = [(int(l[0].x*wt), int(l[0].y*ht)) for _,l in all_lm]
                mx = (coords[0][0]+coords[1][0])//2
                my = (coords[0][1]+coords[1][1])//2
                cv2.line(img, coords[0], coords[1], (255,200,0), 2)
                cv2.circle(img, (mx,my), 6, (255,200,0), -1)

        # Estado
        estado = "IDLE"
        if punhos >= 2: estado = "MOVENDO"
        elif pinca: estado = "CONSTRUINDO"
        elif espalm: estado = "APAGANDO"

        if estado != "CONSTRUINDO":
            self.pinca_anterior = False
            self.ultima_pos = None

        # HUD
        cores_e = {"IDLE":(180,180,180),"CONSTRUINDO":(0,255,0),"APAGANDO":(0,0,255),"MOVENDO":(255,200,0)}
        cv2.rectangle(img, (wt-200,5), (wt-5,35), (30,30,30), -1)
        cv2.putText(img, estado, (wt-195,28), cv2.FONT_HERSHEY_SIMPLEX, 0.5, cores_e[estado], 2)
        cv2.putText(img, f"Escala: {self.escala}x", (wt-200,55), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200,200,200), 1)

        # Cursor
        if self.cursor_x is not None:
            cc = cores_e.get(estado, (255,255,255))
            cv2.circle(img, (self.cursor_x, self.cursor_y), 8, cc, 2)
            cv2.circle(img, (self.cursor_x, self.cursor_y), 4, self.cor_atual, -1)

        # Lógica
        if estado != "MOVENDO" and self.cursor_x is not None:
            with self._lock:
                fantasma = encontrar_fantasma(self.cursor_x, self.cursor_y, self.blocos, self.ox, self.oy)
            gfx, gfy, gfz = fantasma

            overlay = img.copy()
            if estado == "APAGANDO" and self.blocos:
                mb, md = None, float('inf')
                for b in self.blocos:
                    sx, sy = grid_para_tela(b[0],b[1],b[2], self.ox, self.oy)
                    d = math.hypot(self.cursor_x-sx, self.cursor_y-sy)
                    if d < md: md, mb = d, b
                if mb:
                    desenhar_cubo(overlay, mb[0],mb[1],mb[2], (0,0,255), self.ox, self.oy)
            else:
                for dx in range(self.escala):
                    for dy in range(self.escala):
                        for dz in range(self.escala):
                            desenhar_cubo(overlay, gfx+dx,gfy+dy,gfz+dz, self.cor_atual, self.ox, self.oy)
            cv2.addWeighted(overlay, 0.5, img, 0.5, 0, img)

            if estado == "CONSTRUINDO":
                pos = (gfx, gfy, gfz)
                if not self.pinca_anterior:
                    self._colocar(gfx, gfy, gfz)
                    self.ultima_pos = pos
                elif self.ultima_pos and self.ultima_pos != pos:
                    self._colocar(gfx, gfy, gfz)
                    self.ultima_pos = pos
                self.pinca_anterior = True

            elif estado == "APAGANDO" and self.blocos:
                mb, md = None, float('inf')
                for b in self.blocos:
                    sx, sy = grid_para_tela(b[0],b[1],b[2], self.ox, self.oy)
                    d = math.hypot(self.cursor_x-sx, self.cursor_y-sy)
                    if d < md: md, mb = d, b
                if mb and md < 60:
                    with self._lock:
                        bx,by,bz = mb[0],mb[1],mb[2]
                        self.blocos = [b for b in self.blocos if not(b[0]==bx and b[1]==by and b[2]==bz)]
                        mz = max((b[2] for b in self.blocos if b[0]==bx and b[1]==by), default=-1)
                        self.mapa_alturas[(bx,by)] = mz+1 if mz>=0 else 0

        # Renderizar blocos
        with self._lock:
            for b in sorted(self.blocos, key=lambda b:(b[2],b[0]+b[1])):
                desenhar_cubo(img, b[0],b[1],b[2], b[3], self.ox, self.oy)

        return av.VideoFrame.from_ndarray(img, format="bgr24")

    def get_blocos_json(self):
        with self._lock:
            return json.dumps(self.blocos)

    def load_blocos_json(self, data):
        with self._lock:
            self.blocos.clear()
            self.mapa_alturas.clear()
            for b in data:
                gx,gy,gz,cor = b[0],b[1],b[2],tuple(b[3])
                self.blocos.append((gx,gy,gz,cor))
                self.mapa_alturas[(gx,gy)] = max(self.mapa_alturas.get((gx,gy),0), gz+1)

# ==========================================
# INTERFACE STREAMLIT
# ==========================================
st.set_page_config(page_title="AR Voxel Builder", page_icon="🧱", layout="wide")
ensure_model()

st.title("🖐️ AR Voxel Builder")
st.caption("Construa estruturas 3D com gestos de mão em tempo real")

col1, col2 = st.columns([3, 1])

with col2:
    st.header("🎮 Controles")

    st.subheader("🎨 Cor")
    cor_idx = st.radio("Selecione:", range(len(NOMES_CORES)),
                       format_func=lambda i: NOMES_CORES[i], horizontal=True)

    st.subheader("📐 Escala")
    escala = st.radio("Tamanho:", [1,2,3], format_func=lambda x: f"{x}×{x}×{x}", horizontal=True)

    st.subheader("⚡ Ações")
    btn_clear = st.button("🗑️ Limpar Tudo", use_container_width=True)
    btn_reset = st.button("🔄 Reset Câmera", use_container_width=True)

    st.subheader("💾 Salvar / Carregar")
    btn_download = st.empty()
    uploaded = st.file_uploader("Carregar projeto (.json)", type="json")

    st.divider()
    st.subheader("📖 Gestos")
    st.markdown("""
    | Gesto | Ação |
    |---|---|
    | 👌 Pinça | Colocar bloco |
    | ✋ Mão aberta | Apagar bloco |
    | ✊✊ Dois punhos | Mover tudo |
    """)

with col1:
    ctx = webrtc_streamer(
        key="voxel-builder",
        video_processor_factory=VoxelProcessor,
        rtc_configuration={"iceServers": get_ice_servers()},
        media_stream_constraints={"video": {"width": 640, "height": 480}, "audio": False},
        async_processing=True,
    )

# Sincronizar controles com o processador
if ctx.video_processor:
    ctx.video_processor.cor_atual = CORES_MENU[cor_idx]
    ctx.video_processor.escala = escala
    if btn_clear:
        ctx.video_processor._clear_flag = True
    if btn_reset:
        ctx.video_processor._reset_flag = True
    if uploaded:
        data = json.load(uploaded)
        ctx.video_processor.load_blocos_json(data)

    # Botão de download
    json_data = ctx.video_processor.get_blocos_json()
    btn_download.download_button("📥 Baixar Projeto", data=json_data,
                                  file_name="mundo_voxel.json", mime="application/json",
                                  use_container_width=True)
