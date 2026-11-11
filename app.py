"""
CYBER ANALYST SOC - Deepfake Audit
Módulo 1: Generación de voz sintética (vishing)
Módulo 2: El Ojo y Oído Crítico (análisis de evidencias)
Módulo 3: Simulador de Vishing en Tiempo Real (prueba de estrés)

Estructura del repositorio para Streamlit Cloud:
    app.py
    requirements.txt
    packages.txt            (ffmpeg, para extraer el audio de los videos)
    assets/
        caso1.mp4
        caso2.mp4
        caso3.mp4           <- cuando lo tengas (Módulo 2)
        audio1.mp3          <- Módulo 3, ronda 1
        audio2.mp3          <- Módulo 3, ronda 2
        audio3.mp3          <- Módulo 3, ronda 3
        audio4.mp3          <- Módulo 3, despedida
        sound.mp4           <- Módulo 3, tono de llamada entrante
        foto.jpg            <- Módulo 3, avatar de la llamada
"""
import asyncio
import base64
import io
import os
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
from datetime import datetime

import edge_tts
import numpy as np
import plotly.graph_objects as go
import requests
import streamlit as st
import streamlit.components.v1 as components
from fpdf import FPDF
from scipy import signal
from scipy.io import wavfile

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODULES = ["Módulo 1 · Vishing", "Módulo 2 · Ojo y Oído Crítico",
           "Módulo 3 · Simulador en Tiempo Real", "Módulo 4 · Protocolo Anti-Suplantación"]
TOTAL_CASOS_PLANEADOS = 3

st.set_page_config(
    page_title="Cyber Analyst SOC - Deepfake Audit",
    page_icon="🛡️",
    layout="wide",
)

# =========================================================
# ESTILO (neón + legibilidad + hotspots + botón flotante)
# =========================================================
st.markdown("""
<style>
.stApp { background-color: #0b0f19; color: #e0e6ed; }
[data-testid="stSidebar"] { background-color: #0d1320; }

h1, h2, h3 {
    color: #00f3ff !important;
    font-family: 'Courier New', monospace;
    text-shadow: 0 0 10px rgba(0, 243, 255, 0.5);
}

/* Etiquetas en gris claro */
[data-testid="stWidgetLabel"] p,
.stApp label p { color: #cbd5e1 !important; font-size: 0.95rem !important; }

.stTextArea textarea, .stTextInput input {
    background-color: #0d1b2a !important;
    color: #e5e7eb !important;
    -webkit-text-fill-color: #e5e7eb !important;
    border: 1px solid rgba(0, 243, 255, 0.4) !important;
}
div[data-baseweb="select"] > div {
    background-color: #0d1b2a !important;
    color: #e5e7eb !important;
    border: 1px solid rgba(0, 243, 255, 0.4) !important;
}
div[data-baseweb="select"] span,
div[data-baseweb="select"] div { color: #e5e7eb !important; }
div[data-baseweb="select"] svg { fill: #00f3ff !important; }
[data-testid="stAlert"] p { color: #e5e7eb !important; }
[data-testid="stCaptionContainer"] { color: #94a3b8 !important; }

.cyber-card {
    background: #111827;
    border: 1px solid #00f3ff;
    border-radius: 8px;
    padding: 16px 20px;
    box-shadow: 0 0 15px rgba(0, 243, 255, 0.15);
    margin-bottom: 16px;
}

.stButton>button {
    background-color: #0d1b2a;
    color: #00f3ff;
    border: 1px solid #00f3ff;
    border-radius: 4px;
    padding: 10px 24px;
    font-weight: bold;
    font-family: 'Courier New', monospace;
    transition: all 0.3s ease;
    box-shadow: 0 0 8px rgba(0, 243, 255, 0.3);
}
.stButton>button:hover:not(:disabled) {
    background-color: #00f3ff;
    color: #0b0f19;
    box-shadow: 0 0 20px rgba(0, 243, 255, 0.8);
}
.stButton>button:disabled { opacity: 0.4; }

.status-badge {
    display: inline-block; padding: 4px 12px; border-radius: 12px;
    font-size: 0.85rem; font-weight: bold;
}
.status-active {
    background-color: rgba(0, 255, 157, 0.2); color: #00ff9d;
    border: 1px solid #00ff9d;
}

/* ---------- Títulos con hotspot ---------- */
.titulo { display: flex; align-items: center; gap: 6px; margin: 14px 0 6px 0; }
.titulo h3 { margin: 0; padding: 0; }

/* ---------- Hotspot "?" parpadeante ---------- */
.hint { position: relative; display: inline-block; }
.hint summary {
    list-style: none; cursor: pointer;
    width: 22px; height: 22px; border-radius: 50%;
    background: #00f3ff; color: #0b0f19;
    font: bold 14px 'Courier New', monospace;
    display: flex; align-items: center; justify-content: center;
    animation: hint-pulse 1.8s infinite;
}
.hint summary::-webkit-details-marker { display: none; }
.hint[open] summary { animation: none; background: #00ff9d; }
.hint.quiet summary { animation: none; opacity: .6; }
.hint .tip {
    position: absolute; z-index: 9999; top: 30px; left: 0; width: 320px;
    background: #111827; border: 1px solid #00f3ff; border-radius: 8px;
    padding: 12px; font: normal 0.85rem sans-serif; color: #e5e7eb;
    text-shadow: none; box-shadow: 0 0 15px rgba(0,243,255,.3);
}
.hint.r .tip { left: auto; right: 0; }
.hint .tip b { color: #00f3ff; }
@keyframes hint-pulse {
    0%   { box-shadow: 0 0 0 0 rgba(0,243,255,.7); }
    70%  { box-shadow: 0 0 0 10px rgba(0,243,255,0); }
    100% { box-shadow: 0 0 0 0 rgba(0,243,255,0); }
}

/* ---------- Botón flotante abajo a la derecha (navegación entre módulos) ---------- */
.st-key-next_module,
.st-key-m2_to_m3 {
    position: fixed; bottom: 28px; right: 32px; z-index: 1000;
    width: auto !important;
}
.st-key-next_module button,
.st-key-m2_to_m3 button { animation: hint-pulse 1.8s infinite; }

/* ---------- Barra superior de Streamlit (encabezado y Despliegue) ---------- */
header[data-testid="stHeader"],
[data-testid="stHeader"] {
    background-color: #0b0f19 !important;
    border-bottom: 1px solid rgba(0, 243, 255, 0.25);
}
[data-testid="stToolbar"] *,
[data-testid="stAppDeployButton"] *,
[data-testid="stMainMenu"] * {
    color: #00f3ff !important;
}
[data-testid="stMainMenu"] svg,
[data-testid="stToolbar"] svg {
    fill: #00f3ff !important;
}

/* ---------- Expander "Herramientas del presentador" ---------- */
[data-testid="stExpander"] {
    background-color: #111827 !important;
    border: 1px solid rgba(0, 243, 255, 0.4) !important;
    border-radius: 8px;
}
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary p,
[data-testid="stExpander"] summary span {
    color: #ffffff !important;
    font-weight: bold !important;
    opacity: 1 !important;
}
[data-testid="stExpander"] summary svg {
    fill: #00f3ff !important;
    color: #00f3ff !important;
}

/* ---------- Módulo 3 · Llamada simulada ---------- */
.m3-ring-card { text-align: center; padding: 20px 0; }
.m3-avatar {
    width: 150px; height: 150px; border-radius: 50%; margin: 0 auto 14px auto;
    overflow: hidden; border: 3px solid #00f3ff;
    animation: m3-pulse 1.6s infinite;
}
.m3-avatar img { width: 100%; height: 100%; object-fit: cover; display: block; }
.m3-nombre { color: #e5e7eb; font-size: 22px; font-weight: bold; font-family: 'Courier New', monospace; }
.m3-subtexto { color: #94a3b8; font-size: 14px; margin-top: 4px; }
@keyframes m3-pulse {
    0%   { box-shadow: 0 0 0 0 rgba(0,243,255,.6); }
    70%  { box-shadow: 0 0 0 18px rgba(0,243,255,0); }
    100% { box-shadow: 0 0 0 0 rgba(0,243,255,0); }
}
.m3-incidente, .m3-exito {
    text-align: center; padding: 24px; border-radius: 8px; margin-bottom: 16px;
}
.m3-incidente { background: rgba(255,60,90,0.12); border: 1px solid #ff3c5a; }
.m3-incidente h2, .m3-incidente h3 {
    color: #ff3c5a !important; text-shadow: 0 0 10px rgba(255,60,90,.5); margin: 4px 0;
}
.m3-exito { background: rgba(0,255,157,0.12); border: 1px solid #00ff9d; }
.m3-exito h2, .m3-exito h3 {
    color: #00ff9d !important; text-shadow: 0 0 10px rgba(0,255,157,.5); margin: 4px 0;
}
</style>
""", unsafe_allow_html=True)


