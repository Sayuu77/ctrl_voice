import streamlit as st
import pyaudio
import wave
import speech_recognition as sr
import cv2
import numpy as np
from PIL import Image
import time
import json
import paho.mqtt.client as mqtt
import threading

# Configuración de la página
st.set_page_config(
    page_title="Control de LEDs por Voz y Cámara",
    page_icon="🎮",
    layout="wide"
)

# Variables globales para MQTT
MQTT_BROKER = "broker.mqttdashboard.com"
MQTT_TOPIC = "appcolor"
mqtt_client = None

# Inicializar el reconocedor de voz
recognizer = sr.Recognizer()

# Configuración MQTT
def setup_mqtt():
    global mqtt_client
    try:
        mqtt_client = mqtt.Client("streamlit_app")
        mqtt_client.connect(MQTT_BROKER, 1883, 60)
        mqtt_client.loop_start()
        return True
    except Exception as e:
        st.error(f"Error conectando a MQTT: {e}")
        return False

# Función para enviar comandos a Arduino
def send_command(command):
    global mqtt_client
    if mqtt_client:
        try:
            message = json.dumps({"Act1": command})
            mqtt_client.publish(MQTT_TOPIC, message)
            st.success(f"Comando enviado: {command}")
            return True
        except Exception as e:
            st.error(f"Error enviando comando: {e}")
            return False
    else:
        st.error("Cliente MQTT no conectado")
        return False

# Función para grabar audio
def record_audio(filename, duration=3):
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100
    
    p = pyaudio.PyAudio()
    
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)
    
    st.info("🎙️ Grabando... Habla ahora!")
    frames = []
    
    for i in range(0, int(RATE / CHUNK * duration)):
        data = stream.read(CHUNK)
        frames.append(data)
    
    stream.stop_stream()
    stream.close()
    p.terminate()
    
    # Guardar archivo WAV
    wf = wave.open(filename, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

# Función para transcribir audio
def transcribe_audio(filename):
    try:
        with sr.AudioFile(filename) as source:
            audio = recognizer.record(source)
        
        text = recognizer.recognize_google(audio, language='es-ES')
        return text.lower()
    except sr.UnknownValueError:
        return None
    except sr.RequestError as e:
        st.error(f"Error en el servicio de reconocimiento: {e}")
        return None

# Función para procesar comandos de voz
def process_voice_command(command):
    command = command.lower().strip()
    
    # Mapeo de comandos de voz a acciones
    command_mapping = {
        'rojo': 'rojo',
        'amarillo': 'amarillo', 
        'verde': 'verde',
        'encender rojo': 'rojo',
        'encender amarillo': 'amarillo',
        'encender verde': 'verde',
        'prender rojo': 'rojo',
        'prender amarillo': 'amarillo', 
        'prender verde': 'verde',
        'apagar todo': 'apaga todos los leds',
        'encender todos': 'enciende todos los leds',
        'apagar rojo': 'apaga rojo',
        'apagar amarillo': 'apaga amarillo',
        'apagar verde': 'apaga verde',
        'luz': 'enciende luz',
        'apagar luz': 'apaga luz',
        'abrir puerta': 'abre puerta',
        'cerrar puerta': 'cierra puerta'
    }
    
    # Buscar coincidencia exacta o parcial
    for voice_cmd, action in command_mapping.items():
        if voice_cmd in command:
            return action
    
    # Si no encuentra coincidencia, intentar con palabras individuales
    words = command.split()
    for word in words:
        if word in ['rojo', 'amarillo', 'verde']:
            return word
    
    return None

# Función para detectar colores en la imagen
def detect_colors(image):
    # Convertir PIL Image a OpenCV
    img_cv = np.array(image)
    img_cv = cv2.cvtColor(img_cv, cv2.COLOR_RGB2BGR)
    
    # Convertir a HSV para mejor detección de colores
    hsv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2HSV)
    
    # Definir rangos de colores en HSV
    # Rojo
    red_lower1 = np.array([0, 120, 70])
    red_upper1 = np.array([10, 255, 255])
    red_lower2 = np.array([170, 120, 70])
    red_upper2 = np.array([180, 255, 255])
    
    # Amarillo
    yellow_lower = np.array([20, 100, 100])
    yellow_upper = np.array([30, 255, 255])
    
    # Verde
    green_lower = np.array([36, 100, 100])
    green_upper = np.array([86, 255, 255])
    
    # Crear máscaras
    red_mask1 = cv2.inRange(hsv, red_lower1, red_upper1)
    red_mask2 = cv2.inRange(hsv, red_lower2, red_upper2)
    red_mask = cv2.bitwise_or(red_mask1, red_mask2)
    
    yellow_mask = cv2.inRange(hsv, yellow_lower, yellow_upper)
    green_mask = cv2.inRange(hsv, green_lower, green_upper)
    
    # Calcular porcentaje de cada color
    total_pixels = img_cv.shape[0] * img_cv.shape[1]
    
    red_percent = (cv2.countNonZero(red_mask) / total_pixels) * 100
    yellow_percent = (cv2.countNonZero(yellow_mask) / total_pixels) * 100
    green_percent = (cv2.countNonZero(green_mask) / total_pixels) * 100
    
    detected_colors = []
    
    # Umbral para considerar que el color está presente
    threshold = 1.0  # 1% de la imagen
    
    if red_percent > threshold:
        detected_colors.append('rojo')
    if yellow_percent > threshold:
        detected_colors.append('amarillo')
    if green_percent > threshold:
        detected_colors.append('verde')
    
    # Crear imagen con detecciones visuales
    result_img = img_cv.copy()
    
    # Resaltar áreas detectadas
    if 'rojo' in detected_colors:
        result_img[red_mask > 0] = [0, 0, 255]  # Rojo en BGR
    if 'amarillo' in detected_colors:
        result_img[yellow_mask > 0] = [0, 255, 255]  # Amarillo en BGR
    if 'verde' in detected_colors:
        result_img[green_mask > 0] = [0, 255, 0]  # Verde en BGR
    
    result_img = cv2.cvtColor(result_img, cv2.COLOR_BGR2RGB)
    
    return detected_colors, result_img, {
        'rojo': red_percent,
        'amarillo': yellow_percent, 
        'verde': green_percent
    }

