from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from call_center.models.ticket import Ticket
from call_center.services.simulation_process import Simulation

FECHA = datetime(2024, 1, 1, 9, 0)


def make_tickets(n: int) -> list[Ticket]:
    return [
        Ticket(id=i, fecha_creacion=FECHA, prioridad=(i % 5) + 1)
        for i in range(1, n + 1)
    ]


@pytest.mark.asyncio
async def test_all_tickets_resolved(tmp_path):
    tickets = make_tickets(6)
    with patch("call_center.models.agent.asyncio.sleep"):
        sim = Simulation(tickets=tickets, num_agents=2, output_path=tmp_path / "r.csv")
        await sim.run()
    assert sim.tickets_resolved == 6


@pytest.mark.asyncio
async def test_output_csv_row_count(tmp_path):
    tickets = make_tickets(5)
    output = tmp_path / "r.csv"
    with patch("call_center.models.agent.asyncio.sleep"):
        await Simulation(tickets=tickets, num_agents=3, output_path=output).run()
    with open(output, newline="") as f:
        rows = list(csv.reader(f))
    assert len(rows) == 6  # 1 encabezado + 5 tickets


@pytest.mark.asyncio
async def test_original_tickets_not_mutated(tmp_path):
    tickets = make_tickets(4)
    with patch("call_center.models.agent.asyncio.sleep"):
        await Simulation(tickets=tickets, num_agents=2, output_path=tmp_path / "r.csv").run()
    for t in tickets:
        assert t.agente is None
        assert t.fecha_asignacion is None
        assert t.fecha_resolucion is None


@pytest.mark.asyncio
async def test_multiple_cases_from_same_ticket_list(tmp_path):
    tickets = make_tickets(4)
    for num_agents in [2, 3, 5]:
        output = tmp_path / f"result_{num_agents}.csv"
        with patch("call_center.models.agent.asyncio.sleep"):
            sim = Simulation(tickets=tickets, num_agents=num_agents, output_path=output)
            await sim.run()
        assert sim.tickets_resolved == 4
        assert output.exists()


@pytest.mark.asyncio
async def test_output_csv_has_required_columns(tmp_path):
    tickets = make_tickets(1)
    output = tmp_path / "r.csv"
    with patch("call_center.models.agent.asyncio.sleep"):
        await Simulation(tickets=tickets, num_agents=1, output_path=output).run()
    with open(output, newline="") as f:
        header = next(csv.reader(f))
    assert "id" in header
    assert "agente" in header
    assert "fecha_asignacion" in header
    assert "fecha_resolucion" in header
