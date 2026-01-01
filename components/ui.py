import streamlit as st
from components.recommender import CarRecommender
from config import PAGE_TITLE, PAGE_ICON

def init_session_state():
    """Inicializa variables de sesión"""
    if 'recommender' not in st.session_state:
        st.session_state.recommender = CarRecommender()

def render_sidebar():
    """Renderiza la barra lateral con filtros"""
    st.sidebar.title("🔍 Filtros de Búsqueda")
    
    recommender = st.session_state.recommender
    
    marca = st.sidebar.selectbox(
        "Marca de vehículo",
        ["Cualquiera"] + recommender.db.get_all_marcas()
    )
    marca = None if marca == "Cualquiera" else marca
    
    rango_precio = st.sidebar.selectbox(
        "Rango de precio",
        ["Cualquiera"] + recommender.db.get_all_rangos_precio()
    )
    rango_precio = None if rango_precio == "Cualquiera" else rango_precio
    
    uso_deportivo = st.sidebar.checkbox("¿Uso deportivo?", value=False)
    
    cambio = st.sidebar.selectbox(
        "Tipo de cambio",
        ["Cualquiera", "Manual", "Automático"]
    )
    cambio = None if cambio == "Cualquiera" else cambio
    
    return {
        'marca': marca,
        'rango_precio': rango_precio,
        'uso_deportivo': uso_deportivo,
        'cambio': cambio
    }

def render_main_content(filters):
    """Renderiza el contenido principal"""
    st.title(PAGE_TITLE)
    st.markdown("---")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 🤖 Asistente de Recomendación de Coches")
        st.write("Obtén recomendaciones personalizadas basadas en tus preferencias")
    
    with col2:
        if st.button("🔄 Obtener Recomendación", key="recommend_btn", 
                    use_container_width=True):
            get_recommendation(filters)
    
    st.markdown("---")
    
    # Sección de búsqueda por nombre
    st.subheader("🔎 Buscar Coches Similares")
    modelo_name = st.text_input("Nombre del modelo", placeholder="ej: Jimny")
    
    if modelo_name:
        similar = st.session_state.recommender.get_similar_cars(modelo_name)
        if similar:
            st.success(f"Se encontraron {len(similar)} coches similares a {modelo_name}")
            for car in similar:
                st.info(f"• {car['modelo']._properties.get('name', 'N/A')}")
        else:
            st.warning(f"No se encontraron coches similares a '{modelo_name}'")

def get_recommendation(filters):
    """Obtiene y muestra la recomendación"""
    try:
        with st.spinner("🔄 Analizando base de datos y generando recomendación..."):
            result = st.session_state.recommender.get_recommendations(
                marca=filters['marca'],
                rango_precio=filters['rango_precio'],
                uso_deportivo=filters['uso_deportivo'],
                cambio=filters['cambio']
            )
        
        st.success("✅ Recomendación generada")
        
        st.subheader("💬 Recomendación del LLM")
        st.markdown(result['recommendation'])
        
        st.subheader("🚗 Coches disponibles")
        for car in result['cars']:
            props = car._properties
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Modelo", props.get('name', 'N/A'))
            with col2:
                st.metric("Precio", f"${props.get('precio', 'N/A')}")
            with col3:
                st.metric("Score Deportivo", f"{props.get('score_deportivo', 'N/A')}")
    
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")

def main():
    """Función principal"""
    st.set_page_config(
        page_title=PAGE_TITLE,
        page_icon=PAGE_ICON,
        layout="wide"
    )
    
    init_session_state()
    
    filters = render_sidebar()
    render_main_content(filters)

if __name__ == "__main__":
    main()
