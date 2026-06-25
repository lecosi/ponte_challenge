from __future__ import annotations

import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Iterator

from call_center.models.ticket import Ticket


logger = logging.getLogger(__name__)


class _InvalidRow(Exception):
    """Raised internally when a CSV row fails validation."""


class TicketReader:
    """Streams and validates tickets from a CSV file.

    Reads the file lazily, one row at a time, yielding valid tickets
    as they are parsed. Nothing is held in memory beyond the current
    row, so a file with millions of records has the same footprint
    as one with a handful.

    Tickets are emitted in file order — the simulation does not depend
    on priority order (see README), so no sorting is performed.

    Expected CSV columns (positional): id, fecha_creacion, prioridad

    Invalid rows are logged and skipped; they never stop the stream.

    Attributes:
        filepath: Path to the source CSV file.
        skipped_rows: Number of rows skipped in the last stream() pass.
    """

    COL_ID = 0
    COL_FECHA_CREACION = 1
    COL_PRIORIDAD = 2

    DATETIME_FORMAT = "%Y-%m-%d %H:%M"
    EXPECTED_COLUMNS = 3
    VALID_PRIORITY_RANGE = range(1, 6)  # 1–5 inclusive

    def __init__(self, filepath: str | Path) -> None:
        self.filepath = Path(filepath)
        self.skipped_rows: int = 0

    def stream(self) -> Iterator[Ticket]:
        """Yield valid tickets from the CSV, one at a time.

        Existence is checked eagerly so a missing file fails fast,
        before any iteration begins. Invalid rows are logged as
        warnings and skipped so a single bad line never aborts the read.

        Returns:
            An iterator over valid Ticket objects, in file order.

        Raises:
            FileNotFoundError: If the CSV file doesn't exist.
        """
        if not self.filepath.exists():
            raise FileNotFoundError(
                f"Tickets file not found: {self.filepath}"
            )
        return self._stream()

    def _stream(self) -> Iterator[Ticket]:
        self.skipped_rows = 0

        with open(self.filepath, newline="", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            next(reader, None)  # skip header row

            for row_num, row in enumerate(reader, start=2):
                ticket = self._parse_row(row, row_num)
                if ticket is not None:
                    yield ticket

        if self.skipped_rows:
            logger.warning(
                "Skipped %d invalid row(s) in %s",
                self.skipped_rows,
                self.filepath.name,
            )

    def _parse_row(self, row: list[str], row_num: int) -> Ticket | None:
        """Parse and validate a single CSV row into a Ticket object.

        Logs a warning and returns None for any row that fails
        validation so the caller can skip it gracefully.

        Args:
            row: List of string values from csv.reader.
            row_num: Row number used in warning messages.

        Returns:
            Parsed Ticket, or None if the row is invalid.
        """
        try:
            return self._build_ticket(row)
        except _InvalidRow as e:
            logger.warning("Row %d skipped — %s", row_num, e)
            self.skipped_rows += 1
            return None

    def _build_ticket(self, row: list[str]) -> Ticket:
        """Parse and validate fields, raising _InvalidRow on any failure."""
        if len(row) < self.EXPECTED_COLUMNS:
            raise _InvalidRow(
                f"expected {self.EXPECTED_COLUMNS} columns, got {len(row)}: {row!r}"
            )

        raw_id = row[self.COL_ID].strip()
        raw_fecha = row[self.COL_FECHA_CREACION].strip()
        raw_prioridad = row[self.COL_PRIORIDAD].strip()

        try:
            ticket_id = int(raw_id)
        except ValueError:
            raise _InvalidRow(f"invalid id {raw_id!r} (must be an integer)")

        if ticket_id <= 0:
            raise _InvalidRow(f"id must be a positive integer, got {ticket_id}")

        try:
            fecha_creacion = datetime.strptime(raw_fecha, self.DATETIME_FORMAT)
        except ValueError:
            raise _InvalidRow(
                f"invalid fecha_creacion {raw_fecha!r} "
                f"(expected format: {self.DATETIME_FORMAT})"
            )

        if fecha_creacion > datetime.now():
            raise _InvalidRow(
                f"fecha_creacion {raw_fecha!r} is in the future"
            )

        try:
            prioridad = int(raw_prioridad)
        except ValueError:
            raise _InvalidRow(f"invalid prioridad {raw_prioridad!r} (must be an integer)")

        if prioridad not in self.VALID_PRIORITY_RANGE:
            raise _InvalidRow(f"prioridad {prioridad} is out of range (expected 1–5)")

        return Ticket(
            id=ticket_id,
            fecha_creacion=fecha_creacion,
            prioridad=prioridad,
        )
