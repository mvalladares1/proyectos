"""
BUENOBOT v3.0 - AI Module Tests

Tests para el motor de IA híbrido.
"""
import pytest
import asyncio
from unittest.mock import Mock, patch

# Import modules to test
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.buenobot.config import AIEngineConfig, get_ai_config
from backend.buenobot.evidence import EvidencePack, EvidencePackBuilder
from backend.buenobot.ai.router import AIRouter, EngineSelection
from backend.buenobot.ai.gateway import AIGateway
from backend.buenobot.cache_ai import AICache


class TestAIEngineConfig:
    """Tests para configuración de IA"""
    
    def test_default_config(self):
        """Verifica valores por defecto"""
        config = AIEngineConfig()
        
        assert config.ai_enabled == False
        assert config.default_engine == "mock"
        assert config.cache_enabled == True
        assert config.max_findings_to_ai == 20
    
    def test_complexity_triggers(self):
        """Verifica triggers de complejidad"""
        config = AIEngineConfig()
        
        assert "password_in_query_params" in config.complexity_triggers
        assert "sql_injection_risk" in config.complexity_triggers


class TestEvidencePack:
    """Tests para EvidencePack"""
    
    def test_create_evidence_pack(self):
        """Verifica creación de EvidencePack"""
        pack = EvidencePack(
            scan_id="test123",
            environment="dev",
            gate_status="FAIL",
            risk_triggers=["password_in_query_params"]
        )
        
        assert pack.scan_id == "test123"
        assert pack.environment == "dev"
        assert "password_in_query_params" in pack.risk_triggers
    
    def test_compute_hash(self):
        """Verifica hash de evidencia"""
        pack = EvidencePack(
            scan_id="test123",
            environment="dev",
            gate_status="PASS"
        )
        
        hash1 = pack.compute_hash()
        assert len(hash1) == 16
        
        # Mismo pack = mismo hash
        hash2 = pack.compute_hash()
        assert hash1 == hash2
        
        # Diferente pack = diferente hash
        pack2 = EvidencePack(
            scan_id="test123",
            environment="prod",
            gate_status="PASS"
        )
        hash3 = pack2.compute_hash()
        assert hash1 != hash3
    
    def test_to_dict(self):
        """Verifica serialización"""
        pack = EvidencePack(
            scan_id="test123",
            environment="dev",
            gate_status="WARN",
            risk_triggers=["print_in_routers"]
        )
        
        data = pack.to_dict()
        
        assert data["scan_id"] == "test123"
        assert data["environment"] == "dev"
        assert "print_in_routers" in data["risk_triggers"]


class TestAIRouter:
    """Tests para AI Router"""
    
    def test_select_mock_by_default(self):
        """Verifica selección de mock por defecto"""
        router = AIRouter()
        
        # Sin API key, debería usar mock
        evidence = EvidencePack(
            scan_id="test",
            gate_status="PASS"
        )
        
        selection = router.select_engine(evidence)
        
        assert selection.engine in ["mock", "local"]
        assert "mock" in selection.reason.lower() or "no" in selection.reason.lower()
    
    def test_complexity_score(self):
        """Verifica cálculo de complejidad"""
        router = AIRouter()
        
        # Pack simple
        simple = EvidencePack(scan_id="test", gate_status="PASS")
        score1 = router._calculate_complexity(simple)
        assert score1 == 0
        
        # Pack con findings críticos
        complex_pack = EvidencePack(
            scan_id="test",
            gate_status="FAIL",
            top_findings=[
                {"severity": "critical", "title": "test"},
                {"severity": "high", "title": "test2"}
            ],
            risk_triggers=["password_in_query_params"]
        )
        score2 = router._calculate_complexity(complex_pack)
        assert score2 > score1


class TestAIGateway:
    """Tests para AI Gateway"""
    
    @pytest.mark.asyncio
    async def test_analyze_mock_mode(self):
        """Verifica análisis en modo mock"""
        gateway = AIGateway()
        
        evidence = EvidencePack(
            scan_id="test123",
            environment="dev",
            gate_status="FAIL",
            risk_triggers=["password_in_query_params"]
        )
        
        result = await gateway.analyze(evidence, analysis_mode="basic")
        
        # Verificar estructura de respuesta
        assert "summary" in result or "skipped" in result
        
        if not result.get("skipped"):
            assert "engine_used" in result
            assert result["engine_used"] in ["mock", "local", "openai"]


class TestAICache:
    """Tests para AI Cache"""
    
    def test_cache_disabled(self):
        """Verifica comportamiento con cache deshabilitado"""
        with patch.object(AICache, '__init__', lambda self, *args, **kwargs: None):
            cache = AICache.__new__(AICache)
            cache.enabled = False
            
            result = cache.get("sha", "hash", "mock")
            assert result is None
            
            success = cache.set("sha", "hash", "mock", {"test": "data"})
            assert success == False
    
    def test_compute_key(self):
        """Verifica generación de key"""
        cache = AICache()
        
        if cache.enabled:
            key1 = cache._compute_key("sha1", "hash1", "mock")
            key2 = cache._compute_key("sha1", "hash1", "mock")
            key3 = cache._compute_key("sha1", "hash1", "openai")
            
            assert key1 == key2  # Mismo input = mismo key
            assert key1 != key3  # Diferente engine = diferente key


# Test de integración simple
class TestIntegration:
    """Tests de integración"""
    
    @pytest.mark.asyncio
    async def test_full_flow_mock(self):
        """Test flow completo en modo mock"""
        from backend.buenobot.ai import get_ai_gateway
        
        gateway = get_ai_gateway()
        
        evidence = EvidencePack(
            scan_id="integration_test",
            environment="dev",
            gate_status="WARN",
            risk_triggers=["print_in_routers"],
            top_findings=[
                {
                    "severity": "low",
                    "title": "Print statement found",
                    "location": "backend/routers/test.py:42"
                }
            ]
        )
        
        result = await gateway.analyze(evidence)
        
        # El resultado debe tener estructura válida
        assert isinstance(result, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
