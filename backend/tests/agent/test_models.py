import sys

from app.agent.fakes import FakeToolModel
from app.agent.models import chat_model
from app.config import Settings


def test_fake_provider_never_imports_anthropic():
    for name in [m for m in sys.modules if m.startswith("langchain_anthropic")]:
        del sys.modules[name]

    model = chat_model(Settings(_env_file=None), "specialist", script=["hi"])

    assert isinstance(model, FakeToolModel)
    assert not any(m.startswith("langchain_anthropic") for m in sys.modules)
