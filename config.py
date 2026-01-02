"""
Configuración centralizada de la aplicación
Cargar desde .env o usar valores por defecto
"""

import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# ============================================================================
# NEO4J CONFIGURATION
# ============================================================================

NEO4J = {
    "uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
    "user": os.getenv("NEO4J_USER", "neo4j"),
    "password": os.getenv("NEO4J_PASSWORD", "password"),
}

# ============================================================================
# OLLAMA CONFIGURATION
# ============================================================================

OLLAMA = {
    "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    "model": os.getenv("OLLAMA_MODEL", "mistral"),
    "embed_model": os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text"),
    "temperature": float(os.getenv("OLLAMA_TEMPERATURE", "0.7")),
    "context_window": int(os.getenv("OLLAMA_CONTEXT_WINDOW", "4096")),
}

# ============================================================================
# STREAMLIT CONFIGURATION
# ============================================================================

STREAMLIT = {
    "page_title": "🚗 Car Recommender RAG",
    "page_icon": "🚗",
    "layout": "wide",
    "initial_sidebar_state": "expanded",
}

# ============================================================================
# MEMORY CONFIGURATION
# ============================================================================

MEMORY = {
    "max_messages": int(os.getenv("MAX_MESSAGES", "20")),
    "max_filters_history": int(os.getenv("MAX_FILTERS_HISTORY", "5")),
}

# ============================================================================
# RECOMMENDER CONFIGURATION
# ============================================================================

RECOMMENDER = {
    "top_k_results": int(os.getenv("TOP_K_RESULTS", "5")),
    "min_price": int(os.getenv("MIN_PRICE", "15000")),
    "max_price": int(os.getenv("MAX_PRICE", "500000")),
    "min_power": int(os.getenv("MIN_POWER", "50")),
    "max_power": int(os.getenv("MAX_POWER", "600")),
    "min_autonomy": int(os.getenv("MIN_AUTONOMY", "200")),
    "max_autonomy": int(os.getenv("MAX_AUTONOMY", "1200")),
}

# ============================================================================
# DEFAULT FILTERS
# ============================================================================

DEFAULT_FILTERS = {
    "precio_min": RECOMMENDER["min_price"],
    "precio_max": RECOMMENDER["max_price"],
    "tipo": None,
    "motor": None,
    "potencia_min": RECOMMENDER["min_power"],
    "potencia_max": RECOMMENDER["max_power"],
    "autonomia_min": RECOMMENDER["min_autonomy"],
}

# ============================================================================
# VEHICLE TYPES
# ============================================================================

VEHICLE_TYPES = {
    "Compacto": ["compacto", "hatchback", "segmento C"],
    "SUV Coupé": ["suv coupé","suv coupe","suv"],
    "SUV": ["suv","todocamino","todoterreno","awd","4*4"],
    "Cabrio": ["cabrio", "convertible", "cabriolet", "roadster", "descapotable", "spyder"],
    "Familiar": ["familiar", "touring", "wagon"],
    "Berlina": ["berlina", "sedan", "sedán"],
    "Coupé": ["coupe", "coupé", "fastback", "dos puertas"],
    "SUV Compacto": ["suv compacto", "compacto suv"],
    "Monovolumen": ["monovolumen", "minivan"],
    "Deportivo": ["deportivo", "sport", "racing"],
    "SUV Deportivo": ["deportivo suv", "suv deportivo"],
    "Furgoneta": ["furgo", "van", "furgoneta"],
    "Crossover": ["crossover", "cuv"]    

}

# ============================================================================
# MOTOR TYPES
# ============================================================================

MOTOR_TYPES = {
    "Gasolina": ["gasolina"],
    "Diésel": ["diesel", "diésel", "gasoil"],
    "Híbrido": ["hibrido", "híbrido", "hybrid"],
    "Híbrido Enchufable": ["hibrido enchufable", "híbrido enchufable", "plug-in hybrid"],
    "Eléctrico": ["electrico", "eléctrico", "cero emisiones", "100% electrico", "100% eléctrico"]
}
    


# ============================================================================
# SCORE TYPES
# ============================================================================

SCORE_TYPES = [
    "score_eco",
    "score_urbano",
    "score_familiar",
    "score_deportivo",
    "score_viajes",
    "score_offroad",
]

# ============================================================================
# TOPIC KEYWORDS (USO, ESTILO, LUJO, ECONÓMICO…)
# ============================================================================

TOPICS = {
    "eco": [
        "eco", "sostenible", "verde",
        "electrico", "eléctrico", "hibrido", "híbrido",
        "ambiente", "emision", "emisión",
    ],
    "deportivo": [
        "deportivo", "sport",
        "rapido", "rápido",
        "performance", "potencia", "cv",
        "aceleracion", "aceleración", "adrenalina",
    ],
    "familiar": [
        "familia", "familiar", "niños", "ninos",
        "espacio", "grande", "asientos", "maletero",
        "sillas infantiles",
    ],
    "urbano": [
        "ciudad", "urbano",
        "compacto", "pequeño", "pequeno",
        "estacionamiento", "maniobrabilidad",
        "atascos", "trayectos cortos",
    ],
    "viajes": [
        "viajes", "carretera", "largo recorrido",
        "autonomia", "autonomía",
        "consumo", "paradas", "vacaciones",
    ],
    "offroad": [
        "offroad", "4x4", "awd", "todoterreno",
        "campo", "aventura",
        "montaña", "montana", "nieve", "pistas",
    ],
    "lujo": [
        "lujo", "premium", "alta gama", "tope de gama",
        "acabados", "cuero", "asientos",
        "masaje", "tecnologia", "tecnología",
        "infotainment", "luces matriciales",
    ],
    "economico": [
        "economico", "económico",
        "barato", "precio bajo",
        "presupuesto ajustado",
        "ahorrar", "gasto bajo",
    ],
}

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

LOGGING = {
    "level": os.getenv("LOG_LEVEL", "INFO"),
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
}

# ============================================================================
# VALIDATION
# ============================================================================

def validate_config():
    """
    Validar que la configuración sea correcta
    """
    try:
        # Intentar importar dependencias críticas
        import neo4j  # noqa
        import streamlit  # noqa
        import ollama  # noqa
        from llama_index.llms.ollama import Ollama  # noqa

        return True
    except ImportError as e:
        print(f"❌ Error: Dependencia faltante: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("🔧 CONFIGURACIÓN DE LA APLICACIÓN")
    print("=" * 60)

    p
