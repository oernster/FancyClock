"""Install / upgrade / reinstall operations."""

from __future__ import annotations

import logging
import shutil
import sys
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from fancyclock.version import APP_DISPLAY_NAME
from installer.constants import InstallerIdentity
from installer.ops.desktop_integration import (
    APP_EXE_NAME,
    apply_autostart,
    apply_shortcuts,
    deploy_runtime_icon_assets,
    register_uninstall,
)
from installer.ops.errors import AppRunningError, InstallerOperationError
from installer.ops.payload import payload_zip_path
from installer.ops.running_app import is_app_running

logger = logging.getLogger("installer.install")

# Hex characters of a random id appended to the folder an existing install is
# moved aside to, enough to never collide with an earlier leftover.
BACKUP_SUFFIX_HEX_CHARS = 8


def _progress(progress, *, pct: int | None, message: str) -> None:  # noqa: ANN001
    if not progress:
        return
    if pct is None:
        progress(message)
    else:
        progress({"pct": int(pct), "message": message})


ProgressCb = Callable[[str], None]


@dataclass(frozen=True, slots=True)
class InstallOptions:
    target_dir: Path
    create_desktop_shortcut: bool
    create_start_menu_shortcut: bool
    start_on_signin: bool = False


def _extract_payload_to(
    staging_dir: Path, *, progress=None, cancel_event=None
) -> None:  # noqa: ANN001
    staging_dir.mkdir(parents=True, exist_ok=True)
    _check_cancel(cancel_event)
    _progress(progress, pct=10, message="Extracting payload...")
    logger.info("Extracting payload to %s", staging_dir)
    with zipfile.ZipFile(payload_zip_path(), "r") as zf:
        zf.extractall(staging_dir)

    _check_cancel(cancel_event)

    exe = staging_dir / APP_EXE_NAME
    internal = staging_dir / "_internal"
    if not exe.exists() or not internal.exists():
        raise InstallerOperationError(
            f"Payload is missing {APP_EXE_NAME} or _internal/"
        )


def _move_aside(target_dir: Path) -> Path | None:
    """Rename an existing install out of the way; None when there is none."""
    if not target_dir.exists():
        return None
    suffix = uuid.uuid4().hex[:BACKUP_SUFFIX_HEX_CHARS]
    backup_dir = target_dir.with_name(f"{target_dir.name}.old.{suffix}")
    try:
        target_dir.rename(backup_dir)
    except OSError as exc:
        # A locked file, a permission refusal or a vanished volume all arrive
        # as OSError, all meaning the same thing to the user: the existing
        # install cannot be moved aside, so stop before anything is touched.
        raise InstallerOperationError(
            f"Unable to replace existing install at {target_dir}. Close any "
            "program using files in that folder and run setup again."
        ) from exc
    return backup_dir


def _place_new_bundle(staging_dir: Path, target_dir: Path) -> None:
    try:
        staging_dir.rename(target_dir)
    except OSError:
        # Likely cross-volume move. Copy instead.
        shutil.copytree(staging_dir, target_dir, dirs_exist_ok=False)
        shutil.rmtree(staging_dir, ignore_errors=True)


def _roll_back(
    target_dir: Path, backup_dir: Path | None, exc: Exception
) -> InstallerOperationError:
    """Undo a failed placement and return the error that tells the user.

    Anything at target_dir now was written by the failed placement (the old
    install was moved aside first), so it is removed before the previous
    install goes back. When that cannot be done the backup is left untouched
    and the message says where it is.
    """
    failed = f"Could not put the new files in place at {target_dir} ({exc})"
    shutil.rmtree(target_dir, ignore_errors=True)
    if backup_dir is None:
        return InstallerOperationError(
            f"{failed}. Nothing was installed; run setup again once the cause "
            "is fixed."
        )
    try:
        backup_dir.rename(target_dir)
    except OSError:
        return InstallerOperationError(
            f"{failed}. The previous install could not be moved back; it is "
            f"kept unchanged at {backup_dir}. Rename that folder to "
            f"{target_dir.name} to restore it."
        )
    return InstallerOperationError(
        f"{failed}. The previous install has been put back unchanged; run "
        "setup again once the cause is fixed."
    )


def _swap_in_bundle(staging_dir: Path, target_dir: Path) -> None:
    """Replace target_dir with staging_dir.

    Uses a same-volume rename when possible; falls back to copytree when
    installing across different volumes. The previous install is deleted only
    once the new one is in place; any failure before that restores it or keeps
    it intact and names where it is.
    """

    target_dir = target_dir.resolve()
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Swapping bundle into %s (staging=%s)", target_dir, staging_dir)

    backup_dir = _move_aside(target_dir)
    try:
        _place_new_bundle(staging_dir, target_dir)
    except Exception as exc:  # noqa: BLE001
        # The move and the copy mostly fail as OSError (shutil.Error derives
        # from it) but any failure here must still bring the old install back.
        raise _roll_back(target_dir, backup_dir, exc) from exc
    if backup_dir is not None:
        # The new install is in place, so only now may the previous one go.
        # A file held open inside it leaves the folder behind; the new install
        # still works and the leftover does no harm.
        shutil.rmtree(backup_dir, ignore_errors=True)


