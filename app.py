import streamlit as st
import cv2
import numpy as np
import paho.mqtt.client as mqtt
from PIL import Image
import io
import time
import speech_recognition as sr

# Configuración MQTT
MQTT_BROKER = "broker.mqttdashboard.com"
MQTT_TOPIC = "appcolor"

class LEDController:
    def __init__(self):
        self.mqtt_client = mqtt.Client()
        self.setup_mqtt()
        
    def setup_mqtt(self):
        try:
            self.mqtt_client.connect(MQTT_BROKER, 1883, 60)
            self.mqtt_client.loop_start()
        except Exception as e:
            st.error(f"Error conectando a MQTT: {e}")
    
    def send_command(self, command):
        """Envía comando a Arduino via MQTT"""
        try:
            message = f'{{"Act1":"{command}"}}'
            self.mqtt_client.publish(MQTT_TOPIC, message)
            st.success(f"Comando enviado: {command}")
            return True
        except Exception as e:
            st.error(f"Error enviando comando: {e}")
            return False

class ColorDetector:
    def __init__(self):
        # Rangos de color en HSV
        self.color_ranges = {
            'rojo': [
                (np.array([0, 120, 70]), np.array([10, 255, 255])),
                (np.array([170, 120, 70]), np.array([180, 255, 255]))
            ],
            'verde': [(np.array([40, 40, 40]), np.array([80, 255, 255]))],
            'amarillo': [(np.array([20, 100, 100]), np.array([30, 255, 255]))]
        }
    
    def detect_colors(self, image):
        """Detecta colores rojo, verde y amarillo en la imagen"""
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        detected_colors = []
        
        for color_name, ranges in self.color_ranges.items():
            mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
            
            for lower, upper in ranges:
                color_mask = cv2.inRange(hsv, lower, upper)
                mask = cv2.bitwise_or(mask, color_mask)
            
            # Encontrar contornos
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if area > 500:  # Área mínima para considerar detección
                    detected_colors.append(color_name)
                    break
        
        return list(set(detected_colors))  # Remover duplicados

class VoiceController:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # Comandos de voz reconocidos
        self.voice_commands = {
            'rojo': 'rojo',
            'verde': 'verde', 
            'amarillo': 'amarillo',
            'encender todos': 'enciende todos los leds',
            'apagar todos': 'apaga todos los leds',
            'encender luz': 'enciende luz',
            'apagar luz': 'apaga luz'
        }
    
    def listen_command(self):
        """Escucha y reconoce comandos de voz"""
        try:
            with self.microphone as source:
                st.info("Escuchando... Habla ahora")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=3)
            
            try:
                text = self.recognizer.recognize_google(audio, language='es-ES').lower()
                st.success(f"Reconocido: {text}")
                return text
            except sr.UnknownValueError:
                st.error("No se pudo entender el audio")
                return None
            except sr.RequestError:
                st.error("Error en el servicio de reconocimiento")
                return None
                
        except sr.WaitTimeoutError:
            st.error("Tiempo de espera agotado")
            return None
        except Exception as e:
            st.error(f"Error en reconocimiento de voz: {e}")
            return None
    
    def process_voice_command(self, text):
        """Procesa el texto reconocido y devuelve el comando correspondiente"""
        if not text:
            return None
            
        for voice_cmd, arduino_cmd in self.voice_commands.items():
            if voice_cmd in text:
                return arduino_cmd
        
        # Comandos simples de colores
        if any(color in text for color in ['rojo', 'verde', 'amarillo']):
            for color in ['rojo', 'verde', 'amarillo']:
                if color in text:
                    return color
        
        return None

def main():
    st.set_page_config(page_title="Control de LEDs por Voz y Cámara", layout="wide")
    
    st.title("🎤 Control de LEDs por Voz y Cámara")
    st.markdown("Controla LEDs Arduino con comandos de voz o detección de colores desde la cámara")
    
    # Inicializar controladores
    if 'led_controller' not in st.session_state:
        st.session_state.led_controller = LEDController()
    if 'color_detector' not in st.session_state:
        st.session_state.color_detector = ColorDetector()
    if 'voice_controller' not in st.session_state:
        st.session_state.voice_controller = VoiceController()
    
    # Sidebar para controles manuales
    with st.sidebar:
        st.header("🔄 Controles Manuales")
        
        st.subheader("Controles Individuales")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔴 Rojo"):
                st.session_state.led_controller.send_command("rojo")
            if st.button("🟢 Verde"):
                st.session_state.led_controller.send_command("verde")
            if st.button("🟡 Amarillo"):
                st.session_state.led_controller.send_command("amarillo")
        
        with col2:
            if st.button("💡 Luz"):
                st.session_state.led_controller.send_command("enciende luz")
            if st.button("🚪 Abrir Puerta"):
                st.session_state.led_controller.send_command("abre puerta")
            if st.button("🔒 Cerrar Puerta"):
                st.session_state.led_controller.send_command("cierra puerta")
        
        st.subheader("Controles Grupales")
        if st.button("✨ Encender Todos"):
            st.session_state.led_controller.send_command("enciende todos los leds")
        if st.button("💤 Apagar Todos"):
            st.session_state.led_controller.send_command("apaga todos los leds")
    
    # Pestañas principales
    tab1, tab2 = st.tabs(["🎤 Control por Voz", "📷 Detección por Cámara"])
    
    with tab1:
        st.header("Control por Comandos de Voz")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Instrucciones de Voz")
            st.markdown("""
            **Comandos reconocidos:**
            - **Colores simples**: "rojo", "verde", "amarillo"
            - **Comandos completos**: "encender todos", "apagar todos"
            - **Control de luz**: "encender luz", "apagar luz"
            """)
            
            if st.button("🎤 Iniciar Reconocimiento de Voz", type="primary"):
                with st.spinner("Procesando comando de voz..."):
                    voice_text = st.session_state.voice_controller.listen_command()
                    
                    if voice_text:
                        command = st.session_state.voice_controller.process_voice_command(voice_text)
                        if command:
                            st.session_state.led_controller.send_command(command)
                        else:
                            st.warning("Comando de voz no reconocido")
        
        with col2:
            st.subheader("Estado Actual")
            st.info("Listo para recibir comandos de voz")
            
            st.subheader("Comandos Rápidos")
            quick_commands = ["rojo", "verde", "amarillo", "enciende todos los leds"]
            for cmd in quick_commands:
                if st.button(f"Decir: '{cmd}'", key=f"quick_{cmd}"):
                    st.session_state.led_controller.send_command(cmd)
    
    with tab2:
        st.header("Detección de Colores por Cámara")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Captura de Imagen")
            picture = st.camera_input("Toma una foto para detectar colores")
            
            if picture is not None:
                # Convertir la imagen a formato OpenCV
                image_data = picture.getvalue()
                image = Image.open(io.BytesIO(image_data))
                image_np = np.array(image)
                
                # Detectar colores
                detected_colors = st.session_state.color_detector.detect_colors(image_np)
                
                # Mostrar resultados
                st.subheader("Resultados de Detección")
                if detected_colors:
                    st.success(f"Colores detectados: {', '.join(detected_colors)}")
                    
                    # Encender LEDs según colores detectados
                    for color in detected_colors:
                        st.session_state.led_controller.send_command(color)
                        time.sleep(0.5)  # Pequeña pausa entre comandos
                else:
                    st.warning("No se detectaron colores (rojo, verde, amarillo)")
                
                # Mostrar imagen procesada
                st.image(image, caption="Imagen capturada", use_column_width=True)
        
        with col2:
            st.subheader("Información de Detección")
            st.markdown("""
            **Colores que detecta:**
            - 🔴 **Rojo**: LEDs rojos, objetos rojos
            - 🟢 **Verde**: LEDs verdes, objetos verdes  
            - 🟡 **Amarillo**: LEDs amarillos, objetos amarillos
            
            **Cómo usar:**
            1. Toma una foto de un objeto con uno de estos colores
            2. La app detectará automáticamente los colores
            3. Se encenderán los LEDs correspondientes
            """)
            
            st.subheader("Configuración")
            auto_detect = st.checkbox("Encender LEDs automáticamente al detectar colores", value=True)
            if auto_detect:
                st.info("Los LEDs se encenderán automáticamente")
            else:
                st.warning("La detección solo mostrará resultados")

if __name__ == "__main__":
    main()
