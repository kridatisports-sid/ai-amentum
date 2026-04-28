"""
utils/firebase.py
─────────────────
Firebase Admin SDK wrappers for Firestore and Storage.
All heavy I/O runs in thread executors to stay non-blocking.
"""

import os
import asyncio
import logging
import firebase_admin
from firebase_admin import credentials, firestore, storage as fb_storage
from typing import Optional

logger = logging.getLogger("amentum.firebase")

_db    = None
_bucket = None


def _init():
    global _db, _bucket
    if firebase_admin._apps:
        return

    cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "firebase-credentials.json")
    bucket_name = os.getenv("FIREBASE_STORAGE_BUCKET", "")

    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred, {"storageBucket": bucket_name})

    _db     = firestore.client()
    _bucket = fb_storage.bucket()
    logger.info("Firebase initialised. Bucket: %s", bucket_name)


def _get_db():
    _init()
    return _db


def _get_bucket():
    _init()
    return _bucket


# ── Firestore helpers ─────────────────────────────────────────────────────────

async def save_doc(collection: str, doc_id: str, data: dict):
    loop = asyncio.get_event_loop()
    def _write():
        _get_db().collection(collection).document(doc_id).set(data, merge=True)
    await loop.run_in_executor(None, _write)


async def update_doc(collection: str, doc_id: str, data: dict):
    loop = asyncio.get_event_loop()
    def _update():
        _get_db().collection(collection).document(doc_id).update(data)
    await loop.run_in_executor(None, _update)


async def get_doc(collection: str, doc_id: str) -> Optional[dict]:
    loop = asyncio.get_event_loop()
    def _get():
        doc = _get_db().collection(collection).document(doc_id).get()
        return doc.to_dict() if doc.exists else None
    return await loop.run_in_executor(None, _get)


async def query_collection(
    collection: str,
    filters: list = None,
    order_by: str = None,
    limit: int = 50,
) -> list[dict]:
    loop = asyncio.get_event_loop()
    def _query():
        ref = _get_db().collection(collection)
        if filters:
            for field, op, value in filters:
                ref = ref.where(field, op, value)
        if order_by:
            ref = ref.order_by(order_by, direction=firestore.Query.DESCENDING)
        ref = ref.limit(limit)
        return [d.to_dict() for d in ref.stream()]
    return await loop.run_in_executor(None, _query)


# ── Firebase Storage helpers ──────────────────────────────────────────────────

def upload_to_storage(local_path: str, blob_name: str) -> str:
    """Upload a file to Firebase Storage and return its public URL."""
    try:
        bucket = _get_bucket()
        blob   = bucket.blob(blob_name)
        blob.upload_from_filename(local_path)
        blob.make_public()
        logger.debug("Uploaded %s → %s", local_path, blob.public_url)
        return blob.public_url
    except Exception as e:
        logger.error("Storage upload failed for %s: %s", local_path, e)
        return ""
