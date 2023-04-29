import io
import typing as t

import pdfplumber

from server.lib.truncate import truncate_str


def _clean_sequential_line_numbers_v1(text: str) -> str:
    """Try to find and remove sequential line numbers from a string. v1."""
    # We mostly pass through the text, but we do some cleaning.
    # In particular, we look for lines that start with a number and a space:
    #
    # 1 Some text that goes for a while.
    # 2 Some other text that goes for a while.
    # 3 Yet another text that goes for a while.
    #
    # We want to remove the numbers and the spaces, and remove newlines, so that
    # we get:
    #
    # Some text that goes for a while. Some other text that goes for a while.
    # Yet another text that goes for a while.
    #
    # Importantly, we only do this if the line starts with a number and a space,
    # and we see at least three lines that start with a number and a space. Numbers
    # must be sequential; if we don't see a matching number, we stop.
    #
    # This is primarily useful for ORDINANCE and RESOLUTION documents with
    # line numbers in the gutters.

    lines = text.splitlines()
    cleaned_lines = []

    # If true, we're in a numbered sequence.
    in_sequence = False

    # If in_sequence is true, the next number we expect.
    sequence_number = 0

    # If in_sequence is true, the text we've accumulated so far.
    sequence_line = ""

    # Walk through the lines of the text.
    for i, line in enumerate(lines):
        # If we're not in a sequence...
        if not in_sequence:
            # If this line starts with "1 " or is precisely "1", decide if we
            # should start a sequence by looking at the next two lines to see
            # if they start with "2 " and "3 ". (Be careful not to go out of
            # bounds.)
            if line.startswith("1 ") or line == "1":
                has_2 = i + 1 < len(lines) and (
                    lines[i + 1].startswith("2 ") or lines[i + 1] == "2"
                )
                has_3 = i + 2 < len(lines) and (
                    lines[i + 2].startswith("3 ") or lines[i + 2] == "3"
                )
                if has_2 and has_3:
                    in_sequence = True
                    sequence_number = 2  # we expect this next
                    sequence_line = line[len("1 ") :] if line != "1" else ""
            else:
                # This line doesn't start with "1 ", so just add it to the
                # cleaned lines.
                cleaned_lines.append(line)
        else:
            # We're in a sequence. If this line starts with the next number we
            # expect, add it to the sequence.
            if line.startswith(f"{sequence_number} ") or line == str(sequence_number):
                sequence_line += (
                    " " + line[len(f"{sequence_number} ") :]
                    if line != str(sequence_number)
                    else ""
                )
                sequence_number += 1
            else:
                # We're no longer in a sequence.
                cleaned_lines.append(sequence_line)
                in_sequence = False
                cleaned_lines.append(line)

    if in_sequence:
        cleaned_lines.append(sequence_line)

    return "\n".join(cleaned_lines)


def _clean_headers_footers_v1(text: str) -> str:
    """Clean common headers/footers found in extracted PDF content. v1."""
    # Look for a line that starts with "Template last revised"; if we find it,
    # remove that line and (assuming we don't go out of bounds), the next 3.
    lines = text.splitlines()
    strike_indexes = [
        i for i, line in enumerate(lines) if line.startswith("Template last revised")
    ]
    # Walk through the strike indexes in reverse order so that we don't
    # invalidate the indexes of the lines we're removing.
    for i in reversed(strike_indexes):
        if i + 3 < len(lines):
            del lines[i : i + 4]
    return "\n".join(lines)


def _pdf_clean_v1(text: str) -> str:
    """Clean a string extracted from a PDF using pdfPlumber."""
    text = _clean_sequential_line_numbers_v1(text)
    text = _clean_headers_footers_v1(text)
    return text


def _extract_text_v1(io: io.BytesIO) -> str:
    """Extract text from a text document. Piece of cake!"""
    data = io.read()
    return data.decode("utf-8")


def _extract_pdf_plumber_v1(io: io.BytesIO) -> str:
    """Extract text from a document using pdfPlumber. v1."""
    try:
        with pdfplumber.open(io) as pdf:
            texts = []
            for page in pdf.pages:
                text = page.extract_text()
                text = _pdf_clean_v1(text)
                texts.append(text)
            return "\n".join(texts)
    except Exception as e:
        short_e = truncate_str(str(e), 64)
        return (
            f"Please ignore; we were unable to extract content from the PDF: {short_e}"
        )


def extract_pipeline_v1(io: io.BytesIO, mime_type: str) -> str:
    """Extract text from a document using a pipeline of extractors. v1."""
    if mime_type == "application/pdf":
        return _extract_pdf_plumber_v1(io)
    elif mime_type == "text/plain":
        return _extract_text_v1(io)
    else:
        raise ValueError(f"Unrecognized MIME type {mime_type}.")


@t.runtime_checkable
class ExtractorCallable(t.Protocol):
    __name__: str

    def __call__(self, io: io.BytesIO, mime_type: str) -> str:
        ...


EXTRACTORS: list[ExtractorCallable] = [
    extract_pipeline_v1,
]


EXTRACTORS_BY_NAME: dict[str, ExtractorCallable] = {
    extractor.__name__: extractor for extractor in EXTRACTORS
}
