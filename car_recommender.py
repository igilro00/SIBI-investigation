"""
Recomendador Inteligente - Conversación con extracción de datos y preguntas
Combina criterios, aprende preferencias, y pide datos si faltan
AHORA COMBINA CRITERIOS DE TODA LA CONVERSACIÓN
"""

import logging
import re
from typing import List, Dict, Any, Tuple
from neo4j import GraphDatabase
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding
from config import NEO4J, OLLAMA, TOPICS

logger = logging.getLogger(__name__)

class CarRecommender:
    """Recomendador inteligente que combina criterios de toda la conversación"""
    
    def __init__(self, 
                 neo4j_uri: str = None,
                 neo4j_user: str = None,
                 neo4j_password: str = None,
                 ollama_base_url: str = None,
                 ollama_model: str = None):
        """Inicializar recomendador inteligente"""
        neo4j_uri = neo4j_uri or NEO4J["uri"]
        neo4j_user = neo4j_user or NEO4J["user"]
        neo4j_password = neo4j_password or NEO4J["password"]
        ollama_base_url = ollama_base_url or OLLAMA["base_url"]
        ollama_model = ollama_model or OLLAMA["model"]
        
        try:
            # Neo4j
            self.neo4j_driver = GraphDatabase.driver(
                neo4j_uri,
                auth=(neo4j_user, neo4j_password)
            )
            
            with self.neo4j_driver.session() as session:
                session.run("RETURN 1")
            logger.info("✅ Neo4j conectado")
            
            # LLM
            self.llm = Ollama(
                base_url=ollama_base_url,
                model=ollama_model,
                temperature=OLLAMA["temperature"],
                context_window=OLLAMA["context_window"]
            )
            logger.info(f"✅ Ollama conectado: {ollama_model}")
            
            # Embedding
            self.embed_model = OllamaEmbedding(
                base_url=ollama_base_url,
                model_name=OLLAMA["embed_model"],
            )
            logger.info("✅ Embedding conectado")
            
            # Cargar vehículos
            self.vehicles_db = self._load_vehicles_db()
            logger.info(f"✅ {len(self.vehicles_db)} vehículos cargados")
            
            # Tipos de vehículos para reconocer
            self.vehicle_types = [
                "suv", "berlina", "sedán", "compacto", "familiar", "monovolumen",
                "coupé", "convertible", "pickup", "monoespacial", "todoterreno",
                "city car", "minicooper", "sport", "deportivo"
            ]
            
        except Exception as e:
            logger.error(f"❌ Error inicializando: {e}")
            raise
    
    def _load_vehicles_db(self) -> List[Dict[str, Any]]:
        """Cargar todos los vehículos desde Neo4j"""
        try:
            query = """
            MATCH (m:MODELO)
            RETURN {
                id: m.id,
                name: m.name,
                precio: m.precio,
                potencia: m.potencia,
                aceleracion: m.aceleracion,
                autonomia: m.autonomia,
                cambio: m.cambio,
                score_eco: m.score_eco,
                score_urbano: m.score_urbano,
                score_familiar: m.score_familiar,
                score_deportivo: m.score_deportivo,
                score_viajes: m.score_viajes,
                score_offroad: m.score_offroad
            } as vehicle
            """
            
            with self.neo4j_driver.session() as session:
                result = session.run(query)
                vehicles = [record["vehicle"] for record in result]
            
            # Eliminar duplicados
            seen_ids = set()
            unique_vehicles = []
            for v in vehicles:
                v_id = v.get('id')
                if v_id and v_id not in seen_ids:
                    seen_ids.add(v_id)
                    v = self._clean_vehicle(v)
                    unique_vehicles.append(v)
            
            return unique_vehicles
        except Exception as e:
            logger.warning(f"❌ Error cargando vehículos: {e}")
            return []
    
    def _clean_vehicle(self, vehicle: Dict[str, Any]) -> Dict[str, Any]:
        """Limpiar datos de vehículo"""
        defaults = {
            'precio': 0,
            'potencia': 0,
            'aceleracion': 0,
            'autonomia': 0,
            'cambio': 'N/A',
            'score_eco': 0,
            'score_urbano': 0,
            'score_familiar': 0,
            'score_deportivo': 0,
            'score_viajes': 0,
            'score_offroad': 0,
        }
        
        for key, default_val in defaults.items():
            val = vehicle.get(key)
            if val is None:
                vehicle[key] = default_val
            else:
                try:
                    vehicle[key] = float(val)
                except (TypeError, ValueError):
                    vehicle[key] = default_val
        
        return vehicle
    
    def extract_criteria_from_query(self, user_query: str, memory_context: str) -> Dict[str, Any]:
        """
        EXTRAER CRITERIOS de la query ACTUAL y COMBINAR con memoria
        Entiende tipos de vehículos también
        """
        query_lower = user_query.lower()
        memory_lower = memory_context.lower() if memory_context else ""
        
        criteria = {
            "topics": [],
            "vehicle_type": None,
            "price_range": None,
            "power_range": None,
            "autonomy_min": None,
            "has_enough_data": False
        }
        
        # ============================================================
        # 1. EXTRAER TIPO DE VEHÍCULO (SUV, berlina, etc)
        # ============================================================
        for v_type in self.vehicle_types:
            if v_type in query_lower:
                criteria["vehicle_type"] = v_type
                logger.info(f"📍 Tipo detectado: {v_type}")
                break
        
        # Si no está en query actual, buscar en memoria
        if not criteria["vehicle_type"]:
            for v_type in self.vehicle_types:
                if v_type in memory_lower:
                    criteria["vehicle_type"] = v_type
                    logger.info(f"📍 Tipo de memoria: {v_type}")
                    break
        
        # ============================================================
        # 2. EXTRAER TEMAS (eco, deportivo, familiar, etc)
        # ============================================================
        for topic, keywords in TOPICS.items():
            if any(kw in query_lower for kw in keywords):
                criteria["topics"].append(topic)
        
        # Combinar con memoria
        for topic, keywords in TOPICS.items():
            if any(kw in memory_lower for kw in keywords):
                if topic not in criteria["topics"]:
                    criteria["topics"].append(topic)
        
        # ============================================================
        # 3. EXTRAER PRECIO (números con € o k)
        # ============================================================
        price_patterns = [
            r'(\d+)\s*k',
            r'€\s*(\d+)',
            r'(\d+)\s*€',
            r'menos de\s*(\d+)',
        ]
        
        for pattern in price_patterns:
            matches = re.findall(pattern, query_lower)
            if matches:
                price = int(matches[0])
                if price < 500:
                    price *= 1000
                criteria["price_range"] = (0, price)
                logger.info(f"💰 Precio detectado: hasta €{price:,}")
                break
        
        # Si no en query, buscar en memoria
        if not criteria["price_range"]:
            for pattern in price_patterns:
                matches = re.findall(pattern, memory_lower)
                if matches:
                    price = int(matches[0])
                    if price < 500:
                        price *= 1000
                    criteria["price_range"] = (0, price)
                    logger.info(f"💰 Precio de memoria: hasta €{price:,}")
                    break
        
        # ============================================================
        # 4. EXTRAER POTENCIA
        # ============================================================
        power_patterns = [
            r'(\d+)\s*cv',
            r'(\d+)\s*hp',
            r'(\d+)\s*caballos',
        ]
        
        for pattern in power_patterns:
            matches = re.findall(pattern, query_lower)
            if matches:
                power = int(matches[0])
                criteria["power_range"] = (power, 1000)
                logger.info(f"⚡ Potencia detectada: mín {power} CV")
                break
        
        if not criteria["power_range"]:
            for pattern in power_patterns:
                matches = re.findall(pattern, memory_lower)
                if matches:
                    power = int(matches[0])
                    criteria["power_range"] = (power, 1000)
                    logger.info(f"⚡ Potencia de memoria: mín {power} CV")
                    break
        
        # ============================================================
        # 5. EXTRAER AUTONOMÍA
        # ============================================================
        autonomy_patterns = [
            r'(\d+)\s*km',
            r'autonomía\s*(\d+)',
        ]
        
        for pattern in autonomy_patterns:
            matches = re.findall(pattern, query_lower)
            if matches:
                autonomy = int(matches[0])
                criteria["autonomy_min"] = autonomy
                logger.info(f"🔋 Autonomía detectada: mín {autonomy} km")
                break
        
        if not criteria["autonomy_min"]:
            for pattern in autonomy_patterns:
                matches = re.findall(pattern, memory_lower)
                if matches:
                    autonomy = int(matches[0])
                    criteria["autonomy_min"] = autonomy
                    logger.info(f"🔋 Autonomía de memoria: mín {autonomy} km")
                    break
        
        # ============================================================
        # 6. DETERMINAR SI TIENE SUFICIENTES DATOS
        # ============================================================
        has_type = criteria["vehicle_type"] is not None
        has_topic = len(criteria["topics"]) > 0
        has_price = criteria["price_range"] is not None
        
        # Necesita tipo + precio, o tipo + tema, o tipo + potencia
        if has_type:
            criteria["has_enough_data"] = has_price or has_topic
        else:
            # Sin tipo, necesita al menos 2 criterios
            data_count = sum([has_topic, has_price, criteria["power_range"] is not None])
            criteria["has_enough_data"] = data_count >= 2
        
        logger.info(f"📊 Criterios finales: tipo={criteria['vehicle_type']}, temas={criteria['topics']}, precio={criteria['price_range']}, datos={criteria['has_enough_data']}")
        
        return criteria
    
    def search_vehicles_by_criteria(self, 
                                   criteria: Dict[str, Any],
                                   user_query: str) -> Tuple[List[Dict], bool]:
        """
        BUSCAR vehículos usando criterios combinados
        """
        if not self.vehicles_db:
            return [], criteria["has_enough_data"]
        
        filtered = self.vehicles_db.copy()
        
        # ============================================================
        # FILTRO 1: TIPO DE VEHÍCULO (por nombre/palabras clave)
        # ============================================================
        if criteria["vehicle_type"]:
            v_type = criteria["vehicle_type"].lower()
            
            # Mapeo de tipos a palabras clave en nombres
            type_keywords = {
                "suv": ["suv", "audi q", "bmw x", "mercedes gle", "range rover", "jeep"],
                "berlina": ["berlina", "sedan", "a4", "c-class", "3 series", "accord", "camry"],
                "sedán": ["sedan", "a4", "c-class", "3 series"],
                "compacto": ["compact", "polo", "fiesta", "ibiza", "i30"],
                "familiar": ["familiar", "estate", "touring", "avant", "break"],
                "monovolumen": ["monovolumen", "mpv", "grand", "scenic"],
            }
            
            type_keys = type_keywords.get(v_type, [v_type])
            filtered = [
                v for v in filtered
                if any(kw in v.get("name", "").lower() for kw in type_keys)
            ]
            logger.info(f"🔍 Después filtro tipo {v_type}: {len(filtered)} vehículos")
        
        # ============================================================
        # FILTRO 2: PRECIO
        # ============================================================
        if criteria["price_range"]:
            min_price, max_price = criteria["price_range"]
            filtered = [
                v for v in filtered
                if min_price <= v.get("precio", 0) <= max_price
            ]
            logger.info(f"🔍 Después filtro precio: {len(filtered)} vehículos")
        
        # ============================================================
        # FILTRO 3: POTENCIA
        # ============================================================
        if criteria["power_range"]:
            min_power, max_power = criteria["power_range"]
            filtered = [
                v for v in filtered
                if min_power <= v.get("potencia", 0) <= max_power
            ]
            logger.info(f"🔍 Después filtro potencia: {len(filtered)} vehículos")
        
        # ============================================================
        # FILTRO 4: AUTONOMÍA
        # ============================================================
        if criteria["autonomy_min"]:
            filtered = [
                v for v in filtered
                if v.get("autonomia", 0) >= criteria["autonomy_min"]
            ]
            logger.info(f"🔍 Después filtro autonomía: {len(filtered)} vehículos")
        
        # ============================================================
        # SCORING POR TEMAS
        # ============================================================
        scored = self._score_vehicles(filtered, criteria["topics"])
        
        ranked = sorted(
            scored,
            key=lambda x: x.get("relevance_score", 0),
            reverse=True
        )
        
        logger.info(f"✅ Top 5 encontrados")
        
        return ranked[:5], criteria["has_enough_data"]
    
    def _score_vehicles(self, vehicles: List[Dict], topics: List[str]) -> List[Dict]:
        """Puntuación por temas"""
        
        scored = []
        
        for vehicle in vehicles:
            score = 0.0
            
            for topic in topics:
                score_key = f"score_{topic}"
                vehicle_score = vehicle.get(score_key, 0)
                
                if vehicle_score is None:
                    vehicle_score = 0
                
                try:
                    vehicle_score = float(vehicle_score)
                except:
                    vehicle_score = 0
                
                score += vehicle_score * 100
            
            if score == 0:
                score = 20
            
            vehicle["relevance_score"] = score
            scored.append(vehicle)
        
        return scored
    
    def generate_smart_response(self,
                               user_query: str,
                               vehicles: List[Dict],
                               memory_context: str,
                               criteria: Dict[str, Any],
                               has_enough_data: bool) -> str:
        """GENERAR RESPUESTA INTELIGENTE"""
        
        try:
            # SI NO HAY SUFICIENTES DATOS: PREGUNTAR
            if not has_enough_data:
                return self._generate_asking_response(criteria, user_query)
            
            # SI HAY DATOS: RECOMENDAR
            vehicles_text = self._format_vehicles_for_llm(vehicles)
            criteria_text = self._format_criteria(criteria)
            
            prompt = f"""
            Eres un experto en vehículos y asistente AMIGABLE de recomendación de coches.
            
            El usuario busca:
            {criteria_text}
            
            Pregunta actual: {user_query}
            
            Historial:
            {memory_context}
            
            Vehículos encontrados (Top 5):
            {vehicles_text}
            
            Proporciona una respuesta que:
            1. Confirme QUÉ BUSCA (sé específico con tipo, precio, etc)
            2. Presenta los vehículos y POR QUÉ son perfectos
            3. Compara entre ellos
            4. Sea conversacional y amigable
            5. Usa números reales (precios, potencia, etc)
            6. Sugiere cambios si es necesario
            7. Sé breve pero informativo
            
            Respuesta:
            """
            
            response = self.llm.complete(prompt)
            response_text = response.text if hasattr(response, 'text') else str(response)
            
            logger.info(f"✅ Respuesta generada")
            
            return response_text
            
        except Exception as e:
            logger.error(f"❌ Error generando respuesta: {e}")
            return self._fallback_response(vehicles, has_enough_data)
    
    def _generate_asking_response(self, criteria: Dict[str, Any], user_query: str) -> str:
        """GENERAR PREGUNTAS inteligentes"""
        
        response = "Perfecto, déjame ayudarte a encontrar el coche ideal.\n\n"
        
        if criteria["vehicle_type"]:
            response += f"**He entendido que buscas:** Un {criteria['vehicle_type'].upper()}"
            if criteria["topics"]:
                response += f" {', '.join(criteria['topics'])}"
            response += "\n\n"
        elif criteria["topics"]:
            response += f"**He entendido que buscas:** {', '.join(criteria['topics'])}\n\n"
        
        response += "**Necesito que me cuentes más:**\n\n"
        
        questions = []
        
        if not criteria["vehicle_type"]:
            questions.append("🚗 **¿Qué tipo de coche?**\n   (SUV, berlina, compacto, familiar, etc)")
        
        if not criteria["price_range"]:
            questions.append("💰 **¿Tu presupuesto?**\n   (ej: 'menos de 30k', 'entre 20-50k')")
        
        if not criteria["topics"] and criteria["vehicle_type"]:
            questions.append("🎯 **¿Para qué lo quieres?**\n   (ciudad, familia, viajes, deportivo)")
        
        for q in questions[:2]:
            response += f"• {q}\n"
        
        response += "\n💡 Cuéntame más y te daré opciones muy precisas."
        
        return response
    
    def _format_criteria(self, criteria: Dict[str, Any]) -> str:
        """Formatear criterios extraídos"""
        text = ""
        
        if criteria["vehicle_type"]:
            text += f"**Tipo:** {criteria['vehicle_type'].upper()}\n"
        
        if criteria["topics"]:
            text += f"**Características:** {', '.join(criteria['topics']).title()}\n"
        
        if criteria["price_range"]:
            min_p, max_p = criteria["price_range"]
            text += f"**Presupuesto:** hasta €{max_p:,.0f}\n"
        
        if criteria["power_range"]:
            min_pw, max_pw = criteria["power_range"]
            text += f"**Potencia mínima:** {min_pw:.0f} CV\n"
        
        if criteria["autonomy_min"]:
            text += f"**Autonomía mínima:** {criteria['autonomy_min']} km\n"
        
        return text if text else "Criterios: a definir"
    
    def _format_vehicles_for_llm(self, vehicles: List[Dict]) -> str:
        """Formatear vehículos para LLM"""
        if not vehicles:
            return "No se encontraron vehículos."
        
        text = ""
        for i, v in enumerate(vehicles, 1):
            precio = float(v.get('precio') or 0)
            potencia = float(v.get('potencia') or 0)
            autonomia = float(v.get('autonomia') or 0)
            aceleracion = float(v.get('aceleracion') or 0)
            cambio = v.get('cambio', 'N/A')
            
            text += f"""
            {i}. {v.get('name', 'N/A')} - €{precio:,.0f}
               • Potencia: {potencia:.0f} CV
               • Autonomía: {autonomia:.0f} km
               • 0-100: {aceleracion:.1f}s
               • Cambio: {cambio}
            """
        
        return text
    
    def _fallback_response(self, vehicles: List[Dict], has_enough_data: bool) -> str:
        """Respuesta de fallback"""
        
        if not has_enough_data:
            return "Para mejores recomendaciones, cuéntame: tipo de coche, presupuesto, y para qué lo quieres."
        
        if not vehicles:
            return "No encontré vehículos exactos. ¿Podríamos ajustar algo?"
        
        response = f"Encontré {len(vehicles)} vehículo(s):\n\n"
        for i, v in enumerate(vehicles, 1):
            precio = float(v.get('precio') or 0)
            response += f"{i}. **{v.get('name')}** - €{precio:,.0f}\n"
        
        return response
    
    def close(self):
        """Cerrar conexión"""
        if self.neo4j_driver:
            self.neo4j_driver.close()
