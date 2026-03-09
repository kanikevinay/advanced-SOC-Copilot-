"""Model file integrity verification for SOC Copilot.

Generates and validates SHA-256 hashes for ML model files to detect
tampering or corruption before loading.
"""

import hashlib
import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

from soc_copilot.core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HASH_MANIFEST_FILENAME = "model_hashes.json"
HASH_ALGORITHM = "sha256"
BUFFER_SIZE = 65536  # 64 KB read chunks

# Files that require integrity verification
REQUIRED_MODEL_FILES = [
    "isolation_forest_v1.joblib",
    "random_forest_v1.joblib",
    "feature_order.json",
    "label_map.json",
]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class IntegrityResult:
    """Result of model integrity verification."""
    is_valid: bool
    verified_files: list[str] = field(default_factory=list)
    failed_files: list[str] = field(default_factory=list)
    missing_files: list[str] = field(default_factory=list)
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Hash computation
# ---------------------------------------------------------------------------

def compute_file_hash(filepath: Path) -> str:
    """Compute SHA-256 hash of a file.
    
    Args:
        filepath: Path to the file
    
    Returns:
        Hex-encoded SHA-256 hash string
    
    Raises:
        FileNotFoundError: If file does not exist
        OSError: If file cannot be read
    """
    hasher = hashlib.new(HASH_ALGORITHM)
    
    with open(filepath, "rb") as f:
        while True:
            data = f.read(BUFFER_SIZE)
            if not data:
                break
            hasher.update(data)
    
    return hasher.hexdigest()


# ---------------------------------------------------------------------------
# Manifest generation (used during build)
# ---------------------------------------------------------------------------

def generate_manifest(models_dir: str | Path) -> dict[str, str]:
    """Generate integrity hash manifest for all model files.
    
    This should be called during the build process to create
    a manifest that is bundled with the application.
    
    Args:
        models_dir: Directory containing model files
    
    Returns:
        Dictionary mapping filename to SHA-256 hash
    
    Raises:
        FileNotFoundError: If models_dir does not exist
    """
    models_path = Path(models_dir)
    if not models_path.exists():
        raise FileNotFoundError(f"Models directory not found: {models_path}")
    
    manifest = {}
    
    for filename in REQUIRED_MODEL_FILES:
        filepath = models_path / filename
        if filepath.exists():
            file_hash = compute_file_hash(filepath)
            manifest[filename] = file_hash
            logger.info(
                "model_hash_generated",
                file=filename,
                hash=file_hash[:16] + "...",
            )
        else:
            logger.warning("model_file_missing_for_manifest", file=filename)
    
    return manifest


def save_manifest(models_dir: str | Path, manifest: Optional[dict[str, str]] = None) -> Path:
    """Generate and save integrity manifest to models directory.
    
    Args:
        models_dir: Directory containing model files
        manifest: Pre-computed manifest (if None, will be generated)
    
    Returns:
        Path to the saved manifest file
    """
    models_path = Path(models_dir)
    
    if manifest is None:
        manifest = generate_manifest(models_path)
    
    manifest_path = models_path / HASH_MANIFEST_FILENAME
    
    manifest_data = {
        "algorithm": HASH_ALGORITHM,
        "files": manifest,
    }
    
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)
    
    logger.info(
        "manifest_saved",
        path=str(manifest_path),
        file_count=len(manifest),
    )
    
    return manifest_path


# ---------------------------------------------------------------------------
# Integrity verification (used at load time)
# ---------------------------------------------------------------------------

def load_manifest(models_dir: str | Path) -> Optional[dict[str, str]]:
    """Load integrity manifest from models directory.
    
    Args:
        models_dir: Directory containing model files and manifest
    
    Returns:
        Dictionary mapping filename to expected hash, or None if manifest missing
    """
    manifest_path = Path(models_dir) / HASH_MANIFEST_FILENAME
    
    if not manifest_path.exists():
        logger.warning("integrity_manifest_missing", path=str(manifest_path))
        return None
    
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return data.get("files", {})
    except (json.JSONDecodeError, OSError) as e:
        logger.error("manifest_load_failed", error=str(e))
        return None


def verify_models(models_dir: str | Path) -> IntegrityResult:
    """Verify integrity of all model files against stored manifest.
    
    If no manifest exists, verification is skipped with a warning
    (first-run scenario).
    
    Args:
        models_dir: Directory containing model files
    
    Returns:
        IntegrityResult with verification details
    """
    models_path = Path(models_dir)
    
    if not models_path.exists():
        return IntegrityResult(
            is_valid=False,
            error=f"Models directory not found: {models_path}",
        )
    
    # Load manifest
    expected_hashes = load_manifest(models_path)
    
    if expected_hashes is None:
        # No manifest — skip verification (first run or dev environment)
        logger.warning(
            "integrity_check_skipped",
            reason="No manifest found. Run build to generate model_hashes.json.",
        )
        return IntegrityResult(
            is_valid=True,
            error="Integrity manifest not found — verification skipped",
        )
    
    result = IntegrityResult(is_valid=True)
    
    for filename, expected_hash in expected_hashes.items():
        filepath = models_path / filename
        
        if not filepath.exists():
            result.missing_files.append(filename)
            result.is_valid = False
            logger.error("model_file_missing", file=filename)
            continue
        
        try:
            actual_hash = compute_file_hash(filepath)
        except OSError as e:
            result.failed_files.append(filename)
            result.is_valid = False
            logger.error("model_hash_failed", file=filename, error=str(e))
            continue
        
        if actual_hash != expected_hash:
            result.failed_files.append(filename)
            result.is_valid = False
            logger.error(
                "model_integrity_violation",
                file=filename,
                expected=expected_hash[:16] + "...",
                actual=actual_hash[:16] + "...",
            )
        else:
            result.verified_files.append(filename)
            logger.info("model_verified", file=filename)
    
    if result.is_valid:
        logger.info(
            "all_models_verified",
            count=len(result.verified_files),
        )
    else:
        result.error = (
            f"Integrity check failed: "
            f"{len(result.failed_files)} tampered, "
            f"{len(result.missing_files)} missing"
        )
        logger.error("integrity_check_failed", details=result.error)
    
    return result
