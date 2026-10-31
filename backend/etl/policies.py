"""Store policy manual -> searchable chunks (research R6)."""

import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

from app.text import nfc

HEADING = re.compile(r"^(\d{1,2})(?:\.(\d))?\.?\s+(\S.*)$")
PAGE_HEADER = "Empório da Música Manual de Políticas e Procedimentos"
PAGE_FOOTER = re.compile(r"^(Página \d+|Empório da Música — Sua música começa aqui\..*)$")
COLUMN_GAP = re.compile(r" {3,}")

EXPECTED_TOC: dict[str, str] = {
    "1": "Sobre a Empório da Música",
    "1.1": "Missão",
    "1.2": "Dados da Empresa",
    "2": "Horário de Funcionamento",
    "3": "Formas de Pagamento",
    "3.1": "Regras de Parcelamento",
    "4": "Política de Trocas e Devoluções",
    "4.1": "Direito de Arrependimento (Compras Online)",
    "4.2": "Trocas por Defeito",
    "4.3": "Trocas por Preferência",
    "4.4": "Itens Não Elegíveis para Troca",
    "5": "Política de Frete e Entregas",
    "5.1": "Entregas na Região Metropolitana de Campo Grande",
    "5.2": "Entregas para Outras Cidades",
    "5.3": "Código de Rastreamento",
    "6": "Promoções e Descontos",
    "6.1": "Tipos de Promoção",
    "6.2": "Regras de Promoções",
    "7": "Atendimento via WhatsApp",
    "7.1": "Diretrizes de Atendimento",
    "7.2": "Fluxo de Atendimento Padrão",
    "7.3": "Situações Especiais",
    "8": "Garantia",
    "8.1": "Garantia Legal",
    "8.2": "Garantia do Fabricante",
    "8.3": "O que Não Cobre a Garantia",
    "9": "Privacidade e Proteção de Dados",
    "10": "Disposições Finais",
}


class PolicyParseError(Exception):
    pass


@dataclass(frozen=True)
class PolicyChunk:
    chunk_id: int
    section: str
    title: str
    parent_section: str | None
    parent_title: str | None
    breadcrumb: str
    body: str
    search_text: str


def _clean_lines(pdf_path: Path) -> list[str]:
    reader = PdfReader(pdf_path)
    lines: list[str] = []
    for page in reader.pages[1:]:  # page 1 is the cover
        for raw in page.extract_text(extraction_mode="layout").splitlines():
            line = nfc(raw).rstrip()
            if line.strip() == PAGE_HEADER or PAGE_FOOTER.match(line.strip()):
                continue
            lines.append(line)
    return lines


_ITEM = re.compile(r"^(•|\d+\.)\s+(.*)$")


def _paragraphs(lines: list[str]) -> str:
    """Joins wrapped lines; list items and table rows keep their own line."""
    out: list[str] = []
    wrappable = False  # whether out[-1] may absorb a continuation line
    for line in lines:
        text = line.strip()
        if not text:
            wrappable = False
            continue
        item = _ITEM.match(text)
        if item:
            out.append(f"{item.group(1)} {item.group(2)}")
            wrappable = True
        elif COLUMN_GAP.search(text):
            out.append(COLUMN_GAP.sub(" | ", text))
            wrappable = False
        elif wrappable:
            out[-1] += " " + text
        else:
            out.append(text)
            wrappable = True
    return "\n".join(out)


def build_chunks(pdf_path: Path) -> list[PolicyChunk]:
    sections: list[tuple[str, str, list[str]]] = []
    for line in _clean_lines(pdf_path):
        match = None if line[:1].isspace() else HEADING.match(line)
        if match:
            number = match.group(1) + (f".{match.group(2)}" if match.group(2) else "")
            sections.append((number, match.group(3).strip(), []))
        elif sections:
            sections[-1][2].append(line)
    found = {number: title for number, title, _ in sections}
    if [n for n, _, _ in sections] != list(EXPECTED_TOC) or found != EXPECTED_TOC:
        raise PolicyParseError(
            f"policy headings do not match the expected table of contents: {list(found)}"
        )

    chunks: list[PolicyChunk] = []
    for number, title, body_lines in sections:
        body = _paragraphs(body_lines)
        if not body:
            continue
        parent = number.split(".")[0] if "." in number else None
        parent_title = EXPECTED_TOC[parent] if parent else None
        if parent:
            breadcrumb = f"§{parent} {parent_title} > {number} {title}"
        else:
            breadcrumb = f"§{number} {title}"
        chunks.append(
            PolicyChunk(
                chunk_id=len(chunks) + 1,
                section=number,
                title=title,
                parent_section=parent,
                parent_title=parent_title,
                breadcrumb=breadcrumb,
                body=body,
                search_text=f"{breadcrumb}\n{body}",
            )
        )
    return chunks
