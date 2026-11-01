import pytest

from app.agent.logging import mask_pii


@pytest.mark.parametrize(
    ("raw", "masked"),
    [
        ("mail ana.silva@jmail.com ok", "mail ***@jmail.com ok"),
        ("(67) 99123-4567", "(**) *****-4567"),
        ("67991234567", "(**) *****-4567"),
        ("+55 67 99123-4567", "(**) *****-4567"),
        ("(67) 3341-4444", "(**) *****-4444"),
    ],
)
def test_masks_emails_and_phones(raw, masked):
    assert mask_pii(raw) == masked


def test_order_numbers_stay():
    assert mask_pii("pedido 1234 e 5") == "pedido 1234 e 5"


def test_masks_a_phone_without_an_area_code():
    assert mask_pii("telefone 99123-4567") == "telefone (**) *****-4567"