# =========================================================
# ESTADO GLOBAL
# =========================================================
st.session_state.setdefault("uid", uuid.uuid4().hex)
st.session_state.setdefault("m1_done", False)
st.session_state.setdefault("cases", {})
st.session_state.setdefault("module_nav", MODULES[0])
st.session_state.setdefault("learning", True)
st.session_state.setdefault("caso_actual", 0)
st.session_state.setdefault("m3_phase", "ringing")
st.session_state.setdefault("m3_round", 0)
st.session_state.setdefault("m3_resultados", [])
st.session_state.setdefault("m3_incidente", None)


@st.cache_resource
def get_store():
    """Almacén compartido entre todas las sesiones (se pierde si la app se reinicia)."""
    return {"lock": threading.Lock(), "votes": {}}


# =========================================================
# AYUDANTES DE INTERFAZ
# =========================================================
def hint(title, text, pulsing=True, align="left"):
    """Bolita '?' con tip desplegable. Devuelve '' si el modo aprendizaje está apagado."""
    if not st.session_state.get("learning", True):
        return ""
    cls = "hint" + ("" if pulsing else " quiet") + (" r" if align == "right" else "")
    return (f'<details class="{cls}"><summary>?</summary>'
            f'<div class="tip"><b>{title}</b><br>{text}</div></details>')


def titulo(texto, hint_html=""):
    st.markdown(f'<div class="titulo"><h3>{texto}</h3>{hint_html}</div>',
                unsafe_allow_html=True)


def html_embed(html, height, key=None):
    """st.iframe en versiones nuevas de Streamlit; components.html en las antiguas.
    'key' da una identidad estable al componente entre reruns, para que Streamlit
    no confunda un iframe con otro al cambiar de módulo (evita errores de
    reconciliación tipo 'removeChild' y contenido que se queda pegado)."""
    if hasattr(st, "iframe"):
        try:
            st.iframe(html, height=height, key=key)
        except TypeError:
            st.iframe(html, height=height)
    else:
        try:
            components.html(html, height=height, key=key)
        except TypeError:
            components.html(html, height=height)


@st.cache_data(show_spinner=False)
def load_b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


# =========================================================
# MÓDULO 1 · MOTORES DE VOZ
# =========================================================
EDGE_VOICES = {
    "Dalia (México, femenina)": "es-MX-DaliaNeural",
    "Jorge (México, masculina)": "es-MX-JorgeNeural",
    "Elvira (España, femenina)": "es-ES-ElviraNeural",
    "Álvaro (España, masculina)": "es-ES-AlvaroNeural",
}


async def _edge_stream(text, voice, rate):
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    audio = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio += chunk["data"]
    return audio


def generate_gtts_audio(text, lang="es"):
    from gtts import gTTS
    fp = io.BytesIO()
    gTTS(text=text, lang=lang).write_to_fp(fp)
    return fp.getvalue()


def generate_edge_audio(text, voice, rate="+0%"):
    """Voz neuronal gratuita. Si el servicio falla (a veces pasa en la nube), cae a gTTS."""
    try:
        audio = asyncio.run(_edge_stream(text, voice, rate))
        if audio:
            return audio, None, False
        raise RuntimeError("sin audio")
    except Exception as e:
        try:
            return generate_gtts_audio(text), None, True
        except Exception as e2:
            return None, f"edge-tts: {e} | gTTS: {e2}", False


