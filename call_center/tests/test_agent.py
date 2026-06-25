from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

import pytest

from call_center.models.agent import Agent
from call_center.models.ticket import Ticket

FECHA = datetime(2024, 1, 1, 9, 0)


@pytest.fixture
def ticket() -> Ticket:
    return Ticket(id=1, fecha_creacion=FECHA, prioridad=2)


@pytest.fixture
def agent() -> Agent:
    return Agent(agent_id=1)


@pytest.mark.asyncio
async def test_attend_returns_resolved_ticket(agent, ticket):
    with patch("call_center.models.agent.asyncio.sleep"):
        resolved = await agent.attend(ticket)
    assert resolved.is_resolved


@pytest.mark.asyncio
async def test_attend_does_not_mutate_original(agent, ticket):
    with patch("call_center.models.agent.asyncio.sleep"):
        await agent.attend(ticket)
    assert ticket.agente is None
    assert ticket.fecha_asignacion is None
    assert ticket.fecha_resolucion is None


@pytest.mark.asyncio
async def test_attend_sets_correct_agent_id(agent, ticket):
    with patch("call_center.models.agent.asyncio.sleep"):
        resolved = await agent.attend(ticket)
    assert resolved.agente == agent.id


@pytest.mark.asyncio
async def test_attend_sets_assignment_timestamp(agent, ticket):
    with patch("call_center.models.agent.asyncio.sleep"):
        resolved = await agent.attend(ticket)
    assert resolved.fecha_asignacion is not None


@pytest.mark.asyncio
async def test_attend_resolution_not_before_assignment(agent, ticket):
    with patch("call_center.models.agent.asyncio.sleep"):
        resolved = await agent.attend(ticket)
    assert resolved.fecha_resolucion >= resolved.fecha_asignacion


@pytest.mark.asyncio
async def test_attend_increments_resolved_counter(agent, ticket):
    with patch("call_center.models.agent.asyncio.sleep"):
        await agent.attend(ticket)
    assert agent.tickets_resolved == 1


@pytest.mark.asyncio
async def test_attend_multiple_tickets_accumulates_counter(agent):
    tickets = [Ticket(id=i, fecha_creacion=FECHA, prioridad=1) for i in range(1, 4)]
    with patch("call_center.models.agent.asyncio.sleep"):
        for t in tickets:
            await agent.attend(t)
    assert agent.tickets_resolved == 3
