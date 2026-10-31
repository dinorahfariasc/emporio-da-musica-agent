from pathlib import Path

from etl.pipeline import DATA_DIR
from etl.sources import read_csv

FIXTURES = Path(__file__).parents[1] / "fixtures"
PONTA_PORA = "Ponta Por\N{LATIN SMALL LETTER A WITH TILDE}"


def test_crlf_file_without_final_newline_leaves_no_carriage_returns():
    rows = read_csv(FIXTURES / "crlf_customers.csv", [])

    assert [r.values["customer_id"] for r in rows] == ["1", "2", "3"]
    assert not any(v.endswith("\r") for r in rows for v in r.values.values())
    assert rows[0].values["city"] == rows[2].values["city"] == PONTA_PORA


def test_decomposed_text_is_normalized_and_recorded():
    changes: list[str] = []
    rows = read_csv(FIXTURES / "nfd_customers.csv", changes)

    assert rows[0].values["city"] == rows[1].values["city"] == PONTA_PORA
    assert changes == ["nfd_customers.csv:2 city"]


def test_real_customers_have_a_single_ponta_pora():
    rows = read_csv(DATA_DIR / "customers.csv", [])
    cities = [r.values["city"] for r in rows]

    assert len(rows) == 50
    assert {c for c in cities if c.startswith("Ponta")} == {PONTA_PORA}
    assert cities.count(PONTA_PORA) == 6
    assert not any(v.endswith("\r") for r in rows for v in r.values.values())