def generate_elevenlabs_audio(text, api_key, voice_id):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {"Accept": "audio/mpeg", "Content-Type": "application/json",
               "xi-api-key": api_key}
    data = {"text": text, "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}}
    r = requests.post(url, json=data, headers=headers, timeout=60)
    if r.status_code == 200:
        return r.content, None
    return None, f"Error {r.status_code}: {r.text}"


WAVE_PLAYER_HTML = """
<div style="background:#111827;border-radius:8px;padding:10px;font-family:'Courier New',monospace;">
  <div style="color:#00f3ff;font-weight:bold;font-size:14px;margin-bottom:6px;
              text-shadow:0 0 8px rgba(0,243,255,.5);">
    FRECUENCIA Y PATRÓN DE ONDA SINTÉTICA
  </div>
  <canvas id="c" width="900" height="200" style="width:100%;height:200px;display:block;"></canvas>
  <audio id="a" controls style="width:100%;margin-top:10px;"></audio>
</div>
<script>
  const b64 = "__AUDIO__";
  const bytes = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
  const audio = document.getElementById("a");
  audio.src = URL.createObjectURL(new Blob([bytes], {type: "audio/mpeg"}));
  const canvas = document.getElementById("c");
  const ctx = canvas.getContext("2d");
  let actx = null, analyser = null, data = null;
  function setup() {
    if (actx) return;
    actx = new (window.AudioContext || window.webkitAudioContext)();
    analyser = actx.createAnalyser();
    analyser.fftSize = 2048;
    const src = actx.createMediaElementSource(audio);
    src.connect(analyser);
    analyser.connect(actx.destination);
    data = new Uint8Array(analyser.fftSize);
  }
  audio.addEventListener("play", () => { setup(); if (actx.state === "suspended") actx.resume(); });
  function draw() {
    requestAnimationFrame(draw);
    const w = canvas.width, h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    ctx.lineWidth = 2; ctx.strokeStyle = "#00ff9d";
    ctx.shadowColor = "#00ff9d"; ctx.shadowBlur = 8;
    ctx.beginPath();
    const playing = analyser && !audio.paused && !audio.ended;
    if (playing) {
      analyser.getByteTimeDomainData(data);
      const step = w / data.length;
      for (let i = 0; i < data.length; i++) {
        const y = (data[i] / 255) * h;
        i === 0 ? ctx.moveTo(0, y) : ctx.lineTo(i * step, y);
      }
    } else { ctx.moveTo(0, h / 2); ctx.lineTo(w, h / 2); }
    ctx.stroke();
  }
  draw();
</script>
"""


def render_wave_player(audio_bytes):
    b64 = base64.b64encode(audio_bytes).decode()
    html_embed(WAVE_PLAYER_HTML.replace("__AUDIO__", b64), 310, key="m1_wave_player")


def ir_a_modulo2():
    st.session_state.module_nav = MODULES[1]


def ir_a_modulo3():
    st.session_state.module_nav = MODULES[2]


# =========================================================
# MÓDULO 1 · INTERFAZ
# =========================================================
def render_modulo1():
    st.title("🛡️ CYBER ANALYST SOC // MÓDULO 1")
    st.subheader("Módulo de Generación e Ilusión Sintética (Vishing Vector)")

    st.markdown("""
<div class="cyber-card">
    <span class="status-badge status-active">MODO: SIMULACIÓN DE AMENAZA</span>
    <p style="margin-top:10px;">
        Este módulo simula la fase de <b>Reconocimiento y Armado</b> del atacante.
        Ingresa un texto de ingeniería social para sintetizar la voz objetivo.
    </p>
</div>
""", unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])

    with col1:
        titulo("🎛️ Configuración de Parámetros")
        engine = st.radio(
            "Motor de Síntesis de Voz:",
            ["Neuronal gratuita (edge-tts)", "ElevenLabs API (consume créditos)"],
        )
        api_key, voice_label, rate = "", None, "+0%"
        eleven_voice = "21m00Tcm4TlvDq8ikWAM"

        if "edge-tts" in engine:
            voice_label = st.selectbox("Perfil de voz:", list(EDGE_VOICES.keys()))
            speed = st.slider("Velocidad de habla (%):", -30, 20, -5, step=5)
            rate = f"{speed:+d}%"
        else:
            api_key = st.text_input("ElevenLabs API Key:", type="password")
            eleven_voice = st.selectbox(
                "Perfil de voz:",
                ["21m00Tcm4TlvDq8ikWAM", "AZnzlk1XvdvUeBnXmlld", "EXAVITQu4vr4xnSDxMaL"],
                format_func=lambda x: {
                    "21m00Tcm4TlvDq8ikWAM": "Voz Femenina Corporativa (Rachel)",
                    "AZnzlk1XvdvUeBnXmlld": "Voz Masculina Ejecutiva (Domi)",
                    "EXAVITQu4vr4xnSDxMaL": "Voz Narrativa (Bella)",
                }[x],
            )

        titulo("💬 Guion de Ingeniería Social", hint(
            "¿Por qué funciona un guion así?",
            "Los guiones de vishing suelen combinar <b>autoridad</b> (un cargo), "
            "<b>urgencia</b> (\"ahora mismo\") y un <b>pedido concreto</b> (un pago o un código). "
            "Mira cuántos de los tres tiene el guion que elijas."))
        preset = st.selectbox("Cargar plantilla rápida:", [
            "Personalizado",
            "Hola, soy el Director de Finanzas. Necesito que liberes el pago de la factura 4022 inmediatamente.",
            "Estimado colaborador, detectamos un acceso no autorizado en su cuenta. Dícteme el código de 6 dígitos enviado a su celular.",
        ])
        if preset == "Personalizado":
            user_text = st.text_area(
                "Mensaje a sintetizar:",
                "Buenas tardes, hablo del área de infraestructura de TI...")
        else:
            user_text = st.text_area("Mensaje a sintetizar:", preset)

        btn_generate = st.button("⚡ GENERAR CLONACIÓN DE VOZ")

    with col2:
        salida_hint = ""
        if st.session_state.m1_done:
            salida_hint = hint(
                "Esto es lo que acaba de pasar",
                "Con solo un texto se obtuvo una voz creíble. En un ataque real, el atacante "
                "buscaría audios públicos de una persona concreta (redes, entrevistas) para imitarla. "
                "Cuando termines, pasa al Módulo 2 e intenta distinguir lo real de lo falso.")
        titulo("📊 Salida de Telemetría y Audio", salida_hint)

        if btn_generate:
            if not user_text.strip():
                st.warning("Ingresa un texto válido para continuar.")
            elif "ElevenLabs" in engine and not api_key:
                st.error("Ingresa tu API Key de ElevenLabs para usar este motor.")
            else:
                with st.spinner("Procesando síntesis espectral de voz..."):
                    if "edge-tts" in engine:
                        audio, err, fallback = generate_edge_audio(
                            user_text, EDGE_VOICES[voice_label], rate)
                    else:
                        audio, err = generate_elevenlabs_audio(user_text, api_key, eleven_voice)
                        fallback = False
                if err:
                    st.error(err)
                elif audio:
                    st.session_state.m1_done = True
                    st.session_state.m1_audio = audio
                    st.session_state.m1_fallback = fallback

        if st.session_state.get("m1_audio"):
            if st.session_state.get("m1_fallback"):
                st.warning("El servicio neuronal no respondió; se usó la voz de respaldo (gTTS).")
            st.success("¡Voz sintetizada exitosamente!")
            render_wave_player(st.session_state.m1_audio)
            st.markdown("""
<div style="background-color:#161f30; padding:10px; border-left:3px solid #00ff9d;">
    <small><b>Nota del Analista:</b> Observa cómo el audio sintético mantiene una curva de amplitud homogénea sin micro-pausas respiratorias naturales.</small>
</div>
""", unsafe_allow_html=True)
        else:
            st.info("Configura los parámetros a la izquierda y presiona "
                    "'Generar Clonación de Voz' para ejecutar la telemetría.")

    # Botón flotante: aparece SOLO después de generar la voz
    if st.session_state.m1_done:
        st.button("➡️ IR AL MÓDULO 2", key="next_module", on_click=ir_a_modulo2)


# =========================================================
# MÓDULO 2 · CASOS
# =========================================================
ARTEFACTOS = {
    "labios":      "Labios desincronizados en consonantes (p, b, m)",
    "frase_rota":  "Frases cortadas, incompletas o gramaticalmente raras",
    "piel":        "Piel, pelo o dientes demasiado lisos o artificiales",
    "fondo":       "Fondo, iluminación u objetos inconsistentes",
    "voz_limpia":  "Voz demasiado limpia, sin ruido de ambiente",
    "entonacion":  "Entonación plana, sin pausas ni respiraciones naturales",
    "manos_texto": "Manos, texto o detalles pequeños deformados",
    "contexto":    "Pide algo con urgencia, autoridad o cambia de canal",
    "intuicion":   "No detecto ningún artefacto, pero algo no me cuadra",
}

CASES = [
    # ------------------------------------------------------------------
    # CASO 1 · LISTO
    # ------------------------------------------------------------------
    {
        "id": "caso1",
        "titulo": "Caso 1 · Gerente de área",
        "video": "assets/caso1.mp4",
        "es_deepfake": True,                     # <- True = deepfake, False = real
        "contexto": ("Recibes este video por WhatsApp de un número que no tienes guardado. "
                     "Quien aparece dice ser un gerente de tu área."),
        "transcripcion": "Hola, me presento, mi nombre es Carlos, me des el dato de tu puesto.",
        # IDs de ARTEFACTOS que de verdad están presentes:
        "artefactos": ["frase_rota"],
        "explicacion": (
            "Este clip fue generado con IA. La frase está rota: <i>\"me des el dato de tu puesto\"</i> "
            "no tiene el verbo que la introduce (algo como \"necesito que\"). Las herramientas actuales "
            "producen video y voz bastante convincentes, pero a veces fallan en la estructura de la frase. "
            "<br><br>Fíjate también en lo que pide: un dato aparentemente inocente (tu puesto) que sirve "
            "para armar un ataque más creíble después. Es la fase de <b>reconocimiento</b> del Módulo 1."
        ),
    },

    # ------------------------------------------------------------------
    # CASO 2 · LISTO
    # Personaje ficticio de "sistemas" que pide quedarse con el equipo.
    # Sin tarjeta de contexto: el clip se juzga solo por lo que se ve y se oye.
    # TODO: revisa los artefactos marcados abajo contra el video y ajústalos
    # si al verlo encuentras otra cosa (p. ej. labios, piel o fondo).
    # ------------------------------------------------------------------
    {
        "id": "caso2",
        "titulo": "Caso 2 · Soporte de sistemas",
        "video": "assets/caso2.mp4",
        "es_deepfake": True,
        # Sin "contexto": este caso se presenta sin tarjeta de situación.
        "transcripcion": "Hola, soy de sistemas. Tomaré tu laptop.",
        "artefactos": ["frase_rota", "voz_limpia", "entonacion"],
        "explicacion": (
            "Este clip también fue generado con IA. No hay verificación de identidad ni explicación "
            "del motivo: solo una frase corta y directa que pide quedarse con un equipo físico. "
            "La voz suena demasiado limpia, sin el ruido de ambiente que tendría una oficina real, y la "
            "entonación es pareja, sin la inflexión natural de alguien explicando un procedimiento. "
            "<br><br>El patrón importa más que el clip: un mensaje breve, sin contexto previo y que pide "
            "entregar algo de valor (en Módulo 1 sería un dato o un pago, aquí un equipo) es la misma "
            "señal de alerta aunque cambie el objeto del pedido."
        ),
    },

    # ------------------------------------------------------------------
    # >>> CASO 3 · PENDIENTE <<<
    # Figura pública INVENTADA (influencer/cantante/deportista que no exista).
    # 1) Copia el video a assets/caso3.mp4
    # 2) Quita los '#' del bloque de abajo y completa los textos
    # ------------------------------------------------------------------
    # {
    #     "id": "caso3",
    #     "titulo": "Caso 3 · Figura pública (sorteo/inversión)",
    #     "video": "assets/caso3.mp4",
    #     "es_deepfake": True,     # o False si decides incluir un clip real
    #     "contexto": "Ves este video en una red social, compartido por un contacto.",
    #     "transcripcion": "PEGA AQUÍ LA TRANSCRIPCIÓN",
    #     "artefactos": [],
    #     "explicacion": "EXPLICA AQUÍ QUÉ DELATABA O NO AL CLIP",
    # },
]


