# 🚀 Guía de Inicio Rápido

## ⏱️ Instalación en 5 minutos

### Paso 1: Descargar el proyecto
```bash
# Si ya tienes los archivos, ve al directorio
cd multi-agent-system
```

### Paso 2: Ejecutar script de instalación (Linux/Mac)
```bash
chmod +x setup.sh
./setup.sh
```

### Paso 3: Configurar credenciales
```bash
# Editar archivo .env con tus credenciales
nano .env
```

Completa con tus valores reales:
```bash
OPENMETADATA_URL=https://tu-openmetadata.com
OPENMETADATA_TOKEN=eyJhbGc...
OPENAI_API_KEY=sk-proj-...
JIRA_URL=https://tu-empresa.atlassian.net
JIRA_EMAIL=tu-email@empresa.com
JIRA_API_TOKEN=ATATT3x...
JIRA_PROJECT_KEY=DATA
```

### Paso 4: Ejecutar
```bash
source venv/bin/activate
python multi_agent_system.py
```

---

## 📖 Instalación Manual (Windows)

### Paso 1: Crear entorno virtual
```bash
python -m venv venv
venv\Scripts\activate
```

### Paso 2: Instalar dependencias
```bash
pip install -r requirements.txt
```

### Paso 3: Configurar .env
```bash
copy .env.example .env
notepad .env
```

### Paso 4: Ejecutar
```bash
python multi_agent_system.py
```

---

## 🎯 Primer Uso

### Modo Demostración
El script viene configurado para ejecutar un ejemplo automático:

```bash
python multi_agent_system.py
```

Verás algo como:
```
🚀 Inicializando Sistema Multi-Agente...

Inicializando AGOB (OpenMetadata)...
Inicializando ATIC (Jira)...
Inicializando AORQ (Orquestador)...

✅ Todos los agentes inicializados correctamente
```

### Modo Interactivo
Para interactuar con el sistema:

1. Abre `multi_agent_system.py`
2. Busca al final del archivo:
```python
if __name__ == "__main__":
    main()  # ← Comenta esta línea
    # interactive_session()  # ← Descomenta esta línea
```

3. Ejecuta:
```bash
python multi_agent_system.py
```

4. Interactúa:
```
💬 ¿Qué datos necesitas? > Necesito ventas por región
```

---

## 🔧 Obtener Credenciales

### OpenMetadata Token
1. Accede a tu OpenMetadata → Settings
2. Ve a "Bots"
3. Selecciona o crea un bot
4. Copia el JWT Token

### OpenAI API Key
1. Ve a https://platform.openai.com/api-keys
2. Click en "Create new secret key"
3. Copia la key (comienza con `sk-`)
4. **Importante**: Necesitas tener créditos en tu cuenta

### Jira API Token
1. Ve a https://id.atlassian.com/manage-profile/security/api-tokens
2. Click en "Create API token"
3. Dale un nombre (ej: "Multi-Agent System")
4. Copia el token generado

### Jira Project Key
1. En Jira, ve a tu proyecto
2. La "key" aparece antes del número del issue
3. Ejemplo: En "DATA-123", la key es "DATA"

---

## 📋 Casos de Uso Comunes

### Buscar una tabla existente
```python
from multi_agent_system import AGOB, load_config

config = load_config()
agob = AGOB(
    openmetadata_url=config['openmetadata_url'],
    api_token=config['openmetadata_token'],
    openai_api_key=config['openai_api_key']
)

result = agob.find_table("ventas mensuales")
print(result.message)
```

### Crear un ticket en Jira
```python
from multi_agent_system import ATIC, load_config, TableInfo

config = load_config()
atic = ATIC(
    jira_url=config['jira_url'],
    jira_email=config['jira_email'],
    jira_api_token=config['jira_api_token'],
    project_key=config['jira_project_key']
)

ticket_key = atic.create_ticket(
    user_request="Nueva vista de análisis",
    related_tables=[],  # Lista de TableInfo
    proposed_query="SELECT * FROM ..."
)
print(f"Ticket creado: {ticket_key}")
```

### Flujo completo
```python
from multi_agent_system import AORQ, AGOB, ATIC, load_config

config = load_config()
agob = AGOB(config['openmetadata_url'], config['openmetadata_token'], config['openai_api_key'])
atic = ATIC(config['jira_url'], config['jira_email'], config['jira_api_token'], config['jira_project_key'])
aorq = AORQ(agob=agob, atic=atic)

result = aorq.handle_request(
    "Análisis de churn de clientes",
    interactive=False
)

if result['success']:
    print("✅ Solicitud procesada correctamente")
    if result.get('ticket_created'):
        print(f"Ticket: {result['details']['ticket_key']}")
```

---

## ❓ Preguntas Frecuentes

### ¿Funciona sin credenciales reales?
No, necesitas credenciales válidas de OpenMetadata, OpenAI y Jira.

### ¿Qué modelo de OpenAI usa?
Usa GPT-4o-mini por defecto. Puedes cambiarlo en el código.

### ¿Cuánto cuesta usar OpenAI?
GPT-4o-mini es muy económico. Verifica precios en https://openai.com/pricing

### ¿Puedo usar otro LLM?
Sí, LangChain soporta múltiples LLMs. Modifica la inicialización del LLM.

### ¿Funciona con Jira Server (on-premise)?
Sí, solo cambia la URL a tu servidor Jira.

### ¿Puedo añadir más agentes?
Sí, sigue el patrón de las clases AGOB y ATIC.

---

## 🐛 Problemas Comunes

### Error: "Invalid OpenAI API Key"
- Verifica que la key sea correcta
- Confirma que tienes créditos en OpenAI

### Error: "Connection refused" (OpenMetadata)
- Verifica la URL
- Confirma que el token sea válido
- Revisa conectividad de red

### Error: "Authentication failed" (Jira)
- Verifica email y token
- Confirma que el proyecto exista
- Verifica permisos del usuario

### Error: "Module not found"
```bash
pip install -r requirements.txt
```

---

## 📚 Próximos Pasos

1. **Lee el README.md** para documentación completa
2. **Revisa ejemplos_uso.py** para casos avanzados
3. **Consulta TROUBLESHOOTING.md** si tienes problemas
4. **Ejecuta los tests**: `pytest test_multi_agent_system.py -v`

---

## 🎓 Recursos de Aprendizaje

### LangChain
- Documentación: https://python.langchain.com/docs/
- Tutorial: https://python.langchain.com/docs/get_started/quickstart

### OpenMetadata
- Docs: https://docs.open-metadata.org/
- API: https://docs.open-metadata.org/v1.6.x/developers/apis

### Jira API
- REST API: https://developer.atlassian.com/cloud/jira/platform/rest/v3/
- Python Client: https://jira.readthedocs.io/

---

## 💡 Tips Pro

1. **Usa caché**: Implementa caché para consultas frecuentes
2. **Logging**: Activa logging detallado para debugging
3. **Testing**: Ejecuta tests antes de cambios importantes
4. **Monitoreo**: Implementa health checks para producción
5. **Seguridad**: Nunca commitees el archivo .env

---

## 🤝 Necesitas Ayuda?

- **Errores técnicos**: Ver TROUBLESHOOTING.md
- **Configuración**: Ver README.md
- **Ejemplos**: Ver ejemplos_uso.py
- **Tests**: Ver test_multi_agent_system.py

---

**¡Listo! Ya puedes empezar a usar tu sistema multi-agente! 🎉**

Si todo está configurado correctamente, en menos de 5 minutos tendrás el sistema funcionando.
