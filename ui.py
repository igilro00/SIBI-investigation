import streamlit as st
from recommender import CarRecommender
from config import PAGE_TITLE, PAGE_ICON

def init_session_state():
    """Inicializa variables de sesión"""
    if 'recommender' not in st.session_state:
        st.session_state.recommender = CarRecommender()
    
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    if 'current_filters' not in st.session_state:
        st.session_state.current_filters = {
            'marca': None,
            'rango_precio': None,
            'tipo_carroceria': None,
            'tipo_motor': None,
            'traccion': None,
            'uso_deportivo': False,
            'uso_eco': False,
            'uso_familiar': False,
            'uso_lujo': False,
            'uso_offroad': False,
            'uso_urbano': False,
            'uso_viajes_largos': False
        }
    
    if 'conversation_count' not in st.session_state:
        st.session_state.conversation_count = 0
    
    if 'selected_car' not in st.session_state:
        st.session_state.selected_car = None


def count_active_filters(filters):
    """Cuenta filtros activos"""
    count = 0
    for key, value in filters.items():
        if value is not None and value is not False:
            count += 1
    return count


def format_car_display(car):
    """Formatea un coche para mostrar"""
    props = dict(car) if isinstance(car, dict) else car._properties
    
    info = f"\n**🚗 {props.get('name', 'N/A')}**\n"
    info += f"  • **Precio:** ${props.get('precio', 'N/A')}\n"
    
    if props.get('tipo_motor'):
        info += f"  • **Motor:** {props.get('tipo_motor')}\n"
    if props.get('aceleracion'):
        info += f"  • **Aceleración:** 0-100 km/h en {props.get('aceleracion')}s\n"
    if props.get('potencia'):
        info += f"  • **Potencia:** {props.get('potencia')} hp\n"
    if props.get('autonomia'):
        info += f"  • **Autonomía:** {props.get('autonomia')} km\n"
    if props.get('cambio'):
        info += f"  • **Cambio:** {props.get('cambio')}\n"
    if props.get('traccion'):
        info += f"  • **Tracción:** {props.get('traccion')}\n"
    if props.get('consumo'):
        info += f"  • **Consumo:** {props.get('consumo')} L/100km\n"
    if props.get('emisiones_co2'):
        info += f"  • **CO2:** {props.get('emisiones_co2')} g/km\n"
    
    return info


def extract_filters(user_input_lower, recommender):
    """Extrae filtros del input del usuario"""
    filters = {}
    
    marcas = recommender.db.get_all_marcas()
    rangos = recommender.db.get_all_rangos_precio()
    carrocerias = recommender.db.get_all_tipos_carroceria()
    motores = recommender.db.get_all_tipos_motor()
    tracciones = recommender.db.get_all_tracciones()
    
    # Buscar marca
    for marca in marcas:
        if marca.lower() in user_input_lower:
            filters['marca'] = marca
            break
    
    # Buscar rango precio
    for rango in rangos:
        if rango.lower() in user_input_lower:
            filters['rango_precio'] = rango
            break
    
    # Buscar carrocería
    for carroceria in carrocerias:
        if carroceria.lower() in user_input_lower:
            filters['tipo_carroceria'] = carroceria
            break
    
    # Buscar motor
    for motor in motores:
        if motor.lower() in user_input_lower:
            filters['tipo_motor'] = motor
            break
    
    # Buscar tracción
    for traccion in tracciones:
        if traccion.lower() in user_input_lower:
            filters['traccion'] = traccion
            break
    
    # Detectar usos
    if any(w in user_input_lower for w in ["deportivo", "deporte", "performance", "rápido", "potencia"]):
        filters['uso_deportivo'] = True
    
    if any(w in user_input_lower for w in ["eco", "eficiente", "combustible", "consumo", "verde"]):
        filters['uso_eco'] = True
    
    if any(w in user_input_lower for w in ["familiar", "familia", "niños", "maletero", "espacio"]):
        filters['uso_familiar'] = True
    
    if any(w in user_input_lower for w in ["lujo", "premium", "lux", "exclusivo"]):
        filters['uso_lujo'] = True
    
    if any(w in user_input_lower for w in ["offroad", "off-road", "todoterreno", "terreno"]):
        filters['uso_offroad'] = True
    
    if any(w in user_input_lower for w in ["urbano", "ciudad", "circulación", "tráfico"]):
        filters['uso_urbano'] = True
    
    if any(w in user_input_lower for w in ["viajes", "largos", "carretera", "autonomía", "distancia"]):
        filters['uso_viajes_largos'] = True
    
    return filters


def merge_filters(current, new):
    """Mezcla filtros manteniendo memoria"""
    merged = current.copy()
    for key, value in new.items():
        if value is not None and value is not False:
            merged[key] = value
    return merged


def check_end_conversation(user_input_lower):
    """Verifica si el usuario quiere terminar"""
    end_keywords = ['listo', 'gracias', 'perfecto', 'genial', 'ok', 'vale', 
                    'lo quiero', 'está bien', 'ese es', 'me quedo']
    return any(kw in user_input_lower for kw in end_keywords)


