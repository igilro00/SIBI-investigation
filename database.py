from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
import logging

logger = logging.getLogger(__name__)

class Neo4jDatabase:
    """Maneja todas las operaciones con la base de datos Neo4j"""
    
    def __init__(self):
        try:
            self.driver = GraphDatabase.driver(
                NEO4J_URI,
                auth=(NEO4J_USER, NEO4J_PASSWORD),
                max_connection_lifetime=3600
            )
            
            # Test de conexión
            with self.driver.session() as session:
                session.run("RETURN 1")
            logger.info("✅ Conexión a Neo4j establecida")
        except ServiceUnavailable:
            logger.error("❌ No se puede conectar a Neo4j. Asegurate que el servidor está corriendo.")
            raise
    
    def close(self):
        """Cierra la conexión con Neo4j"""
        if self.driver:
            self.driver.close()
    
    # ==================== FILTROS DE BÚSQUEDA ====================
    
    def get_car_by_preferences(self, marca=None, rango_precio=None,
                                tipo_carroceria=None, tipo_motor=None,
                                traccion=None, uso_deportivo=None,
                                uso_eco=None, uso_familiar=None,
                                uso_lujo=None, uso_offroad=None,
                                uso_urbano=None, uso_viajes_largos=None):
        """
        Obtiene coches según múltiples criterios de preferencia.
        Usa todas las relaciones y nodos de la BD.
        """
        query = """
        MATCH (m:MODELO)
        WHERE 1=1
        """
        
        params = {}
        
        # Filtro por marca
        if marca:
            query += " AND (m)-[:FABRICADO_POR]->(:MARCA {name: $marca})"
            params['marca'] = marca
        
        # Filtro por rango de precio
        if rango_precio:
            query += " AND (m)-[:EN_RANGO]->(:RANGO_PRECIO {name: $rango})"
            params['rango'] = rango_precio
        
        # Filtro por tipo de carrocería
        if tipo_carroceria:
            query += " AND (m)-[:ES_TIPO]->(:TIPO_CARROCERIA {name: $carroceria})"
            params['carroceria'] = tipo_carroceria
        
        # Filtro por tipo de motor
        if tipo_motor:
            query += " AND (m)-[:TIENE_MOTOR]->(:TIPO_MOTOR {name: $motor})"
            params['motor'] = tipo_motor
        
        # Filtro por tracción
        if traccion:
            query += " AND (m)-[:TIPO_TRACCION]->(:TRACCION {name: $traccion})"
            params['traccion'] = traccion
        
        # Filtros por uso (relaciones APTO_PARA)
        if uso_deportivo:
            query += " AND (m)-[:APTO_PARA]->(:USO_DEPORTIVO)"
        if uso_eco:
            query += " AND (m)-[:APTO_PARA]->(:USO_ECO)"
        if uso_familiar:
            query += " AND (m)-[:APTO_PARA]->(:USO_FAMILIAR)"
        if uso_lujo:
            query += " AND (m)-[:APTO_PARA]->(:USO_LUJO)"
        if uso_offroad:
            query += " AND (m)-[:APTO_PARA]->(:USO_OFFROAD)"
        if uso_urbano:
            query += " AND (m)-[:APTO_PARA]->(:USO_URBANO)"
        if uso_viajes_largos:
            query += " AND (m)-[:APTO_PARA]->(:USO_VIAJES_LARGOS)"
        
        query += " RETURN m LIMIT 15"
        
        try:
            with self.driver.session() as session:
                result = session.run(query, params)
                return [record['m'] for record in result]
        except Exception as e:
            logger.error(f"Error en búsqueda: {str(e)}")
            return []
    
    # ==================== OBTENER OPCIONES PARA FILTROS ====================
    
    def get_all_marcas(self):
        """Obtiene todas las marcas disponibles"""
        query = "MATCH (m:MARCA) RETURN m.name as name ORDER BY name"
        try:
            with self.driver.session() as session:
                result = session.run(query)
                return sorted([record['name'] for record in result if record['name']])
        except Exception as e:
            logger.error(f"Error obteniendo marcas: {str(e)}")
            return []
    
    def get_all_rangos_precio(self):
        """Obtiene todos los rangos de precio ordenados"""
        query = """
        MATCH (r:RANGO_PRECIO)
        RETURN r.name as name, r.min as min_price
        ORDER BY r.min ASC
        """
        try:
            with self.driver.session() as session:
                result = session.run(query)
                return [record['name'] for record in result if record['name']]
        except Exception as e:
            logger.error(f"Error obteniendo rangos: {str(e)}")
            return []
    
    def get_all_tipos_carroceria(self):
        """Obtiene todos los tipos de carrocería"""
        query = "MATCH (t:TIPO_CARROCERIA) RETURN t.name as name ORDER BY name"
        try:
            with self.driver.session() as session:
                result = session.run(query)
                return sorted([record['name'] for record in result if record['name']])
        except Exception as e:
            logger.error(f"Error obteniendo tipos de carrocería: {str(e)}")
            return []
    
    def get_all_tipos_motor(self):
        """Obtiene todos los tipos de motor"""
        query = "MATCH (t:TIPO_MOTOR) RETURN t.name as name ORDER BY name"
        try:
            with self.driver.session() as session:
                result = session.run(query)
                return sorted([record['name'] for record in result if record['name']])
        except Exception as e:
            logger.error(f"Error obteniendo tipos de motor: {str(e)}")
            return []
    
    def get_all_tracciones(self):
        """Obtiene todos los tipos de tracción"""
        query = "MATCH (t:TRACCION) RETURN t.name as name ORDER BY name"
        try:
            with self.driver.session() as session:
                result = session.run(query)
                return sorted([record['name'] for record in result if record['name']])
        except Exception as e:
            logger.error(f"Error obteniendo tracciones: {str(e)}")
            return []
    
    # ==================== DETALLES DE COCHES ====================
    
    def get_car_details(self, modelo_name):
        """Obtiene detalles completos de un coche específico"""
        query = """
        MATCH (m:MODELO {name: $name})
        OPTIONAL MATCH (m)-[:FABRICADO_POR]->(marca:MARCA)
        OPTIONAL MATCH (m)-[:EN_RANGO]->(rango:RANGO_PRECIO)
        OPTIONAL MATCH (m)-[:ES_TIPO]->(carroceria:TIPO_CARROCERIA)
        OPTIONAL MATCH (m)-[:TIENE_MOTOR]->(motor:TIPO_MOTOR)
        OPTIONAL MATCH (m)-[:TIPO_TRACCION]->(traccion:TRACCION)
        OPTIONAL MATCH (m)-[:APTO_PARA]->(uso)
        RETURN m as modelo,
            marca,
            rango,
            carroceria,
            motor,
            traccion,
            collect(DISTINCT labels(uso)[0]) as usos_disponibles
        """
        try:
            with self.driver.session() as session:
                result = session.run(query, {'name': modelo_name})
                record = result.single()
                if record:
                    return {
                        'modelo': record['modelo'],
                        'marca': record['marca'],
                        'rango_precio': record['rango'],
                        'carroceria': record['carroceria'],
                        'motor': record['motor'],
                        'traccion': record['traccion'],
                        'usos': record['usos_disponibles']
                    }
                return None
        except Exception as e:
            logger.error(f"Error obteniendo detalles: {str(e)}")
            return None
    
    # ==================== COCHES SIMILARES Y COMPETENCIA ====================
    
    def get_similar_cars(self, modelo_name):
        """
        Obtiene coches similares usando:
        - Relación COMPITE_CON (competencia directa)
        - Mismo rango de precio
        - Misma carrocería
        
        Ahora soporta búsqueda flexible (parcial).
        Ejemplo: "Golf" encontrará "Golf 2.0", "Golf GTI", etc.
        """
        # Primero, intenta búsqueda exacta
        query_exact = """
        MATCH (m1:MODELO {name: $name})
        RETURN m1 as modelo
        LIMIT 1
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query_exact, {'name': modelo_name})
                found = result.single()
                
                # Si no encontró exacto, busca por CONTAINS (case-insensitive)
                if not found:
                    query_partial = """
                    MATCH (m1:MODELO)
                    WHERE toLower(m1.name) CONTAINS toLower($name)
                    RETURN m1 as modelo
                    LIMIT 1
                    """
                    result = session.run(query_partial, {'name': modelo_name})
                    found = result.single()
                
                if not found:
                    return []
                
                # Obtener el nombre exacto del modelo encontrado
                modelo_encontrado = found['modelo']
                modelo_name = modelo_encontrado['name']
        
        except Exception as e:
            logger.error(f"Error encontrando modelo: {str(e)}")
            return []
        
        # Ahora busca similares del modelo encontrado
        query = """
        MATCH (m1:MODELO {name: $name})
        OPTIONAL MATCH (m1)-[comp:COMPITE_CON]-(m2:MODELO)
        OPTIONAL MATCH (m1)-[:EN_RANGO]->(rango:RANGO_PRECIO)<-[:EN_RANGO]-(m3:MODELO)
        OPTIONAL MATCH (m1)-[:ES_TIPO]->(carroceria:TIPO_CARROCERIA)<-[:ES_TIPO]-(m4:MODELO)
        WITH DISTINCT
        CASE
            WHEN m2 IS NOT NULL THEN m2
            WHEN m3 IS NOT NULL THEN m3
            WHEN m4 IS NOT NULL THEN m4
        END as similar_modelo
        WHERE similar_modelo IS NOT NULL AND similar_modelo.name <> $name
        RETURN similar_modelo
        LIMIT 8
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, {'name': modelo_name})
                return [record['similar_modelo'] for record in result]
        except Exception as e:
            logger.error(f"Error obteniendo similares: {str(e)}")
            return []
    
    def search_models_by_partial_name(self, search_term):
        """
        Busca modelos que contengan el término (búsqueda flexible).
        Retorna lista de nombres que coinciden.
        
        Ejemplo: "Golf" encuentra ["Golf 1.4", "Golf 2.0", "Golf GTI"]
        """
        if not search_term or len(search_term) < 1:
            return []
        
        query = """
        MATCH (m:MODELO)
        WHERE toLower(m.name) CONTAINS toLower($term)
        RETURN DISTINCT m.name as nombre
        ORDER BY m.name
        """
        try:
            with self.driver.session() as session:
                result = session.run(query, {'term': search_term})
                return [record['nombre'] for record in result]
        except Exception as e:
            logger.error(f"Error buscando modelos: {str(e)}")
            return []
    
    def get_all_model_names(self):
        """
        Obtiene TODOS los nombres de modelos disponibles (para autocomplete).
        Retorna lista ordenada de nombres.
        """
        query = """
        MATCH (m:MODELO)
        RETURN DISTINCT m.name as nombre
        ORDER BY m.name
        """
        try:
            with self.driver.session() as session:
                result = session.run(query)
                return [record['nombre'] for record in result]
        except Exception as e:
            logger.error(f"Error obteniendo modelos: {str(e)}")
            return []
    
    def get_competing_cars(self, modelo_name):
        """Obtiene coches que compiten directamente (COMPITE_CON)"""
        query = """
        MATCH (m1:MODELO {name: $name})-[rel:COMPITE_CON]-(m2:MODELO)
        RETURN m2 as modelo, type(rel) as relacion
        LIMIT 10
        """
        try:
            with self.driver.session() as session:
                result = session.run(query, {'name': modelo_name})
                return [record for record in result]
        except Exception as e:
            logger.error(f"Error obteniendo competidores: {str(e)}")
            return []
    
    # ==================== RECOMENDACIONES PERSONALIZADAS ====================
    
    def get_ideal_cars_for_use(self, uso_type):
        """
        Obtiene coches ideales para un uso específico.
        Usa relación IDEAL_PARA o APTO_PARA según uso_type.
        uso_type puede ser:
        - USO_DEPORTIVO, USO_ECO, USO_FAMILIAR, USO_LUJO,
        - USO_OFFROAD, USO_URBANO, USO_VIAJES_LARGOS
        """
        query = f"""
        MATCH (m:MODELO)-[:APTO_PARA]->(:{uso_type})
        RETURN m as modelo
        ORDER BY m.score_deportivo DESC
        LIMIT 10
        """
        try:
            with self.driver.session() as session:
                result = session.run(query)
                return [record['modelo'] for record in result]
        except Exception as e:
            logger.error(f"Error obteniendo coches para {uso_type}: {str(e)}")
            return []
    
    def get_best_value_cars(self, rango_precio=None):
        """
        Obtiene coches con mejor relación precio/características.
        Ordena por score y precio.
        """
        query = """
        MATCH (m:MODELO)
        """
        
        if rango_precio:
            query += "-[:EN_RANGO]->(:RANGO_PRECIO {name: $rango})"
        
        query += """
        RETURN m as modelo
        ORDER BY m.score DESC, m.precio ASC
        LIMIT 10
        """
        
        params = {'rango': rango_precio} if rango_precio else {}
        
        try:
            with self.driver.session() as session:
                result = session.run(query, params)
                return [record['modelo'] for record in result]
        except Exception as e:
            logger.error(f"Error obteniendo mejores valores: {str(e)}")
            return []
    
    # ==================== ESTADÍSTICAS ====================
    
    def get_stats(self):
        """Obtiene estadísticas de la base de datos"""
        query = """
        MATCH (n)
        RETURN
        COUNT(DISTINCT n) as total_nodos,
        COUNT(DISTINCT labels(n)[0]) as tipos_nodos
        """
        try:
            with self.driver.session() as session:
                result = session.run(query)
                record = result.single()
                return {
                    'total_nodos': record['total_nodos'],
                    'tipos_nodos': record['tipos_nodos']
                }
        except Exception as e:
            logger.error(f"Error obteniendo stats: {str(e)}")
            return {}
    
    def search_by_price_range(self, min_price, max_price):
        """Busca coches dentro de un rango de precio específico"""
        query = """
        MATCH (m:MODELO)
        WHERE m.precio >= $min AND m.precio <= $max
        RETURN m as modelo
        ORDER BY m.precio ASC
        """
        try:
            with self.driver.session() as session:
                result = session.run(query, {'min': min_price, 'max': max_price})
                return [record['modelo'] for record in result]
        except Exception as e:
            logger.error(f"Error buscando por precio: {str(e)}")
            return []
    
    def get_top_models_by_score(self, limit=10):
        """Obtiene los mejores modelos por puntuación total"""
        query = """
        MATCH (m:MODELO)
        RETURN m as modelo
        ORDER BY m.score DESC
        LIMIT $limit
        """
        try:
            with self.driver.session() as session:
                result = session.run(query, {'limit': limit})
                return [record['modelo'] for record in result]
        except Exception as e:
            logger.error(f"Error obteniendo top modelos: {str(e)}")
            return []