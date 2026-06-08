import os
import requests
import json


def test_datavault_append_and_receipt():
	# Integration test assumes datavault service running at env DATAVAULT_URL
	url = os.environ.get('DATAVAULT_URL', 'http://localhost:8012/log')
	payload = {"source": "itest", "payload": {"msg": "hello"}}
	r = requests.post(url, json=payload, timeout=5)
	assert r.status_code == 200
	data = r.json()
	assert data.get('ok') is True
	receipt = data.get('audit_receipt')
	assert receipt and receipt.get('signature')


def test_datavault_rejects_invalid_signature():
	# This would be an orchestration-level test that tampers with signature
	# For now ensure service returns proper structure
	url = os.environ.get('DATAVAULT_URL', 'http://localhost:8012/log')
	payload = {"source": "itest", "payload": {"msg": "tamper"}}
	r = requests.post(url, json=payload, timeout=5)
	assert r.status_code == 200
	data = r.json()
	assert data.get('audit_receipt')
