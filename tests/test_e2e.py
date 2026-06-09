def test_full_revisions_and_contradictions_workflow(run_saturn, tmp_path):
    assert run_saturn(tmp_path, "init").returncode == 0

    r1 = run_saturn(tmp_path, "facts", "add", "--subject", "Saturn",
                     "--predicate", "is", "--object", "planet")
    assert r1.returncode == 0
    fact1_id = r1.stdout.strip().split()[-1]

    r2 = run_saturn(tmp_path, "facts", "add", "--subject", "Saturn",
                     "--predicate", "is", "--object", "star")
    assert r2.returncode == 0

    r = run_saturn(tmp_path, "contradictions", "list")
    assert r.returncode == 0
    assert "open" in r.stdout

    lines = [l for l in r.stdout.split("\n") if l.strip()]
    contradiction_id = lines[2].split()[0]

    r = run_saturn(tmp_path, "contradictions", "resolve", contradiction_id, "--action", "keep_a")
    assert r.returncode == 0

    r = run_saturn(tmp_path, "contradictions", "list", "--all")
    assert r.returncode == 0
    assert "resolved" in r.stdout

    r = run_saturn(tmp_path, "revisions", "list", "--entity-type", "fact")
    assert r.returncode == 0
    assert "created" in r.stdout

    r = run_saturn(tmp_path, "facts", "update", fact1_id, "--object", "gas giant")
    assert r.returncode == 0

    r = run_saturn(tmp_path, "query", "Saturn")
    assert r.returncode == 0
    assert "gas giant" in r.stdout

    r = run_saturn(tmp_path, "facts", "archive", fact1_id)
    assert r.returncode == 0

    r = run_saturn(tmp_path, "query", "Saturn")
    assert r.returncode == 0
    assert "No matching facts found" in r.stdout

    r = run_saturn(tmp_path, "query", "Saturn", "--include-archived")
    assert r.returncode == 0
    assert "gas giant" in r.stdout


def test_full_cli_happy_path(run_saturn, tmp_path):
    assert run_saturn(tmp_path, "init").returncode == 0
    assert (
        run_saturn(
            tmp_path,
            "facts",
            "add",
            "--subject",
            "Saturn",
            "--predicate",
            "is",
            "--object",
            "a memory quality engine",
            "--source",
            "project overview",
            "--confidence",
            "0.9",
        ).returncode
        == 0
    )

    query_result = run_saturn(tmp_path, "query", "Saturn")
    doctor_result = run_saturn(tmp_path, "doctor")

    assert "Saturn | is | a memory quality engine" in query_result.stdout
    assert doctor_result.returncode == 0
    assert "Workspace health: OK" in doctor_result.stdout
