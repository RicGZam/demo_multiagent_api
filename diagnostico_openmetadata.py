#!/usr/bin/env python3
"""
Script de Diagnóstico de OpenMetadata
======================================
Verifica la conexión y configuración con OpenMetadata
"""

from dotenv import load_dotenv
import os
import requests
import json

# Cargar .env
load_dotenv()

def diagnosticar_openmetadata():
    """Diagnostica la conexión con OpenMetadata"""
    
    print("="*70)
    print("🔍 DIAGNÓSTICO DE OPENMETADATA")
    print("="*70)
    print()
    
    # 1. Verificar configuración
    print("1. VERIFICANDO CONFIGURACIÓN")
    print("-" * 70)
    
    url = os.getenv('OPENMETADATA_URL')
    token = os.getenv('OPENMETADATA_TOKEN')
    
    if not url:
        print("❌ OPENMETADATA_URL no configurada")
        return False
    
    if not token:
        print("❌ OPENMETADATA_TOKEN no configurado")
        return False
    
    print(f"✅ URL: {url}")
    print(f"✅ Token: {token[:20]}..." if len(token) > 20 else f"✅ Token: {token}")
    print()
    
    # 2. Verificar conectividad
    print("2. VERIFICANDO CONECTIVIDAD")
    print("-" * 70)
    
    base_url = url.rstrip('/')
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    try:
        # Intentar health check
        health_url = f"{base_url}/api/v1/util/health-check"
        print(f"Probando: {health_url}")
        
        response = requests.get(health_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ OpenMetadata está accesible (200 OK)")
        elif response.status_code == 401:
            print(f"❌ Error de autenticación (401)")
            print(f"💡 El token puede ser inválido o haber expirado")
            return False
        elif response.status_code == 404:
            print(f"⚠️  Endpoint health-check no encontrado (404)")
            print(f"💡 Puede ser una versión diferente de OpenMetadata")
        else:
            print(f"⚠️  Respuesta inesperada: {response.status_code}")
            print(f"Respuesta: {response.text[:200]}")
    
    except requests.exceptions.Timeout:
        print(f"❌ Timeout al conectar")
        print(f"💡 La URL {url} no responde")
        return False
    except requests.exceptions.ConnectionError:
        print(f"❌ Error de conexión")
        print(f"💡 Verifica que {url} sea accesible")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False
    
    print()
    
    # 3. Probar endpoint de búsqueda
    print("3. PROBANDO BÚSQUEDA")
    print("-" * 70)
    
    search_url = f"{base_url}/api/v1/search/query"
    print(f"Endpoint: {search_url}")
    
    params = {
        'q': '*',  # Buscar todo
        'index': 'table_search_index',
        'from': 0,
        'size': 5
    }
    
    try:
        response = requests.get(
            search_url,
            headers=headers,
            params=params,
            timeout=10
        )
        
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Búsqueda funciona")
            print(f"Estructura de respuesta: {list(data.keys())}")
            
            # Intentar extraer hits
            hits = []
            if 'hits' in data and isinstance(data['hits'], dict):
                hits = data['hits'].get('hits', [])
            elif 'data' in data:
                if isinstance(data['data'], list):
                    hits = data['data']
            
            print(f"Resultados encontrados: {len(hits)}")
            
            if len(hits) > 0:
                print(f"✅ Se encontraron {len(hits)} tablas en el catálogo")
                print("\nPrimeras tablas:")
                for i, hit in enumerate(hits[:3], 1):
                    source = hit.get('_source', hit)
                    name = source.get('name', 'N/A')
                    db = source.get('database', {})
                    if isinstance(db, dict):
                        db_name = db.get('name', 'N/A')
                    else:
                        db_name = str(db)
                    print(f"  {i}. {db_name}.{name}")
            else:
                print(f"⚠️  El catálogo parece estar vacío")
                print(f"💡 Necesitas ingestar metadatos en OpenMetadata")
        
        elif response.status_code == 404:
            print(f"❌ Endpoint de búsqueda no encontrado")
            print(f"💡 Puede ser una versión diferente de la API")
            print(f"\nProbando endpoint alternativo...")
            
            # Probar endpoint alternativo
            tables_url = f"{base_url}/api/v1/tables"
            response2 = requests.get(
                tables_url,
                headers=headers,
                params={'limit': 5},
                timeout=10
            )
            
            if response2.status_code == 200:
                data = response2.json()
                tables = data.get('data', [])
                print(f"✅ Endpoint /api/v1/tables funciona")
                print(f"Tablas encontradas: {len(tables)}")
                
                if len(tables) > 0:
                    print("\nPrimeras tablas:")
                    for i, table in enumerate(tables[:3], 1):
                        name = table.get('name', 'N/A')
                        db = table.get('database', {}).get('name', 'N/A')
                        print(f"  {i}. {db}.{name}")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Respuesta: {response.text[:300]}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    print()
    
    # 4. Verificar bases de datos
    print("4. LISTANDO BASES DE DATOS")
    print("-" * 70)
    
    try:
        databases_url = f"{base_url}/api/v1/databases"
        response = requests.get(
            databases_url,
            headers=headers,
            params={'limit': 100},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            databases = data.get('data', [])
            
            print(f"✅ Bases de datos encontradas: {len(databases)}")
            
            if len(databases) > 0:
                print("\nBases de datos disponibles:")
                for i, db in enumerate(databases, 1):
                    name = db.get('name', 'N/A')
                    service = db.get('service', {}).get('name', 'N/A')
                    print(f"  {i}. {name} (servicio: {service})")
            else:
                print("⚠️  No se encontraron bases de datos")
                print("💡 Necesitas conectar servicios de datos en OpenMetadata")
        else:
            print(f"⚠️  No se pudieron listar bases de datos: {response.status_code}")
            
    except Exception as e:
        print(f"⚠️  Error al listar bases de datos: {str(e)}")
    
    print()
    print("="*70)
    print("✅ DIAGNÓSTICO COMPLETADO")
    print("="*70)
    print()
    
    return True


if __name__ == "__main__":
    try:
        diagnosticar_openmetadata()
    except KeyboardInterrupt:
        print("\n\n👋 Diagnóstico interrumpido")
    except Exception as e:
        print(f"\n❌ Error fatal: {str(e)}")
        import traceback
        traceback.print_exc()
