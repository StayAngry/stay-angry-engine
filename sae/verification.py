"""Ground-truth verification engine."""

from enum import Enum
from pathlib import Path
from pydantic import BaseModel


class VerificationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


class VerificationResult(BaseModel):
    status: VerificationStatus
    message: str
    checked_path: str | None = None


class VerificationEngine:
    @staticmethod
    def verify_directory_exists(target_path: Path) -> VerificationResult:
        if not target_path.exists():
            return VerificationResult(
                status=VerificationStatus.FAIL,
                message=f"Directory does not exist at {target_path}",
                checked_path=str(target_path)
            )
        if not target_path.is_dir():
            return VerificationResult(
                status=VerificationStatus.FAIL,
                message=f"Path exists but is not a directory: {target_path}",
                checked_path=str(target_path)
            )
        return VerificationResult(
            status=VerificationStatus.PASS,
            message="Directory presence verified.",
            checked_path=str(target_path)
        )

    @staticmethod
    def verify_file_content(target_path: Path, expected_content: str | None = None) -> VerificationResult:
        if not target_path.exists():
            return VerificationResult(
                status=VerificationStatus.FAIL,
                message=f"File does not exist at {target_path}",
                checked_path=str(target_path)
            )
        if not target_path.is_file():
            return VerificationResult(
                status=VerificationStatus.FAIL,
                message=f"Path is not a regular file: {target_path}",
                checked_path=str(target_path)
            )

        if expected_content is not None:
            try:
                actual = target_path.read_text(encoding="utf-8")
                if expected_content in actual:
                    return VerificationResult(
                        status=VerificationStatus.PASS,
                        message="File exists and expected content verified.",
                        checked_path=str(target_path)
                    )
                else:
                    return VerificationResult(
                        status=VerificationStatus.FAIL,
                        message="File content did not match expected payload.",
                        checked_path=str(target_path)
                    )
            except Exception as e:
                return VerificationResult(
                    status=VerificationStatus.FAIL,
                    message=f"Could not read file for verification: {e}",
                    checked_path=str(target_path)
                )

        return VerificationResult(
            status=VerificationStatus.PASS,
            message="File presence and readability verified.",
            checked_path=str(target_path)
        )

    @staticmethod
    def verify_path_deleted(target_path: Path) -> VerificationResult:
        if target_path.exists():
            return VerificationResult(
                status=VerificationStatus.FAIL,
                message=f"Path still exists on disk: {target_path}",
                checked_path=str(target_path)
            )
        return VerificationResult(
            status=VerificationStatus.PASS,
            message="Path deletion verified successfully.",
            checked_path=str(target_path)
        )