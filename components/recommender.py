from database import Neo4jDatabase
from llm_handler import OllamaLLMHandler
import logging

logger = logging.getLogger(__name__)


class CarRecommender:
    """Maneja la lógica de recomendación de coches"""
    
    def __init__(self):
        self.db = Neo4jDatabase()
        self.llm = OllamaLLMHandler()
    
    def get_recommendations(self, marca=None, rango_precio=None, 
                           tipo_carroceria=None, tipo_motor=None,
                           traccion=None, uso_deportivo=False, 
                           uso_eco=False, uso_familiar=False,
                           uso_lujo=False, uso_offroad=False,
                           uso_urbano=False, uso_viajes_largos=False):
        """
        Obtiene recomendaciones personalizadas basadas en todos los criterios.
        Combina búsqueda en BD + análisis del LLM.
        
        El LLM detecta automáticamente si hay pocos filtros y sugiere 3 preguntas
        para mejorar futuras recomendaciones.
        """
        
        try:
            # 1. Buscar coches en la BD
            cars = self.db.get_car_by_preferences(
                marca=marca,
                rango_precio=rango_precio,
                tipo_carroceria=tipo_carroceria,
                tipo_motor=tipo_motor,
                traccion=traccion,
                uso_deportivo=uso_deportivo,
                uso_eco=uso_eco,
                uso_familiar=uso_familiar,
                uso_lujo=uso_lujo,
                uso_offroad=uso_offroad,
                uso_urbano=uso_urbano,
                uso_viajes_largos=uso_viajes_largos
            )
            
            if not cars:
                return {
                    'cars': [],
                    'recommendation': '❌ No se encontraron coches con esos criterios. Intenta ajustar los filtros.',
                    'count': 0
                }
            
            # 2. Preparar contexto para el LLM
            preferences_text = self._build_preferences_text(
                marca, rango_precio, tipo_carroceria, tipo_motor,
                traccion, uso_deportivo, uso_eco, uso_familiar,
                uso_lujo, uso_offroad, uso_urbano, uso_viajes_largos
            )
            
            # 3. Preparar diccionario de filtros para que el LLM los cuente
            user_filters = {
                'marca': marca,
                'rango_precio': rango_precio,
                'tipo_carroceria': tipo_carroceria,
                'tipo_motor': tipo_motor,
                'traccion': traccion,
                'uso_deportivo': uso_deportivo,
                'uso_eco': uso_eco,
                'uso_familiar': uso_familiar,
                'uso_lujo': uso_lujo,
                'uso_offroad': uso_offroad,
                'uso_urbano': uso_urbano,
                'uso_viajes_largos': uso_viajes_largos
            }
            
            # 4. Generar recomendación con LLM (pasando los filtros)
            recommendation = self.llm.generate_recommendation(
                preferences_text,
                cars,
                user_filters=user_filters  # Pasar los filtros para que cuente cuántos se usaron
            )
            
            return {
                'cars': cars,
                'recommendation': recommendation,
                'count': len(cars)
            }
        
        except Exception as e:
            logger.error(f"Error generando recomendaciones: {str(e)}")
            return {
                'cars': [],
                'recommendation': f'❌ Error: {str(e)}',
                'count': 0
            }
    
    def get_similar_cars(self, modelo_name):
        """Obtiene coches similares al modelo especificado"""
        try:
            return self.db.get_similar_cars(modelo_name)
        except Exception as e:
            logger.error(f"Error obteniendo similares: {str(e)}")
            return []
    
    def get_competing_cars(self, modelo_name):
        """Obtiene coches competidores directos"""
        try:
            return self.db.get_competing_cars(modelo_name)
        except Exception as e:
            logger.error(f"Error obteniendo competidores: {str(e)}")
            return []
    
    def get_ideal_cars_for_use(self, uso_type):
        """Obtiene coches ideales para un tipo de uso específico"""
        try:
            cars = self.db.get_ideal_cars_for_use(uso_type)
            
            if not cars:
                return {
                    'cars': [],
                    'message': f'No hay coches ideales para {uso_type}',
                    'count': 0
                }
            
            # Generar descripción con LLM
            description = self.llm.generate_use_case_analysis(cars, uso_type)
            
            return {
                'cars': cars,
                'message': description,
                'count': len(cars)
            }
        
        except Exception as e:
            logger.error(f"Error en recomendación de uso: {str(e)}")
            return {'cars': [], 'message': f'❌ Error: {str(e)}', 'count': 0}
    
    def get_best_value_cars(self, rango_precio=None):
        """Obtiene coches con mejor relación precio/características"""
        try:
            cars = self.db.get_best_value_cars(rango_precio)
            
            if not cars:
                return {
                    'cars': [],
                    'message': 'No hay coches con buena relación precio/valor',
                    'count': 0
                }
            
            return {
                'cars': cars,
                'message': f'✅ Se encontraron {len(cars)} coches con excelente relación precio/valor',
                'count': len(cars)
            }
        
        except Exception as e:
            logger.error(f"Error obteniendo mejor valor: {str(e)}")
            return {'cars': [], 'message': f'❌ Error: {str(e)}', 'count': 0}
    
    def get_top_models(self, limit=10):
        """Obtiene los mejores modelos según puntuación"""
        try:
            return self.db.get_top_models_by_score(limit)
        except Exception as e:
            logger.error(f"Error obteniendo top modelos: {str(e)}")
            return []
    
    def search_by_price_range(self, min_price, max_price):
        """Busca coches dentro de un rango de precio específico"""
        try:
            return self.db.search_by_price_range(min_price, max_price)
        except Exception as e:
            logger.error(f"Error buscando por precio: {str(e)}")
            return []
    
    def get_car_details(self, modelo_name):
        """Obtiene detalles completos de un coche"""
        try:
            return self.db.get_car_details(modelo_name)
        except Exception as e:
            logger.error(f"Error obteniendo detalles: {str(e)}")
            return None
    
    def compare_cars_with_llm(self, car1_name, car2_name, aspect):
        """Compara dos coches usando el LLM"""
        try:
            car1 = self.get_car_details(car1_name)
            car2 = self.get_car_details(car2_name)
            
            if not car1 or not car2:
                return "❌ No se encontraron los coches para comparar"
            
            car1_info = self._format_single_car(car1)
            car2_info = self._format_single_car(car2)
            
            return self.llm.compare_cars(car1_info, car2_info, aspect)
        
        except Exception as e:
            logger.error(f"Error comparando coches: {str(e)}")
            return f"❌ Error: {str(e)}"
    
    # ==================== MÉTODOS AUXILIARES ====================
    
    def _build_preferences_text(self, marca, rango_precio, tipo_carroceria,
                                tipo_motor, traccion, uso_deportivo, uso_eco,
                                uso_familiar, uso_lujo, uso_offroad, 
                                uso_urbano, uso_viajes_largos):
        """Construye un texto legible con las preferencias del usuario"""
        
        prefs = []
        
        if marca:
            prefs.append(f"Marca: {marca}")
        if rango_precio:
            prefs.append(f"Rango de precio: {rango_precio}")
        if tipo_carroceria:
            prefs.append(f"Tipo de carrocería: {tipo_carroceria}")
        if tipo_motor:
            prefs.append(f"Tipo de motor: {tipo_motor}")
        if traccion:
            prefs.append(f"Tracción: {traccion}")
        
        # Usos
        usos = []
        if uso_deportivo:
            usos.append("Deportivo")
        if uso_eco:
            usos.append("Eco/Eficiente")
        if uso_familiar:
            usos.append("Familiar")
        if uso_lujo:
            usos.append("Lujo")
        if uso_offroad:
            usos.append("Off-road")
        if uso_urbano:
            usos.append("Urbano")
        if uso_viajes_largos:
            usos.append("Viajes largos")
        
        if usos:
            prefs.append(f"Usos: {', '.join(usos)}")
        
        return "\n".join(prefs) if prefs else "Sin preferencias específicas"
    
    def _format_cars_info(self, cars):
        """Formatea información de coches para el LLM"""
        
        if not cars:
            return "No hay coches disponibles."
        
        formatted = ""
        for i, car in enumerate(cars, 1):
            props = car._properties
            formatted += f"\n{i}. {props.get('name', 'N/A')}\n"
            formatted += f"   - Precio: ${props.get('precio', 'N/A')}\n"
            formatted += f"   - Score General: {props.get('score', 'N/A')}\n"
            formatted += f"   - Score Deportivo: {props.get('score_deportivo', 'N/A')}\n"
            formatted += f"   - Score Off-road: {props.get('score_offroad', 'N/A')}\n"
        
        return formatted
    
    def _format_single_car(self, car):
        """Formatea información de un solo coche"""
        
        props = car._properties
        
        info = f"{props.get('name', 'N/A')}\n"
        info += f"Precio: ${props.get('precio', 'N/A')}\n"
        info += f"Score General: {props.get('score', 'N/A')}\n"
        info += f"Score Deportivo: {props.get('score_deportivo', 'N/A')}\n"
        info += f"Score Off-road: {props.get('score_offroad', 'N/A')}\n"
        
        if props.get('autonomia'):
            info += f"Autonomía: {props.get('autonomia')} km\n"
        if props.get('cambio'):
            info += f"Cambio: {props.get('cambio')}\n"
        if props.get('aceleracion'):
            info += f"Aceleración: {props.get('aceleracion')}s (0-100km/h)\n"
        if props.get('potencia'):
            info += f"Potencia: {props.get('potencia')} hp\n"
        
        return info
    
    def close(self):
        """Cierra la conexión"""
        self.db.close()
