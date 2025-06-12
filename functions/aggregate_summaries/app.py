import os
import boto3
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate

s3 = boto3.client("s3")
OUTPUT_BUCKET = os.environ.get("OUTPUT_BUCKET")


def create_pdf(output_file: str, summaries: list) -> None:
    """Create a PDF file with section summaries."""
    doc = SimpleDocTemplate(output_file, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    for summary in summaries:
        if summary.get("status_code") == 200:
            section_name = summary.get("section_name", "")
            section_summary = summary.get("section_summary", "")
            if section_name:
                story.append(Paragraph(f"<b>{section_name}</b>", styles["Heading1"]))
            if section_summary:
                story.append(Paragraph(section_summary, styles["Normal"]))
    doc.build(story)


def get_output_key(event: dict, request_id: str) -> str:
    """Determine the S3 key for the output PDF."""
    summaries = event.get("summaries", [])
    if summaries and isinstance(summaries, list):
        original_key = summaries[0].get("original_key")
        if original_key and original_key.lower().endswith(".pdf"):
            return original_key[:-4] + "_summarized.pdf"
    return f"{request_id}_summarized.pdf"


def lambda_handler(event, context):
    """Main Lambda function handler for aggregating section summaries and saving PDF to S3."""
    summaries = event.get("summaries", [])
    output_file = "/tmp/aggregated_summaries.pdf"
    create_pdf(output_file, summaries)

    bucket = OUTPUT_BUCKET
    if not bucket:
        raise ValueError("OUTPUT_BUCKET environment variable is not set.")

    key = get_output_key(event, context.aws_request_id)

    s3.upload_file(output_file, bucket, key)

    return {"status_code": 200, "s3_bucket": bucket, "s3_key": key}
