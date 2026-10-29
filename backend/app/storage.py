"""Protected private object storage backend with SHA-256 verification and short-lived download tokens (PRD §§5.4, 13.2)."""

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import hmac
import os
from pathlib import Path
import secrets
import json
import socket
import struct
import subprocess
import tempfile
from typing import Any
from uuid import UUID

from fastapi import HTTPException


STORAGE_ROOT = Path(__file__).resolve().parents[2] / "storage" / "documents"
def _storage_secret():
    configured = os.environ.get("STORAGE_HMAC_SECRET")
    if configured: return configured
    secret_path = Path(__file__).resolve().parents[2] / ".secrets" / "storage-hmac.key"
    secret_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with secret_path.open("x", encoding="utf-8") as handle: handle.write(secrets.token_urlsafe(48))
    except FileExistsError: pass
    return secret_path.read_text(encoding="utf-8").strip()

SECRET_KEY = _storage_secret()
DEFAULT_EXPIRY_SECONDS = 900  # 15 minutes


ALLOWED_MIME_TYPES = {
    "application/pdf": b"%PDF-",
    "image/png": b"\x89PNG\r\n\x1a\n",
    "image/jpeg": b"\xff\xd8\xff",
}


def ensure_storage_dir() -> Path:
    STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
    return STORAGE_ROOT


def validate_file_content(content: bytes, declared_mime_type: str, max_bytes: int = 50 * 1024 * 1024) -> tuple[str, int]:
    """Validate magic bytes, declared MIME type, and size bounds."""
    size = len(content)
    if size == 0:
        raise HTTPException(status_code=400, detail="File cannot be empty")
    if size > max_bytes:
        raise HTTPException(status_code=400, detail=f"File exceeds maximum allowed size of {max_bytes} bytes")

    if declared_mime_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail=f"MIME type '{declared_mime_type}' is not supported")

    magic = ALLOWED_MIME_TYPES[declared_mime_type]
    if not content.startswith(magic):
        raise HTTPException(status_code=400, detail="File content magic signature does not match declared MIME type")

    checksum = sha256(content).hexdigest()
    return checksum, size


def validate_file_name(file_name: str, mime_type: str) -> str:
    extensions = {"application/pdf": {".pdf"}, "image/png": {".png"}, "image/jpeg": {".jpg", ".jpeg"}}
    if (not file_name or Path(file_name).name != file_name or any(c in file_name for c in '\\/:\r\n\x00')
            or Path(file_name).suffix.lower() not in extensions.get(mime_type, set())):
        raise HTTPException(400, detail="File name must be a safe basename with the matching PDF, PNG or JPEG extension")
    return file_name


