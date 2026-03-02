from taskvarios.storage import load_sultandb, save_sultandb


def test_load_sultandb_missing_file_returns_empty_lists(tmp_path):
    missing = tmp_path / "missing.json"
    aors, projects = load_sultandb(str(missing))
    assert aors == []
    assert projects == []


def test_load_sultandb_handles_corrupt_json(tmp_path):
    db_file = tmp_path / "variosdb.json"
    db_file.write_text("{not-json", encoding="utf-8")
    aors, projects = load_sultandb(str(db_file))
    assert aors == []
    assert projects == []


def test_load_sultandb_handles_missing_keys(tmp_path):
    db_file = tmp_path / "variosdb.json"
    db_file.write_text('{"aors":[{"name":"x"}]}', encoding="utf-8")
    aors, projects = load_sultandb(str(db_file))
    assert aors == [{"name": "x"}]
    assert projects == []


def test_save_then_load_round_trip(tmp_path):
    db_file = tmp_path / "variosdb.json"
    expected_aors = [{"name": "home"}]
    expected_projects = [{"name": "work"}]
    save_sultandb(str(db_file), expected_aors, expected_projects)
    aors, projects = load_sultandb(str(db_file))
    assert aors == expected_aors
    assert projects == expected_projects
