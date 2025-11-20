# 🤖 Sistema Multi-Agente para Gestión de Datos

Sistema inteligente con tres agentes cooperativos para automatizar la búsqueda de productos de datos y la creación de tickets en Jira.

## 📋 Descripción

Este sistema implementa una arquitectura multi-agente que coordina tres agentes especializados:

### 🎯 Agentes

1. **AORQ (Agente Orquestador)**
   - Interactúa directamente con el usuario
   - Coordina los otros dos agentes
   - Valida resultados en cada paso
   - Gestiona el flujo completo de la solicitud

2. **AGOB (Agente de OpenMetadata)**
   - Busca productos de datos en OpenMetadata
   - Identifica tablas exactas o relacionadas
   - Usa LLM (GPT-4o-mini) para generar queries SQL
   - Analiza esquemas y metadatos

3. **ATIC (Agente de Tickets Jira)**
   - Crea tickets automáticamente en Jira
   - Documenta la solicitud del usuario
   - Incluye tablas relacionadas y queries propuestas
   - Facilita el seguimiento del trabajo

## 🚀 Características

- ✅ Búsqueda inteligente en catálogo de datos (OpenMetadata)
- ✅ Generación automática de queries SQL con IA
- ✅ Creación automática de tickets en Jira
- ✅ Validación paso a paso con el usuario
- ✅ Manejo robusto de errores
- ✅ Integración con LangChain
- ✅ Código bien documentado y estructurado

## 📦 Instalación

### 1. Clonar o descargar el proyecto

```bash
# Crear directorio del proyecto
mkdir multi-agent-system
cd multi-agent-system
```

### 2. Crear entorno virtual (recomendado)

```bash
python -m venv venv

# Activar en Linux/Mac
source venv/bin/activate

# Activar en Windows
venv\Scripts\activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

## ⚙️ Configuración

### Variables de Entorno

Crea un archivo `.env` en el directorio raíz con las siguientes variables:

```bash
# OpenMetadata
OPENMETADATA_URL=https://your-openmetadata-instance.com
OPENMETADATA_TOKEN=your-jwt-token-here

# OpenAI
OPENAI_API_KEY=sk-your-openai-api-key

# Jira
JIRA_URL=https://your-company.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_API_TOKEN=your-jira-api-token
JIRA_PROJECT_KEY=DATA
```

### Obtener Credenciales

#### OpenMetadata Token
1. Accede a tu instancia de OpenMetadata
2. Ve a Settings → Bots
3. Crea o selecciona un bot
4. Copia el JWT token generado

#### OpenAI API Key
1. Accede a https://platform.openai.com
2. Ve a API Keys
3. Crea una nueva API key
4. **Importante**: Asegúrate de tener créditos disponibles

#### Jira API Token
1. Accede a https://id.atlassian.com/manage-profile/security/api-tokens
2. Click en "Create API token"
3. Dale un nombre descriptivo
4. Copia el token generado

## 💻 Uso

### Modo Demostración (No Interactivo)

```bash
python multi_agent_system.py
```

Este modo ejecuta un ejemplo predefinido mostrando el flujo completo del sistema.

### Modo Interactivo

Edita el archivo `multi_agent_system.py` y descomenta la última línea:

```python
if __name__ == "__main__":
    # main()  # Comentar esta línea
    interactive_session()  # Descomentar esta línea
```

Luego ejecuta:

```bash
python multi_agent_system.py
```

### Ejemplo de Uso Programático

```python
from multi_agent_system import AORQ, AGOB, ATIC, load_config

# Cargar configuración
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

# Procesar solicitud
result = aorq.handle_request(
    "Necesito una tabla con ventas por región",
    interactive=False
)

print(result)
```

## 🔄 Flujo de Trabajo

```
Usuario → AORQ → AGOB (busca en OpenMetadata)
                   ↓
                   ├─→ ¿Tabla exacta encontrada?
                   │   ├─→ SÍ: Mostrar tabla → Fin
                   │   └─→ NO: Buscar relacionadas
                   ↓
                   Generar SQL con LLM
                   ↓
                   Mostrar al usuario
                   ↓
                   ¿Usuario confirma?
                   ├─→ SÍ: ATIC (crear ticket Jira) → Fin
                   └─→ NO: Solicitar más info → Fin
