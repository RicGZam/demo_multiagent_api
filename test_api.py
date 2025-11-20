#!/usr/bin/env python3
"""
Script de Prueba - API REST
============================
Prueba todos los endpoints de la API REST

Uso:
    python test_api.py
"""

import requests
import json
from time import sleep

# Configuración
API_BASE_URL = "http://localhost:8000"

def print_section(title):
    """Imprime un separador de sección"""
    print("\n" + "="*80)
    print(f"🧪 {title}")
    print("="*80 + "\n")


def print_response(response):
    """Imprime la respuesta de manera bonita"""
    print(f"Status Code: {response.status_code}")
    try:
        data = response.json()
        print(f"Response:\n{json.dumps(data, indent=2, ensure_ascii=False)}")
    except:
        print(f"Response: {response.text}")
    print()


def test_root():
    """Test: Endpoint raíz"""
    print_section("TEST 1: Endpoint Raíz")
    
    try:
        response = requests.get(f"{API_BASE_URL}/")
        print_response(response)
        
        if response.status_code == 200:
            print("✅ Test 1 PASSED")
        else:
            print("❌ Test 1 FAILED")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")


def test_health():
    """Test: Health check"""
    print_section("TEST 2: Health Check")
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/health")
        print_response(response)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") in ["healthy", "degraded"]:
                print("✅ Test 2 PASSED")
            else:
                print("⚠️  Test 2 WARNING: Estado inesperado")
        else:
            print("❌ Test 2 FAILED")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")


def test_databases():
    """Test: Listar bases de datos"""
    print_section("TEST 3: Listar Bases de Datos")
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/databases")
        print_response(response)
        
        if response.status_code == 200:
            data = response.json()
            print(f"📊 Bases de datos encontradas: {data.get('count', 0)}")
            
            if data.get('databases'):
                print("\nPrimeras 3 bases de datos:")
                for i, db in enumerate(data['databases'][:3], 1):
                    print(f"  {i}. {db['name']} (servicio: {db['service']})")
            
            print("\n✅ Test 3 PASSED")
        else:
            print("❌ Test 3 FAILED")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")


def test_search_simple():
    """Test: Búsqueda simple"""
    print_section("TEST 4: Búsqueda Simple")
    
    payload = {
        "query": "clientes",
        "user_id": "test_user",
        "create_ticket_if_not_found": False
    }
    
    print(f"Payload:\n{json.dumps(payload, indent=2)}\n")
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/search",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        print_response(response)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('found_exact_match'):
                print(f"✅ Tabla exacta encontrada: {data['exact_match']['name']}")
            elif data.get('related_tables'):
                print(f"📊 Tablas relacionadas: {len(data['related_tables'])}")
                for i, table in enumerate(data['related_tables'][:3], 1):
                    print(f"  {i}. {table['database']}.{table['name']}")
            
            if data.get('generated_query'):
                print(f"\n📝 Query SQL generada:")
                print(data['generated_query'][:200] + "..." if len(data['generated_query']) > 200 else data['generated_query'])
            
            print("\n✅ Test 4 PASSED")
        else:
            print("❌ Test 4 FAILED")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")


def test_search_with_database():
    """Test: Búsqueda con base de datos específica"""
    print_section("TEST 5: Búsqueda con Base de Datos")
    
    payload = {
        "query": "de MySQL Test Database dame clientes y pedidos",
        "user_id": "test_user",
        "create_ticket_if_not_found": False
    }
    
    print(f"Payload:\n{json.dumps(payload, indent=2)}\n")
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/search",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        print_response(response)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('related_tables'):
                print(f"📊 Tablas encontradas: {len(data['related_tables'])}")
                print("\nVerificando que sean de la BD correcta:")
                for table in data['related_tables'][:5]:
                    db = table['database'].lower()
                    if 'mysql' in db or 'test' in db:
                        print(f"  ✅ {table['database']}.{table['name']}")
                    else:
                        print(f"  ⚠️  {table['database']}.{table['name']} (no parece de MySQL Test)")
            
            print("\n✅ Test 5 PASSED")
        else:
            print("❌ Test 5 FAILED")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")


