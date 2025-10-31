#!/usr/bin/env python3
"""
Script de prueba para verificar que los endpoints de inventarios funcionan correctamente
"""
import requests
import json
from typing import Dict, Any

# Configuración
BASE_URL = "http://localhost:8000/api/v1"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": "Bearer YOUR_TOKEN_HERE"  # Reemplazar con token válido
}

def test_endpoint(method: str, endpoint: str, data: Dict[Any, Any] = None) -> Dict[Any, Any]:
    """Función auxiliar para probar endpoints"""
    url = f"{BASE_URL}{endpoint}"
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=HEADERS)
        elif method.upper() == "POST":
            response = requests.post(url, headers=HEADERS, json=data)
        elif method.upper() == "PUT":
            response = requests.put(url, headers=HEADERS, json=data)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=HEADERS)
        else:
            return {"error": f"Método {method} no soportado"}
        
        return {
            "status_code": response.status_code,
            "data": response.json() if response.content else None,
            "error": None
        }
    except requests.exceptions.RequestException as e:
        return {
            "status_code": None,
            "data": None,
            "error": str(e)
        }

def main():
    """Función principal para probar todos los endpoints"""
    print("🧪 Probando endpoints de inventarios...")
    print("=" * 50)
    
    # Lista de endpoints a probar
    endpoints_to_test = [
        {
            "name": "Diagnóstico de base de datos",
            "method": "GET",
            "endpoint": "/inventories/diagnostic",
            "data": None
        },
        {
            "name": "Endpoint de prueba simple",
            "method": "GET",
            "endpoint": "/inventories/test",
            "data": None
        },
        {
            "name": "Inventarios simplificados",
            "method": "GET",
            "endpoint": "/inventories/simple",
            "data": None
        },
        {
            "name": "Listar todos los inventarios",
            "method": "GET",
            "endpoint": "/inventories",
            "data": None
        },
        {
            "name": "Inventarios pendientes de validación",
            "method": "GET", 
            "endpoint": "/inventories/pending-validation",
            "data": None
        },
        {
            "name": "Inventarios con stock bajo",
            "method": "GET",
            "endpoint": "/inventories/low-stock", 
            "data": None
        },
        {
            "name": "Inventarios sin stock",
            "method": "GET",
            "endpoint": "/inventories/out-of-stock",
            "data": None
        },
        {
            "name": "Inventarios de un tendero específico",
            "method": "GET",
            "endpoint": "/shopkeepers/1/inventories",
            "data": None
        }
    ]
    
    results = []
    
    for test in endpoints_to_test:
        print(f"\n📋 {test['name']}")
        print(f"   {test['method']} {test['endpoint']}")
        
        result = test_endpoint(test['method'], test['endpoint'], test['data'])
        
        if result['error']:
            print(f"   ❌ Error: {result['error']}")
        elif result['status_code'] == 200:
            data = result['data']
            if isinstance(data, list):
                print(f"   ✅ Éxito: {len(data)} elementos encontrados")
                if data and len(data) > 0:
                    print(f"   📊 Primer elemento: {data[0].get('product_name', 'N/A')}")
            else:
                print(f"   ✅ Éxito: {data}")
        elif result['status_code'] == 401:
            print(f"   🔐 Error de autenticación: Token requerido")
        elif result['status_code'] == 404:
            print(f"   ❌ No encontrado: {result['data']}")
        else:
            print(f"   ❌ Error {result['status_code']}: {result['data']}")
        
        results.append({
            "test": test['name'],
            "result": result
        })
    
    print("\n" + "=" * 50)
    print("📊 Resumen de pruebas:")
    
    success_count = 0
    auth_errors = 0
    other_errors = 0
    
    for result in results:
        if result['result']['status_code'] == 200:
            success_count += 1
        elif result['result']['status_code'] == 401:
            auth_errors += 1
        else:
            other_errors += 1
    
    print(f"   ✅ Exitosos: {success_count}")
    print(f"   🔐 Errores de autenticación: {auth_errors}")
    print(f"   ❌ Otros errores: {other_errors}")
    
    if auth_errors > 0:
        print(f"\n💡 Nota: Para probar completamente, necesitas un token de autenticación válido.")
        print(f"   Puedes obtenerlo haciendo login en: {BASE_URL}/login")

if __name__ == "__main__":
    main()
