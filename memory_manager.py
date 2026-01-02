"""
Gestor de Memoria para Conversación
Mantiene contexto de filtros y mensajes anteriores
Aprende preferencias del usuario
"""

import json
from typing import List, Dict, Any
from datetime import datetime
from collections import deque
import logging

logger = logging.getLogger(__name__)

class MemoryManager:
    """
    Gestor de memoria para mantener contexto de conversación
    Aprende preferencias, detecta temas, mantiene historial
    """
    
    def __init__(self, max_messages: int = 20, max_filters_history: int = 5):
        """
        Inicializar gestor de memoria
        
        Args:
            max_messages: Máximo número de mensajes a mantener
            max_filters_history: Máximo número de cambios de filtros a recordar
        """
        self.max_messages = max_messages
        self.max_filters_history = max_filters_history
        
        # Queue de mensajes (conversación)
        self.messages: deque = deque(maxlen=max_messages)
        
        # Historial de filtros
        self.filters_history: deque = deque(maxlen=max_filters_history)
        
        # Preferencias del usuario (aprendidas)
        self.user_preferences: Dict[str, Any] = {}
        
        # Temas mencionados
        self.mentioned_topics: set = set()
        
        logger.info("✅ Memory Manager inicializado")
    
    def add_message(self, role: str, content: str, metadata: Dict = None):
        """
        Agregar mensaje al historial
        
        Args:
            role: "user" o "assistant"
            content: Contenido del mensaje
            metadata: Metadata adicional
        """
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        self.messages.append(message)
        
        # Extraer temas si es un mensaje del usuario
        if role == "user":
            self._extract_topics(content)
            self._extract_preferences(content)
        
        logger.debug(f"📝 Mensaje agregado: {role} - {content[:50]}...")
    
    def add_filter_update(self, filters: Dict[str, Any]):
        """
        Registrar cambio de filtros
        
        Args:
            filters: Diccionario de filtros aplicados
        """
        filter_record = {
            "timestamp": datetime.now().isoformat(),
            "filters": filters.copy()
        }
        
        self.filters_history.append(filter_record)
        logger.debug(f"🔄 Filtros actualizados")
    
    def _extract_topics(self, text: str):
        """
        Extraer temas mencionados en el texto
        """
        text_lower = text.lower()
        
        topics = {
            "eco": ["eco", "sostenible", "verde", "electrico", "hibrido", "ambiente"],
            "deportivo": ["deportivo", "rapido", "performance", "potencia", "cv", "aceleracion"],
            "familiar": ["familia", "familiar", "espacio", "grande", "asientos", "maletero"],
            "urbano": ["ciudad", "urbano", "compacto", "pequeño", "estacionamiento"],
            "viajes": ["viajes", "carretera", "largo", "autonomia", "gasolina"],
            "offroad": ["offroad", "4x4", "terreno", "campo", "aventura", "montaña"],
            "lujo": ["lujo", "premium", "confort", "cuero", "tecnologia"],
            "economico": ["economico", "barato", "precio", "presupuesto", "ahorrar"]
        }
        
        for topic, keywords in topics.items():
            if any(kw in text_lower for kw in keywords):
                self.mentioned_topics.add(topic)
    
    def _extract_preferences(self, text: str):
        """
        Extraer preferencias del usuario
        """
        text_lower = text.lower()
        
        # Preferencia de motor
        if any(word in text_lower for word in ["electrico", "ev", "electrica"]):
            self.user_preferences["motor_preference"] = "Eléctrico"
        elif any(word in text_lower for word in ["hibrido", "phev"]):
            self.user_preferences["motor_preference"] = "Híbrido"
        elif any(word in text_lower for word in ["gasolina", "nafta"]):
            self.user_preferences["motor_preference"] = "Gasolina"
        elif any(word in text_lower for word in ["diesel"]):
            self.user_preferences["motor_preference"] = "Diésel"
        
        # Preferencia de cambio
        if "manual" in text_lower:
            self.user_preferences["cambio_preference"] = "Manual"
        elif "automatico" in text_lower or "automática" in text_lower:
            self.user_preferences["cambio_preference"] = "Automático"
    
    def get_context(self) -> str:
        """
        Obtener contexto formateado para el LLM
        """
        context = ""
        
        # Últimos mensajes
        if self.messages:
            context += "HISTORIAL DE CONVERSACIÓN:\n"
            for msg in list(self.messages)[-10:]:
                role = "👤 Usuario" if msg["role"] == "user" else "🤖 Asistente"
                context += f"{role}: {msg['content']}\n"
            context += "\n"
        
        # Temas mencionados
        if self.mentioned_topics:
            context += f"TEMAS DE INTERÉS: {', '.join(sorted(self.mentioned_topics))}\n"
        
        # Preferencias aprendidas
        if self.user_preferences:
            context += "PREFERENCIAS DETECTADAS:\n"
            for pref, value in self.user_preferences.items():
                context += f"- {pref}: {value}\n"
            context += "\n"
        
        # Últimos filtros
        if self.filters_history:
            last_filters = self.filters_history[-1]["filters"]
            context += "ÚLTIMOS FILTROS APLICADOS:\n"
            context += f"- Precio: €{last_filters.get('precio_min', 0):,} - €{last_filters.get('precio_max', 0):,}\n"
            context += f"- Potencia: {last_filters.get('potencia_min', 0)} - {last_filters.get('potencia_max', 0)} CV\n"
            context += f"- Autonomía mín: {last_filters.get('autonomia_min', 0)} km\n"
        
        return context if context else "No hay contexto previo."
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Obtener resumen del estado de memoria
        
        Returns:
            Diccionario con estadísticas de conversación
        """
        return {
            "total_messages": len(self.messages),
            "user_messages": sum(1 for m in self.messages if m["role"] == "user"),
            "assistant_messages": sum(1 for m in self.messages if m["role"] == "assistant"),
            "topics": list(sorted(self.mentioned_topics)),
            "preferences": self.user_preferences.copy(),
            "filter_changes": len(self.filters_history)
        }
    
    def clear(self):
        """
        Limpiar memoria completamente
        """
        self.messages.clear()
        self.filters_history.clear()
        self.user_preferences.clear()
        self.mentioned_topics.clear()
        logger.info("🗑️ Memoria limpiada")
    
    def get_conversation_summary(self) -> str:
        """
        Obtener un resumen de la conversación
        """
        summary = "RESUMEN DE CONVERSACIÓN:\n"
        
        for i, msg in enumerate(self.messages, 1):
            timestamp = msg["timestamp"]
            time_str = timestamp.split("T")[1][:5] if "T" in timestamp else timestamp
            role = "👤" if msg["role"] == "user" else "🤖"
            content_preview = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
            
            summary += f"{i}. [{time_str}] {role} {content_preview}\n"
        
        return summary
    
    def export_memory(self) -> Dict[str, Any]:
        """
        Exportar memoria como diccionario
        """
        return {
            "messages": list(self.messages),
            "filters_history": list(self.filters_history),
            "user_preferences": self.user_preferences.copy(),
            "mentioned_topics": list(self.mentioned_topics),
            "exported_at": datetime.now().isoformat()
        }
    
    def import_memory(self, data: Dict[str, Any]):
        """
        Importar memoria desde diccionario
        """
        try:
            for msg in data.get("messages", []):
                self.messages.append(msg)
            
            for filter_record in data.get("filters_history", []):
                self.filters_history.append(filter_record)
            
            self.user_preferences.update(data.get("user_preferences", {}))
            self.mentioned_topics.update(data.get("mentioned_topics", []))
            
            logger.info("✅ Memoria importada correctamente")
        except Exception as e:
            logger.error(f"Error importando memoria: {e}")
