import streamlit as st
import pandas as pd
from app import generar_sql_desde_pregunta, ejecutar_consulta_bq, responder_usuario_con_datos

# Configuración de la página de Streamlit
st.set_page_config(
    page_title="Business Data Analyst Bot",
    page_icon="📊",
    layout="centered"
)

st.title("📊 Business Data Analyst Chatbot")
st.markdown("Pregúntale a tu base de datos de e-commerce en lenguaje natural y obtén análisis comerciales instantáneos.")

# Inicializar el historial de chat en la sesión de Streamlit si no existe
if "messages" not in st.session_state:
    st.session_state.messages = []

# Mostrar los mensajes anteriores del chat al recargar la página
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Entrada de texto del usuario en el chat inferior
if pregunta_usuario := st.chat_input("¿Qué te gustaría saber de tus ventas? (ej. ¿Cuáles son las categorías más vendidas?)"):
    
    # Agregar la pregunta del usuario al historial y mostrarla
    st.session_state.messages.append({"role": "user", "content": pregunta_usuario})
    with st.chat_message("user"):
        st.markdown(pregunta_usuario)

    # Generar la respuesta del analista virtual
    with st.chat_message("assistant"):
        with st.spinner("Analizando datos y consultando BigQuery..."):
            try:
                # 1. Generar SQL con Gemini
                sql_generado = generar_sql_desde_pregunta(pregunta_usuario)
                
                # 2. Ejecutar consulta en BigQuery
                df_resultado = ejecutar_consulta_bq(sql_generado)
                
                # 3. Redactar respuesta de negocio
                respuesta_final = responder_usuario_con_datos(pregunta_usuario, df_resultado)
                
                # Mostrar la respuesta analítica
                st.markdown(respuesta_final)
                
                # Opcional: Mostrar los datos crudos y el SQL en un desplegable técnico
                with st.expander("Ver detalles técnicos (SQL y Datos)"):
                    st.text(f"SQL Generado:\n{sql_generado}")
                    st.dataframe(df_resultado)
                
                # Guardar respuesta en el historial
                st.session_state.messages.append({"role": "assistant", "content": respuesta_final})
                
            except Exception as e:
                error_msg = f"❌ Ocurrió un error al procesar tu pregunta: {e}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})