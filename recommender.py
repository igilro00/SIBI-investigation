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
        """Obtiene recomendaciones personalizadas"""
        try:
            # 1. Buscar coches en BD
            cars = self.db.get_car_by_preferences(
                marca=marca, rango_precio=rango_precio,
                tipo_carroceria=tipo_carroceria, tipo_motor=tipo_motor,
                traccion=traccion, uso_deportivo=uso_deportivo,
                uso_eco=uso_eco, uso_familiar=uso_familiar,
                uso_lujo=uso_lujo, uso_offroad=uso_offroad,
                uso_urbano=uso_urbano, uso_viajes_largos=uso_viajes_largos
            )
            
            if not cars:
                return {
                    'cars': [],
                    'recommendation': '❌ No se encontraron coches. Intenta otros filtros.',
                    'count': 0
                }
            
            # 2. Preparar contexto
            preferences_text = self._build_preferences_text(
                marca, rango_precio, tipo_carroceria, tipo_motor,
                traccion, uso_deportivo, uso_eco, uso_familiar,
                uso_lujo, uso_offroad, uso_urbano, uso_viajes_largos
            )
            
            # 3. Diccionario de filtros para que el LLM los cuente
            user_filters = {
                'marca': marca, 'rango_precio': rango_precio,
                'tipo_carroceria': tipo_carroceria, 'tipo_motor': tipo_motor,
                'traccion': traccion, 'uso_deportivo': uso_deportivo,
                'uso_eco': uso_eco, 'uso_familiar': uso_familiar,
                'uso_lujo': uso_lujo, 'uso_offroad': uso_offroad,
                'uso_urbano': uso_urbano, 'uso_viajes_largos': uso_viajes_largos
            }
            
            # 4. Generar recomendación con LLM
            recommendation = self.llm.generate_recommendation(
                preferences_text, cars, user_filters=user_filters
            )
            
            return {
                'cars': cars,
                'recommendation': recommendation,
                'count': len(cars)
            }
        
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            return {'cars': [], 'recommendation': f'❌ Error: {str(e)}', 'count': 0}

    def get_similar_cars(self, modelo_name):
        """Obtiene coches similares"""
        try:
            return self.db.get_similar_cars(modelo_name)
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            return []

    def get_competing_cars(self, modelo_name):
        """Obtiene coches competidores directos"""
        try:
            return self.db.get_competing_cars(modelo_name)
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            return []

    def get_ideal_cars_for_use(self, uso_type):
        """Obtiene coches ideales para un uso"""
        try:
            cars = self.db.get_ideal_cars_for_use(uso_type)
            
            if not cars:
                return {'cars': [], 'message': f'No hay coches para {uso_type}', 'count': 0}
            
            description = self.llm.generate_use_case_analysis(cars, uso_type)
            return {'cars': cars, 'message': description, 'count': len(cars)}
        
        except Exception as e:
            return {'cars': [], 'message': f'❌ Error: {str(e)}', 'count': 0}

    def get_best_value_cars(self, rango_precio=None):
        """Obtiene coches con mejor relación precio/características"""
        try:
            cars = self.db.get_best_value_cars(rango_precio)
            
            if not cars:
                return {'cars': [], 'message': 'No hay coches con buena relación', 'count': 0}
            
            return {
                'cars': cars,
                'message': f'✅ Se encontraron {len(cars)} coches con excelente relación precio/valor',
                'count': len(cars)
            }
        
        except Exception as e:
            return {'cars': [], 'message': f'❌ Error: {str(e)}', 'count': 0}

    def get_top_models(self, limit=10):
        """Obtiene los mejores modelos"""
        try:
            return self.db.get_top_models_by_score(limit)
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            return []

    def search_by_price_range(self, min_price, max_price):
        """Busca coches por rango de precio"""
        try:
            return self.db.search_by_price_range(min_price, max_price)
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            return []

    def get_car_details(self, modelo_name):
        """Obtiene detalles de un coche"""
        try:
            return self.db.get_car_details(modelo_name)
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            return None

    def compare_cars_with_llm(self, car1_name, car2_name, aspect):
        """Compara dos coches"""
        try:
            car1 = self.get_car_details(car1_name)
            car2 = self.get_car_details(car2_name)
            
            if not car1 or not car2:
                return "❌ No se encontraron los coches"
            
            car1_info = self._format_single_car(car1)
            car2_info = self._format_single_car(car2)
            
            return self.llm.compare_cars(car1_info, car2_info, aspect)
        
        except Exception as e:
            return f"❌ Error: {str(e)}"

    def search_models(self, search_term):
        """Busca modelos por término"""
        try:
            return self.db.search_models_by_partial_name(search_term)
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            return []

    def get_all_models(self):
        """Obtiene todos los modelos"""
        try:
            return self.db.get_all_model_names()
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            return []

    # ==================== MÉTODOS AUXILIARES ====================

    def _build_preferences_text(self, marca, rango_precio, tipo_carroceria,
                               tipo_motor, traccion, uso_deportivo, uso_eco,
                               uso_familiar, uso_lujo, uso_offroad,
                               uso_urbano, uso_viajes_largos):
        """Construye texto con preferencias"""
        prefs = []
        
        if marca:
            prefs.append(f"**Marca:** {marca}")
        if rango_precio:
            prefs.append(f"**Rango Precio:** {rango_precio}")
        if tipo_carroceria:
            prefs.append(f"**Carrocería:** {tipo_carroceria}")
        if tipo_motor:
            prefs.append(f"**Motor:** {tipo_motor}")
        if traccion:
            prefs.append(f"**Tracción:** {traccion}")
        
        usos = []
        if uso_deportivo: usos.append("Deportivo")
        if uso_eco: usos.append("Eco")
        if uso_familiar: usos.append("Familiar")
        if uso_lujo: usos.append("Lujo")
        if uso_offroad: usos.append("Off-road")
        if uso_urbano: usos.append("Urbano")
        if uso_viajes_largos: usos.append("Viajes largos")
        
        if usos:
            prefs.append(f"**Usos:** {', '.join(usos)}")
        
        return "\n".join(prefs) if prefs else "Sin preferencias específicas"

    def _format_single_car(self, car):
        """Formatea un coche único"""
        props = car._properties if hasattr(car, '_properties') else car
        
        info = f"**{props.get('name', 'N/A')}**\n"
        info += f"Precio: ${props.get('precio', 'N/A')}\n"
        
        if props.get('tipo_motor'):
            info += f"Motor: {props.get('tipo_motor')}\n"
        if props.get('potencia'):
            info += f"Potencia: {props.get('potencia')} hp\n"
        if props.get('aceleracion'):
            info += f"Aceleración: {props.get('aceleracion')}s\n"
        if props.get('autonomia'):
            info += f"Autonomía: {props.get('autonomia')} km\n"
        
        return info

    def close(self):
        """Cierra conexiones"""
        self.db.close()