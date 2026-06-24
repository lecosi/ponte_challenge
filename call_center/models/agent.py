from __future__ import annotations

import asyncio
import random
from dataclasses import replace
from datetime import datetime

from call_center.models.ticket import Ticket


MIN_ATTENTION_SECS = 2
MAX_ATTENTION_SECS = 3


class Agent:
    """Represents a call center agent that processes tickets.

    Each agent runs as an independent async task, pulling tickets
    from a shared queue until no more tickets remain.

    Attributes:
        id: Unique agent identifier.
        tickets_resolved: Counter of tickets completed by this agent.
    """

    def __init__(self, agent_id: int) -> None:
        self.id = agent_id
        self.tickets_resolved: int = 0

    async def attend(self, ticket: Ticket) -> Ticket:
        """Simulate attending a ticket.

        Records assignment time, waits a random duration between
        2 and 3 seconds to simulate work, then records resolution time.

        Does not mutate the incoming ticket — returns a new instance
        with the simulation state populated.

        Args:
            ticket: The unassigned ticket to attend.

        Returns:
            A new Ticket with agente, fecha_asignacion and
            fecha_resolucion populated.
        """
        assigned_at = datetime.now()

        delay = random.uniform(MIN_ATTENTION_SECS, MAX_ATTENTION_SECS)
        await asyncio.sleep(delay)

        self.tickets_resolved += 1
        return replace(
            ticket,
            agente=self.id,
            fecha_asignacion=assigned_at,
            fecha_resolucion=datetime.now(),
        )

    def __repr__(self) -> str:
        return f"Agent(id={self.id}, resolved={self.tickets_resolved})"
