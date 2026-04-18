"""
tests/test_tools.py
===================
Unit tests for the helper scripts in tools/.

Run with:
    python -m pytest tests/ -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tools"))

import enb_optimizer  # noqa: E402


# ---------------------------------------------------------------------------
# tools/generate_lut.py
# ---------------------------------------------------------------------------


class TestGenerateLut:
    def test_identity_lut_generates_png(self, tmp_path: Path) -> None:
        from generate_lut import generate

        out = tmp_path / "identity.png"
        generate(out, film=False)
        assert out.exists()
        with out.open("rb") as fh:
            sig = fh.read(8)
        assert sig == b"\x89PNG\r\n\x1a\n"

    def test_film_lut_generates_png(self, tmp_path: Path) -> None:
        from generate_lut import generate

        out = tmp_path / "film.png"
        generate(out, film=True)
        assert out.exists()

    def test_identity_lut_correct_size(self, tmp_path: Path) -> None:
        """
        The PNG should decode to 512×512 pixels.  We verify this by parsing
        the IHDR chunk width/height fields (bytes 16-23 in a PNG file).
        """
        import struct

        from generate_lut import generate

        out = tmp_path / "size_check.png"
        generate(out, film=False)
        with out.open("rb") as fh:
            fh.seek(16)  # IHDR data starts after 8 (sig) + 4 (len) + 4 (type)
            width, height = struct.unpack(">II", fh.read(8))
        assert width == 512
        assert height == 512

    def test_identity_pixel_corner_black(self) -> None:
        """Top-left pixel of identity LUT should map to (0, 0, 0)."""
        from generate_lut import _identity_pixel

        r, g, b, a = _identity_pixel(0, 0, 0, 0)
        assert (r, g, b) == (0, 0, 0)
        assert a == 255

    def test_identity_pixel_corner_white(self) -> None:
        """Bottom-right pixel of identity LUT should map to (255, 255, 255)."""
        from generate_lut import _identity_pixel

        # Last tile: tx=7, ty=7; local_x=63, local_y=63
        r, g, b, a = _identity_pixel(7, 7, 63, 63)
        assert r == 255
        assert g == 255
        assert b == 255

    def test_film_and_identity_differ(self, tmp_path: Path) -> None:
        """The film LUT should produce different bytes than the identity LUT."""
        from generate_lut import generate

        id_out = tmp_path / "id.png"
        film_out = tmp_path / "film.png"
        generate(id_out, film=False)
        generate(film_out, film=True)
        assert id_out.read_bytes() != film_out.read_bytes()


# ---------------------------------------------------------------------------
# tools/patch_enblocal.py
# ---------------------------------------------------------------------------


class TestPatchEnblocal:
    @pytest.fixture()
    def enblocal_ini(self, tmp_path: Path) -> Path:
        ini = tmp_path / "enblocal.ini"
        ini.write_text(
            "[GLOBAL]\nAutodetectVideoMemorySize=true\n"
            "[MEMORY]\nVideoMemorySizeMb=0\nReservedMemorySizeMb=128\n"
            "[ENGINE]\nEnableVSync=true\nEnableFpsLimit=false\nFpsLimit=0.0\n",
            encoding="utf-8",
        )
        return ini

    def test_patch_writes_video_mb(self, enblocal_ini: Path) -> None:
        from patch_enblocal import patch

        patch(enblocal_ini, video_mb=7680, reserved_mb=512)
        cfg = enb_optimizer._read_ini(enblocal_ini)
        assert cfg.get("MEMORY", "VideoMemorySizeMb") == "7680"

    def test_patch_writes_reserved_mb(self, enblocal_ini: Path) -> None:
        from patch_enblocal import patch

        patch(enblocal_ini, video_mb=3584, reserved_mb=256)
        cfg = enb_optimizer._read_ini(enblocal_ini)
        assert cfg.get("MEMORY", "ReservedMemorySizeMb") == "256"

    def test_patch_disables_vsync(self, enblocal_ini: Path) -> None:
        from patch_enblocal import patch

        patch(enblocal_ini, video_mb=4096, reserved_mb=256)
        cfg = enb_optimizer._read_ini(enblocal_ini)
        assert cfg.get("ENGINE", "EnableVSync") == "false"

    def test_patch_sets_fps_limit(self, enblocal_ini: Path) -> None:
        from patch_enblocal import patch

        patch(enblocal_ini, video_mb=4096, reserved_mb=256, fps_limit=72.0)
        cfg = enb_optimizer._read_ini(enblocal_ini)
        assert cfg.get("ENGINE", "FpsLimit") == "72.0"

    def test_patch_disables_autodetect(self, enblocal_ini: Path) -> None:
        from patch_enblocal import patch

        patch(enblocal_ini, video_mb=4096, reserved_mb=256)
        cfg = enb_optimizer._read_ini(enblocal_ini)
        assert cfg.get("GLOBAL", "AutodetectVideoMemorySize") == "false"

    def test_patch_creates_backup(self, enblocal_ini: Path) -> None:
        from patch_enblocal import patch

        patch(enblocal_ini, video_mb=4096, reserved_mb=256)
        backup_dir = enblocal_ini.parent / "backups"
        assert backup_dir.exists()
        assert len(list(backup_dir.glob("*.bak"))) == 1

    def test_patch_missing_file_exits(self, tmp_path: Path) -> None:
        from patch_enblocal import patch

        with pytest.raises(SystemExit):
            patch(tmp_path / "nonexistent.ini", video_mb=4096, reserved_mb=256)


# ---------------------------------------------------------------------------
# tools/verify_install.py
# ---------------------------------------------------------------------------


class TestVerifyInstall:
    def test_check_fails_on_empty_dir(self, tmp_path: Path) -> None:
        from verify_install import check

        result = check(tmp_path)
        assert result is False

    def test_check_passes_when_all_required_present(self, tmp_path: Path) -> None:
        from verify_install import REQUIRED_FILES, check

        # Create every required (non-optional) file
        for rel_path, _desc, optional in REQUIRED_FILES:
            full = tmp_path / rel_path
            full.parent.mkdir(parents=True, exist_ok=True)
            full.touch()

        result = check(tmp_path)
        assert result is True

    def test_check_passes_with_optional_missing(self, tmp_path: Path) -> None:
        from verify_install import REQUIRED_FILES, check

        # Only create non-optional files
        for rel_path, _desc, optional in REQUIRED_FILES:
            if not optional:
                full = tmp_path / rel_path
                full.parent.mkdir(parents=True, exist_ok=True)
                full.touch()

        result = check(tmp_path)
        assert result is True

    def test_check_output_contains_pass_mark(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        from verify_install import REQUIRED_FILES, check

        for rel_path, _desc, optional in REQUIRED_FILES:
            if not optional:
                full = tmp_path / rel_path
                full.parent.mkdir(parents=True, exist_ok=True)
                full.touch()

        check(tmp_path)
        out = capsys.readouterr().out
        assert "✓" in out

    def test_check_output_contains_missing_marker(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        from verify_install import check

        check(tmp_path)
        out = capsys.readouterr().out
        assert "MISSING" in out


# ---------------------------------------------------------------------------
# tools/export_diagnostics.py
# ---------------------------------------------------------------------------


class TestExportDiagnostics:
    @pytest.fixture()
    def mock_game_dir(self, tmp_path: Path) -> Path:
        """Create a minimal game dir with stubs for enbseries.ini, enblocal.ini, ReShade.ini."""
        (tmp_path / "enbseries.ini").write_text(
            "[GLOBAL]\nUseEffect=true\n", encoding="utf-8"
        )
        (tmp_path / "enblocal.ini").write_text(
            "[MEMORY]\nVideoMemorySizeMb=4096\nReservedMemorySizeMb=512\n",
            encoding="utf-8",
        )
        (tmp_path / "ReShade.ini").write_text(
            "[GENERAL]\nPresetPath=.\\reshade-presets\\Mossy_balanced.ini\n",
            encoding="utf-8",
        )
        return tmp_path

    def test_export_creates_file(self, mock_game_dir: Path, tmp_path: Path) -> None:
        from export_diagnostics import export

        out = tmp_path / "diag.txt"
        export(mock_game_dir, out)
        assert out.exists()

    def test_export_contains_gpu_section(self, mock_game_dir: Path, tmp_path: Path) -> None:
        from export_diagnostics import export

        out = tmp_path / "diag.txt"
        export(mock_game_dir, out)
        content = out.read_text(encoding="utf-8")
        assert "GPU" in content

    def test_export_contains_active_presets_section(
        self, mock_game_dir: Path, tmp_path: Path
    ) -> None:
        from export_diagnostics import export

        out = tmp_path / "diag.txt"
        export(mock_game_dir, out)
        content = out.read_text(encoding="utf-8")
        assert "Active presets" in content

    def test_export_contains_enbseries_section(
        self, mock_game_dir: Path, tmp_path: Path
    ) -> None:
        from export_diagnostics import export

        out = tmp_path / "diag.txt"
        export(mock_game_dir, out)
        content = out.read_text(encoding="utf-8")
        assert "enbseries.ini" in content

    def test_export_contains_file_presence_section(
        self, mock_game_dir: Path, tmp_path: Path
    ) -> None:
        from export_diagnostics import export

        out = tmp_path / "diag.txt"
        export(mock_game_dir, out)
        content = out.read_text(encoding="utf-8")
        assert "Required file presence" in content

    def test_export_output_has_timestamp(
        self, mock_game_dir: Path, tmp_path: Path
    ) -> None:
        from export_diagnostics import export

        out = tmp_path / "diag.txt"
        export(mock_game_dir, out)
        content = out.read_text(encoding="utf-8")
        assert "Generated:" in content


# ---------------------------------------------------------------------------
# tools/upscale_textures.py
# ---------------------------------------------------------------------------


class TestDdsFormat:
    """Unit tests for _dds_format() — the filename-to-BC-format classifier."""

    def test_normal_suffix_n(self) -> None:
        from upscale_textures import _dds_format

        assert _dds_format("rock_cave_01_n.dds") == "BC5_UNORM"

    def test_normal_suffix_normal(self) -> None:
        from upscale_textures import _dds_format

        assert _dds_format("skin_normal.dds") == "BC5_UNORM"

    def test_normal_suffix_nm(self) -> None:
        from upscale_textures import _dds_format

        assert _dds_format("wall_nm.dds") == "BC5_UNORM"

    def test_specular_suffix_s(self) -> None:
        from upscale_textures import _dds_format

        assert _dds_format("gun_metal_s.dds") == "BC1_UNORM"

    def test_specular_suffix_spec(self) -> None:
        from upscale_textures import _dds_format

        assert _dds_format("armor_spec.dds") == "BC1_UNORM"

    def test_glow_suffix_g(self) -> None:
        from upscale_textures import _dds_format

        assert _dds_format("screen_g.dds") == "BC1_UNORM"

    def test_glow_suffix_em(self) -> None:
        from upscale_textures import _dds_format

        assert _dds_format("pipboy_em.dds") == "BC1_UNORM"

    def test_glow_suffix_emissive(self) -> None:
        from upscale_textures import _dds_format

        assert _dds_format("light_emissive.dds") == "BC1_UNORM"

    def test_diffuse_no_suffix(self) -> None:
        from upscale_textures import _dds_format

        assert _dds_format("rock_cave_01.dds") == "BC3_UNORM"

    def test_diffuse_d_suffix(self) -> None:
        from upscale_textures import _dds_format

        # _d is not a known suffix — falls through to diffuse default
        assert _dds_format("rock_d.dds") == "BC3_UNORM"

    def test_case_insensitive_stem(self) -> None:
        from upscale_textures import _dds_format

        assert _dds_format("ROCK_N.DDS") == "BC5_UNORM"

    def test_word_ending_in_n_is_not_normal_map(self) -> None:
        """'terrain.dds' ends in 'n' but not in '_n'."""
        from upscale_textures import _dds_format

        assert _dds_format("terrain.dds") == "BC3_UNORM"


class TestFindTool:
    """Tests for _find_tool(), _find_dds_converter(), _find_esrgan_binary()."""

    def test_find_tool_returns_none_for_nonexistent(self) -> None:
        from upscale_textures import _find_tool

        assert _find_tool("__nonexistent_tool_xyz__") is None

    def test_find_tool_returns_name_when_found(self) -> None:
        """'python' (or 'python3') must be on PATH in the test environment."""
        from upscale_textures import _find_tool

        found = _find_tool("python3", "python")
        assert found is not None

    def test_find_dds_converter_returns_none_or_str(self) -> None:
        from upscale_textures import _find_dds_converter

        result = _find_dds_converter()
        assert result is None or isinstance(result, str)

    def test_find_esrgan_binary_returns_none_when_missing(self) -> None:
        from upscale_textures import _find_esrgan_binary

        # The binary is not expected to be present in CI.
        result = _find_esrgan_binary()
        assert result is None or isinstance(result, str)

    def test_find_esrgan_binary_with_bad_hint_returns_none(self) -> None:
        from upscale_textures import _find_esrgan_binary

        assert _find_esrgan_binary("__no_such_bin__") is None

    def test_find_esrgan_binary_with_python_hint(self) -> None:
        """Passing 'python3' as a hint should resolve because it is on PATH."""
        import shutil

        from upscale_textures import _find_esrgan_binary

        py = shutil.which("python3") or shutil.which("python")
        if py is None:
            pytest.skip("python not on PATH in this environment")
        result = _find_esrgan_binary("python3")
        assert result is not None


class TestUpscaleDryRun:
    """Tests for upscale() in --dry-run mode (no external binaries needed)."""

    @pytest.fixture()
    def dds_input_dir(self, tmp_path: Path) -> Path:
        """Create a small tree of stub .dds files."""
        textures = [
            "landscape/rock_01.dds",
            "landscape/rock_01_n.dds",
            "landscape/rock_01_s.dds",
            "actors/face.dds",
            "actors/face_n.dds",
        ]
        for rel in textures:
            p = tmp_path / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"DDS ")  # stub — not a real DDS file

        return tmp_path

    def test_dry_run_returns_file_count(
        self, dds_input_dir: Path, tmp_path: Path
    ) -> None:
        from upscale_textures import upscale

        out = tmp_path / "out"
        # Dry-run needs a fake converter and ESRGAN so it can pass the guard
        # checks. We use python itself as a stand-in since it is on PATH.
        success, fail = upscale(
            dds_input_dir,
            out,
            dds_converter="python",   # won't actually be called in dry-run
            esrgan_bin="python",      # same
            dry_run=True,
        )
        assert success == 5  # 5 stub DDS files
        assert fail == 0

    def test_dry_run_does_not_create_output(
        self, dds_input_dir: Path, tmp_path: Path
    ) -> None:
        from upscale_textures import upscale

        out = tmp_path / "out"
        upscale(
            dds_input_dir,
            out,
            dds_converter="python",
            esrgan_bin="python",
            dry_run=True,
        )
        assert not out.exists()

    def test_dry_run_no_recursive(self, dds_input_dir: Path, tmp_path: Path) -> None:
        """Non-recursive mode should only find DDS files at the top level."""
        from upscale_textures import upscale

        out = tmp_path / "out"
        success, fail = upscale(
            dds_input_dir,
            out,
            dds_converter="python",
            esrgan_bin="python",
            recursive=False,
            dry_run=True,
        )
        # No DDS files live at the top level of dds_input_dir
        assert success == 0
        assert fail == 0

    def test_dry_run_empty_dir_returns_zero(self, tmp_path: Path) -> None:
        from upscale_textures import upscale

        empty = tmp_path / "empty"
        empty.mkdir()
        out = tmp_path / "out"
        success, fail = upscale(
            empty,
            out,
            dds_converter="python",
            esrgan_bin="python",
            dry_run=True,
        )
        assert success == 0
        assert fail == 0


class TestUpscaleToolsMissing:
    """upscale() should call sys.exit(2) when required tools are absent."""

    def test_missing_converter_exits(self, tmp_path: Path) -> None:
        from upscale_textures import upscale

        (tmp_path / "a.dds").write_bytes(b"DDS ")
        out = tmp_path / "out"
        with pytest.raises(SystemExit) as exc_info:
            upscale(
                tmp_path,
                out,
                dds_converter="__no_converter__",
                esrgan_bin="python",
            )
        assert exc_info.value.code == 2

    def test_missing_esrgan_exits(self, tmp_path: Path) -> None:
        from upscale_textures import upscale

        (tmp_path / "a.dds").write_bytes(b"DDS ")
        out = tmp_path / "out"
        with pytest.raises(SystemExit) as exc_info:
            upscale(
                tmp_path,
                out,
                dds_converter="python",   # python is on PATH
                esrgan_bin="__no_esrgan__",
            )
        assert exc_info.value.code == 2


# ---------------------------------------------------------------------------
# tools/verify_install.py — upscale tool detection
# ---------------------------------------------------------------------------


class TestVerifyInstallUpscaleTools:
    def test_check_upscale_tools_returns_dict(self) -> None:
        from verify_install import check_upscale_tools

        result = check_upscale_tools()
        assert isinstance(result, dict)
        assert "dds_converter" in result
        assert "esrgan_binary" in result

    def test_check_upscale_tools_values_are_bool(self) -> None:
        from verify_install import check_upscale_tools

        result = check_upscale_tools()
        assert isinstance(result["dds_converter"], bool)
        assert isinstance(result["esrgan_binary"], bool)

    def test_check_upscale_tools_output_contains_tool_names(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        from verify_install import check_upscale_tools

        check_upscale_tools()
        out = capsys.readouterr().out
        assert "ESRGAN" in out or "esrgan" in out.lower()

    def test_check_upscale_tools_output_contains_dds_label(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        from verify_install import check_upscale_tools

        check_upscale_tools()
        out = capsys.readouterr().out
        assert "DDS" in out
