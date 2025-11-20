"""
Ejemplos de Uso Avanzado - Sistema Multi-Agente
================================================
Este archivo contiene ejemplos de cómo usar el sistema en diferentes escenarios
"""

from multi_agent_system import AORQ, AGOB, ATIC, load_config
import json


# ============================================================================
# EJEMPLO 1: Uso Básico
# ============================================================================

def ejemplo_basico():
    """Ejemplo simple de búsqueda de datos"""
    print("\n" + "="*80)
    print("EJEMPLO 1: Búsqueda Básica")
    print("="*80)
    
    config = load_config()
    
    # Inicializar agentes
    agob = AGOB(
        openmetadata_url=config['openmetadata_url'],
        api_token=config['openmetadata_token'],
        openai_api_key=config['openai_api_key']
    )
    
    atic = ATIC(
        jira_url=config['jira_url'],
        jira_email=config['jira_email'],
        jira_api_token=config['jira_api_token'],
        project_key=config['jira_project_key']
    )
    
    aorq = AORQ(agob=agob, atic=atic)
    
    # Realizar solicitud
    resultado = aorq.handle_request(
        "Necesito datos de ventas por región",
        interactive=False
    )
    
    print("\nResultado:", json.dumps(resultado, indent=2, ensure_ascii=False))


# ============================================================================
# EJEMPLO 2: Múltiples Solicitudes
# ============================================================================

def ejemplo_multiples_solicitudes():
    """Procesar múltiples solicitudes en batch"""
    print("\n" + "="*80)
    print("EJEMPLO 2: Múltiples Solicitudes")
    print("="*80)
    
    config = load_config()
    
    agob = AGOB(
        openmetadata_url=config['openmetadata_url'],
        api_token=config['openmetadata_token'],
        openai_api_key=config['openai_api_key']
    )
    
    atic = ATIC(
        jira_url=config['jira_url'],
        jira_email=config['jira_email'],
        jira_api_token=config['jira_api_token'],
        project_key=config['jira_project_key']
    )
    
    aorq = AORQ(agob=agob, atic=atic)
    
    # Lista de solicitudes
    solicitudes = [
        "Ventas mensuales por producto",
        "Inventario actual por almacén",
        "Clientes activos en los últimos 30 días",
        "Top 10 productos más vendidos",
        "Análisis de churn de clientes"
    ]
    
    resultados = []
    for solicitud in solicitudes:
        print(f"\n--- Procesando: {solicitud} ---")
        resultado = aorq.handle_request(solicitud, interactive=False)
        resultados.append({
            'solicitud': solicitud,
            'resultado': resultado
        })
    
    # Resumen
    print("\n" + "="*80)
    print("RESUMEN DE RESULTADOS")
    print("="*80)
    for r in resultados:
        estado = "✅ Éxito" if r['resultado']['success'] else "❌ Fallo"
        print(f"{estado} - {r['solicitud']}")
        if r['resultado'].get('ticket_created'):
            print(f"  → Ticket creado: {r['resultado']['details'].get('ticket_key')}")


# ============================================================================
# EJEMPLO 3: Búsqueda Directa con AGOB
# ============================================================================

def ejemplo_agob_directo():
    """Usar AGOB directamente sin el orquestador"""
    print("\n" + "="*80)
    print("EJEMPLO 3: Uso Directo de AGOB")
    print("="*80)
    
    config = load_config()
    
    agob = AGOB(
        openmetadata_url=config['openmetadata_url'],
        api_token=config['openmetadata_token'],
        openai_api_key=config['openai_api_key']
    )
    
    # Búsqueda directa
    resultado = agob.find_table("usuarios activos")
    
    print(f"\nTabla encontrada: {resultado.found}")
    print(f"Mensaje: {resultado.message}")
    
    if resultado.exact_match:
        print(f"\nTabla exacta: {resultado.exact_match.name}")
        print(f"Base de datos: {resultado.exact_match.database}")
        print(f"Columnas: {len(resultado.exact_match.columns)}")
    
    if resultado.related_tables:
        print(f"\nTablas relacionadas: {len(resultado.related_tables)}")
        for table in resultado.related_tables[:3]:
            print(f"  - {table.name}")
    
    if resultado.generated_query:
        print(f"\nQuery generada:\n{resultado.generated_query}")


