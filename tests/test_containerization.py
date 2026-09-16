"""
Automated Tests for Containerization Configuration & Multi-Service Topology.

Validates:
- Dockerfile syntax, multi-stage targets (api, mcp, streamlit), security (non-root appuser).
- docker-compose.yml YAML schema, service definitions, port mappings, volumes, health checks,
  and ordered dependency graphs (service_healthy).
- .dockerignore exclusions for secrets, caches, and local virtualenvs.
- MCP remote SSE configuration and server health endpoint routing.
"""

from pathlib import Path
import pytest
import yaml
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import Settings
from app.mcp.client import EnterpriseMCPClient
from app.mcp.server import create_mcp_server


REPO_ROOT = Path(__file__).resolve().parent.parent


# ==============================================================================
# 1. Docker Compose Schema & Configuration Tests
# ==============================================================================

def test_docker_compose_file_exists_and_parses():
    """Verify docker-compose.yml is valid YAML and defines core configuration."""
    compose_path = REPO_ROOT / "docker-compose.yml"
    assert compose_path.exists(), "docker-compose.yml must exist at repository root"

    with open(compose_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert isinstance(data, dict), "docker-compose.yml must be a valid YAML mapping"
    assert "services" in data, "docker-compose.yml must define 'services'"
    assert "volumes" in data, "docker-compose.yml must define 'volumes'"
    assert "networks" in data, "docker-compose.yml must define 'networks'"


def test_docker_compose_services_topology():
    """Verify all 4 required services are defined with proper configurations."""
    compose_path = REPO_ROOT / "docker-compose.yml"
    with open(compose_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    services = data["services"]
    expected_services = ["qdrant", "mcp", "api", "streamlit"]
    for svc in expected_services:
        assert svc in services, f"Missing required service '{svc}' in docker-compose.yml"


def test_docker_compose_healthchecks():
    """Verify each service defines an explicit healthcheck with required parameters."""
    compose_path = REPO_ROOT / "docker-compose.yml"
    with open(compose_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    services = data["services"]
    for svc_name, svc_config in services.items():
        assert "healthcheck" in svc_config, f"Service '{svc_name}' must have a healthcheck"
        hc = svc_config["healthcheck"]
        assert "test" in hc, f"Healthcheck for '{svc_name}' must define 'test'"
        assert "interval" in hc, f"Healthcheck for '{svc_name}' must define 'interval'"
        assert "timeout" in hc, f"Healthcheck for '{svc_name}' must define 'timeout'"
        assert "retries" in hc, f"Healthcheck for '{svc_name}' must define 'retries'"


def test_docker_compose_startup_dependency_order():
    """Verify clean startup ordering with condition: service_healthy."""
    compose_path = REPO_ROOT / "docker-compose.yml"
    with open(compose_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    services = data["services"]

    # api must depend on qdrant and mcp being healthy
    api_deps = services["api"]["depends_on"]
    assert "qdrant" in api_deps
    assert api_deps["qdrant"]["condition"] == "service_healthy"
    assert "mcp" in api_deps
    assert api_deps["mcp"]["condition"] == "service_healthy"

    # streamlit must depend on api being healthy
    streamlit_deps = services["streamlit"]["depends_on"]
    assert "api" in streamlit_deps
    assert streamlit_deps["api"]["condition"] == "service_healthy"


def test_docker_compose_volumes_and_networking():
    """Verify persistent volumes and shared network are configured."""
    compose_path = REPO_ROOT / "docker-compose.yml"
    with open(compose_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    volumes = data["volumes"]
    assert "qdrant_storage" in volumes, "Must have persistent 'qdrant_storage' volume"
    assert "sqlite_data" in volumes, "Must have persistent 'sqlite_data' volume"

    networks = data["networks"]
    assert "enterprise_agent_network" in networks, "Must have 'enterprise_agent_network'"

    # Verify services attach to network
    for svc_name, svc_config in data["services"].items():
        assert "enterprise_agent_network" in svc_config.get("networks", []), (
            f"Service '{svc_name}' must join 'enterprise_agent_network'"
        )


def test_docker_compose_port_bindings():
    """Verify all host ports are non-conflicting and mapped correctly."""
    compose_path = REPO_ROOT / "docker-compose.yml"
    with open(compose_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    port_map = {}
    for svc_name, svc_config in data["services"].items():
        for port_str in svc_config.get("ports", []):
            host_port = port_str.split(":")[0]
            assert host_port not in port_map, f"Port collision on {host_port} between {port_map.get(host_port)} and {svc_name}"
            port_map[host_port] = svc_name

    assert "8000" in port_map and port_map["8000"] == "api"
    assert "8001" in port_map and port_map["8001"] == "mcp"
    assert "8501" in port_map and port_map["8501"] == "streamlit"
    assert "6333" in port_map and port_map["6333"] == "qdrant"


# ==============================================================================
# 2. Dockerfile Multi-Stage & Security Tests
# ==============================================================================

def test_dockerfile_stages_and_targets():
    """Verify Dockerfile contains builder and all three service targets."""
    dockerfile_path = REPO_ROOT / "Dockerfile"
    assert dockerfile_path.exists(), "Dockerfile must exist at repository root"

    content = dockerfile_path.read_text(encoding="utf-8")

    # Verify required stages
    assert "AS builder" in content
    assert "AS runtime-base" in content
    assert "AS api" in content
    assert "AS mcp" in content
    assert "AS streamlit" in content

    # Verify unprivileged user creation and switch
    assert "useradd" in content
    assert "USER appuser" in content

    # Verify curl is installed for container health checks
    assert "curl" in content

    # Verify healthchecks are declared in Dockerfile
    assert "HEALTHCHECK" in content


def test_dockerfile_no_hardcoded_secrets():
    """Verify Dockerfile does not leak hardcoded tokens or API keys."""
    dockerfile_path = REPO_ROOT / "Dockerfile"
    content = dockerfile_path.read_text(encoding="utf-8").lower()

    forbidden_strings = ["aizasy", "sk-", "password=", "secret_key="]
    for forbidden in forbidden_strings:
        assert forbidden not in content, f"Found potential secret pattern '{forbidden}' in Dockerfile"


# ==============================================================================
# 3. .dockerignore Coverage Tests
# ==============================================================================

def test_dockerignore_coverage():
    """Verify .dockerignore excludes secrets, virtualenvs, and test caches."""
    dockerignore_path = REPO_ROOT / ".dockerignore"
    assert dockerignore_path.exists(), ".dockerignore must exist at repository root"

    content = dockerignore_path.read_text(encoding="utf-8")

    required_patterns = [".git", ".venv", "__pycache__", ".env", ".pytest_cache"]
    for pattern in required_patterns:
        assert pattern in content, f"Pattern '{pattern}' should be present in .dockerignore"


# ==============================================================================
# 4. MCP Configuration & Server Health Route Tests
# ==============================================================================

def test_mcp_server_url_configuration_validation():
    """Verify Settings validates MCP_SERVER_URL."""
    # Valid configurations
    s1 = Settings(MCP_SERVER_URL="http://mcp:8001/sse")
    assert s1.MCP_SERVER_URL == "http://mcp:8001/sse"

    s2 = Settings(MCP_SERVER_URL="https://remote-mcp.internal:8001/sse")
    assert s2.MCP_SERVER_URL == "https://remote-mcp.internal:8001/sse"

    # Default None
    s3 = Settings()
    assert s3.MCP_SERVER_URL is None

    # Invalid scheme
    with pytest.raises(Exception):
        Settings(MCP_SERVER_URL="tcp://invalid-scheme:8001")


def test_enterprise_mcp_client_server_url_attribute():
    """Verify EnterpriseMCPClient accepts and stores remote server_url."""
    client = EnterpriseMCPClient(server_url="http://mcp:8001/sse")
    assert client.server_url == "http://mcp:8001/sse"
    assert not client.is_connected


@pytest.mark.asyncio
async def test_mcp_server_health_route_exists():
    """Verify create_mcp_server registers /health route returning healthy status."""
    server = create_mcp_server()
    routes = server._custom_starlette_routes
    health_routes = [r for r in routes if getattr(r, "path", None) == "/health"]
    assert len(health_routes) == 1, "MCPServer must have a custom /health route registered"

    # Invoke the health endpoint directly
    route = health_routes[0]
    scope = {"type": "http", "method": "GET", "path": "/health", "headers": []}
    req = Request(scope)
    res: JSONResponse = await route.endpoint(req)
    assert res.status_code == 200

    import json
    body = json.loads(res.body.decode("utf-8"))
    assert body["status"] == "healthy"
    assert "enterprise" in body["service"]
