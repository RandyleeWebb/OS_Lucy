#!/usr/bin/env python3
"""
QC-of-QC runner

This script applies intentional mutations to the codebase to validate that the QC suite
detects broken enforcement. It backs up files, applies mutations, runs pytest, and restores files.

USAGE:
  python tests/qc/qc_qc_runner.py

Note: This script modifies files in-place but creates .bak backups and restores them after each test.
Run in a clean git workspace or ensure you can discard changes.
"""
import subprocess
import sys
import os
import shutil
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

MUTATIONS = []


def backup_file(path):
	bak = path + '.bak'
	if not os.path.exists(bak):
		shutil.copy2(path, bak)


def restore_file(path):
	bak = path + '.bak'
	if os.path.exists(bak):
		shutil.copy2(bak, path)
		os.remove(bak)


def replace_in_file(path, pattern, repl):
	with open(path, 'r', encoding='utf-8') as f:
		text = f.read()
	new = re.sub(pattern, repl, text, flags=re.M)
	with open(path, 'w', encoding='utf-8') as f:
		f.write(new)


def run_pytest():
	print('Running pytest...')
	p = subprocess.run([sys.executable, '-m', 'pytest', '-q'], cwd=ROOT)
	return p.returncode


def mutation_remove_safeguard_signature():
	path = os.path.join(ROOT, 'src', 'safeguard', 'main.py')
	backup_file(path)
	print('Mutating SafeGuard signature generation...')
	replace_in_file(path, r"signature = compute_hmac\(token_json.encode\(\)\)", "signature = ''  # MUTATED_REMOVE_SG_SIGNATURE")


def mutation_remove_datavault_signature():
	path = os.path.join(ROOT, 'src', 'datavault', 'main.py')
	backup_file(path)
	print('Mutating DataVault signature generation...')
	replace_in_file(path, r"signature = compute_signature\(receipt_json.encode\(\)\)", "signature = ''  # MUTATED_REMOVE_DV_SIGNATURE")


def mutation_remove_orch_signature():
	path = os.path.join(ROOT, 'src', 'orchestrator', 'pipeline', 'permit.py')
	backup_file(path)
	print('Mutating Orchestrator permit signature generation...')
	replace_in_file(path, r"signature = hmac.new\(ORCH_PERMIT_KEY.encode\(\), canon, hashlib.sha256\)\.hexdigest\(\)", "signature = ''  # MUTATED_REMOVE_ORCH_SIGNATURE")


def mutation_remove_nonce_check():
	path = os.path.join(ROOT, 'src', 'trusted_executor', 'main.py')
	backup_file(path)
	print('Removing nonce replay check...')
	# remove the nonce replay raise
	replace_in_file(path, r"if nonce in NONCE_CACHE:\n\s+raise HTTPException\(status_code=403, detail=\"nonce_replay\"\)", "# MUTATED_REMOVE_NONCE_CHECK\n# nonce replay check removed")
	# remove adding nonce
	replace_in_file(path, r"NONCE_CACHE.add\(nonce\)", "# MUTATED_REMOVE_NONCE_ADD")


def mutation_remove_ttl_check():
	path = os.path.join(ROOT, 'src', 'trusted_executor', 'main.py')
	backup_file(path)
	print('Removing TTL check...')
	replace_in_file(path, r"if not ttl or int\(time.time\(\)\) > int\(ttl\):\n\s+raise HTTPException\(status_code=403, detail=\"permit_expired\"\)", "# MUTATED_REMOVE_TTL_CHECK\n# ttl check removed")


def mutation_remove_auth():
	path = os.path.join(ROOT, 'src', 'orchestrator', 'middleware', 'auth_mw.py')
	backup_file(path)
	print('Mutating auth dependency to allow anonymous...')
	replace_in_file(path, r"def get_current_actor\(request: Request\) -> str:\n[\s\S]*?raise HTTPException\(status_code=403, detail='forbidden_token'\)", "def get_current_actor(request: Request) -> str:\n    request.state.actor = 'anonymous'\n    return 'anonymous'  # MUTATED_REMOVE_AUTH")


def mutation_break_canonical_json():
	path = os.path.join(ROOT, 'src', 'orchestrator', 'pipeline', 'permit.py')
	backup_file(path)
	print('Breaking canonical_json to remove sort_keys/separators (mutate canonicalization)...')
	replace_in_file(path, r"def canonical_json\(obj: dict\) -> bytes:[\s\S]*?return json.dumps\(obj, separators=\(',', ':'\), sort_keys=True\)\.encode\(\)", "def canonical_json(obj: dict) -> bytes:\n    # MUTATED: non-canonical json with default spacing/order\n    return json.dumps(obj).encode()")


def mutation_skip_safeguard_verification():
	path = os.path.join(ROOT, 'src', 'orchestrator', 'server.py')
	backup_file(path)
	print('Skipping SafeGuard verification in orchestrator endpoints...')
	replace_in_file(path, r"sg_res = await verify_safeguard_decision\(actor_id or '', 'inject_proactive', payload\)", "sg_res = {'ok': True, 'decision': 'allow', 'decision_token': None}  # MUTATED_SKIP_SG")


def mutation_skip_datavault_receipt_verification():
	path = os.path.join(ROOT, 'src', 'orchestrator', 'clients', 'datavault.py')
	backup_file(path)
	print('Skipping receipt verification in orchestrator datavault client...')
	replace_in_file(path, r"def verify_receipt\(receipt: dict\) -> bool:[\s\S]*?return hmac.compare_digest\(expected, sig\)", "def verify_receipt(receipt: dict) -> bool:\n    # MUTATED: always accept receipts (insecure)\n    return True")


def mutation_skip_permit_verification():
	path = os.path.join(ROOT, 'src', 'trusted_executor', 'main.py')
	backup_file(path)
	print('Skipping orchestrator permit signature verification...')
	replace_in_file(path, r"if not hmac.compare_digest\(expected, sig\):\n\s+raise HTTPException\(status_code=403, detail=\"invalid_permit_signature\"\)", "# MUTATED_SKIP_PERMIT_SIGNATURE_CHECK")


MUTATIONS = [
	('remove_safeguard_signature', mutation_remove_safeguard_signature),
	('remove_datavault_signature', mutation_remove_datavault_signature),
	('remove_orch_signature', mutation_remove_orch_signature),
	('remove_nonce_check', mutation_remove_nonce_check),
	('remove_ttl_check', mutation_remove_ttl_check),
	('remove_auth', mutation_remove_auth),
	('break_canonical_json', mutation_break_canonical_json),
	('skip_safeguard', mutation_skip_safeguard_verification),
	('skip_datavault_receipt', mutation_skip_datavault_receipt_verification),
	('skip_permit_verification', mutation_skip_permit_verification),
]


def main():
	print('QC-of-QC runner starting...')
	for name, fn in MUTATIONS:
		try:
			print('\n--- Applying mutation:', name)
			fn()
			code = run_pytest()
			if code == 0:
				print(f'MUTATION {name} DID NOT CAUSE TEST FAILURE (pytest exit code 0) --> QC suite might be insufficient')
			else:
				print(f'MUTATION {name} caused pytest to fail as expected (exit code {code})')
		finally:
			# restore all backups to original state
			print('Restoring mutated files...')
			# look for .bak files in repo and restore
			for root, dirs, files in os.walk(ROOT):
				for f in files:
					if f.endswith('.bak'):
						orig = os.path.join(root, f[:-4])
						bak = os.path.join(root, f)
						shutil.copy2(bak, orig)
						os.remove(bak)
	print('QC-of-QC runner finished.')


if __name__ == '__main__':
	main()
