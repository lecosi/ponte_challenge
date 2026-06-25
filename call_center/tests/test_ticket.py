from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from call_center.models.ticket import Ticket

FECHA = datetime(2024, 1, 1, 9, 0)


def make_ticket(id: int = 1, prioridad: int = 3) -> Ticket:
    return Ticket(id=id, fecha_creacion=FECHA, prioridad=prioridad)


class TestTicketState:
    def test_not_resolved_when_fecha_resolucion_is_none(self):
        assert not make_ticket().is_resolved

    def test_resolved_when_fecha_resolucion_is_set(self):
        t = replace(make_ticket(), fecha_resolucion=datetime.now())
        assert t.is_resolved
