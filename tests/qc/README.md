QC-of-QC runner

This folder contains a script qc_qc_runner.py that applies intentional mutations to critical enforcement code paths and runs the test suite to ensure QC detects failures.

Usage:
- Run in a clean git workspace (or ensure you can discard changes):
	python tests/qc/qc_qc_runner.py

The script creates .bak backups of modified files and restores them after each mutation.

Do not run in a production checkout without ensuring backups or using a disposable branch.