def test_ticket_creation():
    """Test: Creación de ticket"""
    print_section("TEST 6: Crear Ticket en Jira")
    
    payload = {
        "user_request": "TEST: Necesito una tabla de análisis de ventas por región",
        "user_id": "test_user",
        "proposed_query": "SELECT region, SUM(sales) FROM sales_data GROUP BY region"
    }
    
    print(f"Payload:\n{json.dumps(payload, indent=2)}\n")
    print("⚠️  NOTA: Este test creará un ticket REAL en Jira")
    
    confirmacion = input("¿Continuar con la creación del ticket? (s/n): ").strip().lower()
    
    if confirmacion not in ['s', 'si', 'sí', 'y', 'yes']:
        print("❌ Test 6 SKIPPED (por elección del usuario)")
        return
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/ticket",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        print_response(response)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Ticket creado: {data.get('ticket_key')}")
            print(f"🔗 URL: {data.get('ticket_url')}")
            print("\n✅ Test 6 PASSED")
        else:
            print("❌ Test 6 FAILED")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")


def test_search_with_auto_ticket():
    """Test: Búsqueda con creación automática de ticket"""
    print_section("TEST 7: Búsqueda con Creación Automática de Ticket")
    
    payload = {
        "query": "TEST: Necesito análisis de productos más vendidos",
        "user_id": "test_user",
        "create_ticket_if_not_found": True
    }
    
    print(f"Payload:\n{json.dumps(payload, indent=2)}\n")
    print("⚠️  NOTA: Este test puede crear un ticket REAL en Jira si no encuentra tabla exacta")
    
    confirmacion = input("¿Continuar? (s/n): ").strip().lower()
    
    if confirmacion not in ['s', 'si', 'sí', 'y', 'yes']:
        print("❌ Test 7 SKIPPED (por elección del usuario)")
        return
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/search",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        print_response(response)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('ticket_created'):
                print(f"✅ Ticket creado automáticamente: {data.get('ticket_key')}")
                print(f"🔗 URL: {data.get('ticket_url')}")
            else:
                print("ℹ️  No se creó ticket (puede que se haya encontrado tabla exacta)")
            
            print("\n✅ Test 7 PASSED")
        else:
            print("❌ Test 7 FAILED")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")


def run_all_tests():
    """Ejecuta todos los tests"""
    print("\n" + "="*80)
    print("🚀 SUITE DE TESTS - API REST SISTEMA MULTI-AGENTE")
    print("="*80)
    print(f"\nURL Base: {API_BASE_URL}")
    print("\n⚠️  Asegúrate de que la API esté corriendo:")
    print("   python api_rest.py")
    print()
    
    input("Presiona Enter para comenzar los tests...")
    
    # Tests básicos (siempre se ejecutan)
    test_root()
    sleep(1)
    
    test_health()
    sleep(1)
    
    test_databases()
    sleep(1)
    
    test_search_simple()
    sleep(1)
    
    test_search_with_database()
    sleep(1)
    
    # Tests que crean tickets (opcionales)
    print("\n" + "="*80)
    print("⚠️  Los siguientes tests pueden crear tickets en Jira")
    print("="*80)
    
    test_ticket_creation()
    sleep(1)
    
    test_search_with_auto_ticket()
    
    # Resumen
    print("\n" + "="*80)
    print("✅ TESTS COMPLETADOS")
    print("="*80)
    print("\n💡 Revisa los resultados arriba")
    print("📚 Documentación de la API: http://localhost:8000/docs")
    print()


if __name__ == "__main__":
    try:
        run_all_tests()
    except KeyboardInterrupt:
        print("\n\n👋 Tests interrumpidos por el usuario")
    except Exception as e:
        print(f"\n❌ Error fatal: {str(e)}")
        import traceback
        traceback.print_exc()
