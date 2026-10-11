# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause
"""
Tests for the full_scan.py entry point.
"""

import contextlib
import io
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch as mock_patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import full_scan  # noqa: E402  pylint: disable=wrong-import-position
from scanner import licenses  # noqa: E402  pylint: disable=wrong-import-position


class TestFullScanMain(unittest.TestCase):
    """
    main() resolves the baseline, runs the checker and sets the exit code.

    Only get_license is stubbed, so the real resolve_allowed_licenses runs and
    a change to its signature fails here rather than in production. The stub
    reports a copyleft license, so the checker must be given the copyleft
    allowed list; proprietary mode, or a hard-coded permissive list, would
    give it the permissive list instead.
    """

    def run_main(self, flagged: dict, warnings: dict = None) -> tuple:
        """
        Run main() with the file listing and checker stubbed out.

        Args:
            flagged: Blocking half of RepoLicenseChecker.run()'s return value.
            warnings: Warning half of RepoLicenseChecker.run()'s return value.

        Returns:
            Tuple of (captured stdout, exit code).
        """
        checker = MagicMock()
        checker.run.return_value = (flagged, warnings or {})
        buffer = io.StringIO()
        with (
            mock_patch.object(sys, "argv", ["full_scan.py", "org/repo"]),
            mock_patch("main.get_license", return_value="GPL-2.0-only") as get_license,
            mock_patch("full_scan.list_repo_files", return_value=["a.c"]),
            mock_patch("full_scan.RepoLicenseChecker", return_value=checker) as checker_class,
        ):
            with contextlib.redirect_stdout(buffer):
                with self.assertRaises(SystemExit) as caught:
                    full_scan.main()
        get_license.assert_called_once_with("org/repo")
        checker_class.assert_called_once_with(["a.c"], licenses.COPYLEFT_LICENSES)
        return buffer.getvalue(), caught.exception.code

    def test_clean_repository_exits_zero(self):
        """With no issues, main() exits 0."""
        output, code = self.run_main({})
        self.assertEqual(code, 0)
        self.assertIn("No license or copyright issues detected", output)

    def test_blocking_issues_exit_one(self):
        """Blocking issues are reported and exit 1, whatever the number of files."""
        issue = {"license_issues": ["Incompatible license: GPL-2.0-only"], "copyright_issues": []}
        output, code = self.run_main({"a.c": issue, "b.c": issue})
        self.assertEqual(code, 1)
        self.assertIn("Incompatible license: GPL-2.0-only", output)

    def test_warning_alone_exits_zero(self):
        """A warning is reported without failing the run."""
        issue = {"license_issues": ["Incompatible license: LicenseRef-x"], "copyright_issues": []}
        output, code = self.run_main({}, {"a.c": issue})
        self.assertEqual(code, 0)
        self.assertIn("W A R N I N G S", output)

    def test_annotations_are_emitted_in_github_actions(self):
        """Inside GitHub Actions, findings also become workflow annotations."""
        issue = {"license_issues": ["Incompatible license: GPL-2.0-only"], "copyright_issues": []}
        with mock_patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}):
            output, _ = self.run_main({"a.c": issue})
        self.assertIn("::error file=a.c::Incompatible license: GPL-2.0-only", output)


if __name__ == "__main__":
    unittest.main()
