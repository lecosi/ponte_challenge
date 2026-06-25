from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

import pytest

from call_center.models.ticket import Ticket
from call_center.services.csv_writer import ResultWriter

FECHA = datetime(2024, 1, 1, 9, 0)


def make_resolved_ticket(id: int = 1, agente: int = 1) -> Ticket:
    return Ticket(
        id=id,
        fecha_creacion=FECHA,
        prioridad=2,
        agente=agente,
        fecha_asignacion=datetime(2024, 1, 1, 10, 0),
        fecha_resolucion=datetime(2024, 1, 1, 10, 2),
    )


class TestFileLifecycle:
    @pytest.mark.asyncio
    async def test_creates_output_file(self, tmp_path):
        output = tmp_path / "out.csv"
        async with ResultWriter(output) as writer:
            await writer.write_ticket(make_resolved_ticket())
        assert output.exists()

    @pytest.mark.asyncio
    async def test_creates_parent_directory_on_enter(self, tmp_path):
        output = tmp_path / "subdir" / "out.csv"
        async with ResultWriter(output) as writer:
            await writer.write_ticket(make_resolved_ticket())
        assert output.parent.exists()

    @pytest.mark.asyncio
    async def test_directory_not_created_before_context(self, tmp_path):
        output = tmp_path / "subdir" / "out.csv"
        ResultWriter(output)  # solo instanciar, sin entrar al contexto
        assert not output.parent.exists()


class TestCSVContent:
    @pytest.mark.asyncio
    async def test_header_row(self, tmp_path):
        output = tmp_path / "out.csv"
        async with ResultWriter(output) as writer:
            await writer.write_ticket(make_resolved_ticket())
        with open(output, newline="") as f:
            header = next(csv.reader(f))
        assert header == ["id", "fecha_creacion", "prioridad", "agente",
                          "fecha_asignacion", "fecha_resolucion"]

    @pytest.mark.asyncio
    async def test_ticket_values_written_correctly(self, tmp_path):
        output = tmp_path / "out.csv"
        async with ResultWriter(output) as writer:
            await writer.write_ticket(make_resolved_ticket(id=42, agente=3))
        with open(output, newline="") as f:
            rows = list(csv.reader(f))
        data = rows[1]
        assert data[0] == "42"   # id
        assert data[2] == "2"    # prioridad
        assert data[3] == "3"    # agente

    @pytest.mark.asyncio
    async def test_timestamps_include_date(self, tmp_path):
        output = tmp_path / "out.csv"
        async with ResultWriter(output) as writer:
            await writer.write_ticket(make_resolved_ticket())
        with open(output, newline="") as f:
            rows = list(csv.reader(f))
        fecha_asignacion = rows[1][4]
        assert len(fecha_asignacion) > 8  # "HH:MM:SS" son 8 chars — con fecha son más

    @pytest.mark.asyncio
    async def test_multiple_tickets_written(self, tmp_path):
        output = tmp_path / "out.csv"
        async with ResultWriter(output) as writer:
            await writer.write_ticket(make_resolved_ticket(id=1))
            await writer.write_ticket(make_resolved_ticket(id=2))
            await writer.write_ticket(make_resolved_ticket(id=3))
        with open(output, newline="") as f:
            rows = list(csv.reader(f))
        assert len(rows) == 4  # 1 header + 3 tickets


class TestRowsWrittenCounter:
    @pytest.mark.asyncio
    async def test_counter_increments_per_ticket(self, tmp_path):
        output = tmp_path / "out.csv"
        async with ResultWriter(output) as writer:
            await writer.write_ticket(make_resolved_ticket(id=1))
            await writer.write_ticket(make_resolved_ticket(id=2))
        assert writer.rows_written == 2


class TestValidation:
    @pytest.mark.asyncio
    async def test_raises_on_unresolved_ticket(self, tmp_path):
        output = tmp_path / "out.csv"
        unresolved = Ticket(id=1, fecha_creacion=FECHA, prioridad=2)
        async with ResultWriter(output) as writer:
            with pytest.raises(ValueError, match="not been resolved"):
                await writer.write_ticket(unresolved)
