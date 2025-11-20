"""
Tests Unitarios - Sistema Multi-Agente
======================================
Tests básicos para validar funcionalidad de los agentes

Para ejecutar:
    pip install pytest pytest-mock
    pytest test_multi_agent_system.py -v
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from multi_agent_system import AGOB, ATIC, AORQ, TableInfo, SearchResult


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def config():
    """Configuración de prueba"""
    return {
        'openmetadata_url': 'https://test.openmetadata.com',
        'openmetadata_token': 'test-token',
        'openai_api_key': 'test-openai-key',
        'jira_url': 'https://test.atlassian.net',
        'jira_email': 'test@test.com',
        'jira_api_token': 'test-jira-token',
        'jira_project_key': 'TEST'
    }


@pytest.fixture
def sample_table():
    """Tabla de ejemplo para tests"""
    return TableInfo(
        name='ventas',
        database='analytics',
        description='Tabla de ventas',
        columns=[
            {'name': 'id', 'type': 'INTEGER', 'description': 'ID'},
            {'name': 'monto', 'type': 'DECIMAL', 'description': 'Monto'}
        ],
        fully_qualified_name='analytics.ventas'
    )


# ============================================================================
# TESTS PARA AGOB
# ============================================================================

class TestAGOB:
    """Tests para el agente AGOB"""
    
    @patch('multi_agent_system.ChatOpenAI')
    def test_agob_initialization(self, mock_llm, config):
        """Test: AGOB se inicializa correctamente"""
        agob = AGOB(
            openmetadata_url=config['openmetadata_url'],
            api_token=config['openmetadata_token'],
            openai_api_key=config['openai_api_key']
        )
        
        assert agob.base_url == 'https://test.openmetadata.com'
        assert agob.api_token == 'test-token'
        assert 'Authorization' in agob.headers
    
    @patch('multi_agent_system.requests.get')
    @patch('multi_agent_system.ChatOpenAI')
    def test_search_openmetadata_success(self, mock_llm, mock_get, config):
        """Test: Búsqueda exitosa en OpenMetadata"""
        # Mock de respuesta
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'hits': {
                'hits': [
                    {
                        '_source': {
                            'name': 'ventas',
                            'database': {'name': 'analytics'},
                            'description': 'Tabla de ventas',
                            'columns': [],
                            'fullyQualifiedName': 'analytics.ventas'
                        }
                    }
                ]
            }
        }
        mock_get.return_value = mock_response
        
        agob = AGOB(
            openmetadata_url=config['openmetadata_url'],
            api_token=config['openmetadata_token'],
            openai_api_key=config['openai_api_key']
        )
        
        results = agob._search_openmetadata('ventas')
        
        assert len(results) == 1
        assert results[0]['_source']['name'] == 'ventas'
    
    def test_parse_search_results(self, config):
        """Test: Parseo correcto de resultados"""
        hits = [
            {
                '_source': {
                    'name': 'usuarios',
                    'database': {'name': 'crm'},
                    'description': 'Tabla de usuarios',
                    'columns': [
                        {'name': 'id', 'dataType': 'INTEGER', 'description': 'ID'}
                    ],
                    'fullyQualifiedName': 'crm.usuarios'
                }
            }
        ]
        
        with patch('multi_agent_system.ChatOpenAI'):
            agob = AGOB(
                openmetadata_url=config['openmetadata_url'],
                api_token=config['openmetadata_token'],
                openai_api_key=config['openai_api_key']
            )
        
        tables = agob._parse_search_results(hits)
        
        assert len(tables) == 1
        assert tables[0].name == 'usuarios'
        assert tables[0].database == 'crm'
        assert len(tables[0].columns) == 1


# ============================================================================
# TESTS PARA ATIC
# ============================================================================

class TestATIC:
    """Tests para el agente ATIC"""
    
    @patch('multi_agent_system.JIRA')
    def test_atic_initialization(self, mock_jira, config):
        """Test: ATIC se inicializa correctamente"""
        atic = ATIC(
            jira_url=config['jira_url'],
            jira_email=config['jira_email'],
            jira_api_token=config['jira_api_token'],
            project_key=config['jira_project_key']
        )
        
        assert atic.project_key == 'TEST'
        mock_jira.assert_called_once()
    
    @patch('multi_agent_system.JIRA')
    def test_create_ticket_success(self, mock_jira, config, sample_table):
        """Test: Creación exitosa de ticket"""
        # Mock del cliente Jira
        mock_issue = Mock()
        mock_issue.key = 'TEST-123'
        mock_jira_instance = Mock()
        mock_jira_instance.create_issue.return_value = mock_issue
        mock_jira_instance.server_url = config['jira_url']
        mock_jira.return_value = mock_jira_instance
        
        atic = ATIC(
            jira_url=config['jira_url'],
            jira_email=config['jira_email'],
            jira_api_token=config['jira_api_token'],
            project_key=config['jira_project_key']
        )
        
        ticket_key = atic.create_ticket(
            user_request='Test request',
            related_tables=[sample_table],
            proposed_query='SELECT * FROM test'
        )
        
        assert ticket_key == 'TEST-123'
        mock_jira_instance.create_issue.assert_called_once()
    
    @patch('multi_agent_system.JIRA')
    def test_build_description(self, mock_jira, config, sample_table):
        """Test: Construcción correcta de descripción"""
        atic = ATIC(
            jira_url=config['jira_url'],
            jira_email=config['jira_email'],
            jira_api_token=config['jira_api_token'],
            project_key=config['jira_project_key']
        )
        
        description = atic._build_description(
            user_request='Test request',
            related_tables=[sample_table],
            proposed_query='SELECT * FROM test'
        )
        
        assert 'Test request' in description
        assert 'ventas' in description
        assert 'SELECT * FROM test' in description
        assert 'h2.' in description  # Formato Jira


# ============================================================================
# TESTS PARA AORQ
# ============================================================================

class TestAORQ:
    """Tests para el agente orquestador AORQ"""
    
    @patch('multi_agent_system.JIRA')
    @patch('multi_agent_system.ChatOpenAI')
    def test_aorq_initialization(self, mock_llm, mock_jira, config):
        """Test: AORQ se inicializa correctamente"""
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
        
        assert aorq.agob is not None
        assert aorq.atic is not None
    
    @patch('multi_agent_system.JIRA')
    @patch('multi_agent_system.ChatOpenAI')
    def test_handle_request_table_found(self, mock_llm, mock_jira, config, sample_table):
        """Test: Flujo cuando se encuentra tabla exacta"""
        # Mock AGOB
        mock_agob = Mock()
        mock_agob.find_table.return_value = SearchResult(
            found=True,
            exact_match=sample_table,
            message='Tabla encontrada'
        )
        
        # Mock ATIC
        mock_atic = Mock()
        
        aorq = AORQ(agob=mock_agob, atic=mock_atic)
        
        result = aorq.handle_request('test query', interactive=False)
        
        assert result['table_found'] is True
        assert result['details']['table_name'] == 'ventas'
        mock_atic.create_ticket.assert_not_called()
    
    @patch('multi_agent_system.JIRA')
    @patch('multi_agent_system.ChatOpenAI')
    def test_handle_request_create_ticket(self, mock_llm, mock_jira, config, sample_table):
        """Test: Flujo cuando se crea ticket"""
        # Mock AGOB (no encuentra tabla exacta)
        mock_agob = Mock()
        mock_agob.find_table.return_value = SearchResult(
            found=False,
            related_tables=[sample_table],
            generated_query='SELECT * FROM test',
            message='No encontrada'
        )
        
        # Mock ATIC
        mock_atic = Mock()
        mock_atic.create_ticket.return_value = 'TEST-456'
        
        aorq = AORQ(agob=mock_agob, atic=mock_atic)
        
        result = aorq.handle_request('test query', interactive=False)
        
        assert result['ticket_created'] is True
        assert result['details']['ticket_key'] == 'TEST-456'
        mock_atic.create_ticket.assert_called_once()


# ============================================================================
# TESTS DE INTEGRACIÓN
# ============================================================================

class TestIntegration:
    """Tests de integración entre componentes"""
    
    @patch('multi_agent_system.requests.get')
    @patch('multi_agent_system.JIRA')
    @patch('multi_agent_system.ChatOpenAI')
    def test_full_workflow_with_ticket(self, mock_llm, mock_jira, mock_get, config):
        """Test: Flujo completo que resulta en creación de ticket"""
        # Mock OpenMetadata response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'hits': {
                'hits': [
                    {
                        '_source': {
                            'name': 'related_table',
                            'database': {'name': 'db'},
                            'description': 'Related',
                            'columns': [],
                            'fullyQualifiedName': 'db.related_table'
                        }
                    }
                ]
            }
        }
        mock_get.return_value = mock_response
        
        # Mock LLM responses
        mock_llm_instance = Mock()
        mock_exact_match = Mock()
        mock_exact_match.content = 'NONE'
        mock_sql = Mock()
        mock_sql.content = 'SELECT * FROM test'
        mock_llm_instance.invoke.side_effect = [mock_exact_match, mock_sql]
        mock_llm.return_value = mock_llm_instance
        
        # Mock Jira
        mock_issue = Mock()
        mock_issue.key = 'TEST-789'
        mock_jira_instance = Mock()
        mock_jira_instance.create_issue.return_value = mock_issue
        mock_jira_instance.server_url = config['jira_url']
        mock_jira.return_value = mock_jira_instance
        
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
        
        # Ejecutar flujo
        result = aorq.handle_request('test query', interactive=False)
        
        # Verificar
        assert result['success'] is True
        assert result['ticket_created'] is True


# ============================================================================
# TESTS DE MODELOS DE DATOS
# ============================================================================

class TestDataModels:
    """Tests para modelos de datos"""
    
    def test_table_info_creation(self):
        """Test: Creación de TableInfo"""
        table = TableInfo(
            name='test_table',
            database='test_db',
            description='Test description',
            columns=[{'name': 'col1', 'type': 'INT', 'description': 'Test'}],
            fully_qualified_name='test_db.test_table'
        )
        
        assert table.name == 'test_table'
        assert table.database == 'test_db'
        assert len(table.columns) == 1
    
    def test_search_result_found(self, sample_table):
        """Test: SearchResult con tabla encontrada"""
        result = SearchResult(
            found=True,
            exact_match=sample_table,
            message='Found'
        )
        
        assert result.found is True
        assert result.exact_match.name == 'ventas'
        assert result.related_tables is None
    
    def test_search_result_not_found(self, sample_table):
        """Test: SearchResult sin tabla exacta"""
        result = SearchResult(
            found=False,
            related_tables=[sample_table],
            generated_query='SELECT * FROM test',
            message='Not found'
        )
        
        assert result.found is False
        assert len(result.related_tables) == 1
        assert result.generated_query is not None


# ============================================================================
# EJECUTAR TESTS
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
