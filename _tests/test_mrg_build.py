"""期数发现与目录重命名回归测试；不需要运行 TeX 或安装 PyMuPDF。"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from _scripts import build_mrg as build


class ProjectTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="MRG project # ~ % ")
        self.root = Path(self.temporary.name).resolve()
        self.paths = patch.multiple(
            build,
            PROJECT_DIR=self.root,
            POSTS=self.root,
            OUTPUT=self.root / "_output" / "MRG_output",
            PDF_OUTPUT=self.root / "_output" / "MRG_output" / "PDF",
            PNG_OUTPUT=self.root / "_output" / "MRG_output" / "PNG",
            BUILD=self.root / "_build" / "MRG_build",
        )
        self.paths.start()
        self.addCleanup(self.temporary.cleanup)
        self.addCleanup(self.paths.stop)

    def add_post(self, folder: str, post: str) -> Path:
        target = self.root / folder
        target.mkdir()
        match = build.POST_FOLDER_PATTERN.fullmatch(folder)
        assert match is not None
        file_post = match["post"]
        (target / build.post_file_name(file_post, "content")).write_text(
            f"% !TeX root = {build.post_file_name(file_post, 'poster')}\n"
            f"\\newcommand{{\\SessionNumber}}{{{post}}}\n"
            "\\Presenter{Example Presenter}{Example University}\n",
            encoding="utf-8",
        )
        for template in ("poster", "cover"):
            (target / build.post_file_name(file_post, template)).write_text(
                build.root_document(template, file_post), encoding="utf-8"
            )
        return target


class DiscoveryTests(ProjectTestCase):
    def test_date_prefix_changes_do_not_change_period(self) -> None:
        folder = self.add_post("MRG41", "41")
        for name in ("26 09 09 MRG41", "26 10 01 MRG41", "MRG41"):
            renamed = self.root / name
            if folder != renamed:
                folder.rename(renamed)
            folder = renamed
            self.assertEqual(build.select_posts("41", False), ["41"])
            self.assertEqual(build.validate_post("41"), folder)

    def test_latest_is_numeric_and_ignores_date_order(self) -> None:
        self.add_post("99 12 31 MRG9", "9")
        self.add_post("26 01 01 MRG41", "41")
        self.assertEqual(build.select_posts("", False), ["41"])
        self.assertEqual(build.select_posts("", True), ["9", "41"])

    def test_duplicate_period_is_rejected(self) -> None:
        self.add_post("MRG41", "41")
        self.add_post("26 09 09 MRG41", "41")
        with self.assertRaisesRegex(ValueError, "两个文件夹"):
            build.discover_posts()

    def test_unrelated_folders_are_not_periods(self) -> None:
        self.add_post("MRG41", "41")
        for name in ("_config", "_output", "MRG41 backup", "prefix MRG42", "MRG0"):
            (self.root / name).mkdir()
        self.assertEqual(build.post_ids(), ["41"])

    def test_folder_and_content_period_must_match(self) -> None:
        self.add_post("26 09 09 MRG41", "42")
        with self.assertRaisesRegex(ValueError, "SessionNumber"):
            build.validate_post("41")


class CreationTests(ProjectTestCase):
    def test_new_period_copies_content_from_prefixed_folder(self) -> None:
        self.add_post("26 09 09 MRG41", "41")
        build.new_post("")
        info = (self.root / "MRG42/MRG42_03_content.tex").read_text(encoding="utf-8")
        self.assertIn(r"\SessionNumber}{42}", info)
        self.assertIn(r"\Presenter{Example Presenter}{Example University}", info)
        self.assertTrue((self.root / "MRG42/MRG42_01_poster.tex").is_file())
        self.assertTrue((self.root / "MRG42/MRG42_02_cover.tex").is_file())
        self.assertEqual(len(list((self.root / "MRG42").iterdir())), 3)
        self.assertEqual(
            sorted(path.name for path in (self.root / "MRG42").iterdir()),
            ["MRG42_01_poster.tex", "MRG42_02_cover.tex", "MRG42_03_content.tex"],
        )

    def test_existing_prefixed_period_is_never_overwritten(self) -> None:
        folder = self.add_post("26 09 09 MRG41", "41")
        before = (folder / "MRG41_03_content.tex").read_bytes()
        with self.assertRaisesRegex(ValueError, "已存在"):
            build.new_post("41")
        self.assertEqual((folder / "MRG41_03_content.tex").read_bytes(), before)
        self.assertFalse((self.root / "MRG41").exists())

    def test_shared_root_comments_follow_folder_rename(self) -> None:
        folder = self.add_post("26 09 09 MRG41", "41")
        config = self.root / "_config"
        config.mkdir()
        for name in ("mrg_brand.tex", "mrg_cover_layout.tex"):
            (config / name).write_text("% !TeX root = ../MRG41/old.tex\n", encoding="utf-8")
        build.sync_root_comments("41")
        for path in config.glob("*.tex"):
            relative = path.read_text(encoding="utf-8").splitlines()[0].split(" = ", 1)[1]
            self.assertTrue((path.parent / relative).resolve().is_file())
            self.assertIn(folder.name, relative)


class WorkspaceTests(ProjectTestCase):
    def test_only_root_files_are_added_to_hidden_list(self) -> None:
        folder = self.add_post("MRG41", "41")
        (self.root / ".vscode").mkdir()
        settings = self.root / ".vscode/settings.json"
        settings.write_text('{"files.exclude": {"_build": true}}\n', encoding="utf-8")
        (self.root / "Makefile").touch()
        (self.root / "README.md").touch()
        (self.root / "_output").mkdir()

        build.sync_workspace_settings()
        excluded = json.loads(settings.read_text(encoding="utf-8"))["files.exclude"]
        self.assertTrue(excluded["Makefile"])
        self.assertTrue(excluded["README.md"])
        self.assertNotIn("MRG41", excluded)
        self.assertNotIn("_output", excluded)
        self.assertNotIn("MRG41_03_content.tex", excluded)
        self.assertTrue((folder / "MRG41_03_content.tex").is_file())

        (self.root / "new-root-file.txt").touch()
        build.sync_workspace_settings()
        excluded = json.loads(settings.read_text(encoding="utf-8"))["files.exclude"]
        self.assertTrue(excluded["new-root-file.txt"])
        last_write = settings.stat().st_mtime_ns
        build.sync_workspace_settings()
        self.assertEqual(settings.stat().st_mtime_ns, last_write)


class MakeTests(ProjectTestCase):
    def test_numeric_make_target_handles_spaces_in_folder_name(self) -> None:
        self.add_post("26 09 09 MRG41", "41")
        repository = Path(__file__).resolve().parents[1]
        shutil.copy2(repository / "Makefile", self.root / "Makefile")
        (self.root / "_scripts").mkdir()
        shutil.copy2(repository / "_scripts/build_mrg.py", self.root / "_scripts/build_mrg.py")
        result = subprocess.run(
            ["make", "-n", "41"],
            cwd=self.root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn('--post "41"', result.stdout)


if __name__ == "__main__":
    unittest.main()
