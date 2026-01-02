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

from config import NEO4J, OLLAMA, TOPICS, VEHICLE_TYPES, MOTOR_TYPES

logger = logging.getLogger(__name__)


class CarRecommender:
    """Recomendador inteligente que combina criterios de toda la conversación"""

    def __init__(
        self,
        neo4j_uri: str = None,
        neo4j_user: str = None,
        neo4j_password: str = None,
        ollama_base_url: str = None,
        ollama_model: str = None,
    ):
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
                auth=(neo4j_user, neo4j_password),
            )
            with self.neo4j_driver.session() as session:
                session.run("RETURN 1")
            logger.info("✅ Neo4j conectado")

            # LLM
            self.llm = Ollama(
                base_url=ollama_base_url,
                model=ollama_model,
                temperature=OLLAMA["temperature"],
                context_window=OLLAMA["context_window"],
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

        except Exception as e:
            logger.error(f"❌ Error inicializando: {e}")
            raise

    # =====================================================================
    # CARGA Y LIMPIEZA DE VEHÍCULOS
    # =====================================================================

    def _load_vehicles_db(self) -> List[Dict[str, Any]]:
        """Cargar todos los vehículos desde Neo4j"""
        try:
            query = """
            MATCH (m:MODELO)
            OPTIONAL MATCH (m)-[:TIPO_TRACCION]->(t:TRACCION)
            RETURN {
                id: m.id,
                name: m.name,
                precio: m.precio,
                potencia: m.potencia,
                aceleracion: m.aceleracion,
                autonomia: m.autonomia,
                cambio: m.cambio,
                traccion: t.tipo,
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
                v_id = v.get("id")
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
            "precio": 0,
            "potencia": 0,
            "aceleracion": 0,
            "autonomia": 0,
            "cambio": "N/A",
            "traccion": "N/A",
            "score_eco": 0,
            "score_urbano": 0,
            "score_familiar": 0,
            "score_deportivo": 0,
            "score_viajes": 0,
            "score_offroad": 0,
        }

        for key, default_val in defaults.items():
            val = vehicle.get(key)
            if val is None:
                vehicle[key] = default_val
            else:
                if key in ("cambio", "traccion", "name", "id"):
                    vehicle[key] = str(val)
                else:
                    try:
                        vehicle[key] = float(val)
                    except (TypeError, ValueError):
                        vehicle[key] = default_val
        return vehicle

    # =====================================================================
    # EXTRACCIÓN DE CRITERIOS
    # =====================================================================

    def extract_criteria_from_query(
        self,
        user_query: str,
        memory_context: str,
    ) -> Dict[str, Any]:
        """
        EXTRAER CRITERIOS de la query ACTUAL y COMBINAR con memoria.

        Detecta tipos, temas, marcas, motor, cambio, tracción, precio, potencia, autonomía.
        """
        query_lower = user_query.lower()
        memory_lower = memory_context.lower() if memory_context else ""

        criteria: Dict[str, Any] = {
            "topics": [],
            "vehicle_types": [],
            "brands": [],
            "motors": [],
            "gearbox": None,
            "traction": None,
            "price_range": None,
            "power_range": None,
            "autonomy_min": None,
            "has_enough_data": False,
        }

        # Marcas
        brand_keywords = {
            "bmw": "bmw",
            "audi": "audi",
            "mercedes-benz": "mercedes",
            "mercedes": "mercedes",
            "volkswagen": "volkswagen",
            "vw": "volkswagen",
            "seat": "seat",
            "cupra": "cupra",
            "skoda": "skoda",
            "peugeot": "peugeot",
            "renault": "renault",
            "citroen": "citroën",
            "citroën": "citroën",
        }
        for kw, canonical in brand_keywords.items():
            if kw in query_lower and canonical not in criteria["brands"]:
                criteria["brands"].append(canonical)

        # Tipos de vehículo (usa VEHICLE_TYPES de config)
        for canonical_type, aliases in VEHICLE_TYPES.items():
            for alias in aliases:
                if alias.lower() in query_lower:
                    if canonical_type not in criteria["vehicle_types"]:
                        criteria["vehicle_types"].append(canonical_type)
                    break
        if not criteria["vehicle_types"]:
            for canonical_type, aliases in VEHICLE_TYPES.items():
                for alias in aliases:
                    if alias.lower() in memory_lower:
                        if canonical_type not in criteria["vehicle_types"]:
                            criteria["vehicle_types"].append(canonical_type)
                        break

        # Temas / uso
        for topic, keywords in TOPICS.items():
            if any(kw in query_lower for kw in keywords):
                if topic not in criteria["topics"]:
                    criteria["topics"].append(topic)
        for topic, keywords in TOPICS.items():
            if any(kw in memory_lower for kw in keywords):
                if topic not in criteria["topics"]:
                    criteria["topics"].append(topic)

        # Motor (usa MOTOR_TYPES de config)
        for canonical_motor, aliases in MOTOR_TYPES.items():
            for alias in aliases:
                if alias.lower() in query_lower:
                    if canonical_motor not in criteria["motors"]:
                        criteria["motors"].append(canonical_motor)
                    break
        if not criteria["motors"]:
            for canonical_motor, aliases in MOTOR_TYPES.items():
                for alias in aliases:
                    if alias.lower() in memory_lower:
                        if canonical_motor not in criteria["motors"]:
                            criteria["motors"].append(canonical_motor)
                        break

        # Cambio
        if "manual" in query_lower:
            criteria["gearbox"] = "Manual"
        elif (
            "automatico" in query_lower
            or "automático" in query_lower
            or "auto" in query_lower
        ):
            criteria["gearbox"] = "Automático"
        else:
            if "manual" in memory_lower:
                criteria["gearbox"] = "Manual"
            elif "automatico" in memory_lower or "automático" in memory_lower:
                criteria["gearbox"] = "Automático"

        # Tracción
        traction_map = {
            "delantera": "FWD",
            "tracción delantera": "FWD",
            "traccion delantera": "FWD",
            "trasera": "RWD",
            "propulsion": "RWD",
            "propulsión": "RWD",
            "tracción trasera": "RWD",
            "traccion trasera": "RWD",
            "4x4": "AWD",
            "awd": "AWD",
            "tracción total": "AWD",
            "traccion total": "AWD",
        }
        for kw, tt in traction_map.items():
            if kw in query_lower:
                criteria["traction"] = tt
                break
        if criteria["traction"] is None:
            for kw, tt in traction_map.items():
                if kw in memory_lower:
                    criteria["traction"] = tt
                    break

        # Precio
        price_patterns = [
            r"(\d+)\s*k",
            r"€\s*(\d+)",
            r"(\d+)\s*€",
            r"menos de\s*(\d+)",
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

        # Potencia
        power_patterns = [
            r"(\d+)\s*cv",
            r"(\d+)\s*hp",
            r"(\d+)\s*caballos",
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

        # Autonomía
        autonomy_patterns = [
            r"(\d+)\s*km",
            r"autonomía\s*(\d+)",
            r"autonomia\s*(\d+)",
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

        # ¿Suficientes datos?
        has_type = len(criteria["vehicle_types"]) > 0
        has_topic = len(criteria["topics"]) > 0
        has_price = criteria["price_range"] is not None
        has_power = criteria["power_range"] is not None
        has_motor = len(criteria["motors"]) > 0

        if has_type:
            criteria["has_enough_data"] = any(
                [has_topic, has_price, has_motor, has_power]
            )
        else:
            data_count = sum([has_topic, has_price, has_power, has_motor])
            criteria["has_enough_data"] = data_count >= 2

        logger.info(
            "📊 Criterios finales: "
            f"tipos={criteria['vehicle_types']}, "
            f"marcas={criteria['brands']}, "
            f"motores={criteria['motors']}, "
            f"topics={criteria['topics']}, "
            f"precio={criteria['price_range']}, "
            f"potencia={criteria['power_range']}, "
            f"autonomía={criteria['autonomy_min']}, "
            f"cambio={criteria['gearbox']}, "
            f"tracción={criteria['traction']}, "
            f"datos={criteria['has_enough_data']}"
        )

        return criteria

    # =====================================================================
    # BÚSQUEDA DE VEHÍCULOS
    # =====================================================================

    def search_vehicles_by_criteria(
        self,
        criteria: Dict[str, Any],
        user_query: str,
    ) -> Tuple[List[Dict], bool]:
        """
        BUSCAR vehículos usando criterios combinados
        """
        if not self.vehicles_db:
            return [], criteria["has_enough_data"]

        filtered = self.vehicles_db.copy()

        # Tipo de vehículo
        if criteria.get("vehicle_types"):
            tipos_lower = [t.lower() for t in criteria["vehicle_types"]]

            type_keywords = {
                "suv": ["suv", "audi q", "bmw x", "mercedes gle", "range rover", "jeep"],
                "compacto": ["compact", "polo", "fiesta", "ibiza", "i30"],
                "berlina": ["berlina", "sedan", "a4", "c-class", "3 series", "accord", "camry"],
                "familiar": ["familiar", "estate", "touring", "avant", "break"],
                "monovolumen": ["monovolumen", "mpv", "grand", "scenic"],
                "deportivo": ["coupé", "coupe", "gt", " m", " rs", " amg"],
            }

            def matches_any_type(v_name: str) -> bool:
                name = v_name.lower()
                for t in tipos_lower:
                    for key, kws in type_keywords.items():
                        if key in t:
                            if any(kw in name for kw in kws):
                                return True
                    if t in name:
                        return True
                return False

            filtered = [v for v in filtered if matches_any_type(v.get("name", ""))]
            logger.info(
                f"🔍 Después filtro tipos {criteria['vehicle_types']}: {len(filtered)} vehículos"
            )

        # Marca
        if criteria.get("brands"):
            brands = [b.lower() for b in criteria["brands"]]
            filtered = [
                v for v in filtered
                if any(b in v.get("name", "").lower() for b in brands)
            ]
            logger.info(
                f"🔍 Después filtro marcas {criteria['brands']}: {len(filtered)} vehículos"
            )

        # Motor (cuando tengas el campo 'motor' en MODELO, activar aquí)
        # if criteria.get("motors"):
        #     motors = [m.lower() for m in criteria["motors"]]
        #     filtered = [
        #         v for v in filtered
        #         if any(m in str(v.get("motor", "")).lower() for m in motors)
        #     ]
        #     logger.info(f"🔍 Después filtro motores {criteria['motors']}: {len(filtered)} vehículos")

        # Cambio
        if criteria.get("gearbox"):
            gb = criteria["gearbox"].lower()
            filtered = [
                v for v in filtered
                if gb in str(v.get("cambio", "")).lower()
            ]
            logger.info(
                f"🔍 Después filtro cambio {criteria['gearbox']}: {len(filtered)} vehículos"
            )

        # Tracción
        if criteria.get("traction"):
            tr = criteria["traction"]  # FWD/RWD/AWD
            filtered = [
                v for v in filtered
                if tr == str(v.get("traccion", "")).upper()
            ]
            logger.info(
                f"🔍 Después filtro tracción {tr}: {len(filtered)} vehículos"
            )

        # Precio
        if criteria.get("price_range"):
            min_price, max_price = criteria["price_range"]
            filtered = [
                v for v in filtered
                if min_price <= v.get("precio", 0) <= max_price
            ]
            logger.info(f"🔍 Después filtro precio: {len(filtered)} vehículos")

        # Potencia
        if criteria.get("power_range"):
            min_power, max_power = criteria["power_range"]
            filtered = [
                v for v in filtered
                if min_power <= v.get("potencia", 0) <= max_power
            ]
            logger.info(f"🔍 Después filtro potencia: {len(filtered)} vehículos")

        # Autonomía
        if criteria.get("autonomy_min"):
            filtered = [
                v for v in filtered
                if v.get("autonomia", 0) >= criteria["autonomy_min"]
            ]
            logger.info(f"🔍 Después filtro autonomía: {len(filtered)} vehículos")

        # Scoring
        scored = self._score_vehicles(filtered, criteria["topics"])
        ranked = sorted(
            scored,
            key=lambda x: x.get("relevance_score", 0),
            reverse=True,
        )

        logger.info("✅ Top 5 encontrados")
        return ranked[:5], criteria["has_enough_data"]

    def _score_vehicles(self, vehicles: List[Dict], topics: List[str]) -> List[Dict]:
        """Puntuación por temas (uso/estilo)"""
        scored: List[Dict[str, Any]] = []

        for vehicle in vehicles:
            score = 0.0
            for topic in topics:
                score_key = f"score_{topic}"
                vehicle_score = vehicle.get(score_key, 0)
                if vehicle_score is None:
                    vehicle_score = 0
                try:
                    vehicle_score = float(vehicle_score)
                except Exception:
                    vehicle_score = 0
                score += vehicle_score * 100

            if score == 0:
                score = 20

            vehicle["relevance_score"] = score
            scored.append(vehicle)

        return scored

    # =====================================================================
    # RESPUESTA INTELIGENTE
    # =====================================================================

    def generate_smart_response(
        self,
        user_query: str,
        vehicles: List[Dict],
        memory_context: str,
        criteria: Dict[str, Any],
        has_enough_data: bool,
    ) -> str:
        """GENERAR RESPUESTA INTELIGENTE"""
        try:
            if not has_enough_data:
                return self._generate_asking_response(criteria, user_query)

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

Instrucciones IMPORTANTES:
- NO inventes restricciones nuevas (precio máximo, que sea económico, potencia mínima, etc.) que NO aparezcan en el texto del usuario ni en criterios anteriores.
- Si el usuario no ha dado presupuesto, NO supongas uno.
- Si el usuario no ha dicho que sea "económico" o "barato", NO lo etiquetes así.
- Usa solo datos reales de los vehículos (precio, potencia, autonomía, etc.) que te doy arriba.

Proporciona una respuesta que:
1. Confirme QUÉ BUSCA (sé específico con tipo, marca, temas de uso).
2. Presente los vehículos y POR QUÉ encajan.
3. Compare entre ellos.
4. Sea conversacional y amigable.
5. Use números reales (precios, potencia, etc.).
6. Sugiera ajustes SOLO como sugerencias, no como hechos del usuario.
7. Sé breve pero informativo.

Respuesta:
"""
            response = self.llm.complete(prompt)
            response_text = response.text if hasattr(response, "text") else str(response)
            logger.info("✅ Respuesta generada")
            return response_text

        except Exception as e:
            logger.error(f"❌ Error generando respuesta: {e}")
            return self._fallback_response(vehicles, has_enough_data)

    def _generate_asking_response(
        self,
        criteria: Dict[str, Any],
        user_query: str,
    ) -> str:
        """GENERAR PREGUNTAS inteligentes y concretas según lo que falte"""
        response = "Perfecto, déjame ayudarte a encontrar el coche ideal.\n\n"

        if criteria.get("vehicle_types"):
            tipos_str = ", ".join(criteria["vehicle_types"])
            response += f"**He entendido que buscas:** {tipos_str.upper()}"
            if criteria.get("brands"):
                response += f" ({', '.join(criteria['brands']).upper()})"
            if criteria["topics"]:
                response += f" | Uso: {', '.join(criteria['topics'])}"
            response += "\n\n"
        elif criteria["topics"]:
            response += (
                f"**He entendido que buscas:** {', '.join(criteria['topics'])}\n\n"
            )

        response += "**Necesito que me aclares algunos detalles:**\n\n"
        questions: list[str] = []

        if not criteria.get("vehicle_types"):
            questions.append(
                "🚗 **¿Qué tipo de coche prefieres?**\n   (SUV, berlina, compacto, familiar, monovolumen, deportivo...)"
            )

        if not criteria["topics"]:
            questions.append(
                "🎯 **¿Para qué lo vas a usar principalmente?**\n   (ciudad, familia, viajes largos, deportivo, offroad, lujo, económico...)"
            )

        if not criteria.get("price_range"):
            questions.append(
                "💰 **¿Cuál es tu presupuesto aproximado?**\n   (por ejemplo: 'menos de 25k', 'hasta 40k', 'entre 20k y 35k')"
            )

        if not criteria.get("motors"):
            questions.append(
                "⚙️ **¿Alguna preferencia de motor?**\n   (Gasolina, Diésel, Híbrido, Híbrido Enchufable, Eléctrico)"
            )

        if not criteria.get("gearbox"):
            if "urbano" in criteria["topics"] or "eco" in criteria["topics"]:
                questions.append(
                    "🔄 **¿Prefieres cambio manual o automático?**\n   (para ciudad y atascos suele ser más cómodo automático)"
                )
            else:
                questions.append(
                    "🔄 **¿Cambio manual o automático?**\n   (si te da igual, dímelo también)"
                )

        if not criteria.get("traction") and (
            "deportivo" in criteria["topics"] or "offroad" in criteria["topics"]
        ):
            questions.append(
                "🛞 **¿Alguna preferencia de tracción?**\n   (delantera, trasera o total/4x4)"
            )

        for q in questions[:3]:
            response += f"• {q}\n"

        response += "\n💡 Cuanto más concreto seas con estos puntos, más preciso será el resultado."
        return response

    # =====================================================================
    # FORMATOS AUXILIARES
    # =====================================================================

    def _format_criteria(self, criteria: Dict[str, Any]) -> str:
        """Formatear criterios extraídos"""
        text = ""

        if criteria.get("vehicle_types"):
            text += f"**Tipo:** {', '.join(criteria['vehicle_types']).upper()}\n"

        if criteria.get("brands"):
            text += f"**Marca:** {', '.join(criteria['brands']).upper()}\n"

        if criteria["topics"]:
            text += (
                f"**Características / uso:** "
                f"{', '.join(criteria['topics']).title()}\n"
            )

        if criteria.get("motors"):
            text += f"**Motor:** {', '.join(criteria['motors'])}\n"

        if criteria.get("gearbox"):
            text += f"**Cambio:** {criteria['gearbox']}\n"

        if criteria.get("traction"):
            text += f"**Tracción:** {criteria['traction']}\n"

        if criteria.get("price_range"):
            _, max_p = criteria["price_range"]
            text += f"**Presupuesto:** hasta €{max_p:,.0f}\n"

        if criteria.get("power_range"):
            min_pw, _ = criteria["power_range"]
            text += f"**Potencia mínima:** {min_pw:.0f} CV\n"

        if criteria.get("autonomy_min"):
            text += f"**Autonomía mínima:** {criteria['autonomy_min']} km\n"

        return text if text else "Criterios: a definir"

    def _format_vehicles_for_llm(self, vehicles: List[Dict]) -> str:
        """Formatear vehículos para LLM"""
        if not vehicles:
            return "No se encontraron vehículos."

        text = ""
        for i, v in enumerate(vehicles, 1):
            precio = float(v.get("precio") or 0)
            potencia = float(v.get("potencia") or 0)
            autonomia = float(v.get("autonomia") or 0)
            aceleracion = float(v.get("aceleracion") or 0)
            cambio = v.get("cambio", "N/A")
            traccion = v.get("traccion", "N/A")

            text += f"""
{i}. {v.get('name', 'N/A')} - €{precio:,.0f}
• Potencia: {potencia:.0f} CV
• Autonomía: {autonomia:.0f} km
• 0-100: {aceleracion:.1f}s
• Cambio: {cambio}
• Tracción: {traccion}
"""
        return text

    def _fallback_response(self, vehicles: List[Dict], has_enough_data: bool) -> str:
        """Respuesta de fallback"""
        if not has_enough_data:
            return (
                "Para mejores recomendaciones, cuéntame: "
                "tipo de coche, presupuesto, y para qué lo quieres."
            )

        if not vehicles:
            return "No encontré vehículos exactos. ¿Podríamos ajustar algo?"

        response = f"Encontré {len(vehicles)} vehículo(s):\n\n"
        for i, v in enumerate(vehicles, 1):
            precio = float(v.get("precio") or 0)
            response += f"{i}. **{v.get('name')}** - €{precio:,.0f}\n"
        return response

    def close(self):
        """Cerrar conexión"""
        if self.neo4j_driver:
            self.neo4j_driver.close()