# =========================================================
# MÓDULO 2 · UTILIDADES (video, audio, gráficas)
# =========================================================
@st.cache_data(show_spinner="Extrayendo audio del video...")
def get_audio(video_path):
    """Devuelve (muestras normalizadas, sample_rate, error)."""
    if not shutil.which("ffmpeg"):
        return None, None, "ffmpeg no está disponible (en Streamlit Cloud agrega packages.txt con 'ffmpeg')."
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    try:
        r = subprocess.run(
            ["ffmpeg", "-y", "-i", video_path, "-vn", "-ac", "1", "-ar", "44100",
             "-f", "wav", tmp.name],
            capture_output=True, timeout=60)
        if r.returncode != 0:
            return None, None, "No se pudo extraer el audio (¿el video tiene pista de audio?)."
        sr, data = wavfile.read(tmp.name)
        x = data.astype(np.float32)
        if x.ndim > 1:
            x = x.mean(axis=1)
        peak = float(np.max(np.abs(x))) if x.size else 0.0
        if peak == 0.0:
            return None, None, "El audio está en silencio total."
        return x / peak, int(sr), None
    except Exception as e:
        return None, None, f"Error al procesar el audio: {e}"
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


def _dark_layout(title, height=230):
    return dict(
        title=dict(text=title, font=dict(size=13)),
        paper_bgcolor="#111827", plot_bgcolor="#111827",
        font=dict(color="#00f3ff", family="Courier New"),
        margin=dict(l=45, r=10, t=40, b=35), height=height,
    )


def fig_spectrogram(x, sr):
    f, t, sxx = signal.spectrogram(x, fs=sr, nperseg=1024, noverlap=512)
    s_db = 10 * np.log10(sxx + 1e-12)
    s_db = np.clip(s_db, s_db.max() - 80, None)
    fig = go.Figure(go.Heatmap(
        z=np.round(s_db[::2], 0), x=t, y=f[::2] / 1000,
        colorscale="Viridis", showscale=False))
    fig.update_layout(**_dark_layout("ESPECTROGRAMA"))
    fig.update_xaxes(title_text="segundos")
    fig.update_yaxes(title_text="kHz")
    return fig


def fig_pausas(x, sr, frame_ms=20, umbral_db=-40, min_silencio_ms=150):
    n = int(sr * frame_ms / 1000)
    frames = len(x) // n
    rms = np.sqrt(np.mean(x[:frames * n].reshape(frames, n) ** 2, axis=1)) + 1e-9
    db = 20 * np.log10(rms)
    t = np.arange(frames) * frame_ms / 1000
    silencio = db < umbral_db
    fig = go.Figure(go.Scatter(x=t, y=db, mode="lines",
                               line=dict(color="#00ff9d", width=1.5)))
    i = 0
    while i < frames:
        if silencio[i]:
            j = i
            while j < frames and silencio[j]:
                j += 1
            if (j - i) * frame_ms >= min_silencio_ms:
                fig.add_vrect(x0=t[i], x1=t[j - 1] + frame_ms / 1000,
                              fillcolor="rgba(255,60,90,0.25)", line_width=0)
            i = j
        else:
            i += 1
    fig.update_layout(**_dark_layout("MAPA DE PAUSAS (zonas rojas = silencio)", 200))
    fig.update_xaxes(title_text="segundos")
    fig.update_yaxes(title_text="dB", range=[-80, 0])
    return fig


FORENSIC_PLAYER_HTML = """
<style>
  body { margin: 0; }
  .box { background:#111827; border:1px solid rgba(0,243,255,.4); border-radius:8px;
         padding:10px; font-family:'Courier New',monospace; color:#e5e7eb; }
  video { width:100%; max-height:360px; background:#000; border-radius:6px; }
  .row { display:flex; flex-wrap:wrap; gap:6px; margin-top:8px; align-items:center; }
  button { background:#0d1b2a; color:#00f3ff; border:1px solid #00f3ff; border-radius:4px;
           padding:6px 10px; cursor:pointer; font-family:inherit; font-weight:bold; }
  button.on, button:hover { background:#00f3ff; color:#0b0f19; }
  #t { margin-left:auto; color:#cbd5e1; font-size:13px; }
</style>
<div class="box">
  <video id="v" controls playsinline></video>
  <div class="row">
    <span>Velocidad:</span>
    <button class="sp" data-r="0.25">0.25×</button>
    <button class="sp" data-r="0.5">0.5×</button>
    <button class="sp on" data-r="1">1×</button>
  </div>
  <div class="row">
    <button id="prev">◀ cuadro</button>
    <button id="next">cuadro ▶</button>
    <span id="t">0.00 s</span>
  </div>
</div>
<script>
  const FPS = 24;
  const bytes = Uint8Array.from(atob("__VIDEO__"), c => c.charCodeAt(0));
  const v = document.getElementById("v");
  v.src = URL.createObjectURL(new Blob([bytes], {type: "video/mp4"}));
  const t = document.getElementById("t");
  const upd = () => { t.textContent = v.currentTime.toFixed(2) + " s"; };
  v.addEventListener("timeupdate", upd);
  v.addEventListener("seeked", upd);
  document.querySelectorAll(".sp").forEach(b => b.addEventListener("click", () => {
    v.playbackRate = parseFloat(b.dataset.r);
    document.querySelectorAll(".sp").forEach(x => x.classList.remove("on"));
    b.classList.add("on");
  }));
  const step = d => {
    v.pause();
    v.currentTime = Math.min(Math.max(0, v.currentTime + d / FPS), v.duration || 0);
  };
  document.getElementById("prev").onclick = () => step(-1);
  document.getElementById("next").onclick = () => step(1);
</script>
"""


# =========================================================
# MÓDULO 2 · VOTOS DEL GRUPO
# =========================================================
def guardar_voto(cid, rec):
    store = get_store()
    with store["lock"]:
        store["votes"].setdefault(cid, {})[st.session_state.uid] = rec


