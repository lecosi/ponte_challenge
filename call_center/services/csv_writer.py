from __future__ import annotations

import csv
from pathlib import Path

from call_center.models.ticket import Ticket


class ResultWriter:
    """Writes resolved tickets to CSV incrementally.

    Uses a context manager pattern to handle file lifecycle.
    Each ticket is written as soon as it is resolved, keeping
    memory usage constant regardless of how many tickets are processed.

    Attributes:
        filepath: Path where the output CSV will be written.

    Usage:
        async with ResultWriter("output.csv") as writer:
            await writer.write_ticket(resolved_ticket)
    """

    OUTPUT_COLUMNS = [
        "id",
        "fecha_creacion",
        "prioridad",
        "agente",
        "fecha_asignacion",
        "fecha_resolucion",
    ]

    DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

    def __init__(self, filepath: str | Path) -> None:
        self.filepath = Path(filepath)
        self._file = None
        self._writer: csv.writer | None = None
        self._rows_written: int = 0

    async def __aenter__(self) -> ResultWriter:
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        self._file = open(
            self.filepath, mode="w", newline="", encoding="utf-8"
        )
        self._writer = csv.writer(self._file)
        self._writer.writerow(self.OUTPUT_COLUMNS)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._file:
            self._file.close()

    async def write_ticket(self, ticket: Ticket) -> None:
        """Write a single resolved ticket to the CSV.

        asyncio is single-threaded: writerow() never yields, so no
        lock is needed to prevent interleaving between agent coroutines.

        Args:
            ticket: A resolved ticket with all fields populated.

        Raises:
            ValueError: If the ticket hasn't been resolved yet.
        """
        if not ticket.is_resolved:
            raise ValueError(f"Ticket {ticket.id} has not been resolved")

        self._writer.writerow([
            ticket.id,
            ticket.fecha_creacion.strftime(self.DATETIME_FORMAT),
            ticket.prioridad,
            ticket.agente,
            ticket.fecha_asignacion.strftime(self.DATETIME_FORMAT),
            ticket.fecha_resolucion.strftime(self.DATETIME_FORMAT),
        ])
        self._rows_written += 1
        # Flush every 500 rows so data reaches disk periodically
        # without paying a syscall per ticket (critical at scale).
        if self._rows_written % 500 == 0:
            self._file.flush()

    @property
    def rows_written(self) -> int:
        """Number of tickets written to the CSV so far."""
        return self._rows_written
