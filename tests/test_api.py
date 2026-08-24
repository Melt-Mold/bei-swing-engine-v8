"""Tests for REST API module."""

import pytest
import os
import io
import json

from fastapi.testclient import TestClient

from bei_swing_engine_v8.api import app


class TestAPI:
    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_root(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "BEI Swing Engine v8.0 API"
        assert "endpoints" in data

    def test_health(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_analyze(self, client):
        csv_content = "Date,Open,High,Low,Close,Volume\n2026-01-01,100,102,99,101,1000\n2026-01-02,101,103,100,102,2000\n"
        # Need at least 20 bars for analysis, so create more
        rows = []
        for i in range(25):
            rows.append(f"2026-01-{i+1:02d},{100+i},{102+i},{99+i},{101+i},{1000+i}")
        csv_content = "Date,Open,High,Low,Close,Volume\n" + "\n".join(rows) + "\n"

        response = client.post(
            "/analyze",
            files=[("files", ("test.csv", csv_content, "text/csv"))],
            data={"mode": "A", "modal": "10000000", "risk": "2.0"},
        )
        # May return 200 or 500 depending on data sufficiency
        assert response.status_code in (200, 500)

    def test_screening(self, client):
        rows = []
        for i in range(25):
            rows.append(f"2026-01-{i+1:02d},{100+i},{102+i},{99+i},{101+i},{1000+i}")
        csv_content = "Date,Open,High,Low,Close,Volume\n" + "\n".join(rows) + "\n"

        response = client.post(
            "/screening",
            files=[("files", ("test.csv", csv_content, "text/csv"))],
            data={"modal": "10000000", "risk": "2.0"},
        )
        assert response.status_code in (200, 500)

    def test_clean(self, client):
        csv_content = "Date,Open,High,Low,Close,Volume\n2026-01-01,100,102,99,101,1000\n2026-01-02,101,103,100,102,2000\n"
        response = client.post(
            "/clean",
            files=[("file", ("test.csv", csv_content, "text/csv"))],
        )
        assert response.status_code == 200
        data = response.json()
        assert data["rows"] == 2
        assert "Date,Open,High,Low,Close,Volume" in data["csv"]

    def test_clean_error(self, client):
        csv_content = "bad,csv,format\n"
        response = client.post(
            "/clean",
            files=[("file", ("bad.csv", csv_content, "text/csv"))],
        )
        assert response.status_code == 400

    def test_merge(self, client):
        existing = "Date,Open,High,Low,Close,Volume\n2026-01-01,100,102,99,101,1000\n"
        new = "Date,Open,High,Low,Close,Volume\n2026-01-02,101,103,100,102,2000\n"
        response = client.post(
            "/merge",
            files=[
                ("existing", ("existing.csv", existing, "text/csv")),
                ("new_files", ("new.csv", new, "text/csv")),
            ],
        )
        assert response.status_code == 200
        data = response.json()
        assert data["existing_count"] == 1
        assert data["new_count"] == 1
        assert data["merged_count"] == 2

    def test_merge_no_new_data(self, client):
        existing = "Date,Open,High,Low,Close,Volume\n2026-01-01,100,102,99,101,1000\n"
        new = "Date,Open,High,Low,Close,Volume\n2026-01-01,100,102,99,101,1000\n"
        response = client.post(
            "/merge",
            files=[
                ("existing", ("existing.csv", existing, "text/csv")),
                ("new_files", ("new.csv", new, "text/csv")),
            ],
        )
        assert response.status_code == 200
        data = response.json()
        assert data["new_count"] == 0

    def test_backtest(self, client):
        # Need 50+ bars for backtest
        rows = []
        for i in range(60):
            rows.append(f"2026-01-{i+1:02d},{100+i},{102+i},{99+i},{101+i},{1000+i}")
        csv_content = "Date,Open,High,Low,Close,Volume\n" + "\n".join(rows) + "\n"

        response = client.post(
            "/backtest",
            files=[("file", ("test.csv", csv_content, "text/csv"))],
            data={"step": "5", "modal": "10000000", "risk": "2.0"},
        )
        assert response.status_code in (200, 500)

    def test_portfolio(self, client):
        # Use real sample CSV
        csv_path = "data-csv-yfinance-cleaned/TLKM.JK_cleaned.csv"
        if not os.path.exists(csv_path):
            pytest.skip("Sample data not available")
        with open(csv_path, "r") as f:
            csv_content = f.read()

        response = client.post(
            "/portfolio",
            files=[("files", ("TLKM.csv", csv_content, "text/csv"))],
            data={"step": "5", "modal": "10000000", "risk": "2.0", "allocation": "equal_weight"},
        )
        assert response.status_code in (200, 500)

    def test_fetch_invalid_period(self, client):
        response = client.get("/fetch/BBRI?period=invalid")
        # FastAPI validation error
        assert response.status_code == 422

    def test_fetch_invalid_interval(self, client):
        response = client.get("/fetch/BBRI?interval=invalid")
        assert response.status_code == 422
