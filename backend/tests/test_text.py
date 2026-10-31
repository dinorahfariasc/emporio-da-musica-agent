from app.text import nfc, normalize_for_cache


def test_nfc_composes_decomposed_text():
    decomposed = "Ponta Pora\N{COMBINING TILDE}"

    assert decomposed != "Ponta Porã"
    assert nfc(decomposed) == "Ponta Porã"


def test_nfc_removes_zero_width_characters():
    assert nfc("•​ O cliente‌‍﻿") == "• O cliente"


def test_normalize_for_cache_collapses_case_and_whitespace():
    assert normalize_for_cache("  Posso  DEVOLVER? ") == "posso devolver?"