def _check_cancel(cancel_event) -> None:  # noqa: ANN001
    if cancel_event is not None and getattr(cancel_event, "is_set", lambda: False)():
        raise InstallerOperationError("Cancelled")


def _copy_self_to_install(identity: InstallerIdentity, install_dir: Path) -> Path:
    install_dir = install_dir.resolve()
    dst = identity.installer_exe_path(install_dir)
    dst.parent.mkdir(parents=True, exist_ok=True)

    src = Path(sys.executable).resolve()
    logger.info("Copying installer from %s to %s", src, dst)
    shutil.copy2(src, dst)
    return dst


def install_new(
    identity: InstallerIdentity,
    opts: InstallOptions,
    *,
    progress=None,
    cancel_event=None,
) -> None:  # noqa: ANN001
    target_dir = opts.target_dir.resolve()

    # Stage in the target's parent directory so we can do an atomic rename when
    # target lives on a non-system drive.
    staging_dir = target_dir.parent / f".fancyclock_staging.install.{uuid.uuid4().hex}"
    if staging_dir.exists():
        shutil.rmtree(staging_dir, ignore_errors=True)

    try:
        _extract_payload_to(staging_dir, progress=progress, cancel_event=cancel_event)
        _progress(progress, pct=45, message="Installing...")

        _check_cancel(cancel_event)
        _swap_in_bundle(staging_dir, target_dir)

        # Make sure icon assets are available next to the installed exe.
        deploy_runtime_icon_assets(install_dir=target_dir)

        _progress(progress, pct=75, message="Registering uninstall entry...")
        _check_cancel(cancel_event)
        logger.info("Registering uninstall entry for %s", target_dir)
        installer_copy = _copy_self_to_install(identity, target_dir)
        register_uninstall(
            identity,
            install_dir=target_dir,
            installer_copy=installer_copy,
            shortcut_desktop=opts.create_desktop_shortcut,
            shortcut_start_menu=opts.create_start_menu_shortcut,
            start_on_signin=opts.start_on_signin,
        )

        _progress(progress, pct=90, message="Creating shortcuts...")
        _check_cancel(cancel_event)
        logger.info("Applying shortcuts")
        apply_shortcuts(
            identity,
            target_dir,
            create_desktop=opts.create_desktop_shortcut,
            create_start_menu=opts.create_start_menu_shortcut,
        )
        apply_autostart(target_dir, opts.start_on_signin)

        _progress(progress, pct=100, message="Completed")
    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir, ignore_errors=True)


def upgrade_or_reinstall(
    identity: InstallerIdentity,
    *,
    current_install_dir: Path,
    opts: InstallOptions,
    progress=None,
    cancel_event=None,
) -> None:
    current_install_dir = current_install_dir.resolve()
    target_dir = opts.target_dir.resolve()

    exe = current_install_dir / APP_EXE_NAME
    if exe.exists() and is_app_running(exe):
        raise AppRunningError(f"{APP_DISPLAY_NAME} is currently running")

    logger.info(
        "Upgrade/reinstall: current=%s target=%s", current_install_dir, target_dir
    )

    staging_dir = target_dir.parent / f".fancyclock_staging.upgrade.{uuid.uuid4().hex}"
    if staging_dir.exists():
        shutil.rmtree(staging_dir, ignore_errors=True)

    try:
        _extract_payload_to(staging_dir, progress=progress, cancel_event=cancel_event)

        _progress(progress, pct=45, message="Replacing application files...")

        _check_cancel(cancel_event)

        if target_dir == current_install_dir:
            _swap_in_bundle(staging_dir, target_dir)
        else:
            # Install to new location, then delete old.
            _swap_in_bundle(staging_dir, target_dir)

            # ignore_errors already swallows every filesystem failure, so the
            # try/except that used to wrap this could never fire. Leaving the
            # old directory behind is the accepted outcome: the new install is
            # already in place and working.
            shutil.rmtree(current_install_dir, ignore_errors=True)

        # Ensure icon assets are present for the active install location.
        deploy_runtime_icon_assets(install_dir=target_dir)

        _progress(progress, pct=75, message="Registering uninstall entry...")
        _check_cancel(cancel_event)
        logger.info("Registering uninstall entry for %s", target_dir)
        installer_copy = _copy_self_to_install(identity, target_dir)
        register_uninstall(
            identity,
            install_dir=target_dir,
            installer_copy=installer_copy,
            shortcut_desktop=opts.create_desktop_shortcut,
            shortcut_start_menu=opts.create_start_menu_shortcut,
            start_on_signin=opts.start_on_signin,
        )

        _progress(progress, pct=90, message="Updating shortcuts...")
        _check_cancel(cancel_event)
        logger.info("Applying shortcuts")
        apply_shortcuts(
            identity,
            target_dir,
            create_desktop=opts.create_desktop_shortcut,
            create_start_menu=opts.create_start_menu_shortcut,
        )
        apply_autostart(target_dir, opts.start_on_signin)

        _progress(progress, pct=100, message="Completed")
    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir, ignore_errors=True)
