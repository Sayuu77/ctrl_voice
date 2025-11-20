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
from io import BytesIO

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
    .color-result-box {
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
    .azul { background: #E3F2FD; color: #1565C0; border: 2px solid #2196F3; }
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

# Función para detectar colores en la imagen
def detectar_colores(imagen):
    """
    Detecta los colores amarillo, rojo y azul en una imagen
    Retorna un diccionario con booleanos para cada color
    """
    try:
        # Convertir PIL Image a OpenCV
        img_array = np.array(imagen)
        
        # Convertir RGB a BGR (OpenCV usa BGR)
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        # Convertir a HSV para mejor detección de colores
        img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        
        # Definir rangos de colores en HSV
        # Amarillo
        amarillo_bajo1 = np.array([20, 100, 100])
        amarillo_alto1 = np.array([30, 255, 255])
        
        # Rojo (necesita dos rangos por la naturaleza del rojo en HSV)
        rojo_bajo1 = np.array([0, 100, 100])
        rojo_alto1 = np.array([10, 255, 255])
        rojo_bajo2 = np.array([170, 100, 100])
        rojo_alto2 = np.array([180, 255, 255])
        
        # Azul
        azul_bajo = np.array([100, 100, 100])
        azul_alto = np.array([130, 255, 255])
        
        # Crear máscaras
        mascara_amarillo = cv2.inRange(img_hsv, amarillo_bajo1, amarillo_alto1)
        mascara_rojo1 = cv2.inRange(img_hsv, rojo_bajo1, rojo_alto1)
        mascara_rojo2 = cv2.inRange(img_hsv, rojo_bajo2, rojo_alto2)
        mascara_rojo = cv2.bitwise_or(mascara_rojo1, mascara_rojo2)
        mascara_azul = cv2.inRange(img_hsv, azul_bajo, azul_alto)
        
        # Aplicar operaciones morfológicas para limpiar las máscaras
        kernel = np.ones((5,5), np.uint8)
        mascara_amarillo = cv2.morphologyEx(mascara_amarillo, cv2.MORPH_OPEN, kernel)
        mascara_rojo = cv2.morphologyEx(mascara_rojo, cv2.MORPH_OPEN, kernel)
        mascara_azul = cv2.morphologyEx(mascara_azul, cv2.MORPH_OPEN, kernel)
        
        # Contar píxeles de cada color
        pixeles_amarillo = cv2.countNonZero(mascara_amarillo)
        pixeles_rojo = cv2.countNonZero(mascara_rojo)
        pixeles_azul = cv2.countNonZero(mascara_azul)
        
        # Umbral mínimo de píxeles para considerar que el color está presente
        umbral_minimo = 500  # Ajustar según necesidad
        
        # Determinar qué colores están presentes
        amarillo_detectado = pixeles_amarillo > umbral_minimo
        rojo_detectado = pixeles_rojo > umbral_minimo
        azul_detectado = pixeles_azul > umbral_minimo
        
        # Calcular porcentajes
        total_pixeles = img_array.shape[0] * img_array.shape[1]
        porcentaje_amarillo = (pixeles_amarillo / total_pixeles) * 100
        porcentaje_rojo = (pixeles_rojo / total_pixeles) * 100
        porcentaje_azul = (pixeles_azul / total_pixeles) * 100
        
        return {
            "amarillo": amarillo_detectado,
            "rojo": rojo_detectado,
            "azul": azul_detectado,
            "porcentajes": {
                "amarillo": porcentaje_amarillo,
                "rojo": porcentaje_rojo,
                "azul": porcentaje_azul
            },
            "pixeles": {
                "amarillo": pixeles_amarillo,
                "rojo": pixeles_rojo,
                "azul": pixeles_azul
            }
        }
        
    except Exception as e:
        st.error(f"Error en la detección de colores: {e}")
        return {
            "amarillo": False,
            "rojo": False,
            "azul": False,
            "porcentajes": {"amarillo": 0, "rojo": 0, "azul": 0},
            "pixeles": {"amarillo": 0, "rojo": 0, "azul": 0}
        }

# Función para enviar comandos de colores por MQTT
def enviar_colores_mqtt(deteccion_colores):
    """Envía los colores detectados por MQTT al ESP32"""
    try:
        client1 = paho.Client("streamlit-color-detection")
        client1.on_publish = on_publish
        client1.connect(broker, port)
        
        # Crear mensaje JSON con los colores detectados
        mensaje_colores = {
            "amarillo": deteccion_colores["amarillo"],
            "rojo": deteccion_colores["rojo"],
            "azul": deteccion_colores["azul"]
        }
        
        message = json.dumps(mensaje_colores)
        ret = client1.publish("appcolor", message)
        
        st.toast("🎨 Comando de colores enviado al ESP32", icon="✅")
        time.sleep(1)
        client1.disconnect()
        return True
    except Exception as e:
        st.error(f"❌ Error al enviar comando de colores: {e}")
        return False

# Inicializar session state
if 'last_command' not in st.session_state:
    st.session_state.last_command = ""
if 'last_received' not in st.session_state:
    st.session_state.last_received = ""
if 'uploaded_image' not in st.session_state:
    st.session_state.uploaded_image = None
if 'color_detection' not in st.session_state:
    st.session_state.color_detection = None

# Header principal
st.markdown('<div class="main-title">🎤 Control por Voz y Cámara</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Controla dispositivos IoT con comandos de voz o detección de colores</div>', unsafe_allow_html=True)

# Sección de comandos disponibles
with st.expander("📋 Comandos Disponibles", expanded=True):
    col1, col2 = st.columns(2)
    
    with col1:
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
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="command-list">
            <div class="command-item luz-principal"><strong>💡 Enciende la luz</strong> - Enciende luz principal</div>
            <div class="command-item luz-principal"><strong>🔌 Apaga la luz</strong> - Apaga luz principal</div>
            
            <div class="command-item puerta"><strong>🚪 Abre la puerta</strong> - Abre la puerta</div>
            <div class="command-item puerta"><strong>🚪 Cierra la puerta</strong> - Cierra la puerta</div>
            
            <div style="margin-top: 1rem; padding: 0.5rem; background: #E3F2FD; border-radius: 5px;">
                <small>🎨 <strong>Detección de Colores:</strong> Sube una imagen para detectar colores y controlar LEDs automáticamente</small>
            </div>
        </div>
        """, unsafe_allow_html=True)

# SECCIÓN DE DETECCIÓN DE COLORES POR CÁMARA
st.markdown("---")
st.markdown('<div class="camera-section">', unsafe_allow_html=True)
st.markdown("### 🎨 Detección de Colores desde Imagen")

# Subir imagen
uploaded_file = st.file_uploader("Sube una imagen para detectar colores (amarillo, rojo, azul)", 
                                type=['jpg', 'jpeg', 'png'])

if uploaded_file is not None:
    # Mostrar imagen
    imagen = Image.open(uploaded_file)
    st.image(imagen, caption="Imagen cargada", use_column_width=True)
    
    # Botón para procesar imagen
    if st.button("🔍 Analizar Colores en la Imagen", use_container_width=True):
        with st.spinner("Analizando colores..."):
            # Detectar colores
            deteccion = detectar_colores(imagen)
            st.session_state.color_detection = deteccion
            
            # Mostrar resultados
            st.markdown("### 📊 Resultados de la Detección")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if deteccion["amarillo"]:
                    st.markdown('<div class="color-indicator amarillo">🟡 AMARILLO DETECTADO</div>', unsafe_allow_html=True)
                    st.write(f"Porcentaje: {deteccion['porcentajes']['amarillo']:.2f}%")
                    st.write(f"Píxeles: {deteccion['pixeles']['amarillo']}")
                else:
                    st.markdown('<div class="color-indicator">⚫ AMARILLO NO DETECTADO</div>', unsafe_allow_html=True)
            
            with col2:
                if deteccion["rojo"]:
                    st.markdown('<div class="color-indicator rojo">🔴 ROJO DETECTADO</div>', unsafe_allow_html=True)
                    st.write(f"Porcentaje: {deteccion['porcentajes']['rojo']:.2f}%")
                    st.write(f"Píxeles: {deteccion['pixeles']['rojo']}")
                else:
                    st.markdown('<div class="color-indicator">⚫ ROJO NO DETECTADO</div>', unsafe_allow_html=True)
            
            with col3:
                if deteccion["azul"]:
                    st.markdown('<div class="color-indicator azul">🔵 AZUL DETECTADO</div>', unsafe_allow_html=True)
                    st.write(f"Porcentaje: {deteccion['porcentajes']['azul']:.2f}%")
                    st.write(f"Píxeles: {deteccion['pixeles']['azul']}")
                else:
                    st.markdown('<div class="color-indicator">⚫ AZUL NO DETECTADO</div>', unsafe_allow_html=True)
            
            # Enviar comandos automáticamente según los colores detectados
            if st.button("🚀 Aplicar Detección a los LEDs", use_container_width=True):
                if enviar_colores_mqtt(deteccion):
                    st.success("✅ Comandos de colores enviados exitosamente!")
                    
                    # Mostrar resumen de acciones
                    acciones = []
                    if deteccion["amarillo"]:
                        acciones.append("🟡 LED Amarillo ENCENDIDO")
                    else:
                        acciones.append("⚫ LED Amarillo APAGADO")
                    
                    if deteccion["rojo"]:
                        acciones.append("🔴 LED Rojo ENCENDIDO")
                    else:
                        acciones.append("⚫ LED Rojo APAGADO")
                    
                    if deteccion["azul"]:
                        acciones.append("🔵 LED Verde (como Azul) ENCENDIDO")
                    else:
                        acciones.append("⚫ LED Verde APAGADO")
                    
                    st.markdown("#### 💡 Acciones realizadas:")
                    for accion in acciones:
                        st.markdown(f"- {accion}")

st.markdown('</div>', unsafe_allow_html=True)

# SECCIÓN DE CONTROL POR VOZ (MANTENIENDO LA FUNCIONALIDAD ORIGINAL)
st.markdown("---")
st.markdown('<div class="voice-section">', unsafe_allow_html=True)
st.markdown("### 🎤 Control por Voz")

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

# Procesar eventos
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

# Mostrar resultados del comando
if result:
    if "GET_TEXT" in result:
        command = result.get("GET_TEXT").strip()
        
        # Normalizar el comando
        command = command.lower().strip(' .!?')
        st.session_state.last_command = command
        
        # Mostrar comando reconocido
        st.markdown("### 🎯 Comando Reconocido")
        st.markdown(f'<div class="result-box"><span style="font-size: 1.4rem; color: #7E57C2; font-weight: 600;">"{command}"</span></div>', unsafe_allow_html=True)
        
        # Mapeo de comandos más flexible con control de encendido/apagado
        command_mapping = {
            # Comandos para ENCENDER LED Amarillo
            'enciende el amarillo': 'enciende amarillo',
            'prende el amarillo': 'enciende amarillo',
            'enciende amarillo': 'enciende amarillo',
            'enciende la luz amarilla': 'enciende amarillo',
            'amarillo enciende': 'enciende amarillo',
            
            # Comandos para APAGAR LED Amarillo
            'apaga el amarillo': 'apaga amarillo',
            'apaga amarillo': 'apaga amarillo',
            
            # Comandos para ENCENDER LED Rojo
            'enciende el rojo': 'enciende rojo',
            'prende el rojo': 'enciende rojo',
            'enciende rojo': 'enciende rojo',
            'enciende la luz roja': 'enciende rojo',
            'rojo enciende': 'enciende rojo',
            
            # Comandos para APAGAR LED Rojo
            'apaga el rojo': 'apaga rojo',
            'apaga rojo': 'apaga rojo',
            
            # Comandos para ENCENDER LED Verde
            'enciende el verde': 'enciende verde',
            'prende el verde': 'enciende verde',
            'enciende verde': 'enciende verde',
            'enciende la luz verde': 'enciende verde',
            'verde enciende': 'enciende verde',
            
            # Comandos para APAGAR LED Verde
            'apaga el verde': 'apaga verde',
            'apaga verde': 'apaga verde',
            
            # Comandos para TODOS los LEDs
            'enciende todos los leds': 'enciende todos los leds',
            'prende todos los leds': 'enciende todos los leds',
            'enciende todos los led': 'enciende todos los leds',
            'apaga todos los leds': 'apaga todos los leds',
            'apaga todos los led': 'apaga todos los leds',
            
            # Comandos para luz principal
            'enciende las luces': 'enciende luz',
            'prende las luces': 'enciende luz', 
            'enciende la luz': 'enciende luz',
            'prende la luz': 'enciende luz',
            'apaga las luces': 'apaga luz',
            'apaga la luz': 'apaga luz',
            
            # Comandos para puerta
            'abre la puerta': 'abre puerta',
            'abre puerta': 'abre puerta',
            'cierra la puerta': 'cierra puerta',
            'cierra puerta': 'cierra puerta',
            
            # Comandos simples (sin "enciende/apaga" - por defecto encienden)
            'amarillo': 'enciende amarillo',
            'rojo': 'enciende rojo',
            'verde': 'enciende verde',
        }
        
        # Buscar comando similar
        normalized_command = command_mapping.get(command, command)
        
        # Determinar si es comando de encendido o apagado
        es_encendido = normalized_command.startswith('enciende')
        es_apagado = normalized_command.startswith('apaga')
        
        # Mostrar feedback visual del comando normalizado
        color_indicators = {
            'enciende amarillo': ('🟡 ENCENDIENDO LED AMARILLO', 'status-indicator'),
            'apaga amarillo': ('🔴 APAGANDO LED AMARILLO', 'status-indicator-off'),
            'enciende rojo': ('🔴 ENCENDIENDO LED ROJO', 'status-indicator'),
            'apaga rojo': ('🔴 APAGANDO LED ROJO', 'status-indicator-off'),
            'enciende verde': ('🟢 ENCENDIENDO LED VERDE', 'status-indicator'),
            'apaga verde': ('🔴 APAGANDO LED VERDE', 'status-indicator-off'),
            'enciende todos los leds': ('🌈 ENCENDIENDO TODOS LOS LEDs', 'status-indicator'),
            'apaga todos los leds': ('🔴 APAGANDO TODOS LOS LEDs', 'status-indicator-off'),
            'enciende luz': ('💡 ENCENDIENDO LUZ PRINCIPAL', 'status-indicator'),
            'apaga luz': ('🔌 APAGANDO LUZ PRINCIPAL', 'status-indicator-off'),
            'abre puerta': ('🚪 ABRIENDO PUERTA', 'status-indicator'),
            'cierra puerta': ('🚪 CERRANDO PUERTA', 'status-indicator-off')
        }
        
        mensaje, clase_css = color_indicators.get(normalized_command, (f'⚡ {normalized_command}', 'status-indicator'))
        
        st.markdown(f'<div class="{clase_css}">{mensaje}</div>', unsafe_allow_html=True)
        
        # Enviar comando por MQTT
        try:
            client1 = paho.Client("streamlit-voice-control")
            client1.on_publish = on_publish
            client1.connect(broker, port)
            message = json.dumps({"Act1": normalized_command})
            ret = client1.publish("appcolor", message)
            
            # Toast personalizado según el tipo de comando
            if es_encendido:
                st.toast(f"💡 Encendiendo: {normalized_command}", icon="✅")
            elif es_apagado:
                st.toast(f"🔌 Apagando: {normalized_command}", icon="🔴")
            else:
                st.toast(f"📡 Comando enviado: {normalized_command}", icon="✅")
                
            time.sleep(1)  # Dar tiempo para que se envíe el mensaje
            client1.disconnect()
        except Exception as e:
            st.error(f"❌ Error al enviar comando: {e}")

st.markdown('</div>', unsafe_allow_html=True)

# Historial de comandos
if st.session_state.last_command or st.session_state.color_detection:
    with st.expander("📊 Historial de Actividades", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            if st.session_state.last_command:
                st.metric("Último Comando de Voz", st.session_state.last_command)
        with col2:
            if st.session_state.color_detection:
                colores = []
                if st.session_state.color_detection["amarillo"]:
                    colores.append("Amarillo")
                if st.session_state.color_detection["rojo"]:
                    colores.append("Rojo")
                if st.session_state.color_detection["azul"]:
                    colores.append("Azul")
                st.metric("Última Detección", ", ".join(colores) if colores else "Ninguno")

# Información de conexión
with st.expander("🔧 Información de Conexión", expanded=False):
    st.write(f"**Broker MQTT:** `{broker}`")
    st.write(f"**Puerto:** `{port}`")
    st.write(f"**Tópico:** `appcolor`")
    st.write(f"**Cliente ID:** `streamlit-voice-control`")
    
    # Estado de conexión
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
    "Control por Voz y Cámara IoT | Streamlit + ESP32 + MQTT"
    "</div>", 
    unsafe_allow_html=True
)
