# streamlit_app.py - VERSIÓN COMPATIBLE CON STREAMLIT CLOUD
import os
import streamlit as st
import base64
import openai
from PIL import Image, ImageDraw
import io
from bokeh.models.widgets import Button
from bokeh.models import CustomJS
from streamlit_bokeh_events import streamlit_bokeh_events
import time
import paho.mqtt.client as paho
import json

# Configuración de página
st.set_page_config(
    page_title="Sistema IoT: Voz + Visión",
    page_icon="🎤",
    layout="wide"
)

# Estilos CSS
st.markdown("""
<style>
    .main-title {
        font-size: 2.8rem;
        color: #7E57C2;
        text-align: center;
        margin-bottom: 0.5rem;
        font-weight: 700;
    }
    .section-title {
        font-size: 1.5rem;
        color: #7E57C2;
        margin: 1.5rem 0 1rem 0;
        border-bottom: 2px solid #D1C4E9;
        padding-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Funciones auxiliares
def encode_image(image_file):
    return base64.b64encode(image_file.getvalue()).decode("utf-8")

def crop_to_guide_area(image):
    width, height = image.size
    crop_width = int(width * 0.7)
    crop_height = int(height * 0.7)
    left = (width - crop_width) // 2
    top = (height - crop_height) // 2
    right = left + crop_width
    bottom = top + crop_height
    return image.crop((left, top, right, bottom))

def add_guide_rectangle(image):
    img = image.copy()
    draw = ImageDraw.Draw(img)
    width, height = img.size
    rect_width = int(width * 0.7)
    rect_height = int(height * 0.7)
    x1 = (width - rect_width) // 2
    y1 = (height - rect_height) // 2
    x2 = x1 + rect_width
    y2 = y1 + rect_height
    
    for i in range(4):
        draw.rectangle([x1-i, y1-i, x2+i, y2+i], outline="red", width=1)
    
    return img

def pil_to_bytes(pil_image):
    img_byte_arr = io.BytesIO()
    pil_image.save(img_byte_arr, format='JPEG')
    img_byte_arr.seek(0)
    return img_byte_arr

# Callbacks MQTT
def on_publish(client, userdata, result):
    st.toast("Comando enviado exitosamente", icon="✅")

# Configuración
broker = "broker.mqttdashboard.com"
port = 1883

# Inicializar session state
if 'last_command' not in st.session_state:
    st.session_state.last_command = ""
if 'color_results' not in st.session_state:
    st.session_state.color_results = None

# Interfaz principal
st.markdown('<div class="main-title">🤖 Sistema IoT: Control por Voz + Visión</div>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.subheader("🔧 Configuración")
    api_key = st.text_input('Clave de OpenAI', type="password")
    if api_key:
        openai.api_key = api_key

# Pestañas
tab1, tab2 = st.tabs(["🎤 Control por Voz", "📷 Detección de Colores"])

with tab1:
    st.markdown('<div class="section-title">🎤 Control por Comandos de Voz</div>', unsafe_allow_html=True)
    
    stt_button = Button(label=" Iniciar Reconocimiento de Voz ", width=300, height=60)
    stt_button.js_on_event("button_click", CustomJS(code="""
        var recognition = new webkitSpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'es-ES';

        recognition.onresult = function (e) {
            var value = e.results[0][0].transcript;
            if ( value != "") {
                document.dispatchEvent(new CustomEvent("GET_TEXT", {detail: value}));
            }
        }
        recognition.start();
    """))

    result = streamlit_bokeh_events(
        stt_button,
        events="GET_TEXT",
        key="listen",
        refresh_on_update=False,
        override_height=80,
        debounce_time=0
    )

    if result and "GET_TEXT" in result:
        command = result.get("GET_TEXT").strip().lower()
        st.session_state.last_command = command
        
        st.markdown(f"**Comando reconocido:** `{command}`")
        
        # Enviar comando MQTT
        try:
            client = paho.Client("streamlit-voice")
            client.on_publish = on_publish
            client.connect(broker, port)
            
            command_mapping = {
                'rojo': 'enciende rojo',
                'amarillo': 'enciende amarillo', 
                'verde': 'enciende verde',
                'apaga rojo': 'apaga rojo',
                'apaga amarillo': 'apaga amarillo',
                'apaga verde': 'apaga verde',
                'enciende todos': 'enciende todos los leds',
                'apaga todos': 'apaga todos los leds'
            }
            
            normalized_command = command_mapping.get(command, command)
            message = json.dumps({"Act1": normalized_command})
            client.publish("appcolor", message)
            client.disconnect()
            
            st.success(f"Comando enviado: {normalized_command}")
        except Exception as e:
            st.error(f"Error: {e}")

with tab2:
    st.markdown('<div class="section-title">📷 Detección de Colores por Cámara</div>', unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader("Sube una imagen", type=["jpg", "png", "jpeg"])
    
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        processed_image = add_guide_rectangle(image)
        cropped_image = crop_to_guide_area(image)
        
        col1, col2 = st.columns(2)
        with col1:
            st.image(processed_image, caption="Área de análisis", use_container_width=True)
        with col2:
            st.image(cropped_image, caption="Imagen recortada para análisis", use_container_width=True)
        
        if st.button("🔍 Analizar Colores") and api_key:
            with st.spinner("Analizando colores..."):
                try:
                    image_bytes = pil_to_bytes(cropped_image)
                    base64_image = encode_image(image_bytes)
                    
                    response = openai.ChatCompletion.create(
                        model="gpt-4-vision-preview",
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": "Analiza esta imagen y responde SOLO con JSON: {'rojo': true/false, 'amarillo': true/false, 'verde': true/false} para los colores detectados en el objeto principal."},
                                    {
                                        "type": "image_url",
                                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                                    }
                                ]
                            }
                        ],
                        max_tokens=300
                    )
                    
                    result_text = response.choices[0].message.content
                    st.write("Resultado:", result_text)
                    
                except Exception as e:
                    st.error(f"Error en el análisis: {e}")

# Footer
st.markdown("---")
st.markdown("Sistema IoT Integrado | Control por Voz + Visión")
