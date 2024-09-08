import boto3
import json
import time
import os
import uuid
from botocore.exceptions import ClientError
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
import threading

load_dotenv()

# Initialize clients
s3 = boto3.client('s3')
transcribe = boto3.client('transcribe')
comprehend = boto3.client('comprehend')

# Configuration
input_bucket = os.getenv("AUDIO_INPUT_BUCKET")
transcription_bucket = os.getenv("AUDIO_TRANSCRIPTION_BUCKET")
redaction_bucket = os.getenv("AUDIO_TRANSCRIPTION_REDACTION_BUCKET")
language_support = os.getenv("AUDIO_LANGUAGE_SUPPORT", "en-IN,hi-IN").split(",")
thread_count = int(os.getenv("THREAD_COUNT", "4"))
max_parallel_jobs = int(os.getenv("MAX_PARALLEL_JOBS", "5"))

# Queues
audio_file_queue = Queue()
transcription_queue = Queue()
redaction_queue = Queue()

# Flags for termination
all_files_processed = threading.Event()
all_transcriptions_complete = threading.Event()
all_redactions_complete = threading.Event()

# Counter for completed jobs
completed_jobs = 0
jobs_lock = threading.Lock()

def list_files(bucket):
    """List all files in an S3 bucket."""
    response = s3.list_objects_v2(Bucket=bucket)
    if 'Contents' in response:
        return [item['Key'] for item in response['Contents']]
    return []

def generate_unique_job_name():
    """Generate a unique job name using UUID."""
    return f"job-{uuid.uuid4().hex[:8]}"

def start_transcription_job(audio_file_key):
    """Start a transcription job for a single audio file."""
    job_name = generate_unique_job_name()
    audio_file_uri = f's3://{input_bucket}/{audio_file_key}'
    try:
        transcribe.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={'MediaFileUri': audio_file_uri},
            MediaFormat='mp3',
            IdentifyLanguage=True,
            LanguageOptions=language_support,
            OutputBucketName=transcription_bucket,
            Settings={
                'ShowSpeakerLabels': True,
                'MaxSpeakerLabels': 2
            }
        )
        print(f'Started transcription job {job_name} for {audio_file_key}')
        transcription_queue.put(job_name)
    except ClientError as e:
        print(f'Error starting transcription job for {audio_file_key}: {e}')

def manage_transcription_jobs():
    """Manage the starting of transcription jobs."""
    while not all_files_processed.is_set() or not audio_file_queue.empty():
        if transcription_queue.qsize() < max_parallel_jobs and not audio_file_queue.empty():
            audio_file_key = audio_file_queue.get()
            start_transcription_job(audio_file_key)
            audio_file_queue.task_done()
        else:
            time.sleep(5)
    print("All transcription jobs have been started.")

def check_transcription_job_status():
    """Worker to check the status of transcription jobs."""
    global completed_jobs
    while not all_files_processed.is_set() or not transcription_queue.empty():
        try:
            job_name = transcription_queue.get(timeout=5)
            while True:
                response = transcribe.get_transcription_job(TranscriptionJobName=job_name)
                status = response['TranscriptionJob']['TranscriptionJobStatus']
                if status == 'COMPLETED':
                    print(f'Transcription job {job_name} completed.')
                    redaction_queue.put(job_name)
                    with jobs_lock:
                        completed_jobs += 1
                    break
                elif status == 'FAILED':
                    print(f'Transcription job {job_name} failed.')
                    with jobs_lock:
                        completed_jobs += 1
                    break
                print(f'Transcription job {job_name} is {status}. Waiting...')
                time.sleep(30)
            transcription_queue.task_done()
        except Empty:
            continue
    print("All transcription jobs have been processed.")