def stats_grupo(cid, truth):
    store = get_store()
    with store["lock"]:
        rows = list(store["votes"].get(cid, {}).values())
    n = len(rows)
    if n == 0:
        return None
    acc1 = sum(r["vote1"] == truth for r in rows) / n
    acc2 = sum(r["vote2"] == truth for r in rows) / n
    fallaron = [r["conf2"] for r in rows if r["vote2"] != truth]
    conf_fallo = sum(fallaron) / len(fallaron) if fallaron else None
    return n, acc1, acc2, conf_fallo


def reiniciar_mis_respuestas():
    st.session_state.cases = {}
    st.session_state.caso_actual = 0
    for k in [k for k in st.session_state if k.startswith(("caso", "m1_", "m3", "m4"))]:
        del st.session_state[k]
    st.session_state.m1_done = False
    st.session_state.m3_phase = "ringing"
    st.session_state.m3_round = 0
    st.session_state.m3_resultados = []
    st.session_state.m3_incidente = None


def borrar_votos_grupo():
    store = get_store()
    with store["lock"]:
        store["votes"].clear()


def ir_al_siguiente_caso():
    st.session_state.caso_actual += 1


# =========================================================
# MÓDULO 2 · UN CASO
# =========================================================
def render_case(case, es_ultimo):
    cid = case["id"]
    S = st.session_state.cases.setdefault(cid, {"phase": "blind"})
    truth = "Deepfake" if case["es_deepfake"] else "Real"
    video_path = os.path.join(BASE_DIR, case["video"])

    if case.get("contexto"):
        st.markdown(f'<div class="cyber-card"><b>Situación:</b> {case["contexto"]}</div>',
                    unsafe_allow_html=True)
    if not os.path.exists(video_path):
        st.error(f"Falta el video: `{case['video']}`. Súbelo a esa ruta del repositorio.")
        return

    # ---------------- FASE 1: voto a ciegas ----------------
    if S["phase"] == "blind":
        titulo("1 · Primera impresión", hint(
            "Primero, sin herramientas",
            "Mira y escucha el video tal cual. Nos interesa tu primera impresión, "
            "antes de analizar nada."))
        v_izq, v_centro, v_der = st.columns([1, 2, 1])
        with v_centro:
            st.video(video_path)
        vote1 = st.radio("¿Qué crees que es?", ["Real", "Deepfake"],
                         index=None, horizontal=True, key=f"{cid}_v1")
        titulo("¿Qué tan seguro estás?", hint(
            "Seguridad ≠ acierto",
            "Sentirse seguro no es lo mismo que acertar. Al final comparamos ambas cosas.",
            align="right"))
        conf1 = st.slider("Seguridad (%)", 0, 100, 50, 5, key=f"{cid}_c1")
        if st.button("Enviar primer voto", key=f"{cid}_b1", disabled=vote1 is None):
            S.update(vote1=vote1, conf1=conf1, phase="analysis")
            st.rerun()

    # ---------------- FASE 2: análisis ----------------
    elif S["phase"] == "analysis":
        st.caption(f"Tu primer voto: **{S['vote1']}** ({S['conf1']}% de seguridad)")
        a, b = st.columns(2)
        with a:
            titulo("🎞️ Reproductor forense", hint(
                "Velocidad y cuadros",
                "A velocidad baja y cuadro por cuadro se ven mejor la boca, los dientes y los bordes. "
                "Fíjate en las consonantes p, b y m: ahí los labios deben cerrarse."))
            html_embed(
                FORENSIC_PLAYER_HTML.replace("__VIDEO__", load_b64(video_path)), 520,
                key=f"{cid}_forensic_player")
        with b:
            x, sr, err = get_audio(video_path)
            if err:
                st.warning(err)
            else:
                titulo("📈 Espectrograma", hint(
                    "¿Qué estoy viendo?",
                    "Cada columna es un instante y el color indica la energía en cada frecuencia "
                    "(eje vertical). <b>Cuidado:</b> un audio real muy comprimido (WhatsApp, llamada) "
                    "también muestra cortes en frecuencias altas, así que no es una prueba definitiva.",
                    align="right"))
                st.plotly_chart(fig_spectrogram(x, sr), key=f"{cid}_spec")
                titulo("🔇 Mapa de pausas", hint(
                    "Pausas y silencios",
                    "Las zonas rojas son silencios. En el habla real las pausas suelen traer respiración "
                    "o ruido de fondo; un silencio perfectamente limpio es una pista, pero solo una pista.",
                    align="right"))
                st.plotly_chart(fig_pausas(x, sr), key=f"{cid}_pausas")

        titulo("🧪 Diagnóstico", hint(
            "Ayer vs. hoy",
            "En los deepfakes de hace unos años eran comunes los bordes borrosos, el parpadeo raro "
            "o la voz lenta. Hoy esas señales son mucho menos frecuentes: pesan más la sincronía "
            "labial, las texturas demasiado lisas, el texto del fondo, las manos y la voz demasiado "
            "limpia. Por eso existe la opción <i>\"no detecto nada, pero algo no me cuadra\"</i>: "
            "es una respuesta válida."))
        marcados = [k for k, label in ARTEFACTOS.items()
                    if st.checkbox(label, key=f"{cid}_a_{k}")]

        titulo("🗳️ Voto final", hint(
            "¿Cambiaste de opinión?",
            "Compara con tu primer voto. ¿Qué herramienta te hizo cambiar? "
            "¿Te hizo acertar más o menos?"))
        vote2 = st.radio("¿Qué crees que es ahora?", ["Real", "Deepfake"],
                         index=None, horizontal=True, key=f"{cid}_v2")
        conf2 = st.slider("Seguridad final (%)", 0, 100, 50, 5, key=f"{cid}_c2")
        if st.button("Enviar diagnóstico final", key=f"{cid}_b2", disabled=vote2 is None):
            S.update(vote2=vote2, conf2=conf2, marcados=marcados, phase="reveal")
            guardar_voto(cid, dict(vote1=S["vote1"], conf1=S["conf1"],
                                   vote2=vote2, conf2=conf2))
            st.rerun()

    # ---------------- FASE 3: revelación ----------------
    else:
        ok1, ok2 = S["vote1"] == truth, S["vote2"] == truth
        es = "un deepfake" if case["es_deepfake"] else "un video real"
        if ok2:
            st.success(f"Este clip era **{es}**. Tu voto final fue correcto.")
        else:
            st.error(f"Este clip era **{es}**. Tu voto final fue **{S['vote2']}**.")

        titulo("Tu recorrido")
        c1, c2, c3 = st.columns(3)
        c1.metric("Primer voto", S["vote1"], "acierto" if ok1 else "fallo",
                  delta_color="normal" if ok1 else "inverse")
        c2.metric("Voto final", S["vote2"], "acierto" if ok2 else "fallo",
                  delta_color="normal" if ok2 else "inverse")
        c3.metric("Seguridad", f"{S['conf1']}% → {S['conf2']}%")

        titulo("Señales en este clip", hint(
            "Lo que sí y lo que no",
            "Comparamos lo que marcaste con las señales que identificamos en este caso. "
            "Si marcaste algo que no aparece en la lista, puede que también exista: "
            "vuelve a mirar el video.", align="right"))
        reales = set(case["artefactos"])
        marcados = set(S.get("marcados", []))
        for k in ARTEFACTOS:
            if k in reales and k in marcados:
                st.markdown(f"✅ **Detectada:** {ARTEFACTOS[k]}")
            elif k in reales:
                st.markdown(f"⚠️ **Se te pasó:** {ARTEFACTOS[k]}")
            elif k in marcados:
                st.markdown(f"➖ Marcaste: {ARTEFACTOS[k]} (no está en nuestra lista)")
        st.markdown(f'<div class="cyber-card"><b>Transcripción:</b> <i>"{case["transcripcion"]}"</i>'
                    f'<br><br>{case["explicacion"]}</div>', unsafe_allow_html=True)

        titulo("👥 Resultados del grupo", hint(
            "Lo importante",
            "Aunque no distingas el video, hay señales de contexto que no dependen de la imagen "
            "ni del audio: urgencia, autoridad, pedir datos o saltar a otro canal. "
            "Verifica siempre por un canal alterno.", align="right"))
        g = stats_grupo(cid, truth)
        if g is None:
            st.info("Aún no hay votos del grupo.")
        else:
            n, acc1, acc2, conf_fallo = g
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Participantes", n)
            m2.metric("Acierto 1er voto", f"{acc1:.0%}")
            m3.metric("Acierto voto final", f"{acc2:.0%}")
            m4.metric("Seguridad de quienes fallaron",
                      f"{conf_fallo:.0f}%" if conf_fallo is not None else "—")

        st.markdown("---")
        if not es_ultimo:
            st.button("➡️ Siguiente caso", key=f"{cid}_next",
                      on_click=ir_al_siguiente_caso)
        else:
            st.button("➡️ IR AL MÓDULO 3", key="m2_to_m3", on_click=ir_a_modulo3)


