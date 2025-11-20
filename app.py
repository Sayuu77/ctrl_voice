import json
from gtts import gTTS
from googletrans import Translator
import cv2
import numpy as np
from io import BytesIO

# Configuración de página
st.set_page_config(
    page_title="Control por Voz y Cámara",
    page_title="Control por Voz",
    page_icon="🎤",
    layout="centered"
)
@@ -49,13 +46,6 @@
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
@@ -72,22 +62,7 @@
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
    .mic-button:hover {
        transform: scale(1.05);
        box-shadow: 0 12px 35px rgba(126, 87, 194, 0.4);
    }
@@ -100,14 +75,6 @@
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
@@ -128,17 +95,6 @@
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
@@ -187,253 +143,43 @@ def on_message(client, userdata, message):
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
st.markdown('<div class="main-title">🎤 Control por Voz</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Controla dispositivos IoT con comandos de voz</div>', unsafe_allow_html=True)

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
    </div>
    """, unsafe_allow_html=True)

# Icono de micrófono centrado
col1, col2, col3 = st.columns([1, 2, 1])
@@ -615,25 +361,14 @@ def enviar_colores_mqtt(deteccion_colores):
        except Exception as e:
            st.error(f"❌ Error al enviar comando: {e}")

st.markdown('</div>', unsafe_allow_html=True)

# Historial de comandos
if st.session_state.last_command or st.session_state.color_detection:
    with st.expander("📊 Historial de Actividades", expanded=True):
if st.session_state.last_command:
    with st.expander("📊 Historial de Comandos", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            if st.session_state.last_command:
                st.metric("Último Comando de Voz", st.session_state.last_command)
            st.metric("Último Comando", st.session_state.last_command)
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
            st.metric("Estado", "Enviado ✓")

# Información de conexión
with st.expander("🔧 Información de Conexión", expanded=False):
@@ -655,7 +390,7 @@ def enviar_colores_mqtt(deteccion_colores):
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666;'>"
    "Control por Voz y Cámara IoT | Streamlit + ESP32 + MQTT"
    "Control por Voz IoT | Streamlit + ESP32 + MQTT"
    "</div>", 
    unsafe_allow_html=True
)
