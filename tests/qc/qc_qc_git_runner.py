#!/usr/bin/env python3
"""
Git-based QC-of-QC runner

This script creates deterministic git-style patches for intentional mutations, applies them
using `git apply`, runs the test suite, and then restores the repository with
`git checkout -- .` so the working tree remains clean. It fails if any mutation
escapes detection (i.e., pytest still passes when it should fail).

Requirements:
- git installed and available in PATH
- pytest available in Python environment

Run from repository root:
  python tests/qc/qc_qc_git_runner.py

This is safer and more robust than direct regex edits because patches are explicit and
visible in CI logs. The script writes patches to tests/qc/patches/*.patch for inspection.
"""
import os
import sys
import subprocess
import tempfile
import shutil
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATCH_DIR = ROOT / 'tests' / 'qc' / 'patches'
PATCH_DIR.mkdir(parents=True, exist_ok=True)


def git_clean_check():
	p = subprocess.run(['git', 'status', '--porcelain'], cwd=ROOT, capture_output=True, text=True)
	if p.returncode != 0:
		print('git status failed:', p.stderr)
		sys.exit(2)
	if p.stdout.strip():
		print('Working tree is not clean. Commit or stash changes before running this script.')
		print(p.stdout)
		sys.exit(2)


def make_patch(original_path: Path, mutated_text: str, patch_name: str) -> Path:
	# write mutated content to a temp file
	with tempfile.NamedTemporaryFile('w', delete=False, encoding='utf-8') as tf:
		tf.write(mutated_text)
		temp_path = Path(tf.name)

	# use git diff --no-index to create a unified patch between original and temp
	patch_path = PATCH_DIR / f'{patch_name}.patch'
	cmd = ['git', 'diff', '--no-index', '--', str(original_path), str(temp_path)]
	with open(patch_path, 'w', encoding='utf-8') as pf:
		p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
		pf.write(p.stdout)

	os.remove(temp_path)
	return patch_path


def apply_patch(patch_path: Path) -> bool:
	print('\nApplying patch:', patch_path)
	print('--- PATCH CONTENT BEGIN ---')
	print(patch_path.read_text())
	print('--- PATCH CONTENT END ---')
	p = subprocess.run(['git', 'apply', str(patch_path)], cwd=ROOT)
	return p.returncode == 0


def restore_repo():
	print('Restoring repository state (git checkout -- .)')
	subprocess.run(['git', 'checkout', '--', '.'], cwd=ROOT)


def run_pytest():
	print('Running pytest...')
	p = subprocess.run([sys.executable, '-m', 'pytest', '-q'], cwd=ROOT)
	return p.returncode


def mutate_file_in_memory(path: Path, transform_fn):
	orig = path.read_text(encoding='utf-8')
	mutated = transform_fn(orig)
	return mutated


