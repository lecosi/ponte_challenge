from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime


@dataclass
class Ticket:
    """Represents a support ticket in the call center simulation.

    A ticket is a pure data container. Simulation state (agente,
    fecha_asignacion, fecha_resolucion) starts as None and is
    populated by returning new instances — never by in-place mutation.

    Attributes:
        id: Unique ticket identifier.
        fecha_creacion: Ticket creation timestamp.
        prioridad: Priority level (1 = most urgent, 5 = least urgent).
        agente: ID of the agent who attended this ticket.
        fecha_asignacion: Timestamp when an agent picked up the ticket.
        fecha_resolucion: Timestamp when the agent finished attending.
    """

    id: int
    fecha_creacion: datetime
    prioridad: int

    agente: int | None = field(default=None)
    fecha_asignacion: datetime | None = field(default=None)
    fecha_resolucion: datetime | None = field(default=None)

    def as_unassigned(self) -> Ticket:
        """Return a copy with all simulation state cleared.

        Used before enqueuing a ticket so each simulation run
        starts from a clean slate without mutating the original.
        """
        return replace(self, agente=None, fecha_asignacion=None, fecha_resolucion=None)

    @property
    def is_resolved(self) -> bool:
        """Whether this ticket has been resolved by an agent."""
        return self.fecha_resolucion is not None

    def __lt__(self, other: Ticket) -> bool:
        """Enable priority queue ordering.

        Lower priority number = more urgent = processed first.
        Ties are broken by creation date (earlier first).
        """
        if self.prioridad != other.prioridad:
            return self.prioridad < other.prioridad
        return self.fecha_creacion < other.fecha_creacion
