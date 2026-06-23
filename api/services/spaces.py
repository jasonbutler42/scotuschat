"""
DO Spaces upload service.

Provides a boto3 S3 client configured for DigitalOcean Spaces and helpers
for uploading PDF bytes and image bytes to a Spaces bucket.

Used by the Plan 02 file upload route (PIPE-13) and the Phase 12 photo upload
endpoint (PADM-01). Credentials come from api/core/config.py settings fields
(DO Spaces block) — FastAPI service only, never the SvelteKit service.
"""

import io

import boto3

from api.core.config import settings


def get_spaces_client():
    """
    Build a boto3 S3 client pointed at DigitalOcean Spaces.

    Uses the five settings fields added in Phase 7 Plan 01:
    do_spaces_region, do_spaces_endpoint, aws_access_key_id,
    aws_secret_access_key. All default to "" if not set (URL-only path).
    """
    session = boto3.session.Session()
    return session.client(
        "s3",
        region_name=settings.do_spaces_region,
        endpoint_url=settings.do_spaces_endpoint,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )


def upload_pdf_to_spaces(file_bytes: bytes, key: str) -> str:
    """
    Upload PDF bytes to DO Spaces under the given key.

    Returns the key so the caller can store it in admin_jobs.spaces_key.
    """
    client = get_spaces_client()
    client.upload_fileobj(
        io.BytesIO(file_bytes),
        settings.do_spaces_bucket,
        key,
        ExtraArgs={"ContentType": "application/pdf"},
    )
    return key


def upload_photo_to_spaces(file_bytes: bytes, key: str, content_type: str) -> str:
    """Upload image bytes to DO Spaces under the given key.

    key format: people/{person_id}.{ext}
    content_type: caller-supplied MIME type (e.g. "image/jpeg", "image/png").
    Returns the key so the caller can construct the full public URL.

    Mirrors upload_pdf_to_spaces exactly — same client, same upload_fileobj call —
    except the ContentType ExtraArg is caller-supplied rather than hard-coded.
    No ACL ExtraArg is added (DO Spaces ACL setup is deferred per CONTEXT.md).
    """
    client = get_spaces_client()
    client.upload_fileobj(
        io.BytesIO(file_bytes),
        settings.do_spaces_bucket,
        key,
        ExtraArgs={"ContentType": content_type},
    )
    return key
