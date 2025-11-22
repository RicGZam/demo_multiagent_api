"""
API REST para Sistema Multi-Agente
===================================
API que expone el sistema multi-agente para ser consumida por Power Apps
y otras aplicaciones externas.

Endpoints:
- POST /api/search - Buscar datos
- POST /api/ticket - Crear ticket en Jira
- GET /api/health - Health check
- GET /api/databases - Listar bases de datos disponibles

Autor: Sistema Multi-Agente
Fecha: 2025-11-18
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
import uvicorn
from datetime import datetime
import logging

from multi_agent_system import AORQ, AGOB, ATIC, load_config

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Crear aplicación FastAPI
app = FastAPI(
    title="API Sistema Multi-Agente",
    description="API REST para búsqueda de datos y creación de tickets",
    version="1.0.0",
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc"  # ReDoc
)

# Configurar CORS para permitir llamadas desde Power Apps
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especifica los orígenes permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Variables globales para agentes
agob_instance = None
atic_instance = None
aorq_instance = None


# ============================================================================
# MODELOS DE DATOS (Request/Response)
# ============================================================================

class SearchRequest(BaseModel):
    """Request para búsqueda de datos"""
    query: str = Field(..., description="Consulta en lenguaje natural", example="dame clientes de MySQL Test Database")
    user_id: Optional[str] = Field(None, description="ID del usuario que hace la solicitud")
    create_ticket_if_not_found: bool = Field(False, description="Crear ticket si no se encuentra la tabla")


class TableInfo(BaseModel):
    """Información de una tabla"""
    name: str
    database: str
    description: str
    fully_qualified_name: str
    columns: List[Dict] = []


class SearchResponse(BaseModel):
    """Response de búsqueda"""
    success: bool
    message: str
    found_exact_match: bool
    exact_match: Optional[TableInfo] = None
    related_tables: Optional[List[TableInfo]] = []
    generated_query: Optional[str] = None
    ticket_created: bool = False
    ticket_key: Optional[str] = None
    ticket_url: Optional[str] = None
    timestamp: str


class TicketRequest(BaseModel):
    """Request para crear ticket"""
    user_request: str = Field(..., description="Descripción de lo que necesita el usuario")
    related_tables: Optional[List[str]] = Field(None, description="Nombres de tablas relacionadas")
    proposed_query: Optional[str] = Field(None, description="Query SQL propuesta")
    user_id: Optional[str] = Field(None, description="ID del usuario solicitante")


class TicketResponse(BaseModel):
    """Response de creación de ticket"""
    success: bool
    message: str
    ticket_key: str
    ticket_url: str
    timestamp: str


class HealthResponse(BaseModel):
    """Response de health check"""
    status: str
    timestamp: str
    services: Dict[str, bool]


class DatabaseInfo(BaseModel):
    """Información de una base de datos"""
    name: str
    service: str
    tables_count: Optional[int] = None


class DatabasesResponse(BaseModel):
    """Response de listado de bases de datos"""
    success: bool
    databases: List[DatabaseInfo]
    count: int
    timestamp: str


# ============================================================================
# INICIALIZACIÓN
# ============================================================================

def get_agents():
    """Obtiene o inicializa los agentes del sistema"""
    global agob_instance, atic_instance, aorq_instance
    
    if agob_instance is None:
        logger.info("Inicializando agentes del sistema...")
        
        try:
            config = load_config()
            
            # Inicializar AGOB
            agob_instance = AGOB(
                openmetadata_url=config['openmetadata_url'],
                api_token=config['openmetadata_token'],
                openai_api_key=config['openai_api_key']
            )
            
            # Inicializar ATIC
            atic_instance = ATIC(
                jira_url=config['jira_url'],
                jira_email=config['jira_email'],
                jira_api_token=config['jira_api_token'],
                project_key=config['jira_project_key']
            )
            
            # Inicializar AORQ
            aorq_instance = AORQ(agob=agob_instance, atic=atic_instance)
            
            logger.info("Agentes inicializados correctamente")
            
        except Exception as e:
            logger.error(f"Error al inicializar agentes: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error al inicializar sistema: {str(e)}")
    
    return aorq_instance, agob_instance, atic_instance


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/", tags=["General"])
async def root():
    """Endpoint raíz - Información de la API"""
    return {
        "message": "API Sistema Multi-Agente",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health"
    }


@app.get("/api/health", response_model=HealthResponse, tags=["General"])
async def health_check():
    """
    Health check - Verifica que todos los servicios estén funcionando
    """
    try:
        aorq, agob, atic = get_agents()
        
        services = {
            "api": True,
            "openmetadata": False,
            "jira": False,
            "llm": False
        }
        
        # Verificar OpenMetadata
        try:
            # Intento simple de búsqueda
            import requests
            response = requests.get(
                f"{agob.base_url}/api/v1/health-check",
                headers=agob.headers,
                timeout=5
            )
            services["openmetadata"] = response.status_code == 200
        except:
            services["openmetadata"] = False
        
        # Verificar Jira
        try:
            atic.jira_client.myself()
            services["jira"] = True
        except:
            services["jira"] = False
        
        # Verificar LLM (simplificado)
        services["llm"] = agob.llm is not None
        
        status = "healthy" if all(services.values()) else "degraded"
        
        return HealthResponse(
            status=status,
            timestamp=datetime.now().isoformat(),
            services=services
        )
        
    except Exception as e:
        logger.error(f"Error en health check: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Service unavailable: {str(e)}")


@app.post("/api/search", response_model=SearchResponse, tags=["Data Search"])
async def search_data(request: SearchRequest):
    """
    Buscar datos en el catálogo de OpenMetadata
    
    Este endpoint busca tablas que coincidan con la consulta del usuario.
    Si no encuentra una coincidencia exacta, devuelve tablas relacionadas
    y una query SQL generada.
    
    Opcionalmente, puede crear un ticket en Jira si no se encuentra la tabla exacta.
    """
    try:
        logger.info(f"Búsqueda recibida: '{request.query}' de usuario: {request.user_id}")
        
        aorq, agob, atic = get_agents()
        
        # Realizar búsqueda con AGOB
        search_result = agob.find_table(request.query)
        
        # Preparar respuesta
        response_data = {
            "success": True,
            "message": search_result.message,
            "found_exact_match": search_result.found,
            "timestamp": datetime.now().isoformat(),
            "ticket_created": False
        }
        
        # Si se encontró tabla exacta
        if search_result.exact_match:
            response_data["exact_match"] = TableInfo(
                name=search_result.exact_match.name,
                database=search_result.exact_match.database,
                description=search_result.exact_match.description,
                fully_qualified_name=search_result.exact_match.fully_qualified_name,
                columns=search_result.exact_match.columns
            )
        
        # Si hay tablas relacionadas
        if search_result.related_tables:
            response_data["related_tables"] = [
                TableInfo(
                    name=t.name,
                    database=t.database,
                    description=t.description,
                    fully_qualified_name=t.fully_qualified_name,
                    columns=t.columns
                )
                for t in search_result.related_tables[:10]  # Limitar a 10
            ]
        
        # Si hay query generada
        if search_result.generated_query:
            response_data["generated_query"] = search_result.generated_query
        
        # Si se solicita crear ticket y no se encontró exacta
        if request.create_ticket_if_not_found and not search_result.found:
            logger.info("Creando ticket automáticamente...")
            
            try:
                ticket_key = atic.create_ticket(
                    user_request=request.query,
                    related_tables=search_result.related_tables or [],
                    proposed_query=search_result.generated_query or ""
                )
                
                response_data["ticket_created"] = True
                response_data["ticket_key"] = ticket_key
                response_data["ticket_url"] = f"{atic.jira_client.server_url}/browse/{ticket_key}"
                
                logger.info(f"Ticket creado: {ticket_key}")
                
            except Exception as e:
                logger.error(f"Error al crear ticket: {str(e)}")
                response_data["message"] += f" (Error al crear ticket: {str(e)})"
        
        return SearchResponse(**response_data)
        
    except Exception as e:
        logger.error(f"Error en búsqueda: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error en búsqueda: {str(e)}")


@app.post("/api/ticket", response_model=TicketResponse, tags=["Jira"])
async def create_ticket(request: TicketRequest):
    """
    Crear un ticket en Jira
    
    Crea un ticket con la solicitud del usuario, tablas relacionadas
    y query SQL propuesta (si aplica).
    """
    try:
        logger.info(f"Solicitud de ticket: '{request.user_request}' de usuario: {request.user_id}")
        
        aorq, agob, atic = get_agents()
        
        # Convertir nombres de tablas a objetos TableInfo si es necesario
        related_tables = []
        if request.related_tables:
            # Aquí podrías buscar las tablas por nombre si es necesario
            # Por ahora, crear objetos simples
            from multi_agent_system import TableInfo as TI
            related_tables = [
                TI(name=name, database="", description="", columns=[], fully_qualified_name=name)
                for name in request.related_tables
            ]
        
        # Crear ticket
        ticket_key = atic.create_ticket(
            user_request=request.user_request,
            related_tables=related_tables,
            proposed_query=request.proposed_query or ""
        )
        
        ticket_url = f"{atic.jira_client.server_url}/browse/{ticket_key}"
        
        logger.info(f"Ticket creado exitosamente: {ticket_key}")
        
        return TicketResponse(
            success=True,
            message=f"Ticket creado exitosamente",
            ticket_key=ticket_key,
            ticket_url=ticket_url,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error al crear ticket: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al crear ticket: {str(e)}")


@app.get("/api/databases", response_model=DatabasesResponse, tags=["Metadata"])
async def list_databases():
    """
    Listar bases de datos disponibles en OpenMetadata
    
    Devuelve la lista de bases de datos que están disponibles
    en el catálogo de OpenMetadata.
    """
    try:
        logger.info("Listando bases de datos disponibles")
        
        aorq, agob, atic = get_agents()
        
        import requests
        
        # Obtener bases de datos de OpenMetadata
        databases_url = f"{agob.base_url}/api/v1/databases"
        response = requests.get(
            databases_url,
            headers=agob.headers,
            params={'limit': 100},
            timeout=10
        )
        
        response.raise_for_status()
        data = response.json()
        
        databases = data.get('data', [])
        
        db_list = []
        for db in databases:
            db_info = DatabaseInfo(
                name=db.get('name', 'N/A'),
                service=db.get('service', {}).get('name', 'N/A'),
                tables_count=None  # Podría obtenerse con una llamada adicional
            )
            db_list.append(db_info)
        
        logger.info(f"Encontradas {len(db_list)} bases de datos")
        
        return DatabasesResponse(
            success=True,
            databases=db_list,
            count=len(db_list),
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error al listar bases de datos: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al listar bases de datos: {str(e)}")


# ============================================================================
# STARTUP/SHUTDOWN
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Evento al iniciar la aplicación"""
    logger.info("="*80)
    logger.info("🚀 Iniciando API Sistema Multi-Agente")
    logger.info("="*80)
    
    try:
        # Inicializar agentes
        get_agents()
        logger.info("✅ Agentes inicializados correctamente")
        logger.info("📚 Documentación disponible en: /docs")
        logger.info("🔍 Health check disponible en: /api/health")
        
    except Exception as e:
        logger.error(f"❌ Error al iniciar: {str(e)}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Evento al cerrar la aplicación"""
    logger.info("👋 Cerrando API Sistema Multi-Agente")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    """
    Ejecutar API en modo desarrollo
    
    Para producción, usar:
    uvicorn api_rest:app --host 0.0.0.0 --port 8000 --workers 4
    """
    
    print("\n" + "="*80)
    print("🚀 INICIANDO API REST - SISTEMA MULTI-AGENTE")
    print("="*80)
    print("\n📚 Documentación:")
    print("   - Swagger UI: http://localhost:8000/docs")
    print("   - ReDoc: http://localhost:8000/redoc")
    print("\n🔗 Endpoints principales:")
    print("   - POST /api/search - Buscar datos")
    print("   - POST /api/ticket - Crear ticket")
    print("   - GET /api/databases - Listar bases de datos")
    print("   - GET /api/health - Health check")
    print("\n⚡ Presiona Ctrl+C para detener")
    print("="*80 + "\n")
    
    uvicorn.run(
        "api_rest:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload en desarrollo
        log_level="info"
    )
