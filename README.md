# AWS Transcribe and Comprehend Workflow

This project provides a Dockerized Python script to manage audio transcription and PII redaction using AWS services. The script handles the following tasks:

1. **Transcribes audio files** from an S3 bucket using AWS Transcribe.
2. **Redacts PII** (Personally Identifiable Information) from the transcriptions using AWS Comprehend.
3. **Saves redacted transcriptions** to a separate S3 bucket.

## Features

- **Concurrency Control:** Limits the number of concurrent transcription jobs.
- **Error Handling:** Includes basic error handling for AWS API calls.
- **Queue Management:** Uses queues to manage transcription and redaction tasks.

## Prerequisites

- **AWS Account:** Ensure you have an AWS account with access to S3, Transcribe, and Comprehend services.
- **AWS Permissions:** `AmazonS3FullAccess`, `AmazonTranscribeFullAccess`, `ComprehendFullAccess`. Attach these permissions to the AWS user with the above credentials
- **Docker:** Make sure Docker is installed on your machine.

## Configuration

1. **Environment Variables:**
   - `AUDIO_INPUT_BUCKET`: S3 bucket containing audio files to transcribe.
   - `AUDIO_TRANSCRIPTION_BUCKET`: S3 bucket where transcriptions will be stored.
   - `AUDIO_TRANSCRIPTION_REDACTION_BUCKET`: S3 bucket for storing redacted transcriptions.
   - `AUDIO_LANGUAGE_SUPPORT`: Comma-separated list of supported languages (default: "en-IN,hi-IN").
   - `THREAD_COUNT`: Number of threads for concurrent processing (default: 4).
   - `MAX_CONCURRENT_JOBS`: Maximum number of concurrent transcription jobs (default: 5).
   - `AWS_ACCESS_KEY_ID`: AWS access key ID.
   - `AWS_SECRET_ACCESS_KEY`: AWS secret access key.
   - `AWS_DEFAULT_REGION`: AWS region (default: "us-east-1").

2. **Dockerfile:**
   - A Dockerfile is provided to build the Docker image for this script.

## Getting Started

### Running docker from Docker Hub

```
docker run -e AUDIO_INPUT_BUCKET=your-input-bucket \
           -e AUDIO_TRANSCRIPTION_BUCKET=your-transcription-bucket \
           -e AUDIO_TRANSCRIPTION_REDACTION_BUCKET=your-redaction-bucket \
           -e AUDIO_LANGUAGE_SUPPORT=en-IN,hi-IN \
           -e THREAD_COUNT=4 \
           -e MAX_CONCURRENT_JOBS=5 \
           -e AWS_ACCESS_KEY_ID=your-access-key-id \
           -e AWS_SECRET_ACCESS_KEY=your-secret-access-key \
           -e AWS_DEFAULT_REGION=us-east-1 \
           rvizsatiz/aws-transcribe-redact:v1
```

### Building and running the Docker Image

```sh
docker build -t aws-transcribe-comprehend .
```

#### Running Docker

```
docker run -e AUDIO_INPUT_BUCKET=your-input-bucket \
           -e AUDIO_TRANSCRIPTION_BUCKET=your-transcription-bucket \
           -e AUDIO_TRANSCRIPTION_REDACTION_BUCKET=your-redaction-bucket \
           -e AUDIO_LANGUAGE_SUPPORT=en-IN,hi-IN \
           -e THREAD_COUNT=4 \
           -e MAX_CONCURRENT_JOBS=5 \
           -e AWS_ACCESS_KEY_ID=your-access-key-id \
           -e AWS_SECRET_ACCESS_KEY=your-secret-access-key \
           -e AWS_DEFAULT_REGION=us-east-1 \
           aws-transcribe-comprehend
```
Replace the environment variables with your actual bucket names, AWS credentials, and configurations.

### Usage

1. Place your audio files in the specified input S3 bucket.
2. Run the Docker container. The script will start transcription jobs for all audio files in the input bucket.
3. Transcriptions will be stored in the specified transcription bucket.
4. The script will then redact PII from the transcriptions and save the redacted files to the redaction bucket.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements, bug fixes, or feature requests.

### Possible improvements:

1. Make reduction optional using parameters.
2. Making queue distributed using redis, rabbitmq or equivalent.

## Contact
For questions or support, vishnu@rootflo.ai
