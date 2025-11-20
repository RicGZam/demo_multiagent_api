#!/bin/bash
# Script de Instalación Rápida - Sistema Multi-Agente
# =====================================================
# Este script automatiza la configuración inicial del proyecto

set -e  # Salir si hay algún error

echo "================================================"
echo "🤖 Sistema Multi-Agente - Instalación Rápida"
echo "================================================"
echo ""

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Función para imprimir mensajes
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 1. Verificar Python
echo "1. Verificando Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    print_success "Python encontrado: $PYTHON_VERSION"
else
    print_error "Python 3 no está instalado"
    echo "Por favor instala Python 3.8 o superior"
    exit 1
fi

# 2. Crear entorno virtual
echo ""
echo "2. Creando entorno virtual..."
if [ -d "venv" ]; then
    print_warning "El entorno virtual ya existe"
    read -p "¿Deseas recrearlo? (s/n): " recreate
    if [ "$recreate" = "s" ]; then
        rm -rf venv
        python3 -m venv venv
        print_success "Entorno virtual recreado"
    fi
else
    python3 -m venv venv
    print_success "Entorno virtual creado"
fi

# 3. Activar entorno virtual
echo ""
echo "3. Activando entorno virtual..."
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    print_success "Entorno virtual activado"
else
    print_error "No se pudo encontrar el script de activación"
    exit 1
fi

# 4. Actualizar pip
echo ""
echo "4. Actualizando pip..."
pip install --upgrade pip > /dev/null 2>&1
print_success "pip actualizado"

# 5. Instalar dependencias
echo ""
echo "5. Instalando dependencias..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    print_success "Dependencias instaladas"
else
    print_error "No se encontró requirements.txt"
    exit 1
fi

# 6. Configurar variables de entorno
echo ""
echo "6. Configurando variables de entorno..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_success "Archivo .env creado desde .env.example"
        print_warning "IMPORTANTE: Edita el archivo .env con tus credenciales reales"
        echo ""
        echo "Variables que debes configurar:"
        echo "  - OPENMETADATA_URL"
        echo "  - OPENMETADATA_TOKEN"
        echo "  - OPENAI_API_KEY"
        echo "  - JIRA_URL"
        echo "  - JIRA_EMAIL"
        echo "  - JIRA_API_TOKEN"
        echo "  - JIRA_PROJECT_KEY"
    else
        print_error "No se encontró .env.example"
    fi
else
    print_warning "El archivo .env ya existe"
fi

# 7. Verificar instalación
echo ""
echo "7. Verificando instalación..."

echo -n "Verificando LangChain... "
python3 -c "import langchain" 2>/dev/null && print_success "OK" || print_error "FALLO"

echo -n "Verificando OpenAI... "
python3 -c "import openai" 2>/dev/null && print_success "OK" || print_error "FALLO"

echo -n "Verificando Jira... "
python3 -c "import jira" 2>/dev/null && print_success "OK" || print_error "FALLO"

echo -n "Verificando Requests... "
python3 -c "import requests" 2>/dev/null && print_success "OK" || print_error "FALLO"

# 8. Información final
echo ""
echo "================================================"
echo "✅ Instalación completada"
echo "================================================"
echo ""
echo "📝 Próximos pasos:"
echo ""
echo "1. Edita el archivo .env con tus credenciales:"
echo "   nano .env  # o usa tu editor preferido"
echo ""
echo "2. Activa el entorno virtual (si no está activo):"
echo "   source venv/bin/activate"
echo ""
echo "3. Ejecuta el sistema:"
echo "   python multi_agent_system.py"
echo ""
echo "4. Para modo interactivo, edita multi_agent_system.py y:"
echo "   - Comenta: main()"
echo "   - Descomenta: interactive_session()"
echo ""
echo "5. Para ejecutar tests:"
echo "   pip install pytest pytest-mock"
echo "   pytest test_multi_agent_system.py -v"
echo ""
echo "📚 Documentación:"
echo "   - README.md: Guía completa"
echo "   - TROUBLESHOOTING.md: Solución de problemas"
echo "   - ejemplos_uso.py: Ejemplos avanzados"
echo ""
echo "🔗 Enlaces útiles:"
echo "   - OpenMetadata: https://docs.open-metadata.org"
echo "   - Jira API: https://developer.atlassian.com/cloud/jira/platform/rest/v3/"
echo "   - LangChain: https://python.langchain.com/docs/"
echo ""
print_success "¡Listo para comenzar! 🚀"
echo ""
