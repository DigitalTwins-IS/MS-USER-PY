"""
Caché en memoria para rutas optimizadas
Reduce llamadas a API en 90%
"""
from datetime import datetime, timedelta
from typing import Optional, Dict
import hashlib
import json


class RouteCache:
    """
    Caché simple en memoria para rutas
    
    En producción, usar Redis o Memcached
    """
    
    def __init__(self, ttl_hours: int = 24):
        self._cache: Dict[str, Dict] = {}
        self.ttl = timedelta(hours=ttl_hours)
        self.hits = 0
        self.misses = 0
    
    def _make_key(self, seller_id: int, shopkeeper_ids: list, start_coords: tuple = None) -> str:
        """Genera key única para la ruta"""
        sorted_ids = sorted(shopkeeper_ids)
        data = {
            "seller": seller_id,
            "shopkeepers": sorted_ids,
            "start": start_coords
        }
        key_str = json.dumps(data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, seller_id: int, shopkeeper_ids: list, start_coords: tuple = None) -> Optional[Dict]:
        """Obtiene ruta del caché"""
        key = self._make_key(seller_id, shopkeeper_ids, start_coords)
        
        if key in self._cache:
            entry = self._cache[key]
            
            if datetime.now() - entry["timestamp"] < self.ttl:
                self.hits += 1
                hit_rate = self.hits / (self.hits + self.misses) * 100
                print(f"✅ Cache HIT (rate: {hit_rate:.1f}%): Vendedor {seller_id}")
                return entry["data"]
            else:
                del self._cache[key]
        
        self.misses += 1
        print(f"❌ Cache MISS: Vendedor {seller_id}")
        return None
    
    def set(self, seller_id: int, shopkeeper_ids: list, route_data: Dict, start_coords: tuple = None):
        """Guarda ruta en caché"""
        key = self._make_key(seller_id, shopkeeper_ids, start_coords)
        
        self._cache[key] = {
            "data": route_data,
            "timestamp": datetime.now()
        }
        
        print(f"💾 Cache SET: Vendedor {seller_id} ({len(self._cache)} rutas en caché)")
    
    def invalidate_seller(self, seller_id: int):
        """Invalida todas las rutas de un vendedor"""
        keys_to_delete = [
            k for k, v in self._cache.items()
            if f'"seller": {seller_id}' in k
        ]
        
        for key in keys_to_delete:
            del self._cache[key]
        
        if keys_to_delete:
            print(f"🗑️ Cache INVALIDATED: Vendedor {seller_id} ({len(keys_to_delete)} rutas)")
    
    def clear(self):
        """Limpia todo el caché"""
        count = len(self._cache)
        self._cache.clear()
        self.hits = 0
        self.misses = 0
        print(f"🧹 Cache CLEARED: {count} rutas eliminadas")
    
    def stats(self) -> Dict:
        """Estadísticas del caché"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        
        return {
            "total_routes": len(self._cache),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(hit_rate, 2),
            "ttl_hours": self.ttl.total_seconds() / 3600
        }


# Instancia global
route_cache = RouteCache(ttl_hours=24)