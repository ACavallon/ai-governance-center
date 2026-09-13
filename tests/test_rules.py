import sys
sys.path.insert(0, "/mnt/data/ai-governance-center/backend")
from app.rule_engine import evaluate_expression

def test_all_true():
    facts={"deployment":{"decision_domain":"EMPLOYMENT","function":"ranking"}}
    expr={"all":[{"fact":"deployment.decision_domain","operator":"eq","value":"EMPLOYMENT"},{"fact":"deployment.function","operator":"in","value":["ranking","selection"]}]}
    assert evaluate_expression(expr,facts) is True

def test_unknown():
    facts={"deployment":{}}
    expr={"fact":"deployment.function","operator":"eq","value":"ranking"}
    assert evaluate_expression(expr,facts) is None