```

## 📊 Estructura del Proyecto

```
multi-agent-system/
├── multi_agent_system.py    # Sistema completo
├── requirements.txt          # Dependencias
├── README.md                # Este archivo
├── .env                     # Configuración (no incluir en git)
└── .env.example             # Plantilla de configuración
```

## 🔧 Arquitectura Técnica

### Tecnologías Utilizadas

- **LangChain**: Orquestación de LLM y chains
- **OpenAI GPT-4o-mini**: Generación de SQL y análisis
- **OpenMetadata API**: Búsqueda en catálogo de datos
- **Jira REST API**: Creación de tickets
- **Python 3.8+**: Lenguaje base

### Clases Principales

#### `AGOB` (OpenMetadata Agent)
```python
- find_table(user_request: str) -> SearchResult
- _search_openmetadata(query: str) -> List[Dict]
- _parse_search_results(hits: List[Dict]) -> List[TableInfo]
- _find_exact_match(user_request: str, tables: List[TableInfo]) -> Optional[TableInfo]
- _generate_sql_query(user_request: str, tables: List[TableInfo]) -> str
```

#### `ATIC` (Jira Ticket Agent)
```python
- create_ticket(user_request: str, related_tables: List[TableInfo], proposed_query: str) -> str
- _build_description(...) -> str
```

#### `AORQ` (Orchestrator Agent)
```python
- handle_request(user_input: str, interactive: bool) -> Dict
- _show_found_table(table: TableInfo)
- _show_alternatives(search_result: SearchResult)
```

## 🛡️ Manejo de Errores

El sistema incluye manejo robusto de errores:

- ✅ Timeout en llamadas a APIs
- ✅ Validación de credenciales
- ✅ Manejo de respuestas vacías
- ✅ Errores de red
- ✅ Parsing de JSON
- ✅ Excepciones de Jira

## 🧪 Testing

Para probar con datos de ejemplo sin credenciales reales:

```python
# El sistema detecta automáticamente credenciales de ejemplo
# y muestra advertencias apropiadas
```

## 📝 Personalización

### Cambiar el Modelo de LLM

En la clase `AGOB`, modifica:

```python
self.llm = ChatOpenAI(
    model="gpt-4o-mini",  # Cambiar a otro modelo
    temperature=0,
    openai_api_key=openai_api_key
)
```

### Modificar Tipo de Issue en Jira

En el método `create_ticket` de `ATIC`:

```python
issue_dict = {
    'project': {'key': self.project_key},
    'issuetype': {'name': 'Story'},  # Cambiar a 'Bug', 'Epic', etc.
    # ...
}
```

### Ajustar Número de Resultados

En `_search_openmetadata`:

```python
params = {
    'size': 10,  # Cambiar número de resultados
    # ...
}
```

## 🚨 Solución de Problemas

### Error: "Invalid OpenAI API Key"
- Verifica que la API key esté correcta
- Confirma que tienes créditos en tu cuenta de OpenAI

### Error: "Connection to OpenMetadata failed"
- Verifica la URL de OpenMetadata
- Confirma que el token JWT sea válido
- Revisa la conectividad de red

### Error: "Jira authentication failed"
- Verifica email y API token
- Confirma que el proyecto key exista
- Revisa permisos del usuario en Jira

### Error: "Module not found"
- Ejecuta: `pip install -r requirements.txt`
- Verifica que el entorno virtual esté activado

## 🔐 Seguridad

**IMPORTANTE**: 
- ⚠️ **NUNCA** incluyas el archivo `.env` en control de versiones
- ⚠️ Usa variables de entorno en producción
- ⚠️ Rota las API keys regularmente
- ⚠️ Limita permisos de los tokens al mínimo necesario

Añade al `.gitignore`:
```
.env
*.pyc
__pycache__/
venv/
```

## 📚 Recursos Adicionales

- [Documentación OpenMetadata API](https://docs.open-metadata.org/v1.6.x/developers/apis)
- [Documentación Jira REST API](https://developer.atlassian.com/cloud/jira/platform/rest/v3/)
- [Documentación LangChain](https://python.langchain.com/docs/get_started/introduction)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)

## 🤝 Contribuciones

Este es un proyecto de ejemplo. Para mejoras:

1. Fork del repositorio
2. Crea una rama para tu feature
3. Commit de cambios
4. Push a la rama
5. Crea un Pull Request

## 📄 Licencia

Este proyecto es código de ejemplo para propósitos educativos.

## 👥 Autor

Sistema creado como ejemplo de arquitectura multi-agente con LangChain.

## 📞 Soporte

Para preguntas sobre:
- **OpenMetadata**: https://slack.open-metadata.org/
- **LangChain**: https://github.com/langchain-ai/langchain
- **Jira API**: https://community.atlassian.com/

---

**Nota**: Este sistema requiere acceso a OpenMetadata, Jira y OpenAI. Asegúrate de tener las credenciales apropiadas antes de ejecutar.
