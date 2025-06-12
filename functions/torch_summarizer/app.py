import re
from typing import Any, Dict, List, Optional
from transformers import pipeline, Pipeline
import concurrent.futures
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_summarizer() -> Pipeline:
    """
    Lazily initializes and returns the summarization pipeline.
    """
    return pipeline(
        "summarization",
        model="./pipes/summarization-model",
        tokenizer="./pipes/summarization-tokenizer",
    )


# Initialize the summarizer once at module load
summarizer: Pipeline = get_summarizer()


def split_text_into_chunks(text: str, max_words: int = 512) -> List[str]:
    """
    Splits text into chunks of approximately max_words words.
    """
    sentences = re.split(r"([.!?])\s+", text)
    if len(sentences) > 1:
        sentences = [
            "".join(pair) for pair in zip(sentences[0::2], sentences[1::2])
        ] + ([sentences[-1]] if len(sentences) % 2 else [])
    chunks = []
    current_chunk = []
    current_tokens = 0

    for sentence in sentences:
        sentence_tokens = len(sentence.split())
        if current_tokens + sentence_tokens > max_words and current_chunk:
            chunks.append(" ".join(current_chunk).strip())
            current_chunk = [sentence]
            current_tokens = sentence_tokens
        else:
            current_chunk.append(sentence)
            current_tokens += sentence_tokens

    if current_chunk:
        chunks.append(" ".join(current_chunk).strip())
    return chunks


def summarize_text(text_chunks: List[str], summarizer: Pipeline) -> str:
    """
    Summarizes a list of text chunks concurrently and concatenates the results in order.
    """
    summaries = [None] * len(text_chunks)
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_idx = {
            executor.submit(summarizer, chunk): idx
            for idx, chunk in enumerate(text_chunks)
        }
        for future in concurrent.futures.as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                result = future.result()
                summaries[idx] = result[0]["summary_text"]
            except Exception as exc:
                logger.error(f"Summarization failed for chunk {idx}: {exc}")
                summaries[idx] = ""
    return " ".join(filter(None, summaries))


def lambda_handler(
    event: Dict[str, Any], context: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Main Lambda function handler for summarizing articles.
    """
    section_name = event.get("section_name")
    section_text = event.get("section_text")
    original_key = event.get("original_key")

    if not isinstance(section_text, str) or not section_text.strip():
        return {
            "summary": {
                "status_code": 400,
                "original_key": original_key,
                "section_name": section_name,
                "section_summary": "",
                "error": "Missing or invalid 'section_text' in event.",
            }
        }

    try:
        max_length = int(summarizer.tokenizer.model_max_length * 0.65)
        text_chunks = split_text_into_chunks(section_text, max_words=max_length)
        summary_text = summarize_text(text_chunks, summarizer)
        response = {
            "status_code": 200,
            "original_key": original_key,
            "section_name": section_name,
            "section_summary": summary_text,
            "error": "",
        }
    except Exception as exc:
        logger.exception("Error during summarization")
        response = {
            "status_code": 500,
            "original_key": original_key,
            "section_name": section_name,
            "section_summary": "",
            "error": "Internal server error.",
        }
    return {"summary": response}
