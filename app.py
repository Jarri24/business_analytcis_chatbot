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
        model="gemini-3.6-flash",
        contents=f"{prompt_sistema}\n\nPregunta del usuario: {pregunta_usuario}"
    )
    
    sql_query = response.text.strip().replace("