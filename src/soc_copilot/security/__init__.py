"""Security module for SOC Copilot

Provides:
- File permission enforcement (permissions)
- Input validation and path traversal prevention (input_validator)
- ML model integrity verification (model_integrity)
"""

from .permissions import (
    set_secure_file_permissions,
    set_secure_directory_permissions,
    validate_permissions,
    PermissionStatus,
)

from .input_validator import (
    validate_path,
    validate_log_file,
    validate_model_file,
    sanitize_log_line,
    sanitize_filename,
    ValidationResult,
)

from .model_integrity import (
    verify_models,
    generate_manifest,
    save_manifest,
    IntegrityResult,
)

__all__ = [
    # Permissions
    "set_secure_file_permissions",
    "set_secure_directory_permissions",
    "validate_permissions",
    "PermissionStatus",
    # Input validation
    "validate_path",
    "validate_log_file",
    "validate_model_file",
    "sanitize_log_line",
    "sanitize_filename",
    "ValidationResult",
    # Model integrity
    "verify_models",
    "generate_manifest",
    "save_manifest",
    "IntegrityResult",
]
