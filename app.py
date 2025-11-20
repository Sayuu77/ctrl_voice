import os
import streamlit as st
from bokeh.models.widgets import Button
from bokeh.models import CustomJS
from streamlit_bokeh_events import streamlit_bokeh_events
from PIL import Image
import time
import paho.mqtt.client as paho
import json
from gtts import gTTS
from googletrans import Translator
import cv2
import numpy as np
import tempfile

# Configuración de página
st.set_page_config(
    page_title="Control por Voz y Cámara",
    page_icon="🎤",
    layout="centered"
)

# Estilos CSS modernos
st.markdown("""
<style>
    .main-title {
        font-size: 2.8rem;
        color: #7E57C2;
        text-align: center;
        margin-bottom: 0.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #7E57C2, #BA68C8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .subtitle {
        font-size: 1.3rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: 500;
    }
    .voice-section {
        background: linear-gradient(135deg, #F3E5F5, #EDE7F6);
        border: 2px solid #D1C4E9;
        border-radius: 20px;
        padding: 3rem 2rem;
        margin: 2rem 0;
        text-align: center;
    }
    .camera-section {
        background: linear-gradient(135deg, #E8F5E8, #C8E6C9);
        border: 2px solid #4CAF50;
        border-radius: 20px;
        padding: 2rem;
        margin: 2rem 0;
    }
    .mic-button {
        background: linear-gradient(135deg, #7E57C2, #BA68C8);
        color: white;
        border: none;
        border-radius: 50%;
        width: 120px;
        height: 120px;
        font-size: 3rem;
        margin: 1rem auto;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 8px 25px rgba(126, 87, 194, 0.3);
    }
    .camera-button {
        background: linear-gradient(135deg, #4CAF50, #66BB6A);
        color: white;
        border: none;
        border-radius: 15px;
        padding: 1rem 2rem;
        font-size: 1.2rem;
        margin: 1rem auto;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 8px 25px rgba(76, 175, 80, 0.3);
    }
    .mic-button:hover, .camera-button:hover {
        transform: scale(1.05);
        box-shadow: 0 12px 35px rgba(126, 87, 194, 0.4);
    }
    .result-box {
        background: white;
        border: 2px solid #7E57C2;
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1.5rem 0;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
    }
    .color-detection-box {
        background: white;
        border: 2px solid #4CAF50;
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1.5rem 0;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
    }
    .status-indicator {
        display: inline-flex;
        align-items: center;
        background: #E8F5E8;
        color: #2E7D32;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: 500;
        margin: 0.5rem 0;
    }
    .status-indicator-off {
        display: inline-flex;
        align-items: center;
        background: #FFEBEE;
        color: #C62828;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: 500;
        margin: 0.5rem 0;
    }
    .color-indicator {
        display: inline-flex;
        align-items: center;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: 500;
        margin: 0.25rem;
    }
    .amarillo { background: #FFF9C4; color: #F57F17; border: 2px solid #FFEB3B; }
    .rojo { background: #FFEBEE; color: #C62828; border: 2px solid #F44336; }
    .verde { background: #E8F5E8; color: #2E7D32; border: 2px solid #4CAF50; }
    .pulse {
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
    }
    .info-text {
        color: #666;
        font-size: 1rem;
        margin: 1rem 0;
    }
    .command-list {
        background: #F8F9FA;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    .command-item {
        padding: 0.5rem;
        margin: 0.25rem 0;
        border-left: 4px solid;
        background: white;
    }
    .led-amarillo { border-left-color: #FFEB3B; }
    .led-rojo { border-left-color: #F44336; }
    .led-verde { border-left-color: #4CAF50; }
    .led-todos { border-left-color: #9C27B0; }
    .luz-principal { border-left-color: #2196F3; }
    .puerta { border-left-color: #FF9800; }
</style>
""", unsafe_allow_html=True)

# Callbacks MQTT
def on_publish(client, userdata, result):
    st.toast("Comando enviado exitosamente", icon="✅")

def on_message(client, userdata, message):
    global message_received
    time.sleep(2)
    message_received = str(message.payload.decode("utf-8"))
    st.session_state.last_received = message_received

# Configuración MQTT
broker = "broker.mqttdashboard.com"
port = 1883

