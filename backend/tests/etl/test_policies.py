import pytest

from etl.pipeline import DATA_DIR
from etl.policies import EXPECTED_TOC, build_chunks

pytest.importorskip("pypdf")


@pytest.fixture(scope="module")
def chunks():
    return build_chunks(DATA_DIR / "store_policies.pdf")


def test_headings_match_the_expected_toc():
    assert len([k for k in EXPECTED_TOC if "." not in k]) == 10
    assert len([k for k in EXPECTED_TOC if "." in k]) == 18


def test_subsection_4_1(chunks):
    chunk = next(c for c in chunks if c.section == "4.1")
    assert chunk.title == "Direito de Arrependimento (Compras Online)"
    assert chunk.parent_section == "4"
    assert chunk.parent_title == "Política de Trocas e Devoluções"
    assert chunk.breadcrumb.startswith("§4 Política de Trocas e Devoluções > 4.1")
    assert "7 (sete) dias" in chunk.body


def test_no_page_artifacts(chunks):
    for c in chunks:
        assert "Manual de Políticas e Procedimentos" not in c.search_text
        assert "​" not in c.search_text
        assert "Sua música começa aqui" not in c.search_text
        assert "Página " not in c.body


def test_sections_without_subsections_are_single_chunks(chunks):
    for section in ("2", "9", "10"):
        assert [c.section for c in chunks].count(section) == 1
