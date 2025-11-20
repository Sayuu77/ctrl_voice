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

# Instrucciones para el usuario
st.markdown("""
### Comandos de voz disponibles:
- **Para LEDs**: "enciende el led amarillo", "apaga el led rojo", "enciende todos los leds"
- **Para luces**: "enciende la luz", "apaga la luz principal"  
- **Para puerta**: "abre la puerta", "cierra la puerta"
- **Comandos simples**: "amarillo", "rojo", "verde"
""")

stt_button = Button(label=" Inicio ", width=200)

stt_button.js_on_event("button_click", CustomJS(code="""
    var recognition = new webkitSpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'es-ES';  // Configurar para español

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
        
        # Conectar y publicar el comando
        try:
            client1.on_publish = on_publish
            client1.connect(broker, port)
            
            # Crear mensaje JSON
            message = json.dumps({"Act1": comando})
            
            # Publicar en el topic correcto
            ret = client1.publish("voice_ctrl", message)
            
            if ret[0] == 0:
                st.success(f"✅ Comando enviado: '{comando}'")
            else:
                st.error("❌ Error al enviar el comando")
                
        except Exception as e:
            st.error(f"Error de conexión: {e}")

# Sección para mostrar estado
st.markdown("---")
st.subheader("Estado del Sistema")

# Placeholder para el estado actual (podrías implementar suscripción MQTT para actualizaciones en tiempo real)
st.info("Los comandos se envían al Arduino via MQTT. El estado se actualizará cuando el Arduino procese el comando.")

try:
    os.mkdir("temp")
except:
    pass
