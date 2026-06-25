from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from call_center.models.ticket import Ticket

FECHA = datetime(2024, 1, 1, 9, 0)


def make_ticket(id: int = 1, prioridad: int = 3) -> Ticket:
    return Ticket(id=id, fecha_creacion=FECHA, prioridad=prioridad)


def make_attended_ticket(**kwargs) -> Ticket:
    return replace(
        make_ticket(**kwargs),
        agente=1,
        fecha_asignacion=datetime(2024, 1, 1, 10, 0),
        fecha_resolucion=datetime(2024, 1, 1, 10, 2),
    )


class TestTicketState:
    def test_not_resolved_when_fecha_resolucion_is_none(self):
        assert not make_ticket().is_resolved

    def test_resolved_when_fecha_resolucion_is_set(self):
        t = replace(make_ticket(), fecha_resolucion=datetime.now())
        assert t.is_resolved


class TestAsUnassigned:
    def test_clears_simulation_fields(self):
        copy = make_attended_ticket().as_unassigned()
        assert copy.agente is None
        assert copy.fecha_asignacion is None
        assert copy.fecha_resolucion is None

    def test_preserves_base_fields(self):
        original = make_attended_ticket(id=7, prioridad=2)
        copy = original.as_unassigned()
        assert copy.id == 7
        assert copy.prioridad == 2
        assert copy.fecha_creacion == FECHA

    def test_does_not_mutate_original(self):
        original = make_attended_ticket()
        original.as_unassigned()
        assert original.agente == 1


class TestOrdering:
    def test_lower_priority_number_comes_first(self):
        high = Ticket(id=1, fecha_creacion=FECHA, prioridad=1)
        low = Ticket(id=2, fecha_creacion=FECHA, prioridad=5)
        assert high < low

    def test_earlier_date_breaks_priority_tie(self):
        early = Ticket(id=1, fecha_creacion=datetime(2024, 1, 1, 8, 0), prioridad=2)
        late = Ticket(id=2, fecha_creacion=datetime(2024, 1, 1, 10, 0), prioridad=2)
        assert early < late

    def test_sort_respects_priority_then_date(self):
        tickets = [
            Ticket(id=1, fecha_creacion=datetime(2024, 1, 1, 10, 0), prioridad=5),
            Ticket(id=2, fecha_creacion=datetime(2024, 1, 1, 10, 0), prioridad=1),
            Ticket(id=3, fecha_creacion=datetime(2024, 1, 1, 8, 0), prioridad=1),
        ]
        result = sorted(tickets)
        assert [t.id for t in result] == [3, 2, 1]