# Funciones para detección de colores
def detectar_colores(imagen):
    """
    Detecta colores amarillo, rojo y verde en una imagen
    Retorna un diccionario con los colores detectados y sus porcentajes
    """
    # Convertir a espacio de color HSV
    hsv = cv2.cvtColor(imagen, cv2.COLOR_RGB2HSV)
    
    # Definir rangos de colores en HSV
    # Amarillo
    amarillo_bajo = np.array([20, 100, 100])
    amarillo_alto = np.array([30, 255, 255])
    
    # Rojo (dos rangos porque el rojo está en ambos extremos del espectro)
    rojo_bajo1 = np.array([0, 100, 100])
    rojo_alto1 = np.array([10, 255, 255])
    rojo_bajo2 = np.array([160, 100, 100])
    rojo_alto2 = np.array([180, 255, 255])
    
    # Verde
    verde_bajo = np.array([35, 100, 100])
    verde_alto = np.array([85, 255, 255])
    
    # Crear máscaras
    mascara_amarillo = cv2.inRange(hsv, amarillo_bajo, amarillo_alto)
    mascara_rojo1 = cv2.inRange(hsv, rojo_bajo1, rojo_alto1)
    mascara_rojo2 = cv2.inRange(hsv, rojo_bajo2, rojo_alto2)
    mascara_rojo = cv2.bitwise_or(mascara_rojo1, mascara_rojo2)
    mascara_verde = cv2.inRange(hsv, verde_bajo, verde_alto)
    
    # Calcular porcentajes
    total_pixeles = imagen.shape[0] * imagen.shape[1]
    
    porcentaje_amarillo = (np.sum(mascara_amarillo > 0) / total_pixeles) * 100
    porcentaje_rojo = (np.sum(mascara_rojo > 0) / total_pixeles) * 100
    porcentaje_verde = (np.sum(mascara_verde > 0) / total_pixeles) * 100
    
    # Umbral para considerar que el color está presente
    umbral_deteccion = 2.0  # 2% de la imagen
    
    colores_detectados = {
        'amarillo': porcentaje_amarillo >= umbral_deteccion,
        'rojo': porcentaje_rojo >= umbral_deteccion,
        'verde': porcentaje_verde >= umbral_deteccion,
        'porcentajes': {
            'amarillo': round(porcentaje_amarillo, 2),
            'rojo': round(porcentaje_rojo, 2),
            'verde': round(porcentaje_verde, 2)
        }
    }
    
    return colores_detectados

def enviar_comando_color(color, accion):
    """Envía comando MQTT para controlar LEDs según color detectado"""
    try:
        client = paho.Client("streamlit-camera-control")
        client.on_publish = on_publish
        client.connect(broker, port)
        
        comando = f"{accion} {color}"
        message = json.dumps({"Act1": comando})
        ret = client.publish("appcolor", message)
        
        st.toast(f"💡 {accion.capitalize()} LED {color.upper()}", icon="✅")
        time.sleep(1)
        client.disconnect()
        return True
    except Exception as e:
        st.error(f"❌ Error al enviar comando: {e}")
        return False

# Inicializar session state
if 'last_command' not in st.session_state:
    st.session_state.last_command = ""
if 'last_received' not in st.session_state:
    st.session_state.last_received = ""
if 'foto_tomada' not in st.session_state:
    st.session_state.foto_tomada = None
if 'colores_detectados' not in st.session_state:
    st.session_state.colores_detectados = {}

# Header principal
st.markdown('<div class="main-title">🎤 Control por Voz y Cámara</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Controla dispositivos IoT con comandos de voz y detección de colores</div>', unsafe_allow_html=True)