def mutation_funcs():
	mutations = []

	def remove_safeguard_signature(text):
		return re.sub(r"signature\s*=\s*compute_hmac\(token_json.encode\(\)\)", "signature = ''  # MUTATED_REMOVE_SG_SIGNATURE", text, flags=re.M)

	def remove_datavault_signature(text):
		return re.sub(r"signature\s*=\s*compute_signature\(receipt_json.encode\(\)\)", "signature = ''  # MUTATED_REMOVE_DV_SIGNATURE", text, flags=re.M)

	def remove_orch_signature(text):
		return re.sub(r"signature\s*=\s*hmac\.new\(ORCH_PERMIT_KEY\.encode\(\), canon, hashlib\.sha256\)\.hexdigest\(\)", "signature = ''  # MUTATED_REMOVE_ORCH_SIGNATURE", text, flags=re.M)

	def remove_nonce_check(text):
		t = re.sub(r"if nonce in NONCE_CACHE:\n\s+raise HTTPException\(status_code=403, detail=\"nonce_replay\"\)", "# MUTATED_REMOVE_NONCE_CHECK\n# nonce replay check removed", text, flags=re.M)
		t = re.sub(r"NONCE_CACHE.add\(nonce\)", "# MUTATED_REMOVE_NONCE_ADD", t, flags=re.M)
		return t

	def remove_ttl_check(text):
		return re.sub(r"if not ttl or int\(time.time\(\)\) > int\(ttl\):\n\s+raise HTTPException\(status_code=403, detail=\"permit_expired\"\)", "# MUTATED_REMOVE_TTL_CHECK\n# ttl check removed", text, flags=re.M)

	def remove_auth(text):
		return re.sub(r"def get_current_actor\(request: Request\) -> str:[\s\S]*?raise HTTPException\(status_code=403, detail='forbidden_token'\)", "def get_current_actor(request: Request) -> str:\n    request.state.actor = 'anonymous'\n    return 'anonymous'  # MUTATED_REMOVE_AUTH", text, flags=re.M)

	def break_canonical_json(text):
		return re.sub(r"return json.dumps\(obj, separators=\(',', ':'\), sort_keys=True\)\.encode\(\)", "return json.dumps(obj).encode()  # MUTATED_BREAK_CANONICAL", text, flags=re.M)

	def skip_safeguard_verification(text):
		return re.sub(r"sg_res = await verify_safeguard_decision\(actor_id or '', 'inject_proactive', payload\)", "sg_res = {'ok': True, 'decision': 'allow', 'decision_token': None}  # MUTATED_SKIP_SG", text, flags=re.M)

	def skip_datavault_receipt_verification(text):
		return re.sub(r"def verify_receipt\(receipt: dict\) -> bool:[\s\S]*?return hmac.compare_digest\(expected, sig\)", "def verify_receipt(receipt: dict) -> bool:\n    # MUTATED: always accept receipts (insecure)\n    return True", text, flags=re.M)

	def skip_permit_verification(text):
		return re.sub(r"if not hmac.compare_digest\(expected, sig\):\n\s+raise HTTPException\(status_code=403, detail=\\\"invalid_permit_signature\\\"\)", "# MUTATED_SKIP_PERMIT_SIGNATURE_CHECK", text, flags=re.M)

	# mapping of target file path relative to repo root to mutation function and name
	mapping = [
		('src/safeguard/main.py', remove_safeguard_signature, 'remove_safeguard_signature'),
		('src/datavault/main.py', remove_datavault_signature, 'remove_datavault_signature'),
		('src/orchestrator/pipeline/permit.py', remove_orch_signature, 'remove_orch_signature'),
		('src/trusted_executor/main.py', remove_nonce_check, 'remove_nonce_check'),
		('src/trusted_executor/main.py', remove_ttl_check, 'remove_ttl_check'),
		('src/orchestrator/middleware/auth_mw.py', remove_auth, 'remove_auth'),
		('src/orchestrator/pipeline/permit.py', break_canonical_json, 'break_canonical_json'),
		('src/orchestrator/server.py', skip_safeguard_verification, 'skip_safeguard'),
		('src/orchestrator/clients/datavault.py', skip_datavault_receipt_verification, 'skip_datavault_receipt'),
		('src/trusted_executor/main.py', skip_permit_verification, 'skip_permit_verification'),
	]

	for relpath, fn, name in mapping:
		yield (Path(ROOT / relpath), fn, name)


def main():
	git_clean_check()
	any_escape = False

	for path, fn, name in mutate_file_in_mapping():
		print('\n=== Mutation:', name, 'target file:', path)
		if not path.exists():
			print('Target file does not exist:', path)
			continue

		mutated = mutate_file_in_memory(path, fn)
		patch = make_patch(path, mutated, name)
		applied = apply_patch(patch)
		if not applied:
			print('Failed to apply patch', patch)
			restore_repo()
			any_escape = True
			continue

		# run tests; expecting failures
		code = run_pytest()
		if code == 0:
			print(f'ERROR: Mutation {name} did NOT cause pytest to fail -> QC-of-QC escaped detection')
			any_escape = True
		else:
			print(f'OK: Mutation {name} caused pytest to fail (exit code {code})')

		# restore repo state after each mutation
		restore_repo()

	if any_escape:
		print('\nQC-of-QC detected escapes. Failing run.')
		sys.exit(1)
	else:
		print('\nAll mutations detected. QC-of-QC passed.')
		sys.exit(0)


def mutate_file_in_mapping():
	for path, fn, name in mutation_funcs():
		yield path, fn, name


if __name__ == '__main__':
	main()