# Interfaz principal de Streamlit
def main():
    st.title("🎮 Control de LEDs por Voz y Cámara")
    st.markdown("Controla los LEDs mediante comandos de voz o detección de colores por cámara")
    
    # Inicializar MQTT
    if 'mqtt_connected' not in st.session_state:
        st.session_state.mqtt_connected = setup_mqtt()
    
    # Sidebar para controles
    with st.sidebar:
        st.header("⚙️ Configuración")
        
        st.subheader("Control por Voz")
        voice_duration = st.slider("Duración de grabación (segundos)", 1, 5, 3)
        
        st.subheader("Control por Cámara")
        camera_col = st.color_picker("Color de referencia", "#FF0000")
        detection_threshold = st.slider("Umbral de detección (%)", 0.1, 5.0, 1.0)
        
        st.subheader("Estado del Sistema")
        if st.session_state.mqtt_connected:
            st.success("✅ Conectado a MQTT")
        else:
            st.error("❌ No conectado a MQTT")
    
    # Crear pestañas para diferentes funcionalidades
    tab1, tab2, tab3 = st.tabs(["🎤 Control por Voz", "📷 Control por Cámara", "🎯 Comandos Rápidos"])
    
    with tab1:
        st.header("Control por Comandos de Voz")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Grabar Comando")
            if st.button("🎤 Iniciar Grabación de Voz", use_container_width=True):
                with st.spinner("Preparando grabación..."):
                    audio_file = "voice_command.wav"
                    record_audio(audio_file, voice_duration)
                    
                    # Transcribir audio
                    transcribed_text = transcribe_audio(audio_file)
                    
                    if transcribed_text:
                        st.success(f"🎯 Comando detectado: '{transcribed_text}'")
                        
                        # Procesar comando
                        command = process_voice_command(transcribed_text)
                        if command:
                            if send_command(command):
                                st.balloons()
                        else:
                            st.error("Comando no reconocido. Intenta con: 'rojo', 'amarillo', 'verde', etc.")
                    else:
                        st.error("No se pudo entender el comando. Intenta nuevamente.")
        
        with col2:
            st.subheader("Comandos de Voz Disponibles")
            st.markdown("""
            **Colores básicos:**
            - "rojo", "amarillo", "verde"
            
            **Comandos completos:**
            - "encender rojo/amarillo/verde"
            - "apagar rojo/amarillo/verde" 
            - "encender todos", "apagar todo"
            - "luz", "apagar luz"
            - "abrir puerta", "cerrar puerta"
            """)
            
            st.subheader("Último Comando")
            if 'last_command' in st.session_state:
                st.info(f"Último comando: {st.session_state.last_command}")
    
    with tab2:
        st.header("Control por Detección de Colores")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Capturar Imagen")
            camera_input = st.camera_input("Toma una foto con la cámara")
            
            if camera_input is not None:
                image = Image.open(camera_input)
                
                # Detectar colores
                detected_colors, result_img, percentages = detect_colors(image)
                
                # Mostrar resultados
                st.subheader("Resultados de Detección")
                
                if detected_colors:
                    st.success(f"🎨 Colores detectados: {', '.join(detected_colors)}")
                    
                    # Encender LEDs según colores detectados
                    for color in detected_colors:
                        if send_command(color):
                            st.info(f"✅ Encendiendo LED {color}")
                else:
                    st.warning("⚠️ No se detectaron los colores buscados")
                
                # Mostrar porcentajes
                st.write("**Porcentajes de detección:**")
                for color, percent in percentages.items():
                    st.write(f"- {color.capitalize()}: {percent:.2f}%")
        
        with col2:
            st.subheader("Imagen Procesada")
            if camera_input is not None:
                st.image(result_img, caption="Áreas de color detectadas", use_column_width=True)
                
                # Leyenda de colores
                st.markdown("""
                **Leyenda:**
                - 🔴 Rojo: LED Rojo
                - 🟡 Amarillo: LED Amarillo  
                - 🟢 Verde: LED Verde
                """)
    
    with tab3:
        st.header("Comandos Rápidos")
        
        st.subheader("Control Individual de LEDs")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔴 Encender Rojo", use_container_width=True):
                send_command("rojo")
            if st.button("⚫ Apagar Rojo", use_container_width=True):
                send_command("apaga rojo")
                
        with col2:
            if st.button("🟡 Encender Amarillo", use_container_width=True):
                send_command("amarillo")
            if st.button("⚫ Apagar Amarillo", use_container_width=True):
                send_command("apaga amarillo")
                
        with col3:
            if st.button("🟢 Encender Verde", use_container_width=True):
                send_command("verde")
            if st.button("⚫ Apagar Verde", use_container_width=True):
                send_command("apaga verde")
        
        st.subheader("Control Grupal")
        col4, col5 = st.columns(2)
        
        with col4:
            if st.button("🎯 Encender Todos los LEDs", use_container_width=True):
                send_command("enciende todos los leds")
                
        with col5:
            if st.button("💤 Apagar Todos los LEDs", use_container_width=True):
                send_command("apaga todos los leds")
        
        st.subheader("Otros Controles")
        col6, col7, col8 = st.columns(3)
        
        with col6:
            if st.button("💡 Encender Luz", use_container_width=True):
                send_command("enciende luz")
            if st.button("🌙 Apagar Luz", use_container_width=True):
                send_command("apaga luz")
                
        with col7:
            if st.button("🚪 Abrir Puerta", use_container_width=True):
                send_command("abre puerta")
                
        with col8:
            if st.button("🔒 Cerrar Puerta", use_container_width=True):
                send_command("cierra puerta")

    # Footer
    st.markdown("---")
    st.markdown("### 📊 Estado del Sistema")
    
    status_col1, status_col2, status_col3 = st.columns(3)
    
    with status_col1:
        st.metric("Conexión MQTT", "Conectado" if st.session_state.mqtt_connected else "Desconectado")
    
    with status_col2:
        st.metric("Servicio de Voz", "Activo")
    
    with status_col3:
        st.metric("Detección de Colores", "Listo")

# Instrucciones de instalación
def show_installation_instructions():
    st.sidebar.markdown("---")
    st.sidebar.header("📋 Instalación Requerida")
    st.sidebar.markdown("""
    ```bash
    pip install streamlit pyaudio speechrecognition opencv-python pillow paho-mqtt
    ```
    
    **Nota para Windows:**
    - Puede necesitar `pip install pipwin` y luego `pipwin install pyaudio`
    
    **Nota para macOS:**
    - `brew install portaudio`
    - `pip install pyaudio`
    """)

if __name__ == "__main__":
    show_installation_instructions()
    main()
