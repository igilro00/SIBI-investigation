"""
Chatbot Inteligente - Conversación con extracción de criterios
Pide datos si faltan, combina información, tiene memoria real
"""

import streamlit as st
from datetime import datetime
from car_recommender import CarRecommender
from memory_manager import MemoryManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURACIÓN STREAMLIT
# ============================================================================

st.set_page_config(
    page_title="🚗 Car Chatbot Smart",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown(
    """
    """,
    unsafe_allow_html=True
)

# ============================================================================
# TÍTULO
# ============================================================================

st.title("🚗 AI Car Chatbot - Smart Edition")
st.markdown("**Conversación inteligente - Combina criterios y aprende preferencias**")

# ============================================================================
# INICIALIZAR COMPONENTES
# ============================================================================

@st.cache_resource
def init_recommender():
    try:
        recommender = CarRecommender()
        logger.info("✅ Recomendador inicializado")
        return recommender
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        st.error(f"Error: {e}")
        return None


def init_memory():
    # Nueva memoria por sesión, sin cache global
    return MemoryManager()


# Inicializar sesión
if "recommender" not in st.session_state:
    st.session_state.recommender = init_recommender()

if "memory" not in st.session_state:
    st.session_state.memory = init_memory()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ============================================================================
# DISPLAY CHAT
# ============================================================================

st.subheader("💬 Chat")
chat_container = st.container()

with chat_container:
    if st.session_state.chat_history:
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                st.chat_message("user").write(msg["content"])
            else:
                st.chat_message("assistant").write(msg["content"])
    else:
        st.info(
            """
💡 **¡Hola! Soy tu asistente inteligente de coches.**

Puedo ayudarte a encontrar el coche perfecto. Ejemplos:

- "Busco un SUV barato"
- "Quiero algo deportivo menos de 50k"
- "Necesito un coche familiar"
- "Dame opciones eco y rápidas"

Cuanto más detalles des, mejores serán mis recomendaciones.
            """
        )

# ============================================================================
# INPUT DEL USUARIO - SIEMPRE ACTIVO
# ============================================================================

st.markdown("---")

user_input = st.chat_input("Cuéntame qué buscas en un coche o cambia los criterios...")

if user_input:
    # ====================================================================
    # 1. AGREGAR A HISTORIAL
    # ====================================================================
    st.session_state.chat_history.append({
        "role": "user",
        "content": user_input,
        "timestamp": datetime.now().isoformat()
    })

    # ====================================================================
    # 2. AGREGAR A MEMORIA
    # ====================================================================
    st.session_state.memory.add_message("user", user_input)

    # ====================================================================
    # 3. MOSTRAR MENSAJE USUARIO
    # ====================================================================
    with chat_container:
        st.chat_message("user").write(user_input)

    # ====================================================================
    # 4. PROCESAR CON IA INTELIGENTE
    # ====================================================================
    with st.spinner("🤔 Analizando tu búsqueda..."):
        try:
            if st.session_state.recommender:
                # Obtener contexto de conversación anterior
                memory_context = st.session_state.memory.get_context()

                # ================================================
                # PASO 1: EXTRAER CRITERIOS
                # ================================================
                criteria = st.session_state.recommender.extract_criteria_from_query(
                    user_query=user_input,
                    memory_context=memory_context
                )

                # ================================================
                # PASO 2: BUSCAR VEHÍCULOS
                # ================================================
                vehicles, has_enough_data = st.session_state.recommender.search_vehicles_by_criteria(
                    criteria=criteria,
                    user_query=user_input
                )

                # ================================================
                # PASO 3: GENERAR RESPUESTA INTELIGENTE
                # ================================================
                response = st.session_state.recommender.generate_smart_response(
                    user_query=user_input,
                    vehicles=vehicles,
                    memory_context=memory_context,
                    criteria=criteria,
                    has_enough_data=has_enough_data
                )

                # ================================================
                # Agregar respuesta al historial
                # ================================================
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": response,
                    "timestamp": datetime.now().isoformat()
                })
                st.session_state.memory.add_message("assistant", response)

                # ================================================
                # Mostrar respuesta
                # ================================================
                with chat_container:
                    st.chat_message("assistant").write(response)

                # ================================================
                # 5. MOSTRAR RECOMENDACIONES SI EXISTEN
                # ================================================
                if vehicles and has_enough_data:
                    st.markdown("---")
                    st.subheader("⭐ Vehículos recomendados")
                    st.markdown("💡 *Puedes seguir haciendo preguntas o cambiar los criterios en el chat*")

                    for i, vehicle in enumerate(vehicles[:5], 1):
                        with st.expander(
                            f"**{i}. {vehicle.get('name', 'N/A')}** - €{float(vehicle.get('precio') or 0):,.0f}",
                            expanded=(i == 1)
                        ):
                            col1, col2 = st.columns(2)
                            with col1:
                                precio = float(vehicle.get('precio') or 0)
                                potencia = float(vehicle.get('potencia') or 0)
                                autonomia = float(vehicle.get('autonomia') or 0)

                                st.metric("💰 Precio", f"€{precio:,.0f}")
                                st.metric("⚡ Potencia", f"{potencia:.0f} CV")
                                st.metric("🔋 Autonomía", f"{autonomia:.0f} km")

                            with col2:
                                cambio = vehicle.get('cambio', 'N/A')
                                aceleracion = float(vehicle.get('aceleracion') or 0)

                                st.write(f"**🔄 Cambio:** {cambio}")
                                st.write(f"**🏁 0-100:** {aceleracion:.1f}s")
                                st.write(f"**🆔 ID:** `{vehicle.get('id', 'N/A')}`")
            else:
                st.error("❌ Error en el recomendador")
        except Exception as e:
            logger.error(f"Error: {e}")
            st.error(f"❌ Error: {str(e)}")

# ============================================================================
# PIE DE PÁGINA
# ============================================================================

st.markdown("---")
col1, col2, col3 = st.columns([1, 1, 2])

with col1:
    if st.button("🗑️ Limpiar chat", use_container_width=True):
        st.session_state.chat_history = []
        # Crear memoria totalmente nueva (mensajes, filtros, preferencias, temas)
        st.session_state.memory = MemoryManager()
        st.rerun()

with col2:
    st.caption(f"💬 {len(st.session_state.chat_history)} mensajes")

with col3:
    memory_summary = st.session_state.memory.get_summary()
    topics_str = ", ".join(memory_summary["topics"]) if memory_summary["topics"] else "ninguno"
    st.caption(f"🧠 Temas: {topics_str}")