# ============================================================================
# EJEMPLO 4: Crear Ticket Directamente
# ============================================================================

def ejemplo_atic_directo():
    """Usar ATIC directamente para crear un ticket"""
    print("\n" + "="*80)
    print("EJEMPLO 4: Creación Directa de Ticket")
    print("="*80)
    
    config = load_config()
    
    atic = ATIC(
        jira_url=config['jira_url'],
        jira_email=config['jira_email'],
        jira_api_token=config['jira_api_token'],
        project_key=config['jira_project_key']
    )
    
    # Crear un ticket manualmente
    from multi_agent_system import TableInfo
    
    # Tablas de ejemplo
    tablas_ejemplo = [
        TableInfo(
            name="ventas",
            database="analytics",
            description="Registro de todas las ventas",
            columns=[
                {'name': 'id', 'type': 'INTEGER', 'description': 'ID de venta'},
                {'name': 'fecha', 'type': 'DATE', 'description': 'Fecha de venta'},
                {'name': 'monto', 'type': 'DECIMAL', 'description': 'Monto total'}
            ],
            fully_qualified_name="analytics.ventas"
        )
    ]
    
    query_ejemplo = """
    SELECT 
        fecha,
        SUM(monto) as total_ventas
    FROM analytics.ventas
    WHERE fecha >= '2024-01-01'
    GROUP BY fecha
    ORDER BY fecha;
    """
    
    try:
        ticket_key = atic.create_ticket(
            user_request="Dashboard de ventas diarias",
            related_tables=tablas_ejemplo,
            proposed_query=query_ejemplo
        )
        
        print(f"\n✅ Ticket creado: {ticket_key}")
        print(f"URL: {config['jira_url']}/browse/{ticket_key}")
        
    except Exception as e:
        print(f"\n❌ Error al crear ticket: {str(e)}")


# ============================================================================
# EJEMPLO 5: Pipeline Completo con Logging
# ============================================================================

def ejemplo_pipeline_con_logging():
    """Pipeline completo con logging detallado"""
    print("\n" + "="*80)
    print("EJEMPLO 5: Pipeline con Logging Detallado")
    print("="*80)
    
    import logging
    
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger('MultiAgentSystem')
    
    config = load_config()
    
    logger.info("Inicializando agentes...")
    
    agob = AGOB(
        openmetadata_url=config['openmetadata_url'],
        api_token=config['openmetadata_token'],
        openai_api_key=config['openai_api_key']
    )
    
    atic = ATIC(
        jira_url=config['jira_url'],
        jira_email=config['jira_email'],
        jira_api_token=config['jira_api_token'],
        project_key=config['jira_project_key']
    )
    
    aorq = AORQ(agob=agob, atic=atic)
    
    logger.info("Agentes inicializados correctamente")
    
    # Procesar solicitud
    solicitud = "Análisis de retención de clientes por cohortes"
    logger.info(f"Procesando solicitud: {solicitud}")
    
    resultado = aorq.handle_request(solicitud, interactive=False)
    
    if resultado['success']:
        logger.info("Solicitud procesada exitosamente")
        if resultado.get('ticket_created'):
            logger.info(f"Ticket creado: {resultado['details']['ticket_key']}")
    else:
        logger.warning("La solicitud no pudo completarse")
    
    return resultado


# ============================================================================
# EJEMPLO 6: Manejo de Errores
# ============================================================================

def ejemplo_manejo_errores():
    """Demostración de manejo robusto de errores"""
    print("\n" + "="*80)
    print("EJEMPLO 6: Manejo de Errores")
    print("="*80)
    
    config = load_config()
    
    # Intentar con credenciales incorrectas (para demostrar manejo de errores)
    print("\n1. Probando con URL incorrecta de OpenMetadata...")
    try:
        agob_incorrecto = AGOB(
            openmetadata_url="https://url-invalida.com",
            api_token="token-invalido",
            openai_api_key=config['openai_api_key']
        )
        resultado = agob_incorrecto.find_table("test")
        print(f"Resultado: {resultado.message}")
    except Exception as e:
        print(f"✅ Error capturado correctamente: {type(e).__name__}")
    
    print("\n2. Probando con credenciales válidas...")
    try:
        agob = AGOB(
            openmetadata_url=config['openmetadata_url'],
            api_token=config['openmetadata_token'],
            openai_api_key=config['openai_api_key']
        )
        
        # Búsqueda que probablemente no encuentre resultados
        resultado = agob.find_table("tabla_inexistente_12345_xyz")
        print(f"Resultado: {resultado.message}")
        print("✅ Error manejado gracefully sin crashear")
        
    except Exception as e:
        print(f"Error: {str(e)}")


