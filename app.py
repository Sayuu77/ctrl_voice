import os
import streamlit as st
from bokeh.models.widgets import Button
from bokeh.models import CustomJS
from streamlit_bokeh_events import streamlit_bokeh_events
from PIL import Image
import time
import glob
import paho.mqtt.client as paho
import json
from gtts import gTTS
from googletrans import Translator

def on_publish(client, userdata, result):
    print("El dato ha sido publicado \n")
    pass

def on_message(client, userdata, message):
    global message_received
    time.sleep(2)
    message_received = str(message.payload.decode("utf-8"))
    st.write("Respuesta del Arduino:", message_received)

# Configuración MQTT
broker = "broker.mqttdashboard.com"
port = 1883
client1 = paho.Client("GIT-HUBC")
client1.on_message = on_message

st.title("INTERFACES MULTIMODALES")
st.subheader("CONTROL POR VOZ")

image = Image.open('voice_ctrl.jpg')
st.image(image, width=200)

st.write("Toca el Botón y habla ")

# Instrucciones para el usuario con los comandos específicos
st.markdown("""
### Comandos de voz disponibles:
- **Encender individual**: "enciende el verde", "enciende el rojo", "enciende el amarillo"
- **Control general**: "enciende todos", "apaga todos"
""")

stt_button = Button(label=" Inicio ", width=200)

stt_button.js_on_event("button_click", CustomJS(code="""
    var recognition = new webkitSpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'es-ES';

    recognition.onresult = function (e) {
        var value = "";
        for (var i = e.resultIndex; i < e.results.length; ++i) {
            if (e.results[i].isFinal) {
                value += e.results[i][0].transcript;
            }
        }
        if ( value != "") {
            document.dispatchEvent(new CustomEvent("GET_TEXT", {detail: value}));
        }
    }
    
    recognition.onerror = function (e) {
        console.error('Error en reconocimiento de voz:', e.error);
    }
    
    recognition.start();
    """))

result = streamlit_bokeh_events(
    stt_button,
    events="GET_TEXT",
    key="listen",
    refresh_on_update=False,
    override_height=75,
    debounce_time=0)

if result:
    if "GET_TEXT" in result:
        comando = result.get("GET_TEXT").strip()
        st.write("**Comando detectado:**", comando)
        
        # Convertir TODO a minúsculas para consistencia
        comando_normalizado = comando.lower()
        st.write("**Comando normalizado:**", comando_normalizado)
        
        # Conectar y publicar el comando
        try:
            client1.on_publish = on_publish
            client1.connect(broker, port)
            
            # Crear mensaje JSON con el comando en minúsculas
            message = json.dumps({"Act1": comando_normalizado})
            
            # Publicar en el topic correcto
            ret = client1.publish("voice_ctrl", message)
            
            if ret[0] == 0:
                st.success(f"✅ Comando enviado: '{comando_normalizado}'")
            else:
                st.error("❌ Error al enviar el comando")
                
        except Exception as e:
            st.error(f"Error de conexión: {e}")

# Sección para mostrar estado
st.markdown("---")
st.subheader("Estado del Sistema")
st.info("Los comandos se envían al Arduino via MQTT. El estado se actualizará cuando el Arduino procese el comando.")

try:
    os.mkdir("temp")
except:
    pass
