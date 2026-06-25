"""Call center simulation engine.

Orchestrates the ticket processing pipeline using an async
producer-consumer pattern:

    [Ticket stream] → [Queue (FIFO)] → [N Agents] → [CSV Writer]

The queue has a bounded size (backpressure) so that with millions
of tickets, only a controlled number sit in memory at any time.
Fed by a lazy ticket stream, end-to-end memory stays constant
regardless of input size.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Iterable

from call_center.models.agent import Agent
from call_center.models.ticket import Ticket
from call_center.services.csv_writer import ResultWriter


logger = logging.getLogger(__name__)

# Max tickets waiting in the queue at any given time.
QUEUE_MAX_SIZE = 100


class Simulation:
    """Runs a call center simulation with N agents processing tickets.

    Implements a producer-consumer architecture where:
    - A single producer feeds pre-sorted tickets into a bounded queue.
    - N agent workers consume tickets concurrently from the queue.
    - Results are written incrementally to CSV via ResultWriter.

    The bounded queue provides backpressure: if all agents are busy,
    the producer pauses until an agent finishes and frees a slot.

    Attributes:
        num_agents: Number of concurrent agents.
        tickets_resolved: Counter of tickets completed.
    """

    def __init__(
        self,
        tickets: Iterable[Ticket],
        num_agents: int,
        output_path: Path,
    ) -> None:
        """Initialize the simulation.

        Args:
            tickets: Iterable of Ticket objects to process. May be a
                lazy stream (generator) so only a bounded number of
                tickets ever live in memory at once.
            num_agents: Number of concurrent agents to spawn.
            output_path: Path for the results CSV file.
        """
        self._source_tickets = tickets
        self.num_agents = num_agents
        self._output_path = output_path
        self._queue: asyncio.Queue[Ticket | None] = asyncio.Queue(
            maxsize=QUEUE_MAX_SIZE
        )
        self._agents = [Agent(agent_id=i + 1) for i in range(num_agents)]
        self.tickets_resolved = 0

    async def _producer(self) -> None:
        """Feed tickets into the queue as they arrive from the source.

        Pulls from a (possibly lazy) ticket stream and enqueues each
        ticket. With a bounded queue, at most QUEUE_MAX_SIZE tickets
        sit in memory at any time.

        If the queue is full, this coroutine awaits until an agent
        consumes a ticket, providing natural backpressure.
        """
        for ticket in self._source_tickets:
            await self._queue.put(ticket)

        # Put (None) for each agent to signal end of work
        for _ in self._agents:
            await self._queue.put(None)

    async def _agent_worker(
        self, agent: Agent, writer: ResultWriter
    ) -> None:
        """Agent loop: pull tickets from the queue until sentinel.

        Each agent independently pulls the next highest-priority
        ticket, attends it, and writes the result immediately.

        Args:
            agent: The Agent instance running this worker.
            writer: ResultWriter for incremental CSV output.
        """
        while True:
            ticket = await self._queue.get()

            # None is the poison pill — no more tickets
            if ticket is None:
                self._queue.task_done()
                break

            try:
                resolved = await agent.attend(ticket)
                await writer.write_ticket(resolved)
                self.tickets_resolved += 1

                logger.info(
                    "Agent %d resolved ticket %d (priority %d) — %s → %s",
                    agent.id,
                    resolved.id,
                    resolved.prioridad,
                    resolved.fecha_asignacion.strftime("%H:%M:%S"),
                    resolved.fecha_resolucion.strftime("%H:%M:%S"),
                )
            except Exception:
                logger.exception(
                    "Agent %d failed on ticket %d", agent.id, ticket.id
                )
            finally:
                self._queue.task_done()

    async def run(self) -> None:
        """Execute the full simulation.

        Launches one producer and N agent workers concurrently.
        Waits until all tickets have been processed and written.
        """
        start_time = datetime.now()
        logger.info(
            "Starting simulation with %d agents", self.num_agents
        )

        async with ResultWriter(self._output_path) as writer:
            producer = asyncio.create_task(self._producer())
            workers = [
                asyncio.create_task(self._agent_worker(agent, writer))
                for agent in self._agents
            ]

            await asyncio.gather(producer, *workers)

        elapsed = (datetime.now() - start_time).total_seconds()

        logger.info("Simulation complete in %.2f seconds", elapsed)
        logger.info("Tickets resolved: %d", self.tickets_resolved)
        for agent in self._agents:
            logger.info("  %s", agent)
        logger.info("Results written to: %s", self._output_path)