# ============================================================================
# EJEMPLO 7: Integración con Workflow Externo
# ============================================================================

def ejemplo_workflow_externo():
    """Simular integración con un workflow externo"""
    print("\n" + "="*80)
    print("EJEMPLO 7: Integración con Workflow Externo")
    print("="*80)
    
    def procesar_solicitud_usuario(user_id: str, request_text: str):
        """
        Función que podría ser llamada desde una API o UI externa
        """
        print(f"\n📥 Nueva solicitud de usuario {user_id}")
        print(f"Solicitud: {request_text}")
        
        config = load_config()
        
        # Inicializar sistema
        agob = AGOB(
            openmetadata_url=config['openmetadata_url'],
            api_token=config['openmetadata_token'],
            openai_api_key=config['openai_api_key']
        )
        
        atic = ATIC(
            jira_url=config['jira_url'],
            jira_email=config['jira_email'],
            jira_api_token=config['jira_api_token'],
            project_key=config['jira_project_key']
        )
        
        aorq = AORQ(agob=agob, atic=atic)
        
        # Procesar
        resultado = aorq.handle_request(request_text, interactive=False)
        
        # Preparar respuesta para el sistema externo
        response = {
            'user_id': user_id,
            'status': 'success' if resultado['success'] else 'failed',
            'details': resultado
        }
        
        return response
    
    # Simular múltiples usuarios
    usuarios = [
        ('user_001', 'Reporte de ventas trimestrales'),
        ('user_002', 'Análisis de satisfacción de clientes'),
        ('user_003', 'Métricas de performance del equipo')
    ]
    
    respuestas = []
    for user_id, request in usuarios:
        respuesta = procesar_solicitud_usuario(user_id, request)
        respuestas.append(respuesta)
        print(f"✅ Solicitud procesada para {user_id}")
    
    print("\n" + "="*80)
    print("RESUMEN DE RESPUESTAS")
    print("="*80)
    print(json.dumps(respuestas, indent=2, ensure_ascii=False))


# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

def main():
    """
    Ejecutar todos los ejemplos
    """
    ejemplos = [
        ("Ejemplo Básico", ejemplo_basico),
        ("Múltiples Solicitudes", ejemplo_multiples_solicitudes),
        ("AGOB Directo", ejemplo_agob_directo),
        ("ATIC Directo", ejemplo_atic_directo),
        ("Pipeline con Logging", ejemplo_pipeline_con_logging),
        ("Manejo de Errores", ejemplo_manejo_errores),
        ("Workflow Externo", ejemplo_workflow_externo)
    ]
    
    print("\n" + "="*80)
    print("EJEMPLOS DE USO AVANZADO - SISTEMA MULTI-AGENTE")
    print("="*80)
    print("\nSelecciona un ejemplo para ejecutar:")
    for i, (nombre, _) in enumerate(ejemplos, 1):
        print(f"{i}. {nombre}")
    print("0. Ejecutar todos los ejemplos")
    print("q. Salir")
    
    while True:
        seleccion = input("\nOpción: ").strip()
        
        if seleccion == 'q':
            print("👋 ¡Hasta luego!")
            break
        
        try:
            if seleccion == '0':
                for nombre, func in ejemplos:
                    print(f"\n\n{'='*80}")
                    print(f"Ejecutando: {nombre}")
                    print('='*80)
                    func()
                    input("\nPresiona Enter para continuar...")
                break
            else:
                idx = int(seleccion) - 1
                if 0 <= idx < len(ejemplos):
                    ejemplos[idx][1]()
                    input("\nPresiona Enter para continuar...")
                else:
                    print("❌ Opción inválida")
        except ValueError:
            print("❌ Por favor ingresa un número válido")
        except KeyboardInterrupt:
            print("\n\n👋 Interrumpido por el usuario")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
