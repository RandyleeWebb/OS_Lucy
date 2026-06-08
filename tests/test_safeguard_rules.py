from src.safeguard.main import compute_scores, compute_S, RULE_WEIGHTS


def test_simple_scores():
	action = "print('hello')"
	scores = compute_scores(action, {'code': "print('hello')"})
	S = compute_S(scores, RULE_WEIGHTS)
	assert isinstance(S, float)
	assert 0.0 <= S <= 1.0
