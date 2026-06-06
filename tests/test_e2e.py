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
