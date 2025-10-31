#!/usr/bin/env python3
"""
Script de prueba para diagnosticar el problema del inventario
"""
import requests
import json

# URL base del microservicio
BASE_URL = "http://localhost:8000"

def test_debug_endpoint():
    """Probar el endpoint de debug"""
    url = f"{BASE_URL}/api/v1/users/inventory/debug"
    
    data = {
        "shopkeeper_id": 1,
        "product_id": 1,
        "unit_price": 1000.0,
        "current_stock": 50.0,
        "min_stock": 10.0,
        "max_stock": 100.0
    }
    
    print("🔍 Probando endpoint de debug...")
    print(f"URL: {url}")
    print(f"Datos: {json.dumps(data, indent=2)}")
    
    try:
        response = requests.post(url, json=data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_health_endpoint():
    """Probar el endpoint de health"""
    url = f"{BASE_URL}/api/v1/users/inventory/health"
    
    print("\n🏥 Probando endpoint de health...")
    print(f"URL: {url}")
    
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_available_products():
    """Probar el endpoint de productos disponibles"""
    url = f"{BASE_URL}/api/v1/users/inventory/products/available"
    
    print("\n📦 Probando endpoint de productos disponibles...")
    print(f"URL: {url}")
    
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_original_endpoint():
    """Probar el endpoint original con autenticación"""
    url = f"{BASE_URL}/api/v1/users/inventory"
    
    data = {
        "shopkeeper_id": 1,
        "product_id": 1,
        "unit_price": 1000.0,
        "current_stock": 50.0,
        "min_stock": 10.0,
        "max_stock": 100.0
    }
    
    headers = {
        "Authorization": "Bearer test-token",
        "Content-Type": "application/json"
    }
    
    print("\n🔐 Probando endpoint original con autenticación...")
    print(f"URL: {url}")
    print(f"Datos: {json.dumps(data, indent=2)}")
    
    try:
        response = requests.post(url, json=data, headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code in [200, 201, 401]  # 401 es esperado sin token válido
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Iniciando diagnóstico del microservicio de inventario...")
    
    # Probar endpoints en orden
    health_ok = test_health_endpoint()
    debug_ok = test_debug_endpoint()
    products_ok = test_available_products()
    original_ok = test_original_endpoint()
    
    print("\n📊 Resumen de pruebas:")
    print(f"Health Check: {'✅' if health_ok else '❌'}")
    print(f"Debug Endpoint: {'✅' if debug_ok else '❌'}")
    print(f"Available Products: {'✅' if products_ok else '❌'}")
    print(f"Original Endpoint: {'✅' if original_ok else '❌'}")
    
    if not health_ok:
        print("\n❌ El microservicio no está respondiendo correctamente")
    elif not debug_ok:
        print("\n❌ Hay un problema con la validación de datos")
    else:
        print("\n✅ El microservicio está funcionando correctamente")
