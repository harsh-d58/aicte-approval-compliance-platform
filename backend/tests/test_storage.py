"""Unit tests for storage security, magic bytes validation, and download tokens."""

from datetime import datetime, timedelta, timezone
from unittest import TestCase
from unittest.mock import patch
from tempfile import TemporaryDirectory
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID
from uuid import uuid4

from fastapi import HTTPException

from backend.app.storage import (
    generate_download_token,
    retrieve_file,
    store_file,
    validate_file_content,
    verify_download_token,
    _defender_scan_content,
)


class StorageTests(TestCase):
    def setUp(self):
        self.version_id = UUID(int=1)
        self.user_id = UUID(int=2)
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root_patch = patch("backend.app.storage.STORAGE_ROOT", Path(self.temp.name))
        root_patch.start()
        self.addCleanup(root_patch.stop)

    def test_validate_file_content_valid_pdf(self):
        pdf_bytes = b"%PDF-1.4 test document content for aicte approval"
        checksum, size = validate_file_content(pdf_bytes, "application/pdf")
        self.assertEqual(size, len(pdf_bytes))
        self.assertEqual(len(checksum), 64)

    def test_validate_file_content_empty_raises_400(self):
        with self.assertRaises(HTTPException) as ctx:
            validate_file_content(b"", "application/pdf")
        self.assertEqual(ctx.exception.status_code, 400)

    def test_validate_file_content_magic_mismatch_raises_400(self):
        fake_pdf = b"NOT_A_PDF content"
        with self.assertRaises(HTTPException) as ctx:
            validate_file_content(fake_pdf, "application/pdf")
        self.assertEqual(ctx.exception.status_code, 400)

    def test_validate_file_content_unsupported_mime_raises_400(self):
        exe_bytes = b"MZ\x90\x00"
        with self.assertRaises(HTTPException) as ctx:
            validate_file_content(exe_bytes, "application/x-msdownload")
        self.assertEqual(ctx.exception.status_code, 400)

    def test_store_and_retrieve_file(self):
        content = b"%PDF-1.4 test secure store and retrieve"
        key = f"test_{uuid4().hex}.pdf"
        with patch("backend.app.storage.scan_content", return_value={"status": "clean", "engine": "injected unit scanner"}):
            store_file(key, content)
        retrieved = retrieve_file(key)
        self.assertEqual(retrieved, content)

    def test_unavailable_scanner_quarantines_file(self):
        with patch("backend.app.storage.scan_content", return_value={"status": "unavailable"}):
            store_file("unscanned.pdf", b"%PDF-1.4 source")
        with self.assertRaises(HTTPException) as ctx:
            retrieve_file("unscanned.pdf")
        self.assertEqual(ctx.exception.status_code, 423)

    def test_immutable_object_cannot_be_overwritten(self):
        with patch("backend.app.storage.scan_content", return_value={"status": "clean"}):
            store_file("original.pdf", b"%PDF-1.4 original")
            with self.assertRaises(HTTPException) as ctx:
                store_file("original.pdf", b"%PDF-1.4 replacement")
        self.assertEqual(ctx.exception.status_code, 409)
        self.assertEqual(retrieve_file("original.pdf"), b"%PDF-1.4 original")

    def test_checksum_change_rejects_download(self):
        with patch("backend.app.storage.scan_content", return_value={"status": "clean"}):
            stored = store_file("altered.pdf", b"%PDF-1.4 original")
        Path(stored).write_bytes(b"%PDF-1.4 altered")
        with self.assertRaises(HTTPException) as ctx:
            retrieve_file("altered.pdf")
        self.assertEqual(ctx.exception.status_code, 409)

    def test_defender_scan_error_is_never_clean(self):
        with patch("backend.app.storage.Path.is_file", return_value=True), \
             patch("backend.app.storage.subprocess.run", return_value=SimpleNamespace(returncode=2, stdout="Scanner failed", stderr="")):
            result = _defender_scan_content(b"source bytes")
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["exit_code"], 2)

    def test_defender_success_requires_actual_nonremediating_custom_command(self):
        def execute(args, **kwargs):
            self.assertIn("-DisableRemediation", args)
            self.assertEqual(args[args.index("-ScanType") + 1], "3")
            self.assertEqual(Path(args[args.index("-File") + 1]).read_bytes(), b"source bytes")
            self.assertEqual(kwargs["timeout"], 45)
            return SimpleNamespace(returncode=0, stdout="Scan finished", stderr="")
        with patch("backend.app.storage.Path.is_file", return_value=True), \
             patch("backend.app.storage.subprocess.run", side_effect=execute):
            result = _defender_scan_content(b"source bytes")
        self.assertEqual(result["status"], "clean")
        self.assertTrue(result["remediation_disabled"])

    def test_store_file_path_traversal_rejected(self):
        traversal_key = "../../../outside.pdf"
        with self.assertRaises(HTTPException) as ctx:
            store_file(traversal_key, b"%PDF-1.4")
        self.assertEqual(ctx.exception.status_code, 400)

    def test_generate_and_verify_download_token(self):
        token, expires_at = generate_download_token(self.version_id, self.user_id, expires_in_seconds=60)
        self.assertTrue(verify_download_token(self.version_id, self.user_id, token))

        # Rejects wrong user
        other_user = UUID(int=99)
        self.assertFalse(verify_download_token(self.version_id, other_user, token))

        # Rejects wrong version
        other_version = UUID(int=88)
        self.assertFalse(verify_download_token(other_version, self.user_id, token))

        # Rejects tampered token
        tampered = token[:-2] + "ff"
        self.assertFalse(verify_download_token(self.version_id, self.user_id, tampered))

    def test_verify_download_token_expired(self):
        # Generate token with negative expiry
        token, _ = generate_download_token(self.version_id, self.user_id, expires_in_seconds=-10)
        self.assertFalse(verify_download_token(self.version_id, self.user_id, token))
