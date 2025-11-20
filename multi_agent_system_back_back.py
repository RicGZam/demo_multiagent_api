"""
Sistema Multi-Agente para Gestión de Datos
==========================================
Tres agentes cooperativos:
- AORQ: Agente Orquestador
- AGOB: Agente de OpenMetadata
- ATIC: Agente de Tickets (Jira)

Autor: Sistema de IA
Fecha: 2025-11-18
"""

import os
import json
import requests
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from jira import JIRA
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import HumanMessage, SystemMessage
from dotenv import load_dotenv


# ============================================================================
# CONFIGURACIÓN Y MODELOS DE DATOS
# ============================================================================

@dataclass
class TableInfo:
    """Información de una tabla encontrada en OpenMetadata"""
    name: str
    database: str
    description: str
    columns: List[Dict[str, str]]
    fully_qualified_name: str
    

@dataclass
class SearchResult:
    """Resultado de búsqueda en OpenMetadata"""
    found: bool
    exact_match: Optional[TableInfo] = None
    related_tables: Optional[List[TableInfo]] = None
    generated_query: Optional[str] = None
    message: str = ""


# ============================================================================
# AGENTE AGOB - OpenMetadata
# ============================================================================

class AGOB:
    """
    Agente de OpenMetadata (AGOB)
    Responsable de buscar tablas y generar queries SQL cuando sea necesario
    """
    
    def __init__(self, openmetadata_url: str, api_token: str, openai_api_key: str):
        """
        Inicializa el agente AGOB
        
        Args:
            openmetadata_url: URL base de OpenMetadata (ej: https://openmetadata.example.com)
            api_token: Token JWT para autenticación en OpenMetadata
            openai_api_key: API key de OpenAI para el LLM
        """
        self.base_url = openmetadata_url.rstrip('/')
        self.api_token = api_token
        self.headers = {
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json'
        }
        
        # Inicializar el LLM con LangChain
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",  # GPT-4o-mini es el sucesor de GPT-3.5
            temperature=0,
            openai_api_key=openai_api_key
        )
        
    def find_table(self, user_request: str) -> SearchResult:
        """
        Busca una tabla basándose en la solicitud del usuario
        
        Args:
            user_request: Descripción en lenguaje natural de lo que el usuario necesita
            
        Returns:
            SearchResult con la información encontrada
        """
        try:
            print(f"\n[AGOB] 🔍 Buscando datos para: '{user_request}'")
            
            # 1. Extraer información clave del request
            search_keywords, database_filter = self._extract_search_keywords(user_request)
            
            print(f"[AGOB] 🔑 Palabras clave: {', '.join(search_keywords)}")
            if database_filter:
                print(f"[AGOB] 🗄️  Filtrar por base de datos: {database_filter}")
            
            # 2. Buscar tablas en OpenMetadata
            search_results = self._search_openmetadata_smart(search_keywords, database_filter)
            
            if not search_results:
                return SearchResult(
                    found=False,
                    message="No se encontraron tablas relacionadas en el catálogo de datos."
                )
            
            # 3. Procesar resultados
            tables = self._parse_search_results(search_results)
            
            # 4. Verificar si hay coincidencia exacta
            exact_match = self._find_exact_match(user_request, tables)
            
            if exact_match:
                print(f"[AGOB] ✅ Tabla exacta encontrada: {exact_match.name}")
                return SearchResult(
                    found=True,
                    exact_match=exact_match,
                    message=f"Se encontró la tabla exacta: {exact_match.name}"
                )
            
            # 5. Si no hay coincidencia exacta, generar SQL query
            print(f"[AGOB] 🔧 No hay coincidencia exacta. Generando query SQL...")
            generated_query = self._generate_sql_query(user_request, tables)
            
            return SearchResult(
                found=False,
                related_tables=tables,
                generated_query=generated_query,
                message="No existe la tabla exacta, pero se puede crear con las tablas relacionadas."
            )
            
        except Exception as e:
            print(f"[AGOB] ❌ Error: {str(e)}")
            return SearchResult(
                found=False,
                message=f"Error al buscar en OpenMetadata: {str(e)}"
            )
    
    def _extract_search_keywords(self, user_request: str) -> Tuple[List[str], Optional[str]]:
        """
        Extrae palabras clave relevantes y nombre de base de datos del request
        
        Args:
            user_request: Solicitud del usuario
            
        Returns:
            Tupla (keywords, database_name)
        """
        import re
        
        # Detectar nombre de base de datos
        database_patterns = [
            r'base de datos\s+([A-Za-z0-9_\s]+?)(?:\s+y\s+|\s+,|\s+con|\s*$)',
            r'database\s+([A-Za-z0-9_\s]+?)(?:\s+y\s+|\s+,|\s+con|\s*$)',
            r'de\s+([A-Za-z0-9_\s]+?)\s+y\s+crea',
            r'en\s+([A-Za-z0-9_\s]+?)(?:\s+quiero|\s+necesito)'
        ]
        
        database_filter = None
        for pattern in database_patterns:
            match = re.search(pattern, user_request, re.IGNORECASE)
            if match:
                database_filter = match.group(1).strip()
                break
        
        # Palabras clave de negocio (sustantivos relevantes)
        business_keywords = [
            'cliente', 'customer', 'customers',
            'pedido', 'order', 'orders',
            'producto', 'product', 'products',
            'venta', 'sale', 'sales',
            'factura', 'invoice', 'invoices',
            'pago', 'payment', 'payments',
            'usuario', 'user', 'users',
            'empleado', 'employee', 'employees',
            'categoria', 'category', 'categories',
            'proveedor', 'supplier', 'suppliers',
            'inventario', 'inventory',
            'almacen', 'warehouse',
            'ciudad', 'city', 'cities',
            'region', 'region', 'regions',
            'pais', 'country', 'countries'
        ]
        
        # Extraer keywords que aparecen en el request
        keywords = []
        request_lower = user_request.lower()
        
        for keyword in business_keywords:
            if keyword in request_lower:
                keywords.append(keyword)
        
        # Si no se encontraron keywords específicas, usar palabras principales
        if not keywords:
            # Remover palabras comunes
            stop_words = {'de', 'la', 'el', 'en', 'y', 'con', 'por', 'para', 'una', 'un', 
                         'que', 'los', 'las', 'del', 'al', 'se', 'su', 'ha', 'he',
                         'quiero', 'necesito', 'crear', 'tabla', 'datos', 'base',
                         'aparezca', 'hecho', 'total', 'media', 'nombre'}
            
            words = re.findall(r'\b[a-záéíóúñ]{4,}\b', request_lower)
            keywords = [w for w in words if w not in stop_words][:5]
        
        # Si aún no hay keywords, usar un wildcard limitado
        if not keywords:
            keywords = ['*']
        
        return keywords, database_filter
    
    def _search_openmetadata_smart(self, keywords: List[str], database_filter: Optional[str] = None) -> List[Dict]:
        """
        Búsqueda inteligente en OpenMetadata con keywords y filtro de base de datos
        
        Args:
            keywords: Lista de palabras clave para buscar
            database_filter: Nombre de la base de datos para filtrar (opcional)
            
        Returns:
            Lista de resultados de búsqueda
        """
        try:
            # Endpoint de búsqueda de OpenMetadata v1
            search_url = f"{self.base_url}/api/v1/search/query"
            
            # Construir query de búsqueda
            if len(keywords) == 1 and keywords[0] == '*':
                search_query = '*'
            else:
                search_query = ' '.join(keywords)
            
            print(f"[AGOB] 🔗 Conectando a: {search_url}")
            print(f"[AGOB] 🔎 Query de búsqueda: '{search_query}'")
            
            # Parámetros de búsqueda
            params = {
                'q': search_query,
                'index': 'table_search_index',
                'from': 0,
                'size': 20  # Traer más resultados para filtrar
            }
            
            print(f"[AGOB] 📡 Enviando request a OpenMetadata...")
            
            response = requests.get(
                search_url,
                headers=self.headers,
                params=params,
                timeout=30
            )
            
            print(f"[AGOB] 📥 Status code: {response.status_code}")
            
            if response.status_code == 401:
                print(f"[AGOB] ❌ Error de autenticación (401)")
                print(f"[AGOB] 💡 Verifica que tu OPENMETADATA_TOKEN sea válido")
                return []
            
            if response.status_code == 404:
                print(f"[AGOB] ❌ Endpoint no encontrado (404)")
                print(f"[AGOB] 💡 Verifica la URL de OpenMetadata: {self.base_url}")
                return []
            
            response.raise_for_status()
            data = response.json()
            
            # Extraer hits
            hits = []
            if 'hits' in data and isinstance(data['hits'], dict):
                hits = data['hits'].get('hits', [])
            elif 'data' in data:
                if isinstance(data['data'], list):
                    hits = data['data']
            
            print(f"[AGOB] 📊 Encontradas {len(hits)} tablas en búsqueda inicial")
            
            # Si no hay resultados, intentar búsqueda alternativa
            if len(hits) == 0:
                print(f"[AGOB] 🔄 Intentando búsqueda alternativa...")
                hits = self._search_openmetadata_alternative(database_filter)
            
            # Filtrar por base de datos si se especificó
            if database_filter and hits:
                filtered_hits = self._filter_by_database(hits, database_filter)
                if filtered_hits:
                    print(f"[AGOB] ✅ Filtradas {len(filtered_hits)} tablas de '{database_filter}'")
                    return filtered_hits
                else:
                    print(f"[AGOB] ⚠️  No se encontraron tablas en '{database_filter}'")
                    print(f"[AGOB] 💡 Mostrando resultados de todas las bases de datos")
            
            return hits
            
        except Exception as e:
            print(f"[AGOB] ❌ Error inesperado: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    def _filter_by_database(self, hits: List[Dict], database_name: str) -> List[Dict]:
        """
        Filtra resultados por nombre de base de datos
        
        Args:
            hits: Lista de resultados
            database_name: Nombre de la base de datos (puede ser parcial)
            
        Returns:
            Lista filtrada
        """
        filtered = []
        database_lower = database_name.lower()
        
        for hit in hits:
            source = hit.get('_source', hit)
            
            # Extraer nombre de base de datos
            db = source.get('database', {})
            if isinstance(db, dict):
                db_name = db.get('name', '').lower()
                db_fqn = db.get('fullyQualifiedName', '').lower()
            else:
                db_name = str(db).lower()
                db_fqn = ''
            
            # Extraer del fullyQualifiedName de la tabla
            table_fqn = source.get('fullyQualifiedName', '').lower()
            
            # Comprobar coincidencia
            if (database_lower in db_name or 
                database_lower in db_fqn or 
                database_lower in table_fqn or
                # Coincidencia parcial (ej: "MySQL Test" en "MySQL Test Database")
                any(word in db_name for word in database_lower.split()) or
                any(word in table_fqn for word in database_lower.split())):
                filtered.append(hit)
        
        return filtered
        """
        Realiza búsqueda en OpenMetadata usando la API REST
        
        Args:
            query: Texto de búsqueda
            
        Returns:
            Lista de resultados de búsqueda
        """
        try:
            # Endpoint de búsqueda de OpenMetadata v1
            search_url = f"{self.base_url}/api/v1/search/query"
            
            print(f"[AGOB] 🔗 Conectando a: {search_url}")
            print(f"[AGOB] 🔎 Query de búsqueda: '{query}'")
            
            # Parámetros de búsqueda simplificados
            params = {
                'q': query,
                'index': 'table_search_index',
                'from': 0,
                'size': 10
            }
            
            print(f"[AGOB] 📡 Enviando request a OpenMetadata...")
            
            response = requests.get(
                search_url,
                headers=self.headers,
                params=params,
                timeout=30
            )
            
            print(f"[AGOB] 📥 Status code: {response.status_code}")
            
            if response.status_code == 401:
                print(f"[AGOB] ❌ Error de autenticación (401)")
                print(f"[AGOB] 💡 Verifica que tu OPENMETADATA_TOKEN sea válido")
                return []
            
            if response.status_code == 404:
                print(f"[AGOB] ❌ Endpoint no encontrado (404)")
                print(f"[AGOB] 💡 Verifica la URL de OpenMetadata: {self.base_url}")
                return []
            
            response.raise_for_status()
            data = response.json()
            
            # Debug: mostrar estructura de respuesta
            print(f"[AGOB] 📋 Claves en respuesta: {list(data.keys())}")
            
            # Intentar extraer hits de diferentes estructuras posibles
            hits = []
            
            # Estructura típica de Elasticsearch
            if 'hits' in data and isinstance(data['hits'], dict):
                hits = data['hits'].get('hits', [])
            # Estructura alternativa
            elif 'data' in data:
                if isinstance(data['data'], list):
                    hits = data['data']
                elif isinstance(data['data'], dict) and 'hits' in data['data']:
                    hits = data['data']['hits']
            # Si data es directamente una lista
            elif isinstance(data, list):
                hits = data
            
            print(f"[AGOB] 📊 Encontradas {len(hits)} tablas relacionadas")
            
            if len(hits) == 0:
                print(f"[AGOB] ⚠️  No se encontraron resultados")
                print(f"[AGOB] 💡 Posibles causas:")
                print(f"[AGOB]    - No hay tablas que coincidan con '{query}'")
                print(f"[AGOB]    - El catálogo de OpenMetadata está vacío")
                print(f"[AGOB]    - El índice de búsqueda necesita ser reconstruido")
                # Intentar listar todas las tablas
                print(f"[AGOB] 🔄 Intentando búsqueda alternativa...")
                return self._search_openmetadata_alternative()
            
            return hits
            
        except requests.exceptions.Timeout:
            print(f"[AGOB] ⏱️  Timeout al conectar con OpenMetadata")
            print(f"[AGOB] 💡 La URL {self.base_url} no responde")
            return []
        except requests.exceptions.ConnectionError:
            print(f"[AGOB] 🔌 Error de conexión con OpenMetadata")
            print(f"[AGOB] 💡 Verifica que {self.base_url} esté accesible")
            return []
        except requests.exceptions.RequestException as e:
            print(f"[AGOB] ⚠️ Error en la búsqueda: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    print(f"[AGOB] 📄 Detalle del error: {error_detail}")
                except:
                    print(f"[AGOB] 📄 Respuesta: {e.response.text[:200]}")
            return []
        except Exception as e:
            print(f"[AGOB] ❌ Error inesperado: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    def _search_openmetadata_alternative(self, database_filter: Optional[str] = None) -> List[Dict]:
        """
        Búsqueda alternativa: listar tablas disponibles
        
        Args:
            database_filter: Filtrar por base de datos (opcional)
        """
        try:
            # Intentar endpoint de tablas
            tables_url = f"{self.base_url}/api/v1/tables"
            
            print(f"[AGOB] 🔄 Listando tablas desde: {tables_url}")
            
            params = {'limit': 50}  # Traer más tablas
            
            # Si hay filtro de base de datos, intentar usarlo
            if database_filter:
                params['database'] = database_filter
                print(f"[AGOB] 🗄️  Filtrando por base de datos: {database_filter}")
            
            response = requests.get(
                tables_url,
                headers=self.headers,
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # La respuesta puede tener diferentes estructuras
                tables = []
                if 'data' in data:
                    tables = data['data']
                elif isinstance(data, list):
                    tables = data
                
                print(f"[AGOB] ✅ Encontradas {len(tables)} tablas en el catálogo")
                
                # Convertir a formato de hits
                hits = []
                for table in tables:
                    hits.append({
                        '_source': table
                    })
                
                return hits
            else:
                print(f"[AGOB] ⚠️  No se pudo listar tablas (status: {response.status_code})")
                return []
                
        except Exception as e:
            print(f"[AGOB] ⚠️  Búsqueda alternativa falló: {str(e)}")
            return []
    
    def _parse_search_results(self, hits: List[Dict]) -> List[TableInfo]:
        """
        Convierte los resultados de búsqueda en objetos TableInfo
        
        Args:
            hits: Resultados de la búsqueda de OpenMetadata
            
        Returns:
            Lista de objetos TableInfo
        """
        tables = []
        
        for hit in hits:
            source = hit.get('_source', {})
            
            # Extraer información de columnas
            columns = []
            for col in source.get('columns', []):
                columns.append({
                    'name': col.get('name', ''),
                    'type': col.get('dataType', ''),
                    'description': col.get('description', '')
                })
            
            table = TableInfo(
                name=source.get('name', ''),
                database=source.get('database', {}).get('name', ''),
                description=source.get('description', 'Sin descripción'),
                columns=columns,
                fully_qualified_name=source.get('fullyQualifiedName', '')
            )
            
            tables.append(table)
        
        return tables
    
    def _find_exact_match(self, user_request: str, tables: List[TableInfo]) -> Optional[TableInfo]:
        """
        Busca una coincidencia exacta usando el LLM
        
        Args:
            user_request: Solicitud del usuario
            tables: Lista de tablas encontradas
            
        Returns:
            TableInfo si hay coincidencia exacta, None en caso contrario
        """
        if not tables:
            return None
        
        # Preparar información de tablas para el LLM
        tables_info = "\n".join([
            f"- {t.name} ({t.database}): {t.description}"
            for t in tables
        ])
        
        # Prompt para determinar si hay coincidencia exacta
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""Eres un experto en análisis de datos. 
            Determina si alguna de las tablas proporcionadas coincide EXACTAMENTE con lo que el usuario solicita.
            Responde SOLO con el nombre de la tabla si hay coincidencia exacta, o 'NONE' si no hay ninguna coincidencia exacta."""),
            HumanMessage(content=f"""Solicitud del usuario: {user_request}

Tablas disponibles:
{tables_info}

¿Hay alguna tabla que coincida EXACTAMENTE con la solicitud? Responde solo con el nombre de la tabla o 'NONE'.""")
        ])
        
        response = self.llm.invoke(prompt.format_messages())
        result = response.content.strip()
        
        if result.upper() == 'NONE':
            return None
        
        # Buscar la tabla por nombre
        for table in tables:
            if table.name.lower() in result.lower():
                return table
        
        return None
    
    def _generate_sql_query(self, user_request: str, tables: List[TableInfo]) -> str:
        """
        Genera una query SQL usando el LLM basándose en las tablas relacionadas
        
        Args:
            user_request: Solicitud del usuario
            tables: Tablas relacionadas encontradas
            
        Returns:
            Query SQL generada
        """
        # Preparar información detallada de las tablas
        tables_schema = ""
        for table in tables[:5]:  # Limitar a 5 tablas más relevantes
            tables_schema += f"\nTabla: {table.database}.{table.name}\n"
            tables_schema += f"Descripción: {table.description}\n"
            tables_schema += "Columnas:\n"
            for col in table.columns[:10]:  # Limitar columnas
                tables_schema += f"  - {col['name']} ({col['type']}): {col.get('description', 'N/A')}\n"
            tables_schema += "\n"
        
        # Prompt para generar SQL
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""Eres un experto en SQL y análisis de datos.
            Genera una query SQL óptima y eficiente que cumpla con la solicitud del usuario,
            utilizando las tablas y columnas proporcionadas.
            
            Reglas:
            1. Usa JOIN apropiados si es necesario
            2. Incluye comentarios en el SQL explicando la lógica
            3. Usa nombres de columnas claros en el SELECT
            4. Optimiza para rendimiento
            5. La query debe ser ejecutable
            
            Responde SOLO con el código SQL, sin explicaciones adicionales."""),
            HumanMessage(content=f"""Solicitud del usuario: {user_request}

Esquema de tablas disponibles:
{tables_schema}

Genera la query SQL:""")
        ])
        
        response = self.llm.invoke(prompt.format_messages())
        sql_query = response.content.strip()
        
        # Limpiar markdown si está presente
        if sql_query.startswith("```sql"):
            sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
        
        print(f"[AGOB] 📝 Query SQL generada exitosamente")
        return sql_query


# ============================================================================
# AGENTE ATIC - Jira Tickets
# ============================================================================

class ATIC:
    """
    Agente de Tickets Jira (ATIC)
    Responsable de crear issues en Jira cuando se necesita un nuevo producto de datos
    """
    
    def __init__(self, jira_url: str, jira_email: str, jira_api_token: str, project_key: str):
        """
        Inicializa el agente ATIC
        
        Args:
            jira_url: URL de Jira (ej: https://company.atlassian.net)
            jira_email: Email del usuario de Jira
            jira_api_token: Token API de Jira
            project_key: Clave del proyecto (ej: 'DATA', 'ENG')
        """
        self.project_key = project_key
        
        try:
            # Inicializar cliente de Jira
            self.jira_client = JIRA(
                server=jira_url,
                basic_auth=(jira_email, jira_api_token)
            )
            print(f"[ATIC] ✅ Conectado a Jira: {jira_url}")
        except Exception as e:
            print(f"[ATIC] ❌ Error al conectar con Jira: {str(e)}")
            raise
    
    def create_ticket(
        self,
        user_request: str,
        related_tables: List[TableInfo],
        proposed_query: str
    ) -> str:
        """
        Crea un ticket en Jira para solicitar un nuevo producto de datos
        
        Args:
            user_request: Solicitud original del usuario
            related_tables: Tablas relacionadas encontradas
            proposed_query: Query SQL propuesta
            
        Returns:
            Issue key del ticket creado (ej: 'DATA-123')
        """
        try:
            print(f"\n[ATIC] 🎫 Creando ticket en Jira...")
            
            # Preparar descripción detallada
            description = self._build_description(user_request, related_tables, proposed_query)
            
            # Configurar campos del issue
            issue_dict = {
                'project': {'key': self.project_key},
                'summary': f'Nuevo Producto de Datos: {user_request[:80]}',
                'description': description,
                'issuetype': {'name': 'Task'},  # o 'Story', 'Bug', según configuración
                'labels': ['data-product', 'auto-generated'],
                'priority': {'name': 'Medium'}
            }
            
            # Crear el issue
            new_issue = self.jira_client.create_issue(fields=issue_dict)
            
            issue_key = new_issue.key
            issue_url = f"{self.jira_client.server_url}/browse/{issue_key}"
            
            print(f"[ATIC] ✅ Ticket creado: {issue_key}")
            print(f"[ATIC] 🔗 URL: {issue_url}")
            
            return issue_key
            
        except Exception as e:
            print(f"[ATIC] ❌ Error al crear ticket: {str(e)}")
            raise
    
    def _build_description(
        self,
        user_request: str,
        related_tables: List[TableInfo],
        proposed_query: str
    ) -> str:
        """
        Construye la descripción detallada del ticket
        
        Args:
            user_request: Solicitud del usuario
            related_tables: Tablas relacionadas
            proposed_query: Query propuesta
            
        Returns:
            Descripción formateada para Jira
        """
        # Usar formato Jira Markdown
        description = f"""h2. Solicitud del Usuario

{user_request}

h2. Tablas Relacionadas Encontradas

"""
        
        for table in related_tables[:5]:
            description += f"""h3. {table.name}
* *Base de datos:* {table.database}
* *Descripción:* {table.description}
* *Columnas principales:* {', '.join([col['name'] for col in table.columns[:5]])}

"""
        
        description += f"""h2. Query SQL Propuesta

{{code:sql}}
{proposed_query}
{{code}}

h2. Próximos Pasos

# Revisar la query propuesta
# Validar con el equipo de datos
# Crear la tabla/vista en el catálogo
# Notificar al usuario solicitante

---
_Ticket generado automáticamente por el Sistema Multi-Agente_
"""
        
        return description


# ============================================================================
# AGENTE AORQ - Orquestador
# ============================================================================

class AORQ:
    """
    Agente Orquestador (AORQ)
    Coordina la interacción con el usuario y los otros agentes
    """
    
    def __init__(self, agob: AGOB, atic: ATIC):
        """
        Inicializa el orquestador
        
        Args:
            agob: Instancia del agente AGOB
            atic: Instancia del agente ATIC
        """
        self.agob = agob
        self.atic = atic
    
    def handle_request(self, user_input: str, interactive: bool = True) -> Dict:
        """
        Maneja la solicitud completa del usuario
        
        Args:
            user_input: Solicitud del usuario en lenguaje natural
            interactive: Si es True, pide confirmación al usuario (input())
            
        Returns:
            Diccionario con el resultado del procesamiento
        """
        print("\n" + "="*80)
        print("🤖 SISTEMA MULTI-AGENTE - GESTIÓN DE DATOS")
        print("="*80)
        
        result = {
            'success': False,
            'user_request': user_input,
            'table_found': False,
            'ticket_created': False,
            'details': {}
        }
        
        try:
            # PASO 1: Búsqueda con AGOB
            print(f"\n[AORQ] 👤 Solicitud recibida: '{user_input}'")
            search_result = self.agob.find_table(user_input)
            
            # PASO 2: Procesar resultado de búsqueda
            if search_result.found and search_result.exact_match:
                # Tabla exacta encontrada
                table = search_result.exact_match
                result['table_found'] = True
                result['details'] = {
                    'table_name': table.name,
                    'database': table.database,
                    'description': table.description,
                    'fqn': table.fully_qualified_name
                }
                
                self._show_found_table(table)
                
                # Validar con el usuario
                if interactive:
                    confirmation = input("\n¿Esta tabla satisface tu necesidad? (sí/no): ").strip().lower()
                else:
                    confirmation = "sí"
                
                if confirmation in ['sí', 'si', 's', 'yes', 'y']:
                    print("\n[AORQ] ✅ ¡Perfecto! Puedes usar esta tabla para tu análisis.")
                    result['success'] = True
                else:
                    print("\n[AORQ] 😕 Entiendo. Por favor, proporciona más detalles sobre lo que necesitas.")
                    result['success'] = False
                
            else:
                # No hay tabla exacta - mostrar alternativas y query
                self._show_alternatives(search_result)
                
                result['details'] = {
                    'related_tables': [t.name for t in (search_result.related_tables or [])],
                    'generated_query': search_result.generated_query
                }
                
                # Validar con el usuario
                if interactive:
                    confirmation = input("\n¿Te parece correcta esta solución? (sí/no): ").strip().lower()
                else:
                    confirmation = "sí"
                
                if confirmation in ['sí', 'si', 's', 'yes', 'y']:
                    # PASO 3: Crear ticket con ATIC
                    print("\n[AORQ] 📋 Procediendo a crear el ticket...")
                    
                    ticket_key = self.atic.create_ticket(
                        user_request=user_input,
                        related_tables=search_result.related_tables or [],
                        proposed_query=search_result.generated_query or ""
                    )
                    
                    result['success'] = True
                    result['ticket_created'] = True
                    result['details']['ticket_key'] = ticket_key
                    
                    print(f"\n[AORQ] ✅ ¡Listo! Se ha creado el ticket {ticket_key}")
                    print(f"[AORQ] 📧 Recibirás notificaciones sobre el progreso en Jira.")
                else:
                    print("\n[AORQ] 😕 Entiendo que la solución no es exactamente lo que buscas.")
                    print("[AORQ] 💡 Por favor, proporciona más detalles o reformula tu solicitud.")
                    result['success'] = False
            
            return result
            
        except Exception as e:
            print(f"\n[AORQ] ❌ Error inesperado: {str(e)}")
            result['error'] = str(e)
            return result
    
    def _show_found_table(self, table: TableInfo):
        """Muestra información de una tabla encontrada"""
        print("\n" + "─"*80)
        print("📊 TABLA ENCONTRADA")
        print("─"*80)
        print(f"Nombre:      {table.name}")
        print(f"Base de Datos: {table.database}")
        print(f"Descripción: {table.description}")
        print(f"Ruta completa: {table.fully_qualified_name}")
        print(f"\nColumnas ({len(table.columns)}):")
        for col in table.columns[:10]:  # Mostrar primeras 10 columnas
            print(f"  • {col['name']} ({col['type']})")
        if len(table.columns) > 10:
            print(f"  ... y {len(table.columns) - 10} columnas más")
        print("─"*80)
    
    def _show_alternatives(self, search_result: SearchResult):
        """Muestra tablas alternativas y query generada"""
        print("\n" + "─"*80)
        print("🔧 SOLUCIÓN PROPUESTA")
        print("─"*80)
        print("No existe una tabla exacta, pero podemos crearla usando estas tablas:")
        print()
        
        if search_result.related_tables:
            for i, table in enumerate(search_result.related_tables[:3], 1):
                print(f"{i}. {table.database}.{table.name}")
                print(f"   └─ {table.description}")
                print()
        
        if search_result.generated_query:
            print("📝 Query SQL propuesta:")
            print()
            print("```sql")
            print(search_result.generated_query)
            print("```")
        
        print("─"*80)


# ============================================================================
# CONFIGURACIÓN Y MAIN
# ============================================================================

def load_config() -> Dict:
    """
    Carga la configuración desde el archivo .env
    
    Returns:
        Diccionario con la configuración
    """
    # Cargar variables de entorno desde el archivo .env
    load_dotenv()
    
    config = {
        # OpenMetadata
        'openmetadata_url': os.getenv('OPENMETADATA_URL', 'https://openmetadata.example.com'),
        'openmetadata_token': os.getenv('OPENMETADATA_TOKEN', 'your-jwt-token-here'),
        
        # OpenAI
        'openai_api_key': os.getenv('OPENAI_API_KEY', 'sk-your-openai-key-here'),
        
        # Jira
        'jira_url': os.getenv('JIRA_URL', 'https://company.atlassian.net'),
        'jira_email': os.getenv('JIRA_EMAIL', 'your-email@company.com'),
        'jira_api_token': os.getenv('JIRA_API_TOKEN', 'your-jira-api-token'),
        'jira_project_key': os.getenv('JIRA_PROJECT_KEY', 'DATA'),
    }
    
    return config


def main():
    """
    Función principal para ejecutar el sistema multi-agente
    """
    print("🚀 Inicializando Sistema Multi-Agente...")
    print()
    
    # Cargar configuración
    config = load_config()
    
    # Validar que las credenciales no sean los placeholders
    if 'your-' in config['openai_api_key'] or 'example.com' in config['openmetadata_url']:
        print("⚠️  ATENCIÓN: Usando configuración de ejemplo.")
        print("   Para usar en producción, configura las variables de entorno:")
        print("   - OPENMETADATA_URL")
        print("   - OPENMETADATA_TOKEN")
        print("   - OPENAI_API_KEY")
        print("   - JIRA_URL")
        print("   - JIRA_EMAIL")
        print("   - JIRA_API_TOKEN")
        print("   - JIRA_PROJECT_KEY")
        print()
    
    try:
        # Inicializar agentes
        print("Inicializando AGOB (OpenMetadata)...")
        agob = AGOB(
            openmetadata_url=config['openmetadata_url'],
            api_token=config['openmetadata_token'],
            openai_api_key=config['openai_api_key']
        )
        
        print("Inicializando ATIC (Jira)...")
        atic = ATIC(
            jira_url=config['jira_url'],
            jira_email=config['jira_email'],
            jira_api_token=config['jira_api_token'],
            project_key=config['jira_project_key']
        )
        
        print("Inicializando AORQ (Orquestador)...")
        aorq = AORQ(agob=agob, atic=atic)
        
        print("\n✅ Todos los agentes inicializados correctamente")
        print()
        
        # Ejemplo de uso
        print("="*80)
        print("EJEMPLO DE USO")
        print("="*80)
        
        # Solicitud de ejemplo
        user_request = "Necesito una tabla con las ventas mensuales por región y producto"
        
        # Procesar solicitud (en modo no interactivo para el ejemplo)
        result = aorq.handle_request(user_request, interactive=False)
        
        # Mostrar resultado
        print("\n" + "="*80)
        print("RESULTADO FINAL")
        print("="*80)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"\n❌ Error fatal: {str(e)}")
        import traceback
        traceback.print_exc()


# ============================================================================
# EJEMPLO DE USO INTERACTIVO
# ============================================================================

def interactive_session():
    """
    Sesión interactiva con el usuario
    """
    config = load_config()
    
    try:
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
        
        print("\n🤖 Sistema Multi-Agente Iniciado")
        print("Escribe 'salir' para terminar\n")
        
        while True:
            user_input = input("💬 ¿Qué datos necesitas? > ").strip()
            
            if user_input.lower() in ['salir', 'exit', 'quit']:
                print("\n👋 ¡Hasta luego!")
                break
            
            if not user_input:
                continue
            
            # Procesar solicitud
            result = aorq.handle_request(user_input, interactive=True)
            
            print("\n" + "─"*80 + "\n")
        
    except KeyboardInterrupt:
        print("\n\n👋 Sesión interrumpida por el usuario")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


if __name__ == "__main__":
    # Ejecutar modo interactivo directamente
    interactive_session()
    
    # Para ejecutar el ejemplo de demostración, descomenta la siguiente línea:
    # main()
