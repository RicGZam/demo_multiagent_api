# 🔧 Guía de Troubleshooting y Mejores Prácticas

## 📚 Índice
- [Solución de Problemas Comunes](#solución-de-problemas-comunes)
- [Mejores Prácticas](#mejores-prácticas)
- [Optimización de Performance](#optimización-de-performance)
- [Seguridad](#seguridad)
- [Monitoreo y Logging](#monitoreo-y-logging)

---

## 🔍 Solución de Problemas Comunes

### Problema 1: Error de Autenticación en OpenMetadata

**Síntoma:**
```
[AGOB] ❌ Error: 401 Unauthorized
```

**Soluciones:**

1. **Verificar el Token JWT:**
```bash
# El token debe ser un JWT válido
echo $OPENMETADATA_TOKEN | cut -d'.' -f2 | base64 -d
```

2. **Regenerar el Token:**
- Accede a OpenMetadata → Settings → Bots
- Selecciona tu bot
- Click en "Regenerate Token"
- Actualiza la variable de entorno

3. **Verificar Permisos:**
El bot necesita permisos de:
- View All (Tablas)
- View All (Databases)
- Search (Índices)

### Problema 2: Error de Conexión con Jira

**Síntoma:**
```
[ATIC] ❌ Error al conectar con Jira: CAPTCHA_CHALLENGE
```

**Soluciones:**

1. **Verificar URL:**
```python
# Debe ser la URL base, sin paths adicionales
# ✅ Correcto: https://company.atlassian.net
# ❌ Incorrecto: https://company.atlassian.net/browse/
```

2. **Problemas con CAPTCHA:**
- Jira puede activar CAPTCHA si detecta muchos intentos
- Espera 15 minutos antes de reintentar
- Verifica que estás usando un API Token, no la contraseña

3. **Verificar Proyecto:**
```python
# Listar proyectos disponibles
from jira import JIRA
jira = JIRA(server=JIRA_URL, basic_auth=(EMAIL, TOKEN))
projects = jira.projects()
for p in projects:
    print(f"{p.key}: {p.name}")
```

### Problema 3: LLM No Genera SQL Correctamente

**Síntoma:**
```
Query generada: ```sql\nSELECT...\n```
```

**Soluciones:**

1. **Limpiar Output:**
Ya implementado en el código:
```python
if sql_query.startswith("```sql"):
    sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
```

2. **Mejorar el Prompt:**
```python
# Añadir más contexto al prompt
SystemMessage(content="""Eres un experto en SQL.
IMPORTANTE: Responde SOLO con código SQL puro, sin markdown.
No uses backticks ni formato markdown.
Solo el código SQL ejecutable.""")
```

3. **Validar SQL:**
```python
import sqlparse

def validate_sql(query: str) -> bool:
    try:
        parsed = sqlparse.parse(query)
        return len(parsed) > 0 and parsed[0].get_type() == 'SELECT'
    except:
        return False
```

### Problema 4: Rate Limiting de OpenAI

**Síntoma:**
```
openai.error.RateLimitError: Rate limit exceeded
```

**Soluciones:**

1. **Implementar Retry con Backoff:**
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
def call_llm_with_retry(self, prompt):
    return self.llm.invoke(prompt)
```

2. **Usar Caché:**
```python
from langchain.cache import SQLiteCache
from langchain.globals import set_llm_cache

set_llm_cache(SQLiteCache(database_path=".langchain.db"))
```

3. **Ajustar TPM (Tokens Per Minute):**
```python
self.llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    max_tokens=1000,  # Limitar tokens por request
    request_timeout=30  # Timeout más corto
)
```

### Problema 5: Timeout en Búsqueda de OpenMetadata

**Síntoma:**
```
requests.exceptions.Timeout: Request timeout
```

**Soluciones:**

1. **Aumentar Timeout:**
```python
response = requests.get(
    search_url,
    headers=self.headers,
    params=params,
    timeout=60  # Aumentar de 30 a 60 segundos
)
```

2. **Implementar Paginación:**
```python
def search_with_pagination(self, query: str, total_results: int = 50):
    all_results = []
    page_size = 10
    
    for page in range(total_results // page_size):
        params['from'] = page * page_size
        params['size'] = page_size
        
        response = requests.get(...)
        hits = response.json().get('hits', {}).get('hits', [])
        all_results.extend(hits)
        
        if len(hits) < page_size:
            break
    
    return all_results
```

---

## ✅ Mejores Prácticas

### 1. Configuración

**Usar Variables de Entorno:**
```python
# ✅ Bueno
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')

# ❌ Malo
api_key = "sk-1234..."  # Nunca hardcodear
```

**Validar Configuración al Inicio:**
```python
def validate_config(config: Dict) -> List[str]:
    """Retorna lista de errores de configuración"""
    errors = []
    
    required_keys = [
        'openmetadata_url',
        'openmetadata_token',
        'openai_api_key',
        'jira_url',
        'jira_email',
        'jira_api_token',
        'jira_project_key'
    ]
    
    for key in required_keys:
        if not config.get(key) or 'your-' in config.get(key, ''):
            errors.append(f"Falta configurar: {key}")
    
    return errors
```

### 2. Logging

**Implementar Logging Estructurado:**
```python
import logging
import json

class StructuredLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        
    def log_event(self, event_type: str, **kwargs):
        log_data = {
            'event': event_type,
            'timestamp': datetime.now().isoformat(),
            **kwargs
        }
        self.logger.info(json.dumps(log_data))

# Uso
logger = StructuredLogger('AGOB')
logger.log_event(
    'search_started',
    query=user_request,
    user_id=user_id
)
```

### 3. Manejo de Errores

**Errores Específicos:**
```python
class OpenMetadataError(Exception):
    """Error relacionado con OpenMetadata"""
    pass

class JiraError(Exception):
    """Error relacionado con Jira"""
    pass

class LLMError(Exception):
    """Error relacionado con el LLM"""
    pass

# Uso
try:
    result = self._search_openmetadata(query)
except requests.exceptions.Timeout:
    raise OpenMetadataError("Timeout al buscar en OpenMetadata")
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 401:
        raise OpenMetadataError("Token de OpenMetadata inválido")
    raise
```

### 4. Testing

**Usar Fixtures y Mocks:**
```python
@pytest.fixture
def mock_openmetadata_response():
    return {
        'hits': {
            'hits': [
                {
                    '_source': {
                        'name': 'test_table',
                        'database': {'name': 'test_db'},
                        'description': 'Test',
                        'columns': [],
                        'fullyQualifiedName': 'test_db.test_table'
                    }
                }
            ]
        }
    }

def test_search(mock_openmetadata_response):
    with patch('requests.get') as mock_get:
        mock_get.return_value.json.return_value = mock_openmetadata_response
        # Test code here
```

### 5. Documentación

**Docstrings Completos:**
```python
def find_table(self, user_request: str) -> SearchResult:
    """
    Busca una tabla basándose en la solicitud del usuario.
    
    Este método realiza los siguientes pasos:
    1. Busca tablas en OpenMetadata usando el API de búsqueda
    2. Parsea los resultados y extrae información relevante
    3. Determina si hay una coincidencia exacta usando el LLM
    4. Si no hay coincidencia, genera una query SQL alternativa
    
    Args:
        user_request: Descripción en lenguaje natural de lo que 
                     el usuario necesita. Ejemplo: "ventas por región"
    
    Returns:
        SearchResult: Objeto con los siguientes atributos:
            - found (bool): True si se encontró tabla exacta
            - exact_match (TableInfo | None): Tabla exacta encontrada
            - related_tables (List[TableInfo] | None): Tablas relacionadas
            - generated_query (str | None): Query SQL generada
            - message (str): Mensaje descriptivo del resultado
    
    Raises:
        OpenMetadataError: Si hay problemas con la API de OpenMetadata
        LLMError: Si el LLM no puede generar una query válida
    
    Example:
        >>> agob = AGOB(url, token, api_key)
        >>> result = agob.find_table("ventas mensuales")
        >>> if result.found:
        ...     print(f"Tabla: {result.exact_match.name}")
    """
    # Implementación
```

---

## ⚡ Optimización de Performance

### 1. Caché de Resultados

```python
from functools import lru_cache
from datetime import datetime, timedelta

class CachedAGOB(AGOB):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cache = {}
        self.cache_ttl = timedelta(hours=1)
    
    def find_table(self, user_request: str) -> SearchResult:
        cache_key = hash(user_request)
        
        if cache_key in self.cache:
            cached_result, timestamp = self.cache[cache_key]
            if datetime.now() - timestamp < self.cache_ttl:
                print("[AGOB] ⚡ Usando resultado en caché")
                return cached_result
        
        result = super().find_table(user_request)
        self.cache[cache_key] = (result, datetime.now())
        return result
```

### 2. Procesamiento en Paralelo

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def process_multiple_requests(self, requests: List[str]) -> List[Dict]:
    """Procesar múltiples solicitudes en paralelo"""
    results = []
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(self.handle_request, req, False): req
            for req in requests
        }
        
        for future in as_completed(futures):
            request = futures[future]
            try:
                result = future.result()
                results.append({
                    'request': request,
                    'result': result
                })
            except Exception as e:
                results.append({
                    'request': request,
                    'error': str(e)
                })
    
    return results
```

### 3. Streaming de Respuestas LLM

```python
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

self.llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    streaming=True,
    callbacks=[StreamingStdOutCallbackHandler()]
)
```

---

## 🔒 Seguridad

### 1. Validación de Inputs

```python
def sanitize_user_input(user_input: str) -> str:
    """Limpiar input del usuario"""
    # Remover caracteres peligrosos
    dangerous_chars = ['<', '>', '&', '"', "'"]
    sanitized = user_input
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, '')
    
    # Limitar longitud
    max_length = 500
    sanitized = sanitized[:max_length]
    
    return sanitized.strip()
```

### 2. Secrets Management

```python
from cryptography.fernet import Fernet

class SecretManager:
    def __init__(self, key_file: str = '.secret.key'):
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                self.key = f.read()
        else:
            self.key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(self.key)
        
        self.cipher = Fernet(self.key)
    
    def encrypt(self, text: str) -> bytes:
        return self.cipher.encrypt(text.encode())
    
    def decrypt(self, encrypted: bytes) -> str:
        return self.cipher.decrypt(encrypted).decode()
```

### 3. Rate Limiting por Usuario

```python
from collections import defaultdict
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self, max_requests: int = 10, window: timedelta = timedelta(minutes=1)):
        self.max_requests = max_requests
        self.window = window
        self.requests = defaultdict(list)
    
    def is_allowed(self, user_id: str) -> bool:
        now = datetime.now()
        
        # Limpiar requests antiguas
        self.requests[user_id] = [
            ts for ts in self.requests[user_id]
            if now - ts < self.window
        ]
        
        # Verificar límite
        if len(self.requests[user_id]) >= self.max_requests:
            return False
        
        self.requests[user_id].append(now)
        return True
```

---

## 📊 Monitoreo y Logging

### 1. Métricas

```python
from dataclasses import dataclass
from typing import Dict
import time

@dataclass
class Metrics:
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0.0
    tables_found: int = 0
    tickets_created: int = 0

class MetricsCollector:
    def __init__(self):
        self.metrics = Metrics()
        self.response_times = []
    
    def record_request(self, success: bool, response_time: float, 
                      table_found: bool, ticket_created: bool):
        self.metrics.total_requests += 1
        
        if success:
            self.metrics.successful_requests += 1
        else:
            self.metrics.failed_requests += 1
        
        self.response_times.append(response_time)
        self.metrics.avg_response_time = sum(self.response_times) / len(self.response_times)
        
        if table_found:
            self.metrics.tables_found += 1
        
        if ticket_created:
            self.metrics.tickets_created += 1
    
    def get_metrics(self) -> Dict:
        return {
            'total_requests': self.metrics.total_requests,
            'success_rate': (self.metrics.successful_requests / 
                           max(self.metrics.total_requests, 1) * 100),
            'avg_response_time_seconds': self.metrics.avg_response_time,
            'tables_found': self.metrics.tables_found,
            'tickets_created': self.metrics.tickets_created
        }
```

### 2. Health Checks

```python
class HealthChecker:
    def __init__(self, agob: AGOB, atic: ATIC):
        self.agob = agob
        self.atic = atic
    
    def check_health(self) -> Dict[str, bool]:
        health = {}
        
        # Check OpenMetadata
        try:
            response = requests.get(
                f"{self.agob.base_url}/api/v1/health-check",
                headers=self.agob.headers,
                timeout=5
            )
            health['openmetadata'] = response.status_code == 200
        except:
            health['openmetadata'] = False
        
        # Check Jira
        try:
            self.atic.jira_client.myself()
            health['jira'] = True
        except:
            health['jira'] = False
        
        # Check OpenAI
        try:
            self.agob.llm.invoke("test")
            health['openai'] = True
        except:
            health['openai'] = False
        
        return health
```

---

## 🚀 Deployment

### 1. Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "multi_agent_system.py"]
```

### 2. Environment Variables en Producción

```bash
# Usar secrets management
kubectl create secret generic multi-agent-secrets \
  --from-literal=openmetadata-token=$OPENMETADATA_TOKEN \
  --from-literal=jira-token=$JIRA_API_TOKEN \
  --from-literal=openai-key=$OPENAI_API_KEY
```

### 3. CI/CD

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      - name: Run tests
        run: pytest test_multi_agent_system.py --cov
```

---

## 📞 Soporte

Si tienes problemas no cubiertos en esta guía:

1. Revisa los logs detallados
2. Verifica la configuración de variables de entorno
3. Consulta la documentación oficial de cada servicio
4. Contacta al equipo de soporte

---

**Última actualización:** Noviembre 2025