# Sección de comandos disponibles
with st.expander("📋 Comandos Disponibles", expanded=True):
    st.markdown("""
    <div class="command-list">
        <div class="command-item led-amarillo"><strong>💡 Enciende el amarillo</strong> - Enciende LED amarillo</div>
        <div class="command-item led-amarillo"><strong>🔌 Apaga el amarillo</strong> - Apaga LED amarillo</div>
        
        <div class="command-item led-rojo"><strong>🔴 Enciende el rojo</strong> - Enciende LED rojo</div>
        <div class="command-item led-rojo"><strong>🔌 Apaga el rojo</strong> - Apaga LED rojo</div>
        
        <div class="command-item led-verde"><strong>🟢 Enciende el verde</strong> - Enciende LED verde</div>
        <div class="command-item led-verde"><strong>🔌 Apaga el verde</strong> - Apaga LED verde</div>
        
        <div class="command-item led-todos"><strong>🌈 Enciende todos los LEDs</strong> - Enciende todos los LEDs</div>
        <div class="command-item led-todos"><strong>🔌 Apaga todos los LEDs</strong> - Apaga todos los LEDs</div>
        
        <div class="command-item luz-principal"><strong>💡 Enciende la luz</strong> - Enciende luz principal</div>
        <div class="command-item luz-principal"><strong>🔌 Apaga la luz</strong> - Apaga luz principal</div>
        
        <div class="command-item puerta"><strong>🚪 Abre la puerta</strong> - Abre la puerta</div>
        <div class="command-item puerta"><strong>🚪 Cierra la puerta</strong> - Cierra la puerta</div>
        
        <div style="margin-top: 1rem; padding: 0.5rem; background: #E3F2FD; border-radius: 5px;">
            <small>📷 <strong>Detección por Cámara:</strong> Toma una foto y los LEDs se encienden automáticamente según los colores detectados</small>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Sección de cámara
st.markdown("## 📷 Detección de Colores por Cámara")
st.markdown('<div class="camera-section">', unsafe_allow_html=True)

# Opción para subir imagen o usar cámara
opcion_camara = st.radio("Selecciona el modo:", 
                         ["📤 Subir imagen", "📷 Usar cámara web"], 
                         horizontal=True)

imagen = None

if opcion_camara == "📤 Subir imagen":
    archivo_imagen = st.file_uploader("Sube una imagen", type=['jpg', 'jpeg', 'png'])
    if archivo_imagen is not None:
        imagen = Image.open(archivo_imagen)
        st.session_state.foto_tomada = np.array(imagen)

else:  # Usar cámara web
    foto = st.camera_input("Toma una foto para detectar colores")
    if foto is not None:
        imagen = Image.open(foto)
        st.session_state.foto_tomada = np.array(imagen)

# Procesar imagen si existe
if st.session_state.foto_tomada is not None:
    st.markdown("### 🖼️ Imagen Capturada")
    st.image(st.session_state.foto_tomada, use_column_width=True)
    
    # Botón para procesar la imagen
    if st.button("🔍 Analizar Colores en la Imagen", use_container_width=True):
        with st.spinner("Analizando colores..."):
            # Detectar colores
            st.session_state.colores_detectados = detectar_colores(st.session_state.foto_tomada)
            
            # Mostrar resultados
            st.markdown("### 🎨 Colores Detectados")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.session_state.colores_detectados['amarillo']:
                    st.markdown(f'<div class="color-indicator amarillo">🟡 AMARILLO ({st.session_state.colores_detectados["porcentajes"]["amarillo"]}%)</div>', unsafe_allow_html=True)
                    if st.button("💡 Encender Amarillo", key="amarillo_on"):
                        enviar_comando_color("amarillo", "enciende")
                else:
                    st.markdown('<div class="color-indicator">⚫ AMARILLO (No detectado)</div>', unsafe_allow_html=True)
            
            with col2:
                if st.session_state.colores_detectados['rojo']:
                    st.markdown(f'<div class="color-indicator rojo">🔴 ROJO ({st.session_state.colores_detectados["porcentajes"]["rojo"]}%)</div>', unsafe_allow_html=True)
                    if st.button("💡 Encender Rojo", key="rojo_on"):
                        enviar_comando_color("rojo", "enciende")
                else:
                    st.markdown('<div class="color-indicator">⚫ ROJO (No detectado)</div>', unsafe_allow_html=True)
            
            with col3:
                if st.session_state.colores_detectados['verde']:
                    st.markdown(f'<div class="color-indicator verde">🟢 VERDE ({st.session_state.colores_detectados["porcentajes"]["verde"]}%)</div>', unsafe_allow_html=True)
                    if st.button("💡 Encender Verde", key="verde_on"):
                        enviar_comando_color("verde", "enciende")
                else:
                    st.markdown('<div class="color-indicator">⚫ VERDE (No detectado)</div>', unsafe_allow_html=True)
            
            # Botón para encender todos los colores detectados
            colores_presentes = [
                color for color in ['amarillo', 'rojo', 'verde'] 
                if st.session_state.colores_detectados[color]
            ]
            
            if colores_presentes:
                if st.button("🌈 Encender Todos los Colores Detectados", use_container_width=True):
                    for color in colores_presentes:
                        enviar_comando_color(color, "enciende")
                        time.sleep(0.5)
                    st.success(f"✅ Encendidos: {', '.join(colores_presentes).upper()}")
            
            # Botón para apagar todos los LEDs
            if st.button("🔌 Apagar Todos los LEDs", use_container_width=True):
                enviar_comando_color("todos", "apaga")
                st.success("🔌 Todos los LEDs apagados")

st.markdown('</div>', unsafe_allow_html=True)

# Sección de control por voz (tu código original)
st.markdown("## 🎤 Control por Voz")

# Icono de micrófono centrado
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.markdown('<div class="mic-button pulse">🎤</div>', unsafe_allow_html=True)

st.markdown('<div class="info-text">Haz clic en el botón y di tu comando de voz</div>', unsafe_allow_html=True)

# Botón de reconocimiento de voz
stt_button = Button(label=" Iniciar Reconocimiento de Voz ", width=300, height=60, 
                   button_type="success", css_classes=["pulse"])
stt_button.js_on_event("button_click", CustomJS(code="""
    var recognition = new webkitSpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'es-ES';

    recognition.onstart = function() {
        document.dispatchEvent(new CustomEvent("RECORDING_START"));
    }

    recognition.onresult = function (e) {
        var value = e.results[0][0].transcript;
        if ( value != "") {
            document.dispatchEvent(new CustomEvent("GET_TEXT", {detail: value}));
        }
    }

    recognition.onerror = function(e) {
        document.dispatchEvent(new CustomEvent("RECORDING_ERROR", {detail: e.error}));
    }

    recognition.onend = function() {
        document.dispatchEvent(new CustomEvent("RECORDING_END"));
    }

    recognition.start();
"""))

# Procesar eventos de voz
result = streamlit_bokeh_events(
    stt_button,
    events="GET_TEXT,RECORDING_START,RECORDING_END,RECORDING_ERROR",
    key="listen",
    refresh_on_update=False,
    override_height=80,
    debounce_time=0
)

# Mostrar estado de grabación
if result:
    if "RECORDING_START" in result:
        st.info("🎤 Escuchando... Habla ahora")
    if "RECORDING_END" in result:
        st.success("✅ Grabación completada")
    if "RECORDING_ERROR" in result:
        st.error("❌ Error en el reconocimiento de voz")

# Procesar comandos de voz
if result and "GET_TEXT" in result:
    command = result.get("GET_TEXT").strip()
    
    # Normalizar el comando
    command = command.lower().strip(' .!?')
    st.session_state.last_command = command
    
    # Mostrar comando reconocido
    st.markdown("### 🎯 Comando Reconocido")
    st.markdown(f'<div class="result-box"><span style="font-size: 1.4rem; color: #7E57C2; font-weight: 600;">"{command}"</span></div>', unsafe_allow_html=True)
    
    # Mapeo de comandos (tu código original)
    command_mapping = {
        'enciende el amarillo': 'enciende amarillo',
        'prende el amarillo': 'enciende amarillo',
        'enciende amarillo': 'enciende amarillo',
        'apaga el amarillo': 'apaga amarillo',
        'apaga amarillo': 'apaga amarillo',
        'enciende el rojo': 'enciende rojo',
        'prende el rojo': 'enciende rojo',
        'enciende rojo': 'enciende rojo',
        'apaga el rojo': 'apaga rojo',
        'apaga rojo': 'apaga rojo',
        'enciende el verde': 'enciende verde',
        'prende el verde': 'enciende verde',
        'enciende verde': 'enciende verde',
        'apaga el verde': 'apaga verde',
        'apaga verde': 'apaga verde',
        'enciende todos los leds': 'enciende todos los leds',
        'apaga todos los leds': 'apaga todos los leds',
        'enciende la luz': 'enciende luz',
        'apaga la luz': 'apaga luz',
        'abre la puerta': 'abre puerta',
        'cierra la puerta': 'cierra puerta',
        'amarillo': 'enciende amarillo',
        'rojo': 'enciende rojo',
        'verde': 'enciende verde',
    }
    
    normalized_command = command_mapping.get(command, command)
    
    # Enviar comando por MQTT
    try:
        client1 = paho.Client("streamlit-voice-control")
        client1.on_publish = on_publish
        client1.connect(broker, port)
        message = json.dumps({"Act1": normalized_command})
        ret = client1.publish("appcolor", message)
        
        st.toast(f"📡 Comando enviado: {normalized_command}", icon="✅")
        time.sleep(1)
        client1.disconnect()
    except Exception as e:
        st.error(f"❌ Error al enviar comando: {e}")

# Historial e información
if st.session_state.last_command:
    with st.expander("📊 Historial de Comandos", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Último Comando", st.session_state.last_command)
        with col2:
            st.metric("Estado", "Enviado ✓")

# Información de conexión
with st.expander("🔧 Información de Conexión", expanded=False):
    st.write(f"**Broker MQTT:** `{broker}`")
    st.write(f"**Puerto:** `{port}`")
    st.write(f"**Tópico:** `appcolor`")
    
    try:
        test_client = paho.Client("test-connection")
        test_client.connect(broker, port, 5)
        test_client.disconnect()
        st.success("✅ Conexión MQTT disponible")
    except:
        st.error("❌ No se puede conectar al broker MQTT")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666;'>"
    "Control por Voz y Cámara | Streamlit + ESP32 + MQTT + OpenCV"
    "</div>", 
    unsafe_allow_html=True
)