def should_ask_followup(filters):
    """Si hay < 5 filtros, hace preguntas poco invasivas"""
    filter_count = count_active_filters(filters)
    return filter_count > 0 and filter_count < 5


def main():
    """Función principal"""
    st.set_page_config(
        page_title=PAGE_TITLE,
        page_icon=PAGE_ICON,
        layout="wide"
    )
    
    init_session_state()
    
    # Estilos CSS
    st.markdown("""
    <style>
        .header { text-align: center; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                 border-radius: 10px; margin-bottom: 20px; }
        .header h1 { color: white; margin: 0; font-size: 2.5em; }
        .header p { color: rgba(255,255,255,0.9); margin: 5px 0; }
        .filter-badge { display: inline-block; background: #667eea; color: white; padding: 8px 12px; 
                       border-radius: 15px; margin: 5px 5px 5px 0; font-size: 0.9em; font-weight: 500; }
        .section-title { font-size: 1.3em; font-weight: bold; border-bottom: 3px solid #667eea; 
                        padding-bottom: 10px; margin: 20px 0 15px 0; }
        .message-user { background: #f0f0f0; border-left: 4px solid #999; padding: 15px; 
                       border-radius: 5px; margin: 10px 0; }
        .message-assistant { background: #f0f4ff; border-left: 4px solid #667eea; padding: 15px; 
                            border-radius: 5px; margin: 10px 0; }
        .car-card { background: white; border: 2px solid #e0e0e0; border-radius: 8px; padding: 15px; 
                   margin: 10px 0; }
        .filter-count { background: #667eea; color: white; padding: 3px 10px; border-radius: 12px; 
                       font-weight: bold; margin-left: 10px; }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown("""
    <div class="header">
        <h1>🚗 Tu Asesor Automotriz IA</h1>
        <p>Encontremos el coche perfecto para ti</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Información en sidebar
    with st.sidebar:
        st.markdown("### ℹ️ Sobre este Asesor")
        st.markdown("""
        **Cómo funciona:**
        1. Cuéntame qué tipo de coche buscas
        2. Si hay < 5 filtros, te haré preguntas amables
        3. Recibirás recomendaciones personalizadas
        4. Elige un coche para ver la competencia
        
        **Máximo 10 filtros**
        """)
        
        filter_count = count_active_filters(st.session_state.current_filters)
        st.metric("Filtros", f"{filter_count}/10", delta=f"{10-filter_count} disponibles")
        
        if st.button("🔄 Reiniciar", use_container_width=True):
            st.session_state.current_filters = {
                'marca': None, 'rango_precio': None, 'tipo_carroceria': None,
                'tipo_motor': None, 'traccion': None, 'uso_deportivo': False,
                'uso_eco': False, 'uso_familiar': False, 'uso_lujo': False,
                'uso_offroad': False, 'uso_urbano': False, 'uso_viajes_largos': False
            }
            st.session_state.chat_history = []
            st.session_state.selected_car = None
            st.rerun()
    
    # Mostrar filtros activos
    filter_count = count_active_filters(st.session_state.current_filters)
    if filter_count > 0:
        st.markdown(f"<div class='section-title'>🎯 Filtros Activos: <span class='filter-count'>{filter_count}/10</span></div>", 
                   unsafe_allow_html=True)
        
        badges = []
        f = st.session_state.current_filters
        if f['marca']: badges.append(f"<span class='filter-badge'>📍 {f['marca']}</span>")
        if f['rango_precio']: badges.append(f"<span class='filter-badge'>💰 {f['rango_precio']}</span>")
        if f['tipo_carroceria']: badges.append(f"<span class='filter-badge'>🚙 {f['tipo_carroceria']}</span>")
        if f['tipo_motor']: badges.append(f"<span class='filter-badge'>⚙️ {f['tipo_motor']}</span>")
        if f['traccion']: badges.append(f"<span class='filter-badge'>🛣️ {f['traccion']}</span>")
        if f['uso_deportivo']: badges.append(f"<span class='filter-badge'>⚡ Deportivo</span>")
        if f['uso_eco']: badges.append(f"<span class='filter-badge'>🌱 Eco</span>")
        if f['uso_familiar']: badges.append(f"<span class='filter-badge'>👨👩👧👦 Familiar</span>")
        if f['uso_lujo']: badges.append(f"<span class='filter-badge'>👑 Lujo</span>")
        if f['uso_offroad']: badges.append(f"<span class='filter-badge'>🏔️ Off-road</span>")
        if f['uso_urbano']: badges.append(f"<span class='filter-badge'>🏙️ Urbano</span>")
        if f['uso_viajes_largos']: badges.append(f"<span class='filter-badge'>🛣️ Viajes largos</span>")
        
        st.markdown(" ".join(badges), unsafe_allow_html=True)
    
    # Historial de chat
    st.markdown("<div class='section-title'>💬 Conversación</div>", unsafe_allow_html=True)
    
    for msg in st.session_state.chat_history:
        if msg['role'] == 'user':
            st.markdown(f"<div class='message-user'><strong>Tú:</strong> {msg['content']}</div>", 
                       unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='message-assistant'><strong>Asesor:</strong> {msg['content']}</div>", 
                       unsafe_allow_html=True)
    
    # Input
    st.markdown("---")
    st.markdown("<div class='section-title'>✍️ Tu Mensaje</div>", unsafe_allow_html=True)
    user_input = st.text_input("Escribe tu preferencia sobre coches...", key="user_input")
    
    if user_input:
        user_lower = user_input.lower()
        
        # Agregar al historial
        st.session_state.chat_history.append({'role': 'user', 'content': user_input})
        
        # Extraer y mezclar filtros
        new_filters = extract_filters(user_lower, st.session_state.recommender)
        st.session_state.current_filters = merge_filters(st.session_state.current_filters, new_filters)
        st.session_state.conversation_count += 1
        
        # Verificar si termina
        if check_end_conversation(user_lower):
            response = "✅ Perfecto, espero haberte ayudado a encontrar tu coche ideal. ¡Gracias!"
            st.session_state.chat_history.append({'role': 'assistant', 'content': response})
        else:
            # Obtener recomendaciones
            with st.spinner("🔍 Analizando preferencias..."):
                recommendations = st.session_state.recommender.get_recommendations(
                    marca=st.session_state.current_filters['marca'],
                    rango_precio=st.session_state.current_filters['rango_precio'],
                    tipo_carroceria=st.session_state.current_filters['tipo_carroceria'],
                    tipo_motor=st.session_state.current_filters['tipo_motor'],
                    traccion=st.session_state.current_filters['traccion'],
                    uso_deportivo=st.session_state.current_filters['uso_deportivo'],
                    uso_eco=st.session_state.current_filters['uso_eco'],
                    uso_familiar=st.session_state.current_filters['uso_familiar'],
                    uso_lujo=st.session_state.current_filters['uso_lujo'],
                    uso_offroad=st.session_state.current_filters['uso_offroad'],
                    uso_urbano=st.session_state.current_filters['uso_urbano'],
                    uso_viajes_largos=st.session_state.current_filters['uso_viajes_largos']
                )
            
            # Construir respuesta
            if recommendations['cars']:
                response = recommendations['recommendation']
                
                # Si hay < 5 filtros, agregar sugerencias poco invasivas
                filter_count = count_active_filters(st.session_state.current_filters)
                if filter_count < 5 and filter_count > 0:
                    response += "\n\n**💡 Si quieres refinar:**\n"
                    response += "• ¿Algún uso específico? (deportivo, familiar, eco, lujo, etc.)\n"
                    response += "• ¿Importa algo más? (precio, marca, etc.)"
            else:
                response = "❌ No encontré coches con esos criterios. Intenta ajustar."
            
            st.session_state.chat_history.append({'role': 'assistant', 'content': response})
            
            # Mostrar coches recomendados
            if recommendations['cars']:
                st.markdown("<div class='section-title'>🚗 Coches Recomendados</div>", unsafe_allow_html=True)
                
                for i, car in enumerate(recommendations['cars'], 1):
                    col1, col2 = st.columns([4, 1])
                    
                    with col1:
                        st.markdown(f"<div class='car-card'>{format_car_display(car)}</div>", 
                                   unsafe_allow_html=True)
                    
                    with col2:
                        if st.button(f"Elegir", key=f"car_{i}"):
                            st.session_state.selected_car = car
                            st.rerun()
        
        st.rerun()
    
    # Mostrar coche seleccionado y competencia
    if st.session_state.selected_car:
        st.markdown("---")
        st.markdown("<div class='section-title'>🏆 Coche Seleccionado</div>", unsafe_allow_html=True)
        
        st.markdown(f"<div class='car-card'>{format_car_display(st.session_state.selected_car)}</div>", 
                   unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔥 Ver Competencia Directa", use_container_width=True):
                car_name = st.session_state.selected_car._properties.get('name', '')
                
                with st.spinner("🔍 Buscando coches competentes..."):
                    competing = st.session_state.recommender.get_competing_cars(car_name)
                
                if competing:
                    st.markdown("<div class='section-title'>⚡ Coches Competentes</div>", unsafe_allow_html=True)
                    
                    for comp_car in competing[:5]:
                        if isinstance(comp_car, dict):
                            car_obj = comp_car.get('modelo', comp_car)
                        else:
                            car_obj = comp_car
                        
                        st.markdown(f"<div class='car-card'>{format_car_display(car_obj)}</div>", 
                                   unsafe_allow_html=True)
                else:
                    st.info("ℹ️ No hay coches competentes disponibles")
        
        with col2:
            if st.button("❌ Deseleccionar", use_container_width=True):
                st.session_state.selected_car = None
                st.rerun()


if __name__ == "__main__":
    main()