# =========================================================
# MÓDULO 2 · INTERFAZ
# =========================================================
def render_modulo2():
    st.title("🛡️ CYBER ANALYST SOC // MÓDULO 2")
    st.subheader("El Ojo y Oído Crítico (Análisis de Evidencias)")
    st.markdown(f"""
<div class="cyber-card">
    <span class="status-badge status-active">MODO: LABORATORIO FORENSE</span>
    <p style="margin-top:10px;">
        Vas a analizar clips y decidir si son reales o deepfakes. Primero votas a ciegas,
        luego usas las herramientas y votas de nuevo. <b>No te decimos cuántos son falsos.</b>
        Ningún personaje ni voz corresponde a una persona real.
    </p>
</div>
""", unsafe_allow_html=True)
    st.caption(f"{len(CASES)} de {TOTAL_CASOS_PLANEADOS} casos cargados")

    idx = st.session_state.caso_actual
    if idx >= len(CASES):
        st.success("Ya completaste todos los casos disponibles del Módulo 2.")
        st.button("➡️ IR AL MÓDULO 3", key="m2_to_m3_fin", on_click=ir_a_modulo3)
        return

    case = CASES[idx]
    st.caption(f"Caso {idx + 1} de {len(CASES)} · {case['titulo']}")
    render_case(case, es_ultimo=(idx == len(CASES) - 1))


# =========================================================
# MÓDULO 3 · SIMULADOR DE VISHING EN TIEMPO REAL
# =========================================================
M3_NOMBRE = "Francis Wilkerson"
M3_SUBTEXTO = "Llamada entrante · Finanzas"
M3_TIEMPO_RONDA = 20  # segundos, solo visual/cosmético

M3_AVATAR = "assets/foto.jpg"
M3_RINGTONE = "assets/sound.mp4"
M3_AUDIO_DESPEDIDA = "assets/audio4.mp3"

M3_RONDAS = [
    {
        "audio": "assets/audio1.mp3",
        "opcion_cumplir": "🔑 Compartir mi clave de acceso",
        "opcion_verificar": "🛡️ Desplegar protocolo de verificación",
        "explicacion_incidente": (
            "Compartiste tu clave de acceso solo porque alguien lo pidió por teléfono con urgencia, "
            "sin verificar su identidad por otro canal (por ejemplo, llamando de vuelta a un número "
            "conocido o preguntando a su jefe directo)."
        ),
    },
    {
        "audio": "assets/audio2.mp3",
        "opcion_cumplir": "💸 Aprobar transferencia",
        "opcion_verificar": "🛡️ Desplegar protocolo de verificación",
        "explicacion_incidente": (
            "Autorizaste una orden de pago basándote solo en la voz de la llamada, sin confirmar la "
            "instrucción por un canal alterno. Las transferencias urgentes pedidas por voz, sin "
            "confirmación escrita ni doble autorización, son la forma más común de fraude por vishing."
        ),
    },
    {
        "audio": "assets/audio3.mp3",
        "opcion_cumplir": "✅ Marcar como completada sin alerta",
        "opcion_verificar": "🛡️ Desplegar protocolo de verificación",
        "explicacion_incidente": (
            "Ocultaste una alerta de revisión para \"ayudar\" a cerrar rápido, eliminando el control "
            "que hubiera detectado el fraude a tiempo. Pedir que se omita una revisión es en sí mismo "
            "una señal de alerta, incluso si el resto de la llamada suena creíble."
        ),
    },
]


@st.cache_data(show_spinner=False)
def audio_bytes_for_browser(path):
    """Devuelve (bytes, mime) listos para reproducir en el navegador.
    Si el archivo ya es un formato de audio reproducible, lo regresa tal cual.
    Si es un contenedor de video (p. ej. .mp4) extrae solo el audio con ffmpeg."""
    ext = os.path.splitext(path)[1].lower()
    directos = {".mp3": "audio/mpeg", ".wav": "audio/wav", ".ogg": "audio/ogg", ".m4a": "audio/mp4"}
    if ext in directos:
        with open(path, "rb") as f:
            return f.read(), directos[ext]
    if not shutil.which("ffmpeg"):
        return None, None
    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tmp.close()
    try:
        r = subprocess.run(
            ["ffmpeg", "-y", "-i", path, "-vn", "-acodec", "libmp3lame", tmp.name],
            capture_output=True, timeout=60)
        if r.returncode != 0:
            return None, None
        with open(tmp.name, "rb") as f:
            return f.read(), "audio/mpeg"
    except Exception:
        return None, None
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


M3_AUDIO_HTML = """
<div style="background:#111827;border:1px solid rgba(0,243,255,.4);border-radius:8px;padding:10px;">
  <audio controls autoplay __LOOP__ style="width:100%;">
    <source src="data:__MIME__;base64,__B64__">
  </audio>
</div>
"""

# Reproductor invisible: suena pero no muestra barra ni controles (para el tono de llamada).
M3_AUDIO_HIDDEN_HTML = """
<audio autoplay __LOOP__ style="display:none;">
  <source src="data:__MIME__;base64,__B64__">
</audio>
"""


def render_m3_audio(path, loop=False, show_controls=True, key=None):
    """Inserta un <audio> directamente en la página con st.markdown (sin iframe).
    No necesita JavaScript propio, así que evita el conflicto de reconciliación
    de React que ocurría al meterlo en un componente/iframe aparte."""
    data, mime = audio_bytes_for_browser(path)
    if data is None:
        st.warning(f"No se pudo cargar el audio: `{path}`.")
        return
    b64 = base64.b64encode(data).decode()
    template = M3_AUDIO_HTML if show_controls else M3_AUDIO_HIDDEN_HTML
    html = (template
            .replace("__LOOP__", "loop" if loop else "")
            .replace("__MIME__", mime)
            .replace("__B64__", b64))
    st.markdown(html, unsafe_allow_html=True)


M3_TIMER_HTML = """
<div style="background:#111827;border:1px solid rgba(255,60,90,.5);border-radius:8px;
            padding:14px;text-align:center;font-family:'Courier New',monospace;">
  <div style="color:#94a3b8;font-size:13px;letter-spacing:1px;">TIEMPO PARA DECIDIR</div>
  <div id="m3t" style="font-size:42px;font-weight:bold;color:#00ff9d;">__SECONDS__</div>
</div>
<script>
  let s = __SECONDS__;
  const el = document.getElementById("m3t");
  const tick = () => {
    s -= 1;
    if (s < 0) s = 0;
    el.textContent = s;
    el.style.color = s <= 5 ? "#ff3c5a" : "#00ff9d";
    if (s > 0) setTimeout(tick, 1000);
  };
  setTimeout(tick, 1000);
</script>
"""


