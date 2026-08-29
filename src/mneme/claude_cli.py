from __future__ import annotations

import argparse
import hashlib
import stat
import sys
from pathlib import Path

from .canonical import canonical_json_bytes
from .claude_activation import (
    ClaudeGlobalActivation,
    ClaudeSyntheticActivationConfig,
)
from .claude_contracts import (
    CLAUDE_GLOBAL_NONCLAIMS,
    ClaudeGlobalProjectionRequest,
    LocalManualWriteAuthorization,
)
from .claude_projection import (
    _reject_ads,
    _reject_control_characters,
    _reject_network_or_uri,
    _reject_strong_private_parts,
    _reject_symlink_chain,
)
from .errors import (
    ClaudeContractError,
    CliInputError,
    RealActivationNotAuthorizedError,
    StoreConflictError,
)
from .records import MemoryRecord
from .store import MemoryStore, _next_head
from .transactions import TransactionProposal


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise CliInputError(message)


def _parser() -> _Parser:
    parser = _Parser(prog="mneme-claude-global")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("verify")
    for name in ("plan", "apply-synthetic", "status"):
        command = commands.add_parser(name)
        command.add_argument("--root", required=True)
        command.add_argument("--execution-mode", default="synthetic_test")
        command.add_argument("--runtime-root")
        command.add_argument("--claude-user-memory")
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        arguments = _parser().parse_args(argv)
        payload = _dispatch(arguments)
        exit_code = 0
    except CliInputError:
        payload = {"reason_codes": ["input_error"], "status": "ERROR"}
        exit_code = 1
    except RealActivationNotAuthorizedError:
        payload = {
            "reason_codes": ["real_activation_not_authorized"],
            "status": "REFUSED",
        }
        exit_code = 2
    except (ClaudeContractError, StoreConflictError):
        payload = {"reason_codes": ["policy_refusal"], "status": "REFUSED"}
        exit_code = 2
    except (OSError, ValueError, TypeError):
        payload = {"reason_codes": ["input_error"], "status": "ERROR"}
        exit_code = 1
    sys.stdout.write(canonical_json_bytes(payload).decode("utf-8") + "\n")
    return exit_code


def _dispatch(arguments: argparse.Namespace) -> dict[str, object]:
    if arguments.command == "verify":
        return {
            "profile": "mneme.claude-global/0.1",
            "real_activation": "NOT_AUTHORIZED",
            "status": "PASS",
        }
    _reject_real_target_overrides(arguments)
    root = Path(arguments.root)
    if arguments.command == "status":
        return _status(root)
    activation, plan, authorization = _synthetic_operation(root)
    if arguments.command == "plan":
        return plan.to_dict()
    if arguments.command == "apply-synthetic":
        return activation.apply_synthetic(plan, authorization).to_dict()
    raise CliInputError("unknown command")


def _reject_real_target_overrides(arguments: argparse.Namespace) -> None:
    if (
        arguments.execution_mode != "synthetic_test"
        or arguments.runtime_root is not None
        or arguments.claude_user_memory is not None
    ):
        raise RealActivationNotAuthorizedError(
            "real target overrides are not authorized in this candidate"
        )


def _synthetic_operation(root: Path):
    record = {
        "record_version": "mneme.memory-record/0.1",
        "record_id": "record:synthetic:activation",
        "record_type": "instruction",
        "scope": {"kind": "global", "subject": "core"},
        "content": {"text": "Synthetic provider-neutral activation memory."},
        "relations": [],
        "provenance": {
            "event_id": "event:synthetic:activation",
            "source_ref": "synthetic:claude-cli",
        },
        "status": "active",
    }
    transaction = TransactionProposal.from_dict(
        {
            "transaction_version": "mneme.transaction/0.1",
            "transaction_id": "transaction:synthetic:activation",
            "expected_source_head": "GENESIS",
            "declared_record_count": 1,
            "record_digests": [MemoryRecord.from_dict(record).digest()],
            "records": [record],
            "authority_ref": "authorization:synthetic:activation",
            "commit_marker": "MNEME_COMMIT/0.1",
        }
    )
    expected_head = _next_head("GENESIS", transaction.digest())
    request = ClaudeGlobalProjectionRequest.sealed(
        {
            "request_version": "mneme.claude-global-projection-request/0.1",
            "request_id": "request:synthetic:activation",
            "expected_source_head": expected_head,
            "route_id": "route://global/tier0",
            "allowed_scope_paths": ["global/core"],
            "required_record_ids": ["record:synthetic:activation"],
            "byte_budget": 16000,
            "target_kind": "claude_code_user_memory_import",
            "projection_ref": "projection:synthetic:activation",
            "not_claimed": list(CLAUDE_GLOBAL_NONCLAIMS),
        }
    )
    authorization = LocalManualWriteAuthorization.sealed(
        {
            "authorization_version": "mneme.local-manual-write-authorization/0.1",
            "authorization_id": "authorization:synthetic:activation",
            "principal_ref": "principal:neo.k",
            "transaction_ref": "transaction:synthetic:activation",
            "transaction_digest": transaction.digest(),
            "expected_source_head": "GENESIS",
            "allowed_scope_paths": ["global/core"],
            "status": "active",
            "source_role": "user",
            "source_user_item_ref": "user-item:synthetic:activation",
            "source_user_item_digest": "e" * 64,
            "not_claimed": list(CLAUDE_GLOBAL_NONCLAIMS),
        }
    )
    activation = ClaudeGlobalActivation()
    plan = activation.plan(
        ClaudeSyntheticActivationConfig(root),
        transaction,
        request,
    )
    return activation, plan, authorization


def _status(root: Path) -> dict[str, object]:
    config = ClaudeSyntheticActivationConfig(root)
    if not root.exists():
        return {
            "claude_memory_readback": "NOT_RUN",
            "real_claude_user_memory": "NOT_TOUCHED",
            "status": "ABSENT",
            "synthetic_root_ref": root.as_uri(),
        }
    _reject_symlink_chain(root, stop=root)
    required = (
        config.store_root / "HEAD",
        config.projection_target,
        config.user_memory_target,
    )
    for path in required:
        _validate_status_path(path, root)
    if not all(path.is_file() for path in required):
        return {
            "claude_memory_readback": "NOT_RUN",
            "real_claude_user_memory": "NOT_TOUCHED",
            "status": "PARTIAL",
            "synthetic_root_ref": root.as_uri(),
        }
    head = MemoryStore(config.store_root).head()
    return {
        "claude_memory_readback": "NOT_RUN",
        "head": head,
        "projection_sha256": _sha256_file(config.projection_target),
        "real_claude_user_memory": "NOT_TOUCHED",
        "status": "PRESENT",
        "synthetic_root_ref": root.as_uri(),
        "user_memory_sha256": _sha256_file(config.user_memory_target),
    }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(65536):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_status_path(path: Path, root: Path) -> None:
    _reject_control_characters(path, label="synthetic status")
    _reject_network_or_uri(path)
    _reject_ads(path)
    _reject_symlink_chain(path, stop=root)
    resolved_root = root.resolve(strict=True)
    resolved = path.resolve(strict=False)
    if not resolved.is_relative_to(resolved_root):
        raise ClaudeContractError("synthetic status path escapes sandbox root")
    _reject_strong_private_parts(resolved)
    if path.exists():
        metadata = path.lstat()
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise ClaudeContractError("synthetic status path must be one regular file")
