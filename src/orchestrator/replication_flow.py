from .clients import datavault, prompt, safeguard


def replicate_agent(agent_id: str):
	# 1. Ask safeguard for audit
	audit = safeguard.audit(agent_id, 'replicate')
	# write audit to datavault and capture entry id/result so UI can fetch it
	audit_write = datavault.write('orchestrator', {'event': 'replication_audit', 'agent_id': agent_id, 'audit': audit})
	if audit.get('decision') != 'allow':
		# write deny event including datavault entry
		res = datavault.write('orchestrator', {'event': 'replication_denied', 'agent_id': agent_id, 'audit': audit})
		return {'ok': False, 'reason': 'safeguard_denied', 'audit': audit, 'datavault': res, 'datavault_audit': audit_write}
	# 2. ask prompt to update state
	P_t = {'cpu': 0.5, 'mem': 0.5}
	prompt_res = prompt.update(P_t)
	prompt_write = datavault.write('orchestrator', {'event': 'prompt_update', 'agent_id': agent_id, 'prompt': prompt_res})
	# 3. record replication event
	r = datavault.write('orchestrator', {'event': 'replicated', 'agent_id': agent_id})
	return {'ok': True, 'prompt': prompt_res, 'datavault': r, 'audit': audit, 'datavault_audit': audit_write, 'datavault_prompt': prompt_write}
