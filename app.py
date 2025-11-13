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

# Configuración de página
st.set_page_config(
    page_title="Control por Voz",
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
    .mic-button:hover {
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

# Inicializar session state
if 'last_command' not in st.session_state:
    st.session_state.last_command = ""
if 'last_received' not in st.session_state:
    st.session_state.last_received = ""

# Header principal
st.markdown('<div class="main-title">🎤 Control por Voz</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Controla dispositivos IoT con comandos de voz</div>', unsafe_allow_html=True)

# Sección de comandos disponibles
with st.expander("📋 Comandos Disponibles", expanded=True):
    st.markdown("""
    <div class="command-list">
        <div class="command-item led-amarillo"><strong>💡 Amarillo</strong> - Enciende el LED amarillo (3 segundos)</div>
        <div class="command-item led-rojo"><strong>🔴 Rojo</strong> - Enciende el LED rojo (3 segundos)</div>
        <div class="command-item led-verde"><strong>🟢 Verde</strong> - Enciende el LED verde (3 segundos)</div>
        <div class="command-item led-todos"><strong>🌈 Todos los LEDs</strong> - Enciende todos los LEDs (3 segundos)</div>
        <div class="command-item luz-principal"><strong>💡 Enciende la luz</strong> - Enciende la luz principal</div>
        <div class="command-item luz-principal"><strong>🔌 Apaga la luz</strong> - Apaga la luz principal</div>
        <div class="command-item puerta"><strong>🚪 Abre la puerta</strong> - Abre la puerta</div>
        <div class="command-item puerta"><strong>🚪 Cierra la puerta</strong> - Cierra la puerta</div>
    </div>
    """, unsafe_allow_html=True)

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
        
        # Mapeo de comandos más flexible con nuevos LEDs
        command_mapping = {
            # Comandos para LED Amarillo
            'amarillo': 'amarillo',
            'luz amarilla': 'amarillo',
            'prende el amarillo': 'amarillo',
            'enciende el amarillo': 'amarillo',
            'enciende la luz amarilla': 'amarillo',
            'led amarillo': 'amarillo',
            
            # Comandos para LED Rojo
            'rojo': 'rojo',
            'luz roja': 'rojo',
            'prende el rojo': 'rojo',
            'enciende el rojo': 'rojo',
            'enciende la luz roja': 'rojo',
            'led rojo': 'rojo',
            
            # Comandos para LED Verde
            'verde': 'verde',
            'luz verde': 'verde',
            'prende el verde': 'verde',
            'enciende el verde': 'verde',
            'enciende la luz verde': 'verde',
            'led verde': 'verde',
            
            # Comandos para todos los LEDs
            'todos los leds': 'todos los leds',
            'todos los led': 'todos los leds',
            'enciende todos los leds': 'todos los leds',
            'prende todos los leds': 'todos los leds',
            'todos': 'todos los leds',
            
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
            'abre': 'abre puerta',
            'cierra la puerta': 'cierra puerta',
            'cierra puerta': 'cierra puerta',
            'cierra': 'cierra puerta'
        }
        
        # Buscar comando similar
        normalized_command = command_mapping.get(command, command)
        
        # Mostrar feedback visual del comando normalizado
        color_indicators = {
            'amarillo': '🟡',
            'rojo': '🔴', 
            'verde': '🟢',
            'todos los leds': '🌈',
            'enciende luz': '💡',
            'apaga luz': '🔌',
            'abre puerta': '🚪',
            'cierra puerta': '🚪'
        }
        
        emoji = color_indicators.get(normalized_command, '⚡')
        
        st.markdown(f'<div class="status-indicator">{emoji} Comando normalizado: "{normalized_command}"</div>', unsafe_allow_html=True)
        
        # Enviar comando por MQTT
        try:
            client1 = paho.Client("streamlit-voice-control")
            client1.on_publish = on_publish
            client1.connect(broker, port)
            message = json.dumps({"Act1": normalized_command})
            ret = client1.publish("appcolor", message)
            st.toast(f"📡 Comando enviado: {normalized_command}", icon="✅")
            time.sleep(1)  # Dar tiempo para que se envíe el mensaje
            client1.disconnect()
        except Exception as e:
            st.error(f"❌ Error al enviar comando: {e}")

# Historial de comandos
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
    "Control por Voz IoT | Streamlit + ESP32 + MQTT"
    "</div>", 
    unsafe_allow_html=True
)
