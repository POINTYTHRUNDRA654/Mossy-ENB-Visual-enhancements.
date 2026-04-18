"""
tests/test_enb_optimizer.py
===========================
Unit tests for enb_optimizer.py.

Run with:
    python -m pytest tests/ -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make sure the repo root is on sys.path so we can import enb_optimizer.
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import enb_optimizer  # noqa: E402  (import after path manipulation)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_ini(tmp_path: Path) -> Path:
    """Write a minimal enbseries.ini into a tmp directory and return the path."""
    ini = tmp_path / "enbseries.ini"
    ini.write_text(
        "[GLOBAL]\nUseEffect=true\n\n[SSAO_SSIL]\nEnableAmbientOcclusion=true\nAOType=1\n",
        encoding="utf-8",
    )
    return ini


@pytest.fixture()
def patched_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """
    Redirect enb_optimizer module-level paths to a tmp directory so that
    apply/tune commands don't touch the real repository files.
    """
    dest = tmp_path / "enbseries.ini"
    backup_dir = tmp_path / "backups"

    # Seed a basic active ini
    dest.write_text(
        "[GLOBAL]\nUseEffect=true\n\n[BLOOM]\nEnableBloom=true\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(enb_optimizer, "DEST_INI", dest)
    monkeypatch.setattr(enb_optimizer, "BACKUP_DIR", backup_dir)
    return tmp_path


# ---------------------------------------------------------------------------
# _read_ini / _write_ini round-trip
# ---------------------------------------------------------------------------


class TestReadWriteIni:
    def test_read_preserves_case(self, tmp_ini: Path) -> None:
        cfg = enb_optimizer._read_ini(tmp_ini)
        # configparser lowercases keys by default; we override optionxform.
        assert cfg.has_option("GLOBAL", "UseEffect")

    def test_read_parses_sections(self, tmp_ini: Path) -> None:
        cfg = enb_optimizer._read_ini(tmp_ini)
        assert "GLOBAL" in cfg.sections()
        assert "SSAO_SSIL" in cfg.sections()

    def test_write_round_trip(self, tmp_path: Path, tmp_ini: Path) -> None:
        cfg = enb_optimizer._read_ini(tmp_ini)
        out = tmp_path / "out.ini"
        enb_optimizer._write_ini(cfg, out)
        cfg2 = enb_optimizer._read_ini(out)
        assert cfg2.get("GLOBAL", "UseEffect") == "true"
        assert cfg2.get("SSAO_SSIL", "EnableAmbientOcclusion") == "true"


# ---------------------------------------------------------------------------
# _backup
# ---------------------------------------------------------------------------


class TestBackup:
    def test_backup_created(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        src = tmp_path / "enbseries.ini"
        src.write_text("[GLOBAL]\nUseEffect=true\n", encoding="utf-8")
        backup_dir = tmp_path / "backups"
        monkeypatch.setattr(enb_optimizer, "BACKUP_DIR", backup_dir)

        backup = enb_optimizer._backup(src)

        assert backup is not None
        assert backup.exists()
        assert backup.suffix == ".bak"

    def test_backup_returns_none_when_file_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        missing = tmp_path / "nonexistent.ini"
        monkeypatch.setattr(enb_optimizer, "BACKUP_DIR", tmp_path / "backups")
        result = enb_optimizer._backup(missing)
        assert result is None


# ---------------------------------------------------------------------------
# _choose_preset_by_vram
# ---------------------------------------------------------------------------


class TestChoosePreset:
    @pytest.mark.parametrize(
        "vram_mib, expected",
        [
            (10000, "ultra"),
            (8192, "ultra"),
            (6000, "balanced"),
            (4096, "balanced"),
            (2048, "performance"),
            (0, "performance"),
        ],
    )
    def test_thresholds(self, vram_mib: int, expected: str) -> None:
        assert enb_optimizer._choose_preset_by_vram(vram_mib) == expected


# ---------------------------------------------------------------------------
# cmd_list
# ---------------------------------------------------------------------------


class TestCmdList:
    def test_list_prints_preset_names(self, capsys: pytest.CaptureFixture) -> None:
        args = enb_optimizer.build_parser().parse_args(["list"])
        enb_optimizer.cmd_list(args)
        out = capsys.readouterr().out
        for name in ("performance", "balanced", "ultra"):
            assert name in out


# ---------------------------------------------------------------------------
# cmd_show
# ---------------------------------------------------------------------------


class TestCmdShow:
    def test_show_performance(self, capsys: pytest.CaptureFixture) -> None:
        args = enb_optimizer.build_parser().parse_args(["show", "--preset", "performance"])
        enb_optimizer.cmd_show(args)
        out = capsys.readouterr().out
        assert "performance" in out.lower()
        assert "GLOBAL" in out

    def test_show_unknown_preset_exits(self) -> None:
        with pytest.raises(SystemExit):
            args = enb_optimizer.build_parser().parse_args(["show", "--preset", "ultra"])
            # Temporarily patch PRESET_FILES to make "ultra" unknown
            real_files = enb_optimizer.PRESET_FILES.copy()
            enb_optimizer.PRESET_FILES.clear()
            try:
                enb_optimizer.cmd_show(args)
            finally:
                enb_optimizer.PRESET_FILES.update(real_files)


# ---------------------------------------------------------------------------
# cmd_apply
# ---------------------------------------------------------------------------


class TestCmdApply:
    def test_apply_balanced_copies_file(
        self, patched_paths: Path, capsys: pytest.CaptureFixture
    ) -> None:
        dest = patched_paths / "enbseries.ini"
        args = enb_optimizer.build_parser().parse_args(["apply", "--preset", "balanced"])
        enb_optimizer.cmd_apply(args)
        out = capsys.readouterr().out
        assert "balanced" in out
        # The destination file should now contain content from the balanced preset
        cfg = enb_optimizer._read_ini(dest)
        assert cfg.has_section("GLOBAL")

    def test_apply_creates_backup(self, patched_paths: Path) -> None:
        backup_dir = patched_paths / "backups"
        args = enb_optimizer.build_parser().parse_args(["apply", "--preset", "performance"])
        enb_optimizer.cmd_apply(args)
        # A backup should have been created
        assert backup_dir.exists()
        backups = list(backup_dir.glob("*.bak"))
        assert len(backups) == 1

    def test_apply_auto_selects_preset(
        self, patched_paths: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        # Simulate 6 GiB VRAM → should pick "balanced"
        monkeypatch.setattr(enb_optimizer, "_detect_vram_mib", lambda: 6144)
        args = enb_optimizer.build_parser().parse_args(["apply", "--auto"])
        enb_optimizer.cmd_apply(args)
        out = capsys.readouterr().out
        assert "balanced" in out


# ---------------------------------------------------------------------------
# cmd_tune
# ---------------------------------------------------------------------------


class TestCmdTune:
    def test_tune_changes_value(self, patched_paths: Path, capsys: pytest.CaptureFixture) -> None:
        args = enb_optimizer.build_parser().parse_args(
            ["tune", "--setting", "GLOBAL/UseEffect", "--value", "false"]
        )
        enb_optimizer.cmd_tune(args)
        dest = patched_paths / "enbseries.ini"
        cfg = enb_optimizer._read_ini(dest)
        assert cfg.get("GLOBAL", "UseEffect") == "false"

    def test_tune_missing_slash_exits(self, patched_paths: Path) -> None:
        args = enb_optimizer.build_parser().parse_args(
            ["tune", "--setting", "GlobalUseEffect", "--value", "false"]
        )
        with pytest.raises(SystemExit):
            enb_optimizer.cmd_tune(args)

    def test_tune_unknown_section_exits(self, patched_paths: Path) -> None:
        args = enb_optimizer.build_parser().parse_args(
            ["tune", "--setting", "NONEXISTENT/SomeKey", "--value", "42"]
        )
        with pytest.raises(SystemExit):
            enb_optimizer.cmd_tune(args)

    def test_tune_creates_backup(self, patched_paths: Path) -> None:
        backup_dir = patched_paths / "backups"
        args = enb_optimizer.build_parser().parse_args(
            ["tune", "--setting", "BLOOM/EnableBloom", "--value", "false"]
        )
        enb_optimizer.cmd_tune(args)
        assert backup_dir.exists()
        backups = list(backup_dir.glob("*.bak"))
        assert len(backups) == 1
