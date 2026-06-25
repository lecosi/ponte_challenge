from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from call_center.services.csv_reader import TicketReader

HEADER = "id,fecha_creacion,prioridad\n"


def write_csv(path: Path, rows: list[str]) -> Path:
    path.write_text(HEADER + "\n".join(rows), encoding="utf-8")
    return path


class TestStreamValidCSV:
    def test_yields_all_valid_rows(self, tmp_path):
        csv_file = write_csv(tmp_path / "t.csv", [
            "1,2024-01-01 09:00,3",
            "2,2024-01-01 08:00,1",
        ])
        reader = TicketReader(csv_file)
        tickets = list(reader.stream())
        assert len(tickets) == 2
        assert reader.skipped_rows == 0

    def test_preserves_file_order(self, tmp_path):
        csv_file = write_csv(tmp_path / "t.csv", [
            "1,2024-01-01 09:00,5",
            "2,2024-01-01 09:00,1",
            "3,2024-01-01 09:00,3",
        ])
        tickets = list(TicketReader(csv_file).stream())
        assert [t.id for t in tickets] == [1, 2, 3]

    def test_stream_is_lazy(self, tmp_path):
        csv_file = write_csv(tmp_path / "t.csv", [
            "1,2024-01-01 09:00,3",
            "2,2024-01-01 08:00,1",
        ])
        stream = TicketReader(csv_file).stream()
        first = next(stream)
        assert first.id == 1

    def test_can_be_streamed_multiple_times(self, tmp_path):
        csv_file = write_csv(tmp_path / "t.csv", ["1,2024-01-01 09:00,3"])
        reader = TicketReader(csv_file)
        assert len(list(reader.stream())) == 1
        assert len(list(reader.stream())) == 1

    def test_raises_if_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            TicketReader("no_existe.csv").stream()


class TestInvalidRows:
    def test_skips_row_with_missing_columns(self, tmp_path):
        csv_file = write_csv(tmp_path / "t.csv", ["1,2024-01-01 09:00"])
        reader = TicketReader(csv_file)
        tickets = list(reader.stream())
        assert reader.skipped_rows == 1
        assert len(tickets) == 0

    def test_skips_row_with_non_integer_id(self, tmp_path):
        csv_file = write_csv(tmp_path / "t.csv", ["abc,2024-01-01 09:00,3"])
        reader = TicketReader(csv_file)
        list(reader.stream())
        assert reader.skipped_rows == 1

    def test_skips_row_with_zero_id(self, tmp_path):
        csv_file = write_csv(tmp_path / "t.csv", ["0,2024-01-01 09:00,3"])
        reader = TicketReader(csv_file)
        list(reader.stream())
        assert reader.skipped_rows == 1

    def test_skips_row_with_negative_id(self, tmp_path):
        csv_file = write_csv(tmp_path / "t.csv", ["-5,2024-01-01 09:00,3"])
        reader = TicketReader(csv_file)
        list(reader.stream())
        assert reader.skipped_rows == 1

    def test_skips_row_with_bad_date_format(self, tmp_path):
        csv_file = write_csv(tmp_path / "t.csv", ["1,01/01/2024,3"])
        reader = TicketReader(csv_file)
        list(reader.stream())
        assert reader.skipped_rows == 1

    def test_skips_row_with_future_date(self, tmp_path):
        future = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M")
        csv_file = write_csv(tmp_path / "t.csv", [f"1,{future},3"])
        reader = TicketReader(csv_file)
        list(reader.stream())
        assert reader.skipped_rows == 1

    def test_skips_row_with_non_integer_priority(self, tmp_path):
        csv_file = write_csv(tmp_path / "t.csv", ["1,2024-01-01 09:00,alta"])
        reader = TicketReader(csv_file)
        list(reader.stream())
        assert reader.skipped_rows == 1

    def test_skips_row_with_priority_zero(self, tmp_path):
        csv_file = write_csv(tmp_path / "t.csv", ["1,2024-01-01 09:00,0"])
        reader = TicketReader(csv_file)
        list(reader.stream())
        assert reader.skipped_rows == 1

    def test_skips_row_with_negative_priority(self, tmp_path):
        csv_file = write_csv(tmp_path / "t.csv", ["1,2024-01-01 09:00,-1"])
        reader = TicketReader(csv_file)
        list(reader.stream())
        assert reader.skipped_rows == 1

    def test_skips_row_with_priority_above_five(self, tmp_path):
        csv_file = write_csv(tmp_path / "t.csv", ["1,2024-01-01 09:00,6"])
        reader = TicketReader(csv_file)
        list(reader.stream())
        assert reader.skipped_rows == 1

    def test_continues_after_invalid_row(self, tmp_path):
        csv_file = write_csv(tmp_path / "t.csv", [
            "1,2024-01-01 09:00,3",
            "fila_mala",
            "2,2024-01-01 08:00,2",
        ])
        reader = TicketReader(csv_file)
        tickets = list(reader.stream())
        assert len(tickets) == 2
        assert reader.skipped_rows == 1

    def test_counts_multiple_invalid_rows(self, tmp_path):
        future = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M")
        csv_file = write_csv(tmp_path / "t.csv", [
            "1,2024-01-01 09:00,3",
            "abc,2024-01-01 09:00,3",
            f"2,{future},3",
            "3,2024-01-01 09:00,9",
        ])
        reader = TicketReader(csv_file)
        tickets = list(reader.stream())
        assert len(tickets) == 1
        assert reader.skipped_rows == 3
