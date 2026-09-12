import os
import streamlit as st
import pandas as pd
from google.cloud import bigquery
from google import genai
from google.oauth2 import service_account

# Cargar variables de entorno localmente si python-dotenv está disponible
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# --- CONFIGURACIÓN DE CREDENCIALES SEGURA (LOCAL Y CLOUD) ---
try:
    # Intenta leer de los secretos de Streamlit (esto funciona en la nube)
    credentials_info = dict(st.secrets["gcp_service_account"])
    credentials = service_account.Credentials.from_service_account_info(credentials_info)
    client_bq = bigquery.Client(credentials=credentials, project=credentials.project_id)
    
    if "GEMINI_API_KEY" in st.secrets:
        client_ai = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    else:
        client_ai = genai.Client()
        
except Exception as e:
    # Validar si estamos en entorno local de Windows o en la nube
    ruta_local = r"C:\Users\JARRISON\OneDrive\1.DAILY\11. CURSOS Y APRENDIZAJE\23.PROYECTOS DE DATA ANALYTICS\credenciales_gcp_b.json"
    if os.path.exists(ruta_local):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = ruta_local
        client_bq = bigquery.Client(project="ferrous-aleph-507816-i4")
        client_ai = genai.Client()
    else:
        st.error(f"⚠️ Error crítico: No se pudieron cargar los 'Secrets' en Streamlit Cloud ni se encontró el archivo local. Asegúrate de configurar los Secrets correctamente en el panel de Streamlit. Detalle: {e}")
        st.stop()

# Definir el esquema de las tablas con las columnas reales exactas
DB_SCHEMA = """
Trabajas con una base de datos en Google BigQuery para un e-commerce peruano de repuestos y accesorios de motos. 
La tabla principal de ventas se llama `ferrous-aleph-507816-i4.ecommerce_analytics.ventas_cloud`.
Las columnas clave y únicas de esta tabla son:
- venta_id (STRING): Identificador único de la transacción.
- fecha (DATE): Fecha en la que se realizó la venta.
- ciudad_envio (STRING): Ciudad de destino del envío (ej. Lima, Arequipa, Trujillo).
- producto (STRING): Nombre específico del producto vendido (ej. 'Casco Integral', 'Aceite Sintetico', 'Cadena Reforzada', 'Guantes Cuero', 'Filtro Aire').
- monto_usd (FLOAT64): Monto total de la venta expresado en Soles (S/).

REGLA ESTRICTA DE COLUMNAS:
- NO existen columnas llamadas 'cantidad' ni 'categoria_producto'. Para calcular unidades vendidas, conteos de transacciones o agrupar por productos, utiliza únicamente la columna 'producto' o 'venta_id'.
"""

def generar_sql_desde_pregunta(pregunta_usuario: str) -> str:
    """Usa Gemini para transformar una pregunta en lenguaje natural a una consulta SQL de BigQuery."""
    prompt_sistema = f"""
    {DB_SCHEMA}
    
    Tu única tarea es generar una consulta SQL de Google BigQuery válida y limpia que responda a la pregunta del usuario.
    REGLAS IMPORTANTES:
    - Devuelve ÚNICAMENTE el código SQL plano, sin bloques de código markdown (como ```sql), sin explicaciones adicionales.
    """
    
    response = client_ai.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"{prompt_sistema}\n\nPregunta del usuario: {pregunta_usuario}"
    )
    
    sql_query = response.text.strip().replace("```sql", "").replace("```", "").strip()
    return sql_query

def ejecutar_consulta_bq(sql: str) -> pd.DataFrame:
    """Ejecuta el SQL generado en BigQuery y devuelve un DataFrame de Pandas."""
    query_job = client_bq.query(sql)
    return query_job.to_dataframe()

def responder_usuario_con_datos(pregunta_usuario: str, df_resultados: pd.DataFrame) -> str:
    """Toma la pregunta original y el DataFrame obtenido de BigQuery para redactar una respuesta de negocio clara."""
    datos_texto = df_resultados.to_string(index=False)
    
    prompt_analista = f"""
    Eres un Analista de Negocios experto en Perú. Un usuario te hizo la siguiente pregunta:
    "{pregunta_usuario}"
    
    Para responderla, se ejecutó una consulta en BigQuery y se obtuvieron los siguientes resultados en formato de datos:
    {datos_texto}
    
    INSTRUCCIONES DE FORMATO Y NEGOCIO:
    - Redacta una respuesta concisa, profesional y directa al grano en español.
    - Expresa obligatoriamente todas las cantidades monetarias utilizando el símbolo de Soles (S/) (ej. S/ 120.50). NUNCA utilices términos genéricos como "unidades monetarias".
    - Destaca los insights principales o los números más relevantes que arrojan los datos.
    - No menciones detalles técnicos de bases de datos o SQL, actúa simplemente como un analista experto explicando los resultados al equipo comercial.
    """
    
    response = client_ai.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt_analista
    )
    
    return response.text.strip()

# --- CONFIGURACIÓN DE LA INTERFAZ WEB CON STREAMLIT ---
st.set_page_config(page_title="Business Data Analyst Chatbot", page_icon="🤖", layout="centered")

st.title("🤖 Business Data Analyst Chatbot")
st.markdown("Pregúntale al chatbot sobre las ventas, productos y métricas de tu e-commerce de motos (en Soles 🇵🇪).")

# Inicializar historial del chat
if "messages" not in st.session_state:
    st.session_state.messages = []

# Mostrar mensajes anteriores en pantalla
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Entrada de texto del usuario
if prompt_usuario := st.chat_input("¿Qué te gustaría saber de tus ventas? (ej. ¿Cuáles son los productos más vendidos?)"):
    # Agregar mensaje del usuario al historial
    st.session_state.messages.append({"role": "user", "content": prompt_usuario})
    with st.chat_message("user"):
        st.markdown(prompt_usuario)

    # Generar respuesta del asistente
    with st.chat_message("assistant"):
        with st.spinner("Analizando tus datos en BigQuery..."):
            try:
                # 1. Generar SQL
                sql_generado = generar_sql_desde_pregunta(prompt_usuario)
                
                # 2. Ejecutar consulta en BigQuery
                df_resultado = ejecutar_consulta_bq(sql_generado)
                
                # 3. Analizar y redactar respuesta de negocio con Gemini
                respuesta_final = responder_usuario_con_datos(prompt_usuario, df_resultado)
                
                st.markdown(respuesta_final)
                
                # Guardar en el historial
                st.session_state.messages.append({"role": "assistant", "content": respuesta_final})
                
            except Exception as e:
                error_msg = f"Ocurrió un error al procesar tu pregunta: {e}"
                st.error(error_msg)