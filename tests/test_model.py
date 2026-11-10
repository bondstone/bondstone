from bondstone.model import ERROR, IGNORE, INFO, WARN, Diagnostic, rank


def test_severities_are_ordered():
    assert rank(IGNORE) < rank(INFO) < rank(WARN) < rank(ERROR)


def test_diagnostic_json_omits_absent_values_and_keeps_key_order():
    diag = Diagnostic("bondstone/view-stale", ERROR, "out of date", path="docs/generated/x.md",
                      hint="Run `bondstone gen`.", fix={"command": ["bondstone", "gen"]})
    assert list(diag.to_dict()) == ["rule", "severity", "path", "message", "hint", "fix"]
    assert diag.to_dict()["fix"] == {"command": ["bondstone", "gen"]}