def get_transcription_result(job_name):
    """Retrieve transcription result from S3."""
    try:
        response = s3.get_object(Bucket=transcription_bucket, Key=f'{job_name}.json')
        body = response['Body'].read()
        content = body.decode('utf-8')
        transcript_text = json.loads(content)
        timeline = []
        segments = transcript_text['results']['items']
        language = transcript_text['results']['language_code']
        for segment in segments:
            if 'alternatives' in segment:
                for alt in segment['alternatives']:
                    if 'content' in alt:
                        timeline.append({
                            'text': alt['content'],
                            'start_time': segment.get('start_time', '0.0'),
                            'end_time': segment.get('end_time', '0.0'),
                            'speaker': segment.get('speaker_label', 'Speaker')
                        })
        return timeline, language
    except ClientError as e:
        print(f'Error retrieving transcription result for {job_name}: {e}')
        return None, None

def detect_pii_entities(timeline, language):
    """Detect PII entities in the text using Amazon Comprehend."""
    try:
        dialogues = [x['text'] for x in timeline]
        concat = " ".join(dialogues)
        removed_pii = remove_pii(concat, language)
        redacted = removed_pii.split()
        index = 0
        for item in timeline:
            words = item['text'].split()
            item['text'] = " ".join(redacted[index:index+len(words)])
            index += len(words)
        return timeline
    except ClientError as e:
        print(f'Error detecting PII entities: {e}')
        return []

def remove_pii(text, language):
    response = comprehend.detect_pii_entities(
        Text=text,
        LanguageCode=language 
    )
    for entity in sorted(response['Entities'], key=lambda x: x['BeginOffset'], reverse=True):
        start = entity['BeginOffset']
        end = entity['EndOffset']
        pii_type = entity['Type']
        
        if pii_type != "DATE_TIME":
            text = text[:start] + f'[REDACTED: {pii_type}]' + text[end:]
    return text

def redact_and_save_transcriptions():
    """Worker to read transcriptions, redact PII, and save to the redaction bucket."""
    global completed_jobs
    total_jobs = 0
    while not all_transcriptions_complete.is_set() or not redaction_queue.empty():
        try:
            job_name = redaction_queue.get(timeout=5)
            print(f"Processing redaction for job: {job_name}")
            transcription_timeline, language = get_transcription_result(job_name)
            if transcription_timeline and len(transcription_timeline) > 0:
                redacted_tl = detect_pii_entities(transcription_timeline, "en")
                redacted_key = f'redacted_{job_name}.json'
                s3.put_object(Bucket=redaction_bucket, Key=redacted_key, Body=json.dumps(redacted_tl))
                print(f'Saved redacted transcription to {redacted_key}')
                total_jobs += 1
            else:
                print(f"No transcription timeline found for job: {job_name}")
            redaction_queue.task_done()
        except Empty:
            if all_transcriptions_complete.is_set() and total_jobs == completed_jobs:
                break
            print("Redaction queue is empty, waiting...")
            continue
        except Exception as e:
            print(f"Error in redaction process: {e}")
    all_redactions_complete.set()
    print("All redactions have been completed.")

if __name__ == "__main__":
    # Populate the audio file queue
    audio_files = list_files(input_bucket)
    total_jobs = len(audio_files)
    for audio_file in audio_files:
        audio_file_queue.put(audio_file)
    
    # Thread pool executor for concurrency
    with ThreadPoolExecutor(max_workers=thread_count) as executor:
        # Start job management
        executor.submit(manage_transcription_jobs)
        
        # Start transcription status checkers
        for _ in range(int(thread_count/2)):
            executor.submit(check_transcription_job_status)
        
        # Start redaction workers
        for _ in range(int(thread_count/2)):
            executor.submit(redact_and_save_transcriptions)
        
        # Wait for all audio files to be processed
        audio_file_queue.join()
        all_files_processed.set()
        print("All files have been processed.")
        
        # Wait for all transcriptions to complete
        transcription_queue.join()
        all_transcriptions_complete.set()
        print("All transcriptions have been completed.")
        
        # Wait for all redactions to complete
        redaction_queue.join()
        print("All redactions have been completed.")

    # Wait for all flags to be set
    all_files_processed.wait()
    all_transcriptions_complete.wait()
    all_redactions_complete.wait()

    print(f"Total jobs processed: {completed_jobs}")
    print("All tasks completed. Exiting the script.")