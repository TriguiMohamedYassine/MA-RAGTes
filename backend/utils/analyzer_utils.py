from typing import Any


def _iter_tests(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aplati récursivement les entrées de tests mochawesome."""
    out: list[dict[str, Any]] = []
    for item in results or []:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "test":
            out.append(item)
        children = item.get("suites") or []
        if isinstance(children, list) and children:
            out.extend(_iter_tests(children))
        direct_tests = item.get("tests") or []
        if isinstance(direct_tests, list):
            for t in direct_tests:
                if isinstance(t, dict):
                    out.append(t)
    return out


def _extract_failures(test_report: dict[str, Any]) -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    for test in _iter_tests(test_report.get("results", [])):
        state = (test.get("state") or "").lower()
        if state != "failed":
            continue
        title = test.get("fullTitle") or test.get("title") or "<unknown test>"
        err = test.get("err") if isinstance(test.get("err"), dict) else {}
        reason = err.get("message") or err.get("estack") or "Test en échec (raison inconnue)."
        reason = str(reason).splitlines()[0][:500]
        code_snippet = str(test.get("code") or "").strip()

        reason_l = reason.lower()
        if "is not a function" in reason_l:
            failure_type = "CALL_ERROR"
            fix = (
                "Vérifier le nom et la visibilité de la fonction (public/external). "
                "Si private/internal, supprimer le test direct et tester via une API publique."
            )
        elif "reverted with" in reason_l or "revert" in reason_l:
            failure_type = "REVERT_MISMATCH"
            fix = "Corriger le setup et les préconditions du test (rôles, état, autorisations, ordre des appels)."
        elif "expected undefined to deeply equal" in reason_l:
            failure_type = "ASSERTION_DATA_SHAPE"
            fix = (
                "Éviter les assertions deep.equal directes sur un champ de struct/tuple potentiellement non exposé "
                "par nom. Préférer des assertions robustes (getter dédié, événement, ou accès tuple cohérent)."
            )
        elif "expected" in reason_l:
            failure_type = "ASSERTION_MISMATCH"
            fix = "Corriger la valeur attendue selon le comportement réel on-chain (types BigInt/enum/string inclus)."
        else:
            failure_type = "OTHER"
            fix = "Corriger uniquement le test; ne pas modifier le contrat Solidity."

        failures.append({
            "test": str(title),
            "reason": reason,
            "type": failure_type,
            "fix": fix,
            "test_code": code_snippet,
        })
    return failures


def _extract_missing_coverage(coverage_report: dict[str, Any]) -> dict[str, list[str]]:
    missing = {"functions": [], "branches": [], "edge_cases": []}

    total = coverage_report.get("total") if isinstance(coverage_report, dict) else None
    if isinstance(total, dict):
        branches = total.get("branches") if isinstance(total.get("branches"), dict) else {}
        if branches.get("total", 0) and branches.get("pct", 0) < 80:
            missing["branches"].append(
                f"Couverture branches insuffisante: {branches.get('pct', 0)}% / 80%"
            )

        functions = total.get("functions") if isinstance(total.get("functions"), dict) else {}
        if functions.get("total", 0) and functions.get("pct", 0) < 85:
            missing["functions"].append(
                f"Couverture functions insuffisante: {functions.get('pct', 0)}% / 85%"
            )

        statements = total.get("statements") if isinstance(total.get("statements"), dict) else {}
        if statements.get("total", 0) and statements.get("pct", 0) < 85:
            missing["edge_cases"].append(
                f"Couverture statements insuffisante: {statements.get('pct', 0)}% / 85%"
            )
        return missing

    # coverage-final.json fallback: on ne détaille pas ici, car l'évaluateur prend
    # la décision finale via execution_summary déjà normalisé.
    return missing
