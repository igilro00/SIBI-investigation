import ollama
from config import OLLAMA_MODEL, OLLAMA_BASE_URL
import logging

logger = logging.getLogger(__name__)


class OllamaLLMHandler:
    """Maneja la comunicación con Ollama para generación de texto"""
    
    def __init__(self, model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL):
        self.model = model
        self.base_url = base_url
        self.client = ollama.Client(host=base_url)
        
        # Verificar conexión
        try:
            self.client.list()
            logger.info(f"✅ Conectado a Ollama en {base_url} usando modelo {model}")
        except Exception as e:
            logger.error(f"❌ Error conectando a Ollama: {str(e)}")
            raise
    
    def generate_recommendation(self, user_preferences, database_results):
        """
        Genera una recomendación personalizada basada en preferencias del usuario
        y resultados de la búsqueda en la BD.
        """
        
        cars_info = self._format_cars_info(database_results)
        
        prompt = f"""Eres un experto en automovilismo con 20 años de experiencia en recomendaciones de vehículos.

El usuario tiene las siguientes preferencias y requisitos:

PREFERENCIAS DEL USUARIO:
{user_preferences}

COCHES DISPONIBLES QUE COINCIDEN:
{cars_info}

Tu tarea es:
1. Analizar cuál es el MEJOR COCHE para este usuario (justificación detallada)
2. Proporcionar 2-3 ALTERNATIVAS RECOMENDADAS (ordenadas por relevancia)
3. Explicar las CARACTERÍSTICAS CLAVE de cada opción
4. Dar un CONSEJO DE COMPRA personalizado

Sé conciso pero informativo. Enfócate en lo que más importa al usuario.
Usa emojis moderadamente para mejorar la legibilidad.
        """
        
        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                stream=False,
                options={
                    'temperature': 0.7,
                    'top_p': 0.9,
                    'num_predict': 1000
                }
            )
            
            return response['response']
        
        except Exception as e:
            logger.error(f"Error generando recomendación: {str(e)}")
            return f"❌ Error al generar recomendación: {str(e)}"
    
    def answer_car_question(self, question, context):
        """
        Responde preguntas sobre coches usando contexto de la BD.
        Ideal para preguntas como "¿Cuál es mejor para off-road?"
        """
        
        prompt = f"""Eres un experto en vehículos muy conocedor.

CONTEXTO - Información disponible sobre vehículos:
{context}

PREGUNTA DEL USUARIO:
{question}

Proporciona una respuesta clara, útil y basada en hechos.
Si no tienes información suficiente en el contexto, indícalo claramente.
        """
        
        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                stream=False,
                options={
                    'temperature': 0.6,
                    'top_p': 0.9,
                    'num_predict': 800
                }
            )
            
            return response['response']
        
        except Exception as e:
            logger.error(f"Error respondiendo pregunta: {str(e)}")
            return f"❌ Error: {str(e)}"
    
    def compare_cars(self, car1_info, car2_info, comparison_aspect):
        """
        Compara dos coches en un aspecto específico.
        comparison_aspect puede ser: "precio", "rendimiento", "comodidad", etc.
        """
        
        prompt = f"""Eres un experto comparador de vehículos.

COCHE 1:
{car1_info}

COCHE 2:
{car2_info}

ASPECTO A COMPARAR: {comparison_aspect}

Proporciona una comparación detallada y objetiva enfocada en el aspecto solicitado.
Indica cuál tiene ventaja y por qué.
        """
        
        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                stream=False,
                options={
                    'temperature': 0.6,
                    'num_predict': 600
                }
            )
            
            return response['response']
        
        except Exception as e:
            logger.error(f"Error comparando coches: {str(e)}")
            return f"❌ Error: {str(e)}"
    
    def generate_use_case_analysis(self, cars_list, use_case):
        """
        Analiza qué coches son mejores para un caso de uso específico.
        use_case puede ser: "familia viajera", "joven urbano", "ejecutivo", etc.
        """
        
        cars_info = self._format_cars_info(cars_list)
        
        prompt = f"""Eres un experto en recomendaciones de vehículos para diferentes estilos de vida.

PERFIL DEL USUARIO: {use_case}

COCHES DISPONIBLES:
{cars_info}

Analiza:
1. ¿Cuál es el MEJOR COCHE para este perfil?
2. ¿Por qué este coche se adapta perfectamente?
3. ¿Cuáles serían las ALTERNATIVAS si el presupuesto es limitado?
4. ¿Qué CARACTERÍSTICAS son más importantes para este perfil?

Sé práctico y enfocado en lo que realmente importa para este tipo de usuario.
        """
        
        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                stream=False,
                options={
                    'temperature': 0.7,
                    'num_predict': 1000
                }
            )
            
            return response['response']
        
        except Exception as e:
            logger.error(f"Error analizando caso de uso: {str(e)}")
            return f"❌ Error: {str(e)}"
    
    def generate_buying_advice(self, car_info):
        """
        Genera consejo de compra detallado para un coche específico.
        Incluye mantenimiento, seguros, etc.
        """
        
        prompt = f"""Eres un asesor de compra de vehículos muy experimentado.

VEHÍCULO A ANALIZAR:
{car_info}

Proporciona un CONSEJO DE COMPRA detallado que incluya:
1. ¿Es una buena compra? (análisis de valor)
2. Mantenimiento esperado
3. Costos operativos estimados
4. Puntos fuertes y débiles
5. A qué tipo de comprador le conviene más

Sé honesto y equilibrado.
        """
        
        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                stream=False,
                options={
                    'temperature': 0.6,
                    'num_predict': 1000
                }
            )
            
            return response['response']
        
        except Exception as e:
            logger.error(f"Error generando consejo de compra: {str(e)}")
            return f"❌ Error: {str(e)}"
    
    def _format_cars_info(self, cars):
        """Formatea la información de coches para que sea legible en el prompt"""
        
        if not cars:
            return "No hay coches disponibles."
        
        formatted = ""
        for i, car in enumerate(cars, 1):
            props = car._properties
            
            formatted += f"\n{i}. {props.get('name', 'N/A')}\n"
            formatted += f"   Precio: ${props.get('precio', 'N/A')}\n"
            formatted += f"   Score General: {props.get('score', 'N/A')}\n"
            formatted += f"   Score Deportivo: {props.get('score_deportivo', 'N/A')}\n"
            formatted += f"   Score Off-road: {props.get('score_offroad', 'N/A')}\n"
            
            if props.get('autonomia'):
                formatted += f"   Autonomía: {props.get('autonomia')} km\n"
            if props.get('cambio'):
                formatted += f"   Cambio: {props.get('cambio')}\n"
            if props.get('aceleracion'):
                formatted += f"   Aceleración: {props.get('aceleracion')}s (0-100km/h)\n"
            if props.get('potencia'):
                formatted += f"   Potencia: {props.get('potencia')} hp\n"
        
        return formatted