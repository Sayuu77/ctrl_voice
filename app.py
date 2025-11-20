import streamlit as st
import cv2
import numpy as np
import json
import paho.mqtt.client as mqtt
import sounddevice as sd
import queue
import vosk

# --- Configuración MQTT ---
MQTT_BROKER = "broker.mqttdashboard.com"
MQTT_TOPIC = "appcolor"

client = mqtt.Client()
client.connect(MQTT_BROKER, 1883, 60)

# --- Función para enviar comandos al ESP32 ---
def enviar_comando(color):
    payload = {"Act1": f"enciende {color}"}
    client.publish(MQTT_TOPIC, json.dumps(payload))

# --- Función de detección de color ---
def detectar_color(frame):
    # Convertimos a HSV
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Rangos de colores (ajustables)
    colores = {
        "rojo": [(0, 100, 100), (10, 255, 255)],
        "verde": [(50, 100, 100), (70, 255, 255)],
        "amarillo": [(20, 100, 100), (30, 255, 255)]
    }

    for color, (lower, upper) in colores.items():
        mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
        if cv2.countNonZero(mask) > 500:  # si hay suficiente píxeles del color
            enviar_comando(color)
            st.success(f"LED {color.upper()} encendido por detección de cámara")
            break

# --- Interfaz Streamlit ---
st.title("Control de LEDs por Voz y Cámara")

# Control manual
st.subheader("Encender LEDs manualmente")
if st.button("Rojo"):
    enviar_comando("rojo")
if st.button("Verde"):
    enviar_comando("verde")
if st.button("Amarillo"):
    enviar_comando("amarillo")

# Control por voz
st.subheader("Control de LEDs por voz")

model = vosk.Model("model")  # Descarga el modelo de Vosk: https://alphacephei.com/vosk/models
q = queue.Queue()

def callback(indata, frames, time, status):
    q.put(bytes(indata))

if st.button("Grabar comando de voz"):
    st.info("Hablando ahora...")
    with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16',
                           channels=1, callback=callback):
        rec = vosk.KaldiRecognizer(model, 16000)
        for _ in range(30):  # Grabación de 3s aprox
            data = q.get()
            if rec.AcceptWaveform(data):
                break
        result = json.loads(rec.Result())
        comando = result.get("text", "")
        st.write(f"Comando detectado: {comando}")
        for color in ["rojo", "verde", "amarillo"]:
            if color in comando.lower():
                enviar_comando(color)
                st.success(f"LED {color.upper()} encendido por voz")

# Control por cámara
st.subheader("Control de LEDs por cámara")
cap = cv2.VideoCapture(0)

if st.button("Tomar foto y detectar color"):
    ret, frame = cap.read()
    if ret:
        st.image(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        detectar_color(frame)
    else:
        st.error("No se pudo acceder a la cámara")
cap.release()
