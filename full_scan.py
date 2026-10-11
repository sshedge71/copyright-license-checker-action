# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause
"""
Check every tracked file in the current checkout for license issues.

main.py checks the lines a pull request changes; this checks the whole
repository, using the same license baseline and report.
"""

import argparse
import os
import sys

from main import LOG_PREFIX, beautify_output, emit_workflow_annotations, resolve_allowed_licenses
from scanner.repo_checker import RepoLicenseChecker
from scanner.repo_files import list_repo_files


def parse_args(argv: list) -> argparse.Namespace:
    """Parse the repository name from command-line arguments."""
    parser = argparse.ArgumentParser(description="Full-repository license compliance checker.")
    parser.add_argument("repo_name", help="The name of the GitHub repository.")
    return parser.parse_args(argv)


def main() -> None:
    """
    The main function of the script.
    """
    args = parse_args(sys.argv[1:])
    # The full scan applies the opensource rules only; proprietary mode's
    # rules compare added and deleted lines, which a whole file does not have.
    repo_license, allowed_licenses = resolve_allowed_licenses(
        mode="opensource", repo_name=args.repo_name
    )

    checker = RepoLicenseChecker(list_repo_files(), allowed_licenses)
    flagged_files, warning_files = checker.run()

    beautify_output(flagged_files, warning_files, repo_license, LOG_PREFIX)
    if os.environ.get("GITHUB_ACTIONS") == "true":
        emit_workflow_annotations(flagged_files, warning_files)

    sys.exit(1 if flagged_files else 0)


if __name__ == "__main__":
    main()
