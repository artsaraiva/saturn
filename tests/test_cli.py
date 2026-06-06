def test_help_lists_phase_one_commands(run_saturn, tmp_path):
    result = run_saturn(tmp_path, "--help")

    assert result.returncode == 0
    assert "init" in result.stdout
    assert "facts" in result.stdout
    assert "query" in result.stdout
    assert "doctor" in result.stdout


def test_root_command_requires_a_subcommand(run_saturn, tmp_path):
    result = run_saturn(tmp_path)

    assert result.returncode != 0
    assert "usage:" in result.stderr


def test_facts_requires_a_subcommand(run_saturn, tmp_path):
    result = run_saturn(tmp_path, "facts")

    assert result.returncode != 0
    assert "usage:" in result.stderr