def render_m3_timer(seconds, key=None):
    html_embed(M3_TIMER_HTML.replace("__SECONDS__", str(seconds)), 110, key=key)


def m3_contestar():
    st.session_state.m3_phase = "call"
    st.session_state.m3_round = 0
    st.session_state.m3_resultados = []
    st.session_state.m3_incidente = None
    st.session_state.m3_round_start = time.time()
    st.session_state.m3_timer_round = 0


def m3_decidir(cumplio):
    idx = st.session_state.m3_round
    ronda = M3_RONDAS[idx]
    inicio = st.session_state.get("m3_round_start", time.time())
    elapsed = round(time.time() - inicio, 1)

    if cumplio:
        st.session_state.m3_incidente = {
            "ronda": idx + 1,
            "segundos": elapsed,
            "accion": ronda["opcion_cumplir"],
            "explicacion": ronda["explicacion_incidente"],
        }
        st.session_state.m3_phase = "incident"
    else:
        st.session_state.m3_resultados.append({"ronda": idx + 1, "segundos": elapsed})
        if idx + 1 >= len(M3_RONDAS):
            st.session_state.m3_phase = "success"
        else:
            st.session_state.m3_round = idx + 1
            st.session_state.m3_round_start = time.time()
            st.session_state.m3_timer_round = idx + 1


def m3_reiniciar():
    st.session_state.m3_phase = "ringing"
    st.session_state.m3_round = 0
    st.session_state.m3_resultados = []
    st.session_state.m3_incidente = None
    st.session_state.pop("m3_timer_round", None)
    st.session_state.pop("m3_round_start", None)


def render_m3_llamada_entrante():
    foto_path = os.path.join(BASE_DIR, M3_AVATAR)
    foto_b64 = load_b64(foto_path) if os.path.exists(foto_path) else ""
    st.markdown(f"""
<div class="m3-ring-card">
    <div class="m3-avatar"><img src="data:image/jpeg;base64,{foto_b64}"></div>
    <div class="m3-nombre">{M3_NOMBRE}</div>
    <div class="m3-subtexto">{M3_SUBTEXTO}</div>
</div>
""", unsafe_allow_html=True)

    ring_path = os.path.join(BASE_DIR, M3_RINGTONE)
    if os.path.exists(ring_path):
        render_m3_audio(ring_path, loop=True, show_controls=False, key="m3_ring_audio")
    else:
        st.warning(f"Falta el tono de llamada: `{M3_RINGTONE}`.")

    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        st.button("📞 RESPONDER", key="m3_contestar", on_click=m3_contestar,
                   use_container_width=True)


def render_m3_ronda():
    idx = st.session_state.m3_round
    ronda = M3_RONDAS[idx]

    if st.session_state.get("m3_timer_round") != idx:
        st.session_state.m3_round_start = time.time()
        st.session_state.m3_timer_round = idx

    foto_path = os.path.join(BASE_DIR, M3_AVATAR)
    foto_b64 = load_b64(foto_path) if os.path.exists(foto_path) else ""
    st.markdown(f"""
<div class="m3-ring-card" style="padding:10px 0;">
    <div class="m3-avatar" style="width:90px;height:90px;">
        <img src="data:image/jpeg;base64,{foto_b64}">
    </div>
    <div class="m3-nombre" style="font-size:16px;">{M3_NOMBRE} · En llamada</div>
</div>
""", unsafe_allow_html=True)

    audio_path = os.path.join(BASE_DIR, ronda["audio"])
    if os.path.exists(audio_path):
        render_m3_audio(audio_path, loop=False, key=f"m3_audio_ronda_{idx}")
    else:
        st.warning(f"Falta el audio: `{ronda['audio']}`.")

    st.caption(f"Ronda {idx + 1} de {len(M3_RONDAS)}")
    render_m3_timer(M3_TIEMPO_RONDA, key=f"m3_timer_{idx}")

    titulo("¿Qué haces?")
    b1, b2 = st.columns(2)
    with b1:
        st.button(ronda["opcion_cumplir"], key=f"m3_cumplir_{idx}",
                   on_click=m3_decidir, args=(True,), use_container_width=True)
    with b2:
        st.button(ronda["opcion_verificar"], key=f"m3_verificar_{idx}",
                   on_click=m3_decidir, args=(False,), use_container_width=True)


def render_m3_incidente():
    inc = st.session_state.m3_incidente
    st.markdown("""
<div class="m3-incidente">
    <h2>🚨 INCIDENTE DE SEGURIDAD</h2>
    <h3>FONDOS EXFILTRADOS</h3>
</div>
""", unsafe_allow_html=True)
    st.error(f"En la ronda {inc['ronda']} elegiste **{inc['accion']}** en {inc['segundos']} segundos, "
             f"sin verificar la solicitud por un canal alterno.")
    st.markdown(f'<div class="cyber-card">{inc["explicacion"]}</div>', unsafe_allow_html=True)

    if st.session_state.m3_resultados:
        titulo("Lo que sí hiciste bien antes de fallar")
        for r in st.session_state.m3_resultados:
            st.markdown(f"✅ Ronda {r['ronda']}: verificaste en {r['segundos']} segundos.")

    st.button("🔁 Reintentar simulación", key="m3_retry", on_click=m3_reiniciar)


def render_m3_exito():
    audio_path = os.path.join(BASE_DIR, M3_AUDIO_DESPEDIDA)
    if os.path.exists(audio_path):
        render_m3_audio(audio_path, loop=False, key="m3_audio_despedida")

    st.markdown("""
<div class="m3-exito">
    <h2>✅ PROTOCOLO CORRECTO</h2>
    <h3>3 DE 3 VERIFICACIONES</h3>
</div>
""", unsafe_allow_html=True)
    st.success("Verificaste la solicitud por un canal alterno en las tres rondas, sin ceder a la "
               "presión de tiempo ni a la autoridad simulada de la llamada.")

    titulo("Tu recorrido")
    for r in st.session_state.m3_resultados:
        st.markdown(f"✅ Ronda {r['ronda']}: verificaste en {r['segundos']} segundos.")

    st.button("🔁 Repetir simulación", key="m3_retry_ok", on_click=m3_reiniciar)


def render_modulo3():
    st.title("🛡️ CYBER ANALYST SOC // MÓDULO 3")
    st.subheader("Simulador de Vishing en Tiempo Real (Prueba de Estrés)")
    st.markdown("""
<div class="cyber-card">
    <span class="status-badge status-active">MODO: PRESIÓN OPERATIVA</span>
    <p style="margin-top:10px;">
        Vas a recibir una llamada simulada. En cada pausa deberás decidir, bajo presión de tiempo,
        entre cumplir lo que te piden o desplegar el protocolo de verificación. Ningún personaje ni
        voz corresponde a una persona real.
    </p>
</div>
""", unsafe_allow_html=True)

    phase = st.session_state.m3_phase
    if phase == "ringing":
        render_m3_llamada_entrante()
    elif phase == "call":
        render_m3_ronda()
    elif phase == "incident":
        render_m3_incidente()
    elif phase == "success":
        render_m3_exito()


