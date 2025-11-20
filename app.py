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
    .color-detected {
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: bold;
        margin: 0.25rem;
        display: inline-block;
    }
    .color-yellow { background: #FFF9C4; color: #F57F17; border: 2px solid #FFEB3B; }
    .color-red { background: #FFEBEE; color: #C62828; border: 2px solid #F44336; }
    .color-green { background: #E8F5E8; color: #2E7D32; border: 2px solid #4CAF50; }
</style>
""", unsafe_allow_html=True)

# Función para detectar colores básica con PIL (sin OpenCV)
def detectar_colores(imagen):
    """
    Detecta los colores amarillo, verde y rojo en una imagen usando PIL
    Retorna un diccionario con los colores detectados
    """
    # Convertir la imagen a RGB si no lo está
    if imagen.mode != 'RGB':
        imagen = imagen.convert('RGB')
    
    # Reducir el tamaño de la imagen para mejorar el rendimiento
    imagen = imagen.resize((100, 100))
    
    # Obtener los píxeles de la imagen
    pixels = imagen.load()
    width, height = imagen.size
    
    # Contadores para cada color
    count_amarillo = 0
    count_verde = 0
    count_rojo = 0
    total_pixels = width * height
    
    # Definir rangos de colores en RGB
    for x in range(width):
        for y in range(height):
            r, g, b = pixels[x, y]
            
            # Detectar AMARILLO (alto en rojo y verde, bajo en azul)
            if r > 150 and g > 150 and b < 100 and abs(r - g) < 50:
                count_amarillo += 1
            
            # Detectar VERDE (alto en verde, bajo en rojo y azul)
            elif g > 100 and r < g * 0.8 and b < g * 0.8:
                count_verde += 1
            
            # Detectar ROJO (alto en rojo, bajo en verde y azul)
            elif r > 100 and g < r * 0.6 and b < r * 0.6:
                count_rojo += 1
    
    # Calcular porcentajes
    porcentaje_amarillo = (count_amarillo / total_pixels) * 100
    porcentaje_verde = (count_verde / total_pixels) * 100
    porcentaje_rojo = (count_rojo / total_pixels) * 100
    
    # Umbral para considerar que un color está presente
    umbral_deteccion = 0.5  # 0.5% de la imagen
    
    colores_detectados = {
        'amarillo': porcentaje_amarillo > umbral_deteccion,
        'verde': porcentaje_verde > umbral_deteccion,
        'rojo': porcentaje_rojo > umbral_deteccion,
        'porcentajes': {
            'amarillo': round(porcentaje_amarillo, 2),
            'verde': round(porcentaje_verde, 2),
            'rojo': round(porcentaje_rojo, 2)
        }
    }
    
    return colores_detectados

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
if 'foto_tomada' not in st.session_state:
    st.session_state.foto_tomada = None
if 'colores_detectados' not in st.session_state:
    st.session_state.colores_detectados = None

# Header principal
st.markdown('<div class="main-title">🎤 Control por Voz</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Controla dispositivos IoT con comandos de voz</div>', unsafe_allow_html=True)

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
            <small>💡 <strong>Nota:</strong> Los LEDs permanecen encendidos hasta que los apagues con un comando</small>
        </div>
    </div>
    """, unsafe_allow_html=True)

# SECCIÓN NUEVA: DETECCIÓN DE COLORES CON CÁMARA
st.markdown("---")
st.markdown("### 📷 Detección de Colores con Cámara")

# Tomar foto con la cámara
foto = st.camera_input("Toma una foto para detectar colores (amarillo, verde, rojo)")

if foto is not None:
    # Procesar la imagen
    imagen = Image.open(foto)
    st.session_state.foto_tomada = imagen
    
    # Detectar colores
    with st.spinner("🔍 Analizando colores en la imagen..."):
        colores_detectados = detectar_colores(imagen)
        st.session_state.colores_detectados = colores_detectados
    
    # Mostrar resultados
    st.markdown("### 🎨 Colores Detectados")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.image(imagen, caption="Foto tomada", use_column_width=True)
    
    with col2:
        # Mostrar qué colores se detectaron
        st.markdown("**Resultados de detección:**")
        
        if colores_detectados['amarillo']:
            st.markdown('<div class="color-detected color-yellow">🟡 AMARILLO Detectado</div>', unsafe_allow_html=True)
            st.write(f"Porcentaje: {colores_detectados['porcentajes']['amarillo']}%")
        
        if colores_detectados['verde']:
            st.markdown('<div class="color-detected color-green">🟢 VERDE Detectado</div>', unsafe_allow_html=True)
            st.write(f"Porcentaje: {colores_detectados['porcentajes']['verde']}%")
        
        if colores_detectados['rojo']:
            st.markdown('<div class="color-detected color-red">🔴 ROJO Detectado</div>', unsafe_allow_html=True)
            st.write(f"Porcentaje: {colores_detectados['porcentajes']['rojo']}%")
        
        # Si no se detectó ningún color
        if not any([colores_detectados['amarillo'], colores_detectados['verde'], colores_detectados['rojo']]):
            st.info("ℹ️ No se detectaron los colores amarillo, verde o rojo en la imagen.")
            st.write(f"Porcentajes: Amarillo: {colores_detectados['porcentajes']['amarillo']}%, Verde: {colores_detectados['porcentajes']['verde']}%, Rojo: {colores_detectados['porcentajes']['rojo']}%")
        
        # Botón para enviar comandos basados en colores detectados
        st.markdown("### 💡 Acciones Rápidas")
        colores_para_encender = []
        
        if colores_detectados['amarillo']:
            colores_para_encender.append("amarillo")
        if colores_detectados['verde']:
            colores_para_encender.append("verde")
        if colores_detectados['rojo']:
            colores_para_encender.append("rojo")
        
        if colores_para_encender:
            if st.button(f"🔄 Encender LEDs detectados ({', '.join(colores_para_encender)})"):
                try:
                    client1 = paho.Client("streamlit-color-detection")
                    client1.on_publish = on_publish
                    client1.connect(broker, port)
                    
                    for color in colores_para_encender:
                        message = json.dumps({"Act1": f"enciende {color}"})
                        ret = client1.publish("appcolor", message)
                        st.toast(f"💡 Encendiendo LED {color}", icon="✅")
                        time.sleep(0.5)  # Pequeña pausa entre comandos
                    
                    client1.disconnect()
                    st.success("✅ Comandos enviados exitosamente")
                except Exception as e:
                    st.error(f"❌ Error al enviar comandos: {e}")

# El resto del código original permanece igual...
# [Aquí va todo el resto de tu código original de control por voz]

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
    "Control por Voz IoT | Streamlit + ESP32 + MQTT | Detección de Colores"
    "</div>", 
    unsafe_allow_html=True
)
