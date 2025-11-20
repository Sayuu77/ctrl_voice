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

def on_publish(client,userdata,result):             #create function for callback
    print("el dato ha sido publicado \n")
    pass

def on_message(client, userdata, message):
    global message_received
    time.sleep(2)
    message_received=str(message.payload.decode("utf-8"))
    st.write(message_received)

broker="broker.mqttdashboard.com"
port=1883
client1= paho.Client("GIT-HUBC")
client1.on_message = on_message

st.title("INTERFACES MULTIMODALES")
st.subheader("CONTROL POR VOZ")

image = Image.open('voice_ctrl.jpg')
st.image(image, width=200)

st.write("Toca el Botón y habla ")

# Agregar instrucciones para el usuario
st.markdown("""
### Comandos de voz disponibles:
- **Para luces:** "enciende luz", "apaga luz", "enciende amarillo", "apaga rojo", etc.
- **Para todos los LEDs:** "enciende todos los leds", "apaga todos los leds"
- **Para puerta:** "abre puerta", "cierra puerta"
""")

stt_button = Button(label=" Inicio ", width=200)

stt_button.js_on_event("button_click", CustomJS(code="""
    var recognition = new webkitSpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
 
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
        comando_voz = result.get("GET_TEXT").strip()
        st.write(f"Comando detectado: {comando_voz}")
        
        # Procesar el comando y mostrar feedback
        comando_minusculas = comando_voz.lower()
        
        # Determinar qué acción se está solicitando
        if any(palabra in comando_minusculas for palabra in ["enciende", "apaga", "abre", "cierra", "amarillo", "rojo", "verde", "luz", "puerta"]):
            st.success(f"Comando reconocido: '{comando_voz}'")
            
            # Publicar el comando via MQTT
            client1.on_publish = on_publish                            
            client1.connect(broker,port)  
            
            # Enviar el comando exactamente como lo espera el Arduino
            message = json.dumps({"Act1": comando_voz})
            ret = client1.publish("voice_ctrl", message)
            
            st.info("Comando enviado al Arduino via MQTT")
            
            # Mostrar confirmación visual del comando
            if "enciende" in comando_minusculas and "luz" in comando_minusculas:
                st.balloons()
                st.success("💡 Luz principal encendida")
            elif "apaga" in comando_minusculas and "luz" in comando_minusculas:
                st.success("💡 Luz principal apagada")
            elif "enciende" in comando_minusculas and "amarillo" in comando_minusculas:
                st.success("🟡 LED amarillo encendido")
            elif "apaga" in comando_minusculas and "amarillo" in comando_minusculas:
                st.success("🟡 LED amarillo apagado")
            elif "enciende" in comando_minusculas and "rojo" in comando_minusculas:
                st.success("🔴 LED rojo encendido")
            elif "apaga" in comando_minusculas and "rojo" in comando_minusculas:
                st.success("🔴 LED rojo apagado")
            elif "enciende" in comando_minusculas and "verde" in comando_minusculas:
                st.success("🟢 LED verde encendido")
            elif "apaga" in comando_minusculas and "verde" in comando_minusculas:
                st.success("🟢 LED verde apagado")
            elif "abre" in comando_minusculas and "puerta" in comando_minusculas:
                st.success("🚪 Puerta abierta")
            elif "cierra" in comando_minusculas and "puerta" in comando_minusculas:
                st.success("🚪 Puerta cerrada")
                
        else:
            st.warning("Comando no reconocido. Intenta con: 'enciende luz', 'apaga rojo', etc.")
    
    try:
        os.mkdir("temp")
    except:
        pass

# Agregar sección de estado actual
st.markdown("---")
st.subheader("Estado del Sistema")

# Botón para probar conexión
if st.button("Probar conexión MQTT"):
    try:
        client1.connect(broker, port)
        st.success("✅ Conexión MQTT establecida correctamente")
    except Exception as e:
        st.error(f"❌ Error en conexión MQTT: {e}")

# Nota importante
st.info("""
**Nota:** Asegúrate de que:
1. El Arduino esté conectado a Internet
2. El topic MQTT sea 'voice_ctrl'
3. Hables claro y uses los comandos especificados
""")
