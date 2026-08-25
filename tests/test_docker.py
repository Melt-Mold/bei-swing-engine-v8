"""Tests for Docker configuration files."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class TestDockerfile:
    def test_dockerfile_exists(self):
        assert (ROOT / "Dockerfile").exists()

    def test_dockerfile_has_required_instructions(self):
        text = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        assert "FROM python:3.13" in text
        assert "requirements.txt" in text
        assert "PYTHONPATH=/app" in text
        assert "HEALTHCHECK" in text

    def test_dockerignore_exists(self):
        assert (ROOT / ".dockerignore").exists()

    def test_dockerignore_ignores_venv_and_output(self):
        text = (ROOT / ".dockerignore").read_text(encoding="utf-8")
        assert ".venv" in text or "venv" in text
        assert "output_test" in text
        assert "__pycache__" in text


class TestDockerCompose:
    def test_docker_compose_exists(self):
        assert (ROOT / "docker-compose.yml").exists()

    def test_docker_compose_has_expected_services(self):
        text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        assert "services:" in text
        assert "engine:" in text
        assert "webui:" in text
        assert "chat:" in text
        assert "api:" in text

    def test_docker_compose_port_mappings(self):
        text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        assert '"8501:8501"' in text or "'8501:8501'" in text or "8501:8501" in text
        assert '"8502:8502"' in text or "'8502:8502'" in text or "8502:8502" in text
        assert '"8000:8000"' in text or "'8000:8000'" in text or "8000:8000" in text