def _defender_scan_content(content: bytes) -> dict[str, Any]:
    """Bounded custom scan with remediation disabled; any error stays quarantined.

    Microsoft documents code 0 as success and code 2 as either a threat or an
    error. We deliberately do not call code 2 infected without threat evidence.
    https://learn.microsoft.com/en-us/defender-endpoint/command-line-arguments-microsoft-defender-antivirus
    """
    started = datetime.now(timezone.utc).isoformat()
    platform = Path(os.environ.get("ProgramData", "C:/ProgramData")) / "Microsoft/Windows Defender/Platform"
    candidates = sorted(platform.glob("*/MpCmdRun.exe"), reverse=True)
    candidates.append(Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Windows Defender/MpCmdRun.exe")
    executable = next((p for p in candidates if p.is_file()), None)
    evidence = {"status": "unavailable", "engine": "Microsoft Defender custom scan", "at": started}
    if executable is None:
        return {**evidence, "reason": "Microsoft Defender scanner executable is unavailable"}
    try:
        with tempfile.TemporaryDirectory(prefix="aicte-scan-") as directory:
            source = Path(directory) / "source.bin"
            source.write_bytes(content)
            result = subprocess.run([str(executable), "-Scan", "-ScanType", "3", "-File", str(source), "-DisableRemediation"],
                capture_output=True, text=True, errors="replace", timeout=45,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        # DisableRemediation prevents code 0 from representing a remediated file.
        return {**evidence, "status": "clean" if result.returncode == 0 else "error",
            "exit_code": result.returncode, "result": (result.stdout + result.stderr)[-2000:],
            "remediation_disabled": True, "platform_version": executable.parent.name}
    except (OSError, subprocess.TimeoutExpired) as error:
        return {**evidence, "reason": f"Scanner could not complete: {type(error).__name__}"}


def scan_content(content: bytes) -> dict[str, Any]:
    """Actual ClamAV INSTREAM adapter. An absent scanner never means clean."""
    started = datetime.now(timezone.utc).isoformat()
    host = os.environ.get("CLAMD_HOST")
    engine = os.environ.get("FILE_SCAN_ENGINE", "auto").lower()
    if engine == "defender" or (engine == "auto" and not host and os.name == "nt"):
        return _defender_scan_content(content)
    if not host:
        return {"status": "unavailable", "engine": "ClamAV", "at": started, "reason": "CLAMD_HOST is not configured"}
    try:
        with socket.create_connection((host, int(os.environ.get("CLAMD_PORT", "3310"))), timeout=10) as client:
            client.sendall(b"zINSTREAM\0")
            for offset in range(0, len(content), 65536):
                chunk = content[offset:offset+65536]
                client.sendall(struct.pack("!I", len(chunk)) + chunk)
            client.sendall(struct.pack("!I", 0))
            result = b""
            while len(result) < 4096 and b"\0" not in result:
                part = client.recv(1024)
                if not part: break
                result += part
        reply = result.decode("utf-8", errors="replace").strip("\0\r\n")
        status = "clean" if reply == "stream: OK" else "infected" if reply.endswith(" FOUND") else "error"
        return {"status": status, "engine": "ClamAV INSTREAM", "at": started, "result": reply}
    except (OSError, ValueError):
        return {"status": "unavailable", "engine": "ClamAV", "at": started, "reason": "Scanner connection or protocol failed"}


def store_file(object_key: str, content: bytes) -> str:
    """Store file securely preventing path traversal."""
    root = ensure_storage_dir()
    # Path traversal check
    clean_key = Path(object_key).name
    if not clean_key or clean_key in (".", "..") or "/" in object_key.replace("\\", "/").strip("/").split("/")[:-1]:
        # Subdirectories are allowed if safe
        pass

    target_path = (root / object_key).resolve()
    if not target_path.is_relative_to(root.resolve()):
        raise HTTPException(status_code=400, detail="Invalid object storage path")

    target_path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents a later upload from replacing historical bytes.
    try:
        with target_path.open("xb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError:
        raise HTTPException(409, detail="Immutable object already exists") from None
    evidence = {"sha256": sha256(content).hexdigest(), "size_bytes": len(content), **scan_content(content)}
    try:
        target_path.with_name(target_path.name + ".scan.json").write_text(json.dumps(evidence), encoding="utf-8")
    except OSError:
        target_path.unlink(missing_ok=True)
        raise
    return str(target_path)


def retrieve_file(object_key: str) -> bytes:
    """Read file content safely."""
    root = ensure_storage_dir()
    target_path = (root / object_key).resolve()
    if not target_path.is_relative_to(root.resolve()) or not target_path.is_file():
        raise HTTPException(status_code=404, detail="Requested file not found in storage")
    try:
        evidence = json.loads(target_path.with_name(target_path.name + ".scan.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise HTTPException(423, detail="File is quarantined: no malware scan evidence") from None
    if evidence.get("status") != "clean":
        raise HTTPException(423, detail="File is quarantined pending a successful malware scan")
    content = target_path.read_bytes()
    if sha256(content).hexdigest() != evidence.get("sha256"):
        raise HTTPException(409, detail="Stored file checksum mismatch")
    return content


def file_scan_evidence(object_key: str) -> dict[str, Any]:
    target = (ensure_storage_dir() / object_key).resolve()
    if not target.is_relative_to(STORAGE_ROOT.resolve()): raise HTTPException(400)
    try: return json.loads(target.with_name(target.name + ".scan.json").read_text(encoding="utf-8"))
    except (OSError, ValueError): return {"status": "unavailable"}


def generate_download_token(version_id: UUID, user_id: UUID, expires_in_seconds: int = DEFAULT_EXPIRY_SECONDS) -> tuple[str, datetime]:
    """Generate a tamper-proof short-lived download token using HMAC-SHA256."""
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)
    ts = str(int(expires_at.timestamp()))
    payload = f"{version_id}:{user_id}:{ts}"
    signature = hmac.new(SECRET_KEY.encode("utf-8"), payload.encode("utf-8"), sha256).hexdigest()
    token = f"{ts}.{signature}"
    return token, expires_at


def verify_download_token(version_id: UUID, user_id: UUID, token: str) -> bool:
    """Verify that download token signature is valid and has not expired."""
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return False
        ts_str, signature = parts
        expiry_ts = int(ts_str)
        now_ts = int(datetime.now(timezone.utc).timestamp())
        if now_ts > expiry_ts:
            return False

        expected_payload = f"{version_id}:{user_id}:{ts_str}"
        expected_sig = hmac.new(SECRET_KEY.encode("utf-8"), expected_payload.encode("utf-8"), sha256).hexdigest()
        return hmac.compare_digest(signature, expected_sig)
    except Exception:
        return False
