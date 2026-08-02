"""Text generation for the verbal channel (TODO 4.3).

The provider choice is **private to each peer** (Appendix F Table 21) and is
never negotiated, so everything here is behind one interface: `template` runs
offline at zero tokens, `ollama` runs locally on Itay's machine for graded
matches, `groq` runs on Diana's during development.
"""

from core.infra.llm.base import ProviderError, TextProvider
from core.infra.llm.factory import build_provider, build_writer
from core.infra.llm.template import TemplateProvider
from core.infra.llm.writer import HintWriter, WrittenHint

__all__ = [
    "TextProvider",
    "ProviderError",
    "TemplateProvider",
    "HintWriter",
    "WrittenHint",
    "build_provider",
    "build_writer",
]
