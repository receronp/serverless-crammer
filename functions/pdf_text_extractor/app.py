import re
import io
import boto3
from base64 import b64decode
from urllib.parse import urlparse
from pdfminer.high_level import extract_text
from typing import Dict, List


def lambda_handler(event: dict, context: object) -> dict:
    """Main Lambda function handler for PDF text extraction and processing."""
    try:
        pdf_bytes = get_pdf_bytes(event)
        full_text = extract_pdf_text(pdf_bytes)
        cleaned_text = clean_text(full_text)
        sections_dict = extract_sections_with_paragraphs(cleaned_text)

        return [
            {"section_name": k, "section_text": " ".join(v)}
            for k, v in sections_dict.items()
        ]
    except Exception as e:
        return []


def get_pdf_bytes(event: dict) -> bytes:
    """Extract PDF bytes from different event sources, including S3 event triggers."""
    # Handle direct S3 event (Step Function or EventBridge trigger)
    if (
        "detail" in event
        and "bucket" in event["detail"]
        and "object" in event["detail"]
    ):
        bucket = event["detail"]["bucket"]["name"]
        key = event["detail"]["object"]["key"]
        s3 = boto3.client("s3")
        obj = s3.get_object(Bucket=bucket, Key=key)
        return obj["Body"].read()
    # Handle file_uri (custom event)
    if event.get("file_uri"):
        return get_pdf_from_s3(event["file_uri"])
    # Handle API Gateway/Lambda Proxy with base64
    elif event.get("isBase64Encoded"):
        return b64decode(event["body"])
    # Fallback: treat as raw bytes
    else:
        return event["body"].encode()


def get_pdf_from_s3(s3_uri: str) -> bytes:
    """Download PDF from S3 bucket."""
    parsed = urlparse(s3_uri)
    s3 = boto3.client("s3")
    obj = s3.get_object(Bucket=parsed.netloc, Key=parsed.path.lstrip("/"))
    return obj["Body"].read()


def extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract raw text from PDF bytes."""
    with io.BytesIO(pdf_bytes) as pdf_stream:
        return extract_text(pdf_stream)


def clean_text(text: str) -> str:
    """Clean and normalize extracted text."""
    # Normalize line endings and whitespace
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove newlines between section numbers and headers
    text = re.sub(r"\n+(\d+)\s*\n+([A-Z][A-Za-z0-9 \-\?]{3,})", r"\n\1 \2", text)

    # Remove page numbers and isolated numbers
    text = re.sub(r"^\s*\d+\s*$", "", text, flags=re.MULTILINE)

    # Remove inline footnote markers (e.g., "word.1 " -> "word. ")
    text = re.sub(r"(\w\.)\d+(\s)", r"\1\2", text)

    # Remove figure/table references (e.g., "Figure 1:")
    text = re.sub(r"(Figure|Table)\s+\d+[.:].*?\n", "", text, flags=re.IGNORECASE)

    # Join hyphenated words across line breaks
    text = re.sub(r"(\w+)-\n(\w+)", r"\1\2", text)

    # Normalize multiple spaces and newlines
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def extract_sections_with_paragraphs(text: str) -> Dict[str, List[str]]:
    """
    Extract sections and paragraphs from cleaned text.

    Args:
        text: Cleaned text from PDF

    Returns:
        Dictionary with section titles as keys and lists of paragraphs as values
    """
    # Section header: number(s) + at least 4 non-space chars after
    section_header_regex = re.compile(
        r"^("
        r"(\d{1,2}(\.\d{1,2})*\s+[A-Z][A-Za-z0-9 \-\?]{3,})"
        r"|REFERENCES"
        r"|References"
        r"|APPENDIX(\s+[A-Z])?"
        r"|Appendix(\s+[A-Z])?"
        r")$"
    )

    sections = {}
    current_section = None
    current_paragraph = []

    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue

        # Match section headers (numbered or special)
        if section_header_regex.match(line):
            if current_section and current_paragraph:
                sections[current_section] = current_paragraph
            current_section = line
            current_paragraph = []
            continue

        # Check for paragraph breaks (empty line or significant change in line length)
        if current_paragraph and (
            len(line.split()) < 5
            or len(line) > 100
            and len(current_paragraph[-1]) > 100
        ):
            current_paragraph.append(line)
        else:
            if current_paragraph:
                current_paragraph[-1] += " " + line
            else:
                current_paragraph.append(line)

    if current_section and current_paragraph:
        sections[current_section] = current_paragraph

    return {
        section: merge_paragraphs(paragraphs)
        for section, paragraphs in sections.items()
        if not re.match(r"^(REFERENCES|References|APPENDIX|Appendix)", section)
    }


def merge_paragraphs(paragraphs: List[str]) -> List[str]:
    """Merge fragmented paragraphs and clean up. Disregard short paragraphs."""
    merged = []
    current = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # If current paragraph doesn't end with sentence terminator, merge
        if current and not re.search(r"[.!?]\s*$", current):
            current += " " + para
        else:
            if current:
                merged.append(current)
            current = para

    if current:
        merged.append(current)

    # Additional cleaning and filter out short paragraphs (<40 chars, or <8 words)
    cleaned = []
    for para in merged:
        # Remove leftover footnote markers
        para = re.sub(r"\s+\d+$", "", para)
        # Normalize spaces
        para = re.sub(r"\s+", " ", para).strip()
        # Disregard short paragraphs
        if len(para) < 40 or len(para.split()) < 8:
            continue
        cleaned.append(para)

    return cleaned
