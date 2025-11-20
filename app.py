import os
import streamlit as st
import base64
from openai import OpenAI
import openai
from PIL import Image, ImageDraw
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

st.set_page_config(page_title="Detector de Colores Básicos", layout="centered", initial_sidebar_state="collapsed")

# Streamlit page setup
st.title("🎯 Detector de Colores: Rojo, Azul, Verde")

with st.sidebar:
    st.subheader("Instrucciones Rápidas")
    st.markdown("""
    **🎨 Colores detectados:**
    - 🔴 ROJO
    - 🔵 AZUL  
    - 🟢 VERDE
    
    **📸 Para usar:**
    1. Coloca objeto en el **cuadro rojo**
    2. Toma la foto
    3. Haz clic en **Detectar Colores**
    4. Solo el área del cuadro se analiza
    """)

ke = st.text_input('Ingresa tu Clave de OpenAI', type="password")
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
analyze_button = st.button("🔍 Detectar Colores", type="primary", use_container_width=True)

# Check if an image has been uploaded and API key is available
if uploaded_file is not None and api_key and analyze_button:

    with st.spinner("🎨 Analizando colores del objeto..."):
        # Encode the cropped image
        base64_image = encode_image(uploaded_file)
    
        # Simple prompt for basic color detection
        prompt_text = """
        Analiza ESTA imagen y responde SOLO con un JSON que contenga:
        
        {
            "rojo": true/false,
            "azul": true/false, 
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
                        st.markdown("#### 🔴 Rojo")
                        if color_data.get("rojo", False):
                            st.success("**✅ DETECTADO**")
                            st.markdown("El color rojo está presente")
                        else:
                            st.error("**❌ NO DETECTADO**")
                            st.markdown("No se encontró rojo")
                    
                    with col2:
                        st.markdown("#### 🔵 Azul")
                        if color_data.get("azul", False):
                            st.success("**✅ DETECTADO**")
                            st.markdown("El color azul está presente")
                        else:
                            st.error("**❌ NO DETECTADO**")
                            st.markdown("No se encontró azul")
                    
                    with col3:
                        st.markdown("#### 🟢 Verde")
                        if color_data.get("verde", False):
                            st.success("**✅ DETECTADO**")
                            st.markdown("El color verde está presente")
                        else:
                            st.error("**❌ NO DETECTADO**")
                            st.markdown("No se encontró verde")
                            
                    # Resumen final
                    st.markdown("---")
                    colors_found = []
                    if color_data.get("rojo"): colors_found.append("🔴 Rojo")
                    if color_data.get("azul"): colors_found.append("🔵 Azul") 
                    if color_data.get("verde"): colors_found.append("🟢 Verde")
                    
                    if colors_found:
                        st.success(f"**🎯 RESULTADO:** Se detectaron: {', '.join(colors_found)}")
                    else:
                        st.warning("**📝 RESULTADO:** No se detectaron los colores rojo, azul o verde en el objeto")
                        
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
    - El análisis es específico para **rojo, azul y verde**
    """)
