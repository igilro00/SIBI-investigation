import ollama
from config import OLLAMA_MODEL, OLLAMA_BASE_URL
import logging

logger = logging.getLogger(__name__)


class OllamaLLMHandler:
    """Maneja la comunicación con Ollama"""

    def __init__(self, model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL):
        self.model = model
        self.base_url = base_url
        self.client = ollama.Client(host=base_url)
        
        try:
            self.client.list()
            logger.info(f"✅ Conectado a Ollama en {base_url}")
        except Exception as e:
            logger.error(f"❌ Error conectando a Ollama: {str(e)}")
            raise

    def generate_recommendation(self, user_preferences, database_results, user_filters=None):
        """Genera recomendación adaptada al número de filtros"""
        cars_info = self._format_cars_info(database_results)
        
        # Contar filtros activos para adaptar el tono
        filter_count = 0
        if user_filters:
            filter_count = sum(1 for v in user_filters.values() if v is not None and v is not False)
        
        # Adaptar instrucciones según filtros
        tone_instruction = ""
        if filter_count < 5:
            tone_instruction = "El usuario tiene pocos filtros. Sé amable pero NO invasivo. Sugiere 2-3 cosas para refinar SIN insistir."
        elif filter_count >= 10:
            tone_instruction = "El usuario tiene el máximo de filtros. Presenta las mejores opciones sin pedir más."
        
        prompt = f"""Eres un experto en automovilismo con 20 años de experiencia.

{tone_instruction}

PREFERENCIAS DEL USUARIO:
{user_preferences}

COCHES DISPONIBLES:
{cars_info}

Tu tarea:
1. Recomienda el MEJOR COCHE (justificación breve)
2. Proporciona 2-3 ALTERNATIVAS
3. Explica CARACTERÍSTICAS CLAVE
4. Consejo personalizado

Sé conciso. Usa emojis moderadamente. Mantén un tono amigable y conversacional."""
        
        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                stream=False,
                options={'temperature': 0.7, 'top_p': 0.9, 'num_predict': 800}
            )
            return response['response']
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            return f"❌ Error al generar recomendación"

    def answer_car_question(self, question, context):
        """Responde preguntas sobre coches"""
        prompt = f"""Eres un experto en vehículos.

CONTEXTO:
{context}

PREGUNTA:
{question}

Responde de forma clara y útil."""
        
        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                stream=False,
                options={'temperature': 0.6, 'num_predict': 600}
            )
            return response['response']
        except Exception as e:
            return f"❌ Error: {str(e)}"

    def compare_cars(self, car1_info, car2_info, comparison_aspect):
        """Compara dos coches"""
        prompt = f"""Eres un comparador de vehículos.

COCHE 1:
{car1_info}

COCHE 2:
{car2_info}

ASPECTO: {comparison_aspect}

Compara de forma objetiva. Indica ventajas y desventajas."""
        
        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                stream=False,
                options={'temperature': 0.6, 'num_predict': 600}
            )
            return response['response']
        except Exception as e:
            return f"❌ Error: {str(e)}"

    def generate_use_case_analysis(self, cars_list, use_case):
        """Analiza coches para un caso de uso"""
        cars_info = self._format_cars_info(cars_list)
        
        prompt = f"""Eres experto en recomendaciones para diferentes estilos de vida.

PERFIL: {use_case}

COCHES:
{cars_info}

Analiza:
1. MEJOR OPCIÓN para este perfil
2. Por qué se adapta
3. Alternativas si presupuesto es limitado
4. Características más importantes"""
        
        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                stream=False,
                options={'temperature': 0.7, 'num_predict': 800}
            )
            return response['response']
        except Exception as e:
            return f"❌ Error: {str(e)}"

    def generate_buying_advice(self, car_info):
        """Genera consejo de compra"""
        prompt = f"""Eres asesor de compra de vehículos experimentado.

VEHÍCULO:
{car_info}

Proporciona:
1. Análisis de valor
2. Mantenimiento esperado
3. Costos operativos
4. Puntos fuertes/débiles
5. A qué comprador le conviene"""
        
        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                stream=False,
                options={'temperature': 0.6, 'num_predict': 800}
            )
            return response['response']
        except Exception as e:
            return f"❌ Error: {str(e)}"

    def _format_cars_info(self, cars):
        """Formatea información de coches"""
        if not cars:
            return "No hay coches disponibles."
        
        formatted = ""
        for i, car in enumerate(cars, 1):
            props = car._properties if hasattr(car, '_properties') else car
            
            formatted += f"\n{i}. **{props.get('name', 'N/A')}**\n"
            formatted += f"   • Precio: ${props.get('precio', 'N/A')}\n"
            
            if props.get('tipo_motor'):
                formatted += f"   • Motor: {props.get('tipo_motor')}\n"
            if props.get('aceleracion'):
                formatted += f"   • Aceleración: {props.get('aceleracion')}s\n"
            if props.get('potencia'):
                formatted += f"   • Potencia: {props.get('potencia')} hp\n"
            if props.get('autonomia'):
                formatted += f"   • Autonomía: {props.get('autonomia')} km\n"
        
        return formatted