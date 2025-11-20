import os
import streamlit as st
from bokeh.models.widgets import Button
from bokeh.models import CustomJS
from streamlit_bokeh_events import streamlit_bokeh_events
from PIL import Image, ImageDraw
import time
import paho.mqtt.client as paho
import json
from gtts import gTTS
from googletrans import Translator
import base64
from openai import OpenAI
import openai
import io

# Function to encode the image to base64
def encode_image(image_file):
    return base64.b64encode(image_file.getvalue()).decode("utf-8")

# Function to crop image to the guide area
def crop_to_guide_area(image):
    """Crop image to only include the guide rectangle area"""
    width, height = image.size
    
    # Calculate crop area (70% of image size, centered)
    crop_width = int(width * 0.7)
    crop_height = int(height * 0.7)
    left = (width - crop_width) // 2
    top = (height - crop_height) // 2
    right = left + crop_width
    bottom = top + crop_height
    
    # Crop the image
    cropped_image = image.crop((left, top, right, bottom))
    
    return cropped_image

# Function to add guide rectangle to image
def add_guide_rectangle(image):
    """Add a guide rectangle directly to the image"""
    img = image.copy()
    draw = ImageDraw.Draw(img)
    
    # Calculate rectangle dimensions (70% of image size, centered)
    width, height = img.size
    rect_width = int(width * 0.7)
    rect_height = int(height * 0.7)
    x1 = (width - rect_width) // 2
    y1 = (height - rect_height) // 2
    x2 = x1 + rect_width
    y2 = y1 + rect_height
    
    # Draw thick red rectangle
    for i in range(4):  # Multiple lines for thicker border
        draw.rectangle([x1-i, y1-i, x2+i, y2+i], outline="red", width=1)
    
    # Add corner markers
    corner_size = 25
    # Top-left corner
    draw.line([x1, y1, x1 + corner_size, y1], fill="red", width=4)
    draw.line([x1, y1, x1, y1 + corner_size], fill="red", width=4)
    # Top-right corner
    draw.line([x2, y1, x2 - corner_size, y1], fill="red", width=4)
    draw.line([x2, y1, x2, y1 + corner_size], fill="red", width=4)
    # Bottom-left corner
    draw.line([x1, y2, x1 + corner_size, y2], fill="red", width=4)
    draw.line([x1, y2, x1, y2 - corner_size], fill="red", width=4)
    # Bottom-right corner
    draw.line([x2, y2, x2 - corner_size, y2], fill="red", width=4)
    draw.line([x2, y2, x2, y2 - corner_size], fill="red", width=4)
    
    # Add instructional text with background
    text = "COLOCA EL OBJETO DENTRO DEL CUADRO ROJO"
    text_width = draw.textlength(text)
    text_x = (width - text_width) // 2
    text_y = y1 - 40
    
    # Text background
    draw.rectangle([text_x-10, text_y-5, text_x + text_width + 10, text_y + 20], 
                   fill="white", outline="red", width=2)
    
    # Text
    draw.text((text_x, text_y), text, fill="red", stroke_width=1, stroke_fill="white")
    
    return img

# Function to convert PIL image to bytes for upload
def pil_to_bytes(pil_image):
    img_byte_arr = io.BytesIO()
    pil_image.save(img_byte_arr, format='JPEG')
    img_byte_arr.seek(0)
    return img_byte_arr

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

# Configuración de página
st.set_page_config(
    page_title="Control por Voz y Colores",
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
    .mic-button-container {
        display: flex;
        justify-content: center;
        align-items: center;
        margin: 2rem 0;
    }
    .mic-button-wrapper {
        position: relative;
        display: inline-flex;
        flex-direction: column;
        align-items: center;
        gap: 1rem;
    }
    .mic-button-main {
        background: linear-gradient(135deg, #7E57C2, #BA68C8);
        color: white;
        border: none;
        border-radius: 50%;
        width: 140px;
        height: 140px;
        font-size: 3.5rem;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 8px 25px rgba(126, 87, 194, 0.3);
        position: relative;
        z-index: 2;
    }
    .mic-button-main:hover {
        transform: scale(1.05);
        box-shadow: 0 12px 35px rgba(126, 87, 194, 0.4);
    }
    .mic-button-main.recording {
        animation: pulse 1.5s infinite;
        background: linear-gradient(135deg, #FF5252, #FF4081);
    }
    .mic-pulse {
        position: absolute;
        width: 160px;
        height: 160px;
        border-radius: 50%;
        background: rgba(126, 87, 194, 0.2);
        animation: sonar 2s infinite;
        z-index: 1;
    }
    .mic-label {
        font-size: 1.2rem;
        color: #7E57C2;
        font-weight: 600;
        text-align: center;
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
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
    }
    @keyframes sonar {
        0% {
            transform: scale(1);
            opacity: 0.8;
        }
        100% {
            transform: scale(1.3);
            opacity: 0;
        }
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
    .tab-content {
        padding: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Inicializar session state
if 'last_command' not in st.session_state:
    st.session_state.last_command = ""
if 'last_received' not in st.session_state:
    st.session_state.last_received = ""
if 'recording' not in st.session_state:
    st.session_state.recording = False

# Header principal
st.markdown('<div class="main-title">🎤 Control por Voz y Colores</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Controla dispositivos IoT con comandos de voz y detección de colores</div>', unsafe_allow_html=True)

# Tabs para separar funcionalidades
tab1, tab2 = st.tabs(["🎤 Control por Voz", "🎨 Detector de Colores"])

with tab1:
    st.markdown('<div class="tab-content">', unsafe_allow_html=True)
    
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

    # Sección de grabación de voz con diseño mejorado
    st.markdown('<div class="voice-section">', unsafe_allow_html=True)
    
    # Botón de micrófono rediseñado
    st.markdown('<div class="mic-button-container">', unsafe_allow_html=True)
    st.markdown('<div class="mic-button-wrapper">', unsafe_allow_html=True)
    
    # Elemento de pulso (solo se muestra visualmente)
    if st.session_state.recording:
        st.markdown('<div class="mic-pulse"></div>', unsafe_allow_html=True)
    
    # Botón principal de micrófono
    button_html = """
    <div class="mic-button-main %s" onclick="this.dispatchEvent(new CustomEvent('button_click', {bubbles: true}))">
        🎤
    </div>
    """ % ("recording" if st.session_state.recording else "")
    
    st.markdown(button_html, unsafe_allow_html=True)
    
    # Etiqueta del botón
    if st.session_state.recording:
        st.markdown('<div class="mic-label">🎙️ Grabando... Habla ahora</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="mic-label">Haz clic para hablar</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)  # Close wrapper
    st.markdown('</div>', unsafe_allow_html=True)  # Close container
    
    st.markdown('<div class="info-text">Haz clic en el micrófono y di tu comando de voz</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)  # Close voice-section

    # Botón de reconocimiento de voz (funcionalidad)
    stt_button = Button(label=" Iniciar Reconocimiento de Voz ", width=1, height=1, 
                       button_type="success")
    
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
        override_height=1,
        debounce_time=0
    )

    # Mostrar estado de grabación
    if result:
        if "RECORDING_START" in result:
            st.session_state.recording = True
            st.rerun()
        if "RECORDING_END" in result:
            st.session_state.recording = False
            st.rerun()
        if "RECORDING_ERROR" in result:
            st.session_state.recording = False
            st.error("❌ Error en el reconocimiento de voz")
            st.rerun()

    # Mostrar resultados del comando
    if result and "GET_TEXT" in result:
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

    st.markdown('</div>', unsafe_allow_html=True)  # Close tab-content

with tab2:
    st.markdown('<div class="tab-content">', unsafe_allow_html=True)
    
    with st.sidebar:
        st.subheader("Instrucciones Rápidas")
        st.markdown("""
        **🎨 Colores detectados:**
        - 🟡 AMARILLO
        - 🔴 ROJO
        - 🟢 VERDE
        
        **📸 Para usar:**
        1. Coloca objeto en el **cuadro rojo**
        2. Toma la foto
        3. Haz clic en **Detectar Colores**
        4. Solo el área del cuadro se analiza
        """)

    ke = st.text_input('Ingresa tu Clave de OpenAI', type="password", key="api_key")
    if ke:
        os.environ['OPENAI_API_KEY'] = ke

    api_key = os.environ.get('OPENAI_API_KEY')

    # Image source selection
    image_source = st.radio("Selecciona la fuente de la imagen:", 
                            ["Cámara Web", "Subir Archivo"], 
                            horizontal=True)

    uploaded_file = None
    cropped_image = None

    if image_source == "Cámara Web":
        st.subheader("📷 Captura con Guía Integrada")
        
        # Crear una imagen de ejemplo con la guía para mostrar cómo se verá
        st.info("🔴 **La cámara mostrará un cuadro rojo - coloca el objeto dentro de él**")
        
        # Primero mostrar cómo se verá
        example_img = Image.new('RGB', (400, 300), color='lightgray')
        example_with_guide = add_guide_rectangle(example_img)
        
        col_preview, col_instructions = st.columns([2, 1])
        
        with col_preview:
            st.image(example_with_guide, caption="Así se verá la guía en tu cámara", use_container_width=True)
        
        with col_instructions:
            st.markdown("""
            **✅ Posición correcta:**
            - Objeto completamente dentro
            - Centrado en el cuadro
            - Buena iluminación
            
            **❌ A evitar:**
            - Objeto fuera del cuadro
            - Muy lejos o muy cerca
            - Sombras fuertes
            """)
        
        # Ahora la cámara real - procesaremos la imagen después de capturarla
        st.markdown("---")
        st.subheader("🎥 Toma tu foto ahora")
        
        captured_image = st.camera_input(
            "Haz clic aquí para activar la cámara y tomar foto", 
            key="main_camera"
        )
        
        if captured_image is not None:
            # Procesar la imagen: agregar guía y luego recortar
            original_image = Image.open(captured_image)
            
            # Primero mostrar cómo se capturó con la guía superpuesta
            st.subheader("📸 Vista de lo capturado")
            
            # Crear versión con guía para mostrar al usuario
            image_with_guide = add_guide_rectangle(original_image)
            
            col_captured, col_analysis = st.columns(2)
            
            with col_captured:
                st.image(image_with_guide, caption="Así capturaste la imagen", use_container_width=True)
                st.markdown("**Área completa con guía visual**")
            
            with col_analysis:
                # Crear la imagen recortada para análisis
                cropped_image = crop_to_guide_area(original_image)
                st.image(cropped_image, caption="Esta área se analizará", use_container_width=True)
                st.markdown("**Solo esta parte se enviará para detección**")
            
            # Convertir imagen recortada para upload
            image_bytes = pil_to_bytes(cropped_image)
            uploaded_file = type('obj', (object,), {
                'getvalue': lambda: image_bytes.getvalue(),
                'name': 'objeto_analizado.jpg'
            })
            
            st.success("🎯 ¡Perfecto! El objeto está listo para análisis. Haz clic en 'Detectar Colores'")

    else:
        st.subheader("📁 Subir Imagen Existente")
        
        uploaded_original = st.file_uploader("Selecciona una imagen con el objeto", type=["jpg", "png", "jpeg"])
        
        if uploaded_original is not None:
            original_image = Image.open(uploaded_original)
            
            # Procesar imagen subida: agregar guía y mostrar
            st.subheader("📷 Vista Previa con Guía")
            
            image_with_guide = add_guide_rectangle(original_image)
            cropped_image = crop_to_guide_area(original_image)
            
            col_guide, col_crop = st.columns(2)
            
            with col_guide:
                st.image(image_with_guide, caption="Imagen con área de detección", use_container_width=True)
                st.markdown("**El cuadro rojo muestra el área de análisis**")
            
            with col_crop:
                st.image(cropped_image, caption="Área que se analizará", use_container_width=True)
                st.markdown("**Solo esta parte se procesará**")
            
            # Convertir imagen recortada para upload
            image_bytes = pil_to_bytes(cropped_image)
            uploaded_file = type('obj', (object,), {
                'getvalue': lambda: image_bytes.getvalue(),
                'name': 'objeto_analizado.jpg'
            })

    # Button to trigger the analysis
    analyze_button = st.button("🔍 Detectar Colores", type="primary", use_container_width=True, key="analyze_colors")

    # Check if an image has been uploaded and API key is available
    if uploaded_file is not None and api_key and analyze_button:

        with st.spinner("🎨 Analizando colores del objeto..."):
            # Encode the cropped image
            base64_image = encode_image(uploaded_file)
        
            # Simple prompt for basic color detection (solo amarillo, verde, rojo)
            prompt_text = """
            Analiza ESTA imagen y responde SOLO con un JSON que contenga:
            
            {
                "amarillo": true/false,
                "rojo": true/false,
                "verde": true/false
            }
            
            Reglas:
            - "true" si el color está presente en el objeto principal
            - "false" si el color NO está presente  
            - Analiza SOLO el objeto dentro del área visible
            - IGNORA fondos y elementos secundarios
            - Responde EXCLUSIVAMENTE con el JSON, nada más
            """
        
            # Make the request to the OpenAI API
            try:
                response = openai.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt_text},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{base64_image}",
                                    },
                                },
                            ],
                        }
                    ],
                    max_tokens=150,
                )
                
                # Display the response
                if response.choices[0].message.content:
                    st.markdown("---")
                    st.subheader("📊 Resultados de la Detección")
                    
                    # Parse the JSON response
                    try:
                        import json
                        result_text = response.choices[0].message.content.strip()
                        # Limpiar el texto en caso de que haya markdown
                        result_text = result_text.replace('```json', '').replace('```', '').strip()
                        color_data = json.loads(result_text)
                        
                        # Mostrar resultados
                        st.markdown("### 🎨 Colores Detectados en el Objeto")
                        
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.markdown("#### 🟡 Amarillo")
                            if color_data.get("amarillo", False):
                                st.success("**✅ DETECTADO**")
                                st.markdown("El color amarillo está presente")
                                # Enviar comando para encender LED amarillo
                                try:
                                    client1 = paho.Client("color-detection")
                                    client1.on_publish = on_publish
                                    client1.connect(broker, port)
                                    message = json.dumps({"Act1": "enciende amarillo"})
                                    client1.publish("appcolor", message)
                                    time.sleep(0.5)
                                    client1.disconnect()
                                    st.toast("💡 LED amarillo encendido", icon="✅")
                                except Exception as e:
                                    st.error(f"Error al controlar LED: {e}")
                            else:
                                st.error("**❌ NO DETECTADO**")
                                st.markdown("No se encontró amarillo")
                        
                        with col2:
                            st.markdown("#### 🔴 Rojo")
                            if color_data.get("rojo", False):
                                st.success("**✅ DETECTADO**")
                                st.markdown("El color rojo está presente")
                                # Enviar comando para encender LED rojo
                                try:
                                    client1 = paho.Client("color-detection")
                                    client1.on_publish = on_publish
                                    client1.connect(broker, port)
                                    message = json.dumps({"Act1": "enciende rojo"})
                                    client1.publish("appcolor", message)
                                    time.sleep(0.5)
                                    client1.disconnect()
                                    st.toast("💡 LED rojo encendido", icon="✅")
                                except Exception as e:
                                    st.error(f"Error al controlar LED: {e}")
                            else:
                                st.error("**❌ NO DETECTADO**")
                                st.markdown("No se encontró rojo")
                        
                        with col3:
                            st.markdown("#### 🟢 Verde")
                            if color_data.get("verde", False):
                                st.success("**✅ DETECTADO**")
                                st.markdown("El color verde está presente")
                                # Enviar comando para encender LED verde
                                try:
                                    client1 = paho.Client("color-detection")
                                    client1.on_publish = on_publish
                                    client1.connect(broker, port)
                                    message = json.dumps({"Act1": "enciende verde"})
                                    client1.publish("appcolor", message)
                                    time.sleep(0.5)
                                    client1.disconnect()
                                    st.toast("💡 LED verde encendido", icon="✅")
                                except Exception as e:
                                    st.error(f"Error al controlar LED: {e}")
                            else:
                                st.error("**❌ NO DETECTADO**")
                                st.markdown("No se encontró verde")
                                
                        # Resumen final
                        st.markdown("---")
                        colors_found = []
                        if color_data.get("amarillo"): colors_found.append("🟡 Amarillo")
                        if color_data.get("rojo"): colors_found.append("🔴 Rojo")
                        if color_data.get("verde"): colors_found.append("🟢 Verde")
                        
                        if colors_found:
                            st.success(f"**🎯 RESULTADO:** Se detectaron: {', '.join(colors_found)}")
                            # Si se detectaron colores, encender los LEDs correspondientes
                            st.info("💡 Los LEDs se han encendido automáticamente según los colores detectados")
                        else:
                            st.warning("**📝 RESULTADO:** No se detectaron los colores amarillo, rojo o verde en el objeto")
                            
                    except json.JSONDecodeError:
                        st.error("Error al procesar la respuesta del análisis.")
                        st.code(response.choices[0].message.content)
        
            except Exception as e:
                st.error(f"❌ Error en el análisis: {e}")
                st.info("Por favor verifica tu API key e intenta nuevamente")
                
    else:
        # Warnings for user action required
        if not uploaded_file and analyze_button:
            st.warning("⚠️ Primero captura o sube una imagen del objeto.")
        if not api_key and analyze_button:
            st.warning("🔑 Ingresa tu API key de OpenAI para continuar.")

    # Final tips
    with st.expander("💡 Consejos para mejor detección"):
        st.markdown("""
        **🎯 Para mejores resultados:**
        - **Posición:** Objeto centrado en el cuadro rojo
        - **Tamaño:** Que ocupe al menos 50% del área del cuadro  
        - **Iluminación:** Luz natural o artificial uniforme
        - **Fondo:** Preferiblemente neutro (blanco, gris, negro)
        - **Enfoque:** Imagen nítida y clara
        
        **🔍 Nota importante:**
        - Solo el área dentro del **cuadro rojo** se analiza
        - Todo lo fuera del cuadro se ignora
        - El análisis es específico para **amarillo, rojo y verde**
        - Los LEDs se encienden automáticamente según los colores detectados
        """)
    
    st.markdown('</div>', unsafe_allow_html=True)  # Close tab-content

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
    "Control por Voz y Colores IoT | Streamlit + ESP32 + MQTT + OpenAI"
    "</div>", 
    unsafe_allow_html=True
)