# =========================================================
# MÓDULO 4 · PROTOCOLO ANTI-SUPLANTACIÓN
# =========================================================
M4_CATALOGO = {
    "Verificación de identidad": [
        ("m4_fuera_banda", "Verificación fuera de banda",
         "Confirmar la solicitud por un canal distinto y ya conocido (llamada a un número "
         "registrado, mensaje directo a la persona real), nunca por el mismo canal donde "
         "llegó la solicitud."),
        ("m4_palabra_clave", "Palabra clave compartida",
         "Usar un código o palabra clave pactada previamente entre las partes involucradas, "
         "que nunca se comparta por el mismo canal de la solicitud."),
        ("m4_videollamada", "Videollamada con cámara obligatoria",
         "Exigir una videollamada en vivo, con cámara encendida, antes de ejecutar cualquier "
         "instrucción sensible recibida por voz o mensaje."),
    ],
    "Controles de autorización": [
        ("m4_doble_autorizacion", "Doble autorización para transferencias o pagos",
         "Ninguna transferencia o pago se ejecuta con la aprobación de una sola persona; se "
         "requiere una segunda autorización independiente."),
        ("m4_montos_maximos", "Montos máximos sin aprobación adicional",
         "Definir un límite de monto a partir del cual toda operación requiere una revisión y "
         "aprobación adicional, sin excepción por urgencia."),
        ("m4_tiempo_espera", "Tiempo de espera obligatorio ante solicitudes urgentes",
         "Establecer un periodo mínimo de espera antes de ejecutar cualquier solicitud marcada "
         "como urgente, para permitir su verificación."),
    ],
    "Procedimiento ante solicitudes urgentes": [
        ("m4_no_ejecutar_voz", "Nunca ejecutar pagos o datos solo por voz o video",
         "Ninguna instrucción de pago, transferencia o entrega de datos sensibles se ejecuta "
         "basándose únicamente en una llamada o videollamada, sin verificación adicional."),
        ("m4_reportar", "Reportar intentos sospechosos a un canal definido",
         "Todo intento de suplantación o solicitud sospechosa se reporta de inmediato al área "
         "o canal de seguridad designado por la organización."),
    ],
    "Gestión de accesos": [
        ("m4_no_compartir_credenciales", "Nunca compartir credenciales por teléfono o chat",
         "Ninguna clave, token o credencial de acceso se comparte verbalmente, por chat o por "
         "videollamada, bajo ninguna circunstancia."),
        ("m4_renovacion_tokens", "Renovación de tokens solo por canales oficiales de TI",
         "La renovación o desbloqueo de accesos y tokens se realiza únicamente a través de los "
         "canales oficiales y verificados del área de TI."),
    ],
}

M4_IDS = [cid for controles in M4_CATALOGO.values() for cid, _, _ in controles]


def _pdf_parrafo_indentado(pdf, texto, sangria=4, line_height=5):
    """Escribe un párrafo con sangría izquierda, ajustando el margen izquierdo
    temporalmente (forma robusta en fpdf2: evita errores de ancho insuficiente
    que sí pueden ocurrir moviendo X manualmente con set_x)."""
    margen_original = pdf.l_margin
    pdf.set_left_margin(margen_original + sangria)
    pdf.set_x(margen_original + sangria)
    pdf.multi_cell(0, line_height, texto)
    pdf.set_left_margin(margen_original)
    pdf.set_x(margen_original)


def generar_pdf_protocolo(seleccionados, notas=""):
    """Arma el PDF del protocolo en memoria y regresa sus bytes. Estilo sobrio/profesional."""
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    # Encabezado
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(15, 23, 42)  # azul marino muy oscuro
    pdf.cell(0, 12, "Protocolo de Verificación de Identidad Digital", ln=True)

    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(110, 110, 110)
    pdf.multi_cell(0, 5, "Documento de referencia y concientización. No sustituye la política "
                         "oficial de seguridad de la información de tu organización.")
    pdf.ln(2)
    pdf.set_draw_color(15, 23, 42)
    pdf.set_line_width(0.5)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(6)

    # Secciones (solo las que tengan al menos un control marcado)
    for categoria, controles in M4_CATALOGO.items():
        elegidos = [c for c in controles if c[0] in seleccionados]
        if not elegidos:
            continue

        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(13, 42, 74)  # azul marino
        pdf.cell(0, 9, categoria, ln=True)

        for _cid, nombre, descripcion in elegidos:
            pdf.set_font("Helvetica", "B", 10.5)
            pdf.set_text_color(30, 30, 30)
            pdf.multi_cell(0, 6, f"-  {nombre}")

            pdf.set_font("Helvetica", "", 9.5)
            pdf.set_text_color(90, 90, 90)
            _pdf_parrafo_indentado(pdf, descripcion)
            pdf.ln(2)

        pdf.ln(3)

    # Ideas adicionales (texto libre del usuario)
    if notas.strip():
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(13, 42, 74)
        pdf.cell(0, 9, "Ideas adicionales de la organización", ln=True)

        pdf.set_font("Helvetica", "", 9.5)
        pdf.set_text_color(30, 30, 30)
        pdf.multi_cell(0, 5, notas.strip())
        pdf.ln(3)

    # Pie
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(140, 140, 140)
    pdf.cell(0, 6, f"Generado el {datetime.now().strftime('%d/%m/%Y')}", ln=True)

    salida = pdf.output()
    return bytes(salida)


def generar_protocolo():
    seleccionados = {cid for cid in M4_IDS if st.session_state.get(cid)}
    notas = st.session_state.get("m4_notas", "")
    st.session_state.m4_pdf_bytes = generar_pdf_protocolo(seleccionados, notas)


def render_modulo4():
    st.title("🛡️ CYBER ANALYST SOC // MÓDULO 4")
    st.subheader("Creación del Protocolo Anti-Suplantación (Salida Práctica)")

    st.markdown("""
<div class="cyber-card">
    <span class="status-badge status-active">MODO: CONSTRUCCIÓN DE POLÍTICA</span>
    <p style="margin-top:10px;">
        Selecciona los controles de seguridad que aplicarías en tu organización. Al final podrás
        descargar un protocolo de verificación de identidad digital en PDF, con los controles
        que elegiste.
    </p>
</div>
""", unsafe_allow_html=True)

    for categoria, controles in M4_CATALOGO.items():
        titulo(categoria)
        for cid, nombre, descripcion in controles:
            st.checkbox(nombre, key=cid, help=descripcion)

    titulo("💭 Ideas extra", hint(
        "Espacio libre",
        "Añade cualquier control, idea o práctica adicional que podrías desplegar en tu área u "
        "organización. Este texto se incluye tal cual al final del protocolo."))
    st.text_area("Añade ideas extras que podrías desplegar en tu área u organización:",
                 key="m4_notas", height=150,
                 placeholder="Ej. Capacitación trimestral de concientización, lista blanca de "
                             "números autorizados para solicitudes urgentes, etc.")

    hay_seleccion = any(st.session_state.get(cid, False) for cid in M4_IDS)
    if not hay_seleccion:
        st.info("Selecciona al menos un control para poder generar el protocolo.")

    st.button("📄 Generar protocolo", key="m4_generar", on_click=generar_protocolo,
              disabled=not hay_seleccion)

    if st.session_state.get("m4_pdf_bytes"):
        st.success("Protocolo generado. Descárgalo abajo.")
        st.download_button(
            "⬇️ Descargar protocolo (PDF)",
            data=st.session_state.m4_pdf_bytes,
            file_name="protocolo_anti_suplantacion.pdf",
            mime="application/pdf",
            key="m4_download",
        )


# =========================================================
# BARRA LATERAL Y ENRUTADO
# =========================================================
with st.sidebar:
    st.markdown("## 🛡️ SOC // Deepfake Audit")
    st.radio("Módulo", MODULES, key="module_nav")
    st.toggle("Modo aprendizaje (pistas ?)", key="learning")
    with st.expander("Herramientas del presentador"):
        st.button("Reiniciar mis respuestas", on_click=reiniciar_mis_respuestas)
        st.button("Borrar votos del grupo", on_click=borrar_votos_grupo)

if st.session_state.module_nav == MODULES[0]:
    render_modulo1()
elif st.session_state.module_nav == MODULES[1]:
    render_modulo2()
elif st.session_state.module_nav == MODULES[2]:
    render_modulo3()
else:
    render_modulo4()