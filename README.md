# serverless-crammer

A serverless document processing pipeline for PDF text extraction and summarization, built with AWS SAM.

## Overview

This project provides a scalable, event-driven solution for processing PDF documents uploaded to S3. It extracts text, summarizes content using PyTorch models, aggregates results, and sends notifications upon completion.

## Architecture

- **S3 Buckets**:

  - `InputBucket`: Receives PDF uploads, triggers processing.
  - `OutputBucket`: Stores processed and summarized results.

- **State Machine**:  
  Orchestrates the workflow:

  1. Checks if the uploaded file is a PDF.
  2. Extracts text from the PDF.
  3. Splits text into sections and summarizes each section in parallel.
  4. Aggregates summaries.
  5. Sends completion/failure notifications via SNS.

- **Lambda Functions**:

  - `PdfTextExtractorFunction`: Extracts text from PDFs.
  - `TorchSummarizerFunction`: Summarizes text sections using PyTorch (container image).
  - `AggregateSummariesFunction`: Aggregates section summaries and writes to output bucket.

- **Notifications**:
  - SNS topic sends email notifications on completion or failure.

## Deployment Parameters

- `EnvironmentType`: Deployment environment (`dev`, `stage`, `prod`). Default: `dev`.
- `NotificationEmail`: Email address to receive notifications.
- `RetentionDays`: Number of days to retain logs (default: 7).

## How It Works

1. Upload a PDF to the input S3 bucket.
2. An EventBridge rule triggers the Step Functions state machine.
3. The state machine:
   - Validates the file type.
   - Extracts text using Lambda.
   - Summarizes each section in parallel.
   - Aggregates summaries.
   - Publishes a notification to SNS.
4. Results are stored in the output S3 bucket.

## Outputs

- `DocumentProcessingStateMachineArn`: ARN of the Step Functions state machine.
- `InputBucketName`: Name of the input S3 bucket.
- `OutputBucketName`: Name of the output S3 bucket.
- `PdfTextExtractorFunctionArn`: ARN of the PDF text extractor Lambda.
- `TorchSummarizerFunctionArn`: ARN of the summarizer Lambda.
- `AggregateSummariesFunctionArn`: ARN of the aggregator Lambda.

## Requirements

- AWS SAM CLI
- Docker (for building container-based Lambda)
- AWS account with permissions to deploy resources

## Deployment

Before deploying, run the following script to download required model files for the summarizer Lambda:

```bash
pip install -r functions/torch_summarizer/requirements.txt
python functions/torch_summarizer/model_downloader.py
```

This ensures all necessary models are available for the container build.

Then, deploy the stack using AWS SAM:

```bash
sam build
sam deploy --guided
```
