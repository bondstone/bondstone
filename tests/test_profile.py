"""Tests for docs/capabilities/profile.md. Each test carries the example ID it proves."""

from conftest import SYNC, change, fm, junit


def rules(findings):
    return {f.rule for f in findings}


# PROFILE-1 Documents

def test_PROFILE_1_1_unknown_status_is_a_parse_error(proj):
    proj.write({"docs/decisions/0001-x.md": fm("decision", "ADR-0001", "proposed") + "# X\n"})
    assert any(f.file == "docs/decisions/0001-x.md" for f in proj.findings("parse-error"))


def test_PROFILE_1_2_extra_keys_are_ignored(proj):
    proj.write({"docs/decisions/0001-x.md": fm("decision", "ADR-0001", owner="adam") + "# X\n"})
    assert not [f for f in proj.findings() if f.file == "docs/decisions/0001-x.md"]


# PROFILE-2 Roadmap and versions

def test_PROFILE_2_1_current_version_is_first_not_shipped(proj):
    roadmap = proj.root / "docs/roadmap.md"
    roadmap.write_text(roadmap.read_text().replace("Status: active", "Status: shipped"))
    assert proj.load().current.id == "V-1.1"


def test_PROFILE_2_2_unknown_version_status_is_a_parse_error(proj):
    roadmap = proj.root / "docs/roadmap.md"
    roadmap.write_text(roadmap.read_text().replace("Status: planned", "Status: beta"))
    assert any("beta" in f.message for f in proj.findings("parse-error"))


# PROFILE-3 Requirements and examples

def test_PROFILE_3_1_requirement_without_example(proj):
    proj.write({"docs/capabilities/sync.md": SYNC + "\n### SYNC-3 Bare\nRelease: V-1.0\n\nNo example.\n"})
    assert any("SYNC-3" in f.message for f in proj.findings("requirement-has-example"))


def test_PROFILE_3_2_example_must_carry_its_requirement_id(proj):
    proj.write({"docs/capabilities/sync.md": SYNC.replace("- SYNC-1.2:", "- SYNC-3.2:")})
    assert any("SYNC-3.2" in f.message for f in proj.findings("example-id-scoped"))


def test_PROFILE_3_3_plain_id_only_for_a_single_example(proj):
    proj.write({"docs/capabilities/sync.md": SYNC.replace("- SYNC-1.2:", "- SYNC-1:")})
    assert proj.findings("example-id-scoped")


def test_PROFILE_3_4_retired_id_cannot_return(proj):
    proj.write({"docs/capabilities/sync.md": SYNC.replace("retired: []", "retired: [SYNC-2]")})
    assert any("retired" in f.message for f in proj.findings("unique-ids"))


def test_PROFILE_3_5_item_lines_are_read(proj):
    proj.write({"docs/capabilities/sync.md": SYNC.replace(
        "### SYNC-2 Conflict notice\nRelease: V-1.0",
        "### SYNC-2 Conflict notice\nRelease: V-1.1 · Check: manual")})
    req = proj.load().requirements["SYNC-2"]
    assert req.release == "V-1.1" and req.manual


# PROFILE-4 Scope

def test_PROFILE_4_1_later_release_is_out_of_scope(proj):
    proj.write({"docs/capabilities/sync.md": SYNC.replace(
        "### SYNC-2 Conflict notice\nRelease: V-1.0", "### SYNC-2 Conflict notice\nRelease: V-1.1")})
    p = proj.load()
    assert p.in_scope(p.requirements["SYNC-1"]) and not p.in_scope(p.requirements["SYNC-2"])


def test_PROFILE_4_2_requirement_needs_a_release(proj):
    proj.write({"docs/capabilities/sync.md": SYNC.replace(
        "### SYNC-2 Conflict notice\nRelease: V-1.0\n", "### SYNC-2 Conflict notice\n")})
    assert any("SYNC-2" in f.message for f in proj.findings("requirement-has-release"))


def test_PROFILE_4_3_release_must_be_in_the_roadmap(proj):
    proj.write({"docs/capabilities/sync.md": SYNC.replace("Release: V-1.0", "Release: V-9.0", 1)})
    assert any("V-9.0" in f.message for f in proj.findings("no-dangling-links"))


# PROFILE-5 Evidence

def test_PROFILE_5_1_passing_example(proj):
    assert proj.load().examples["SYNC-1.1"].status == "passing"


def test_PROFILE_5_2_prefix_must_stand_alone(proj):
    proj.write({"tests/test_sync.py": "def test_ASYNC_2_retry():\n    pass\n",
                "build/test-results/junit.xml": junit(test_ASYNC_2_retry="pass")})
    assert proj.load().examples["SYNC-2"].status == "untested"


def test_PROFILE_5_3_plain_example_takes_scoped_name(proj):
    proj.write({"build/test-results/junit.xml": junit(test_SYNC_2_1_notice_names_devices="pass")})
    assert proj.load().examples["SYNC-2"].status == "passing"


def test_PROFILE_5_4_requirement_passes_when_every_example_passes(proj):
    p = proj.load()
    assert p.examples["SYNC-1.1"].status == "passing" and p.requirements["SYNC-1"].status == "untested"
    proj.write({"build/test-results/junit.xml": junit(test_SYNC_1_1_a="pass", test_SYNC_1_2_b="pass")})
    assert proj.load().requirements["SYNC-1"].status == "passing"


def test_PROFILE_5_5_a_failure_wins(proj):
    proj.write({"build/test-results/junit.xml": junit(test_SYNC_1_1_a="pass", test_SYNC_1_1_b="fail")})
    assert proj.load().requirements["SYNC-1"].status == "failing"


def test_PROFILE_5_6_test_file_without_report_is_linked(proj):
    proj.write({"build/test-results/junit.xml": None,
                "tests/test_sync.py": "def test_SYNC_2_notice():\n    pass\n"})
    assert proj.load().examples["SYNC-2"].status == "linked"


def test_PROFILE_5_7_unknown_id_in_test_name_warns(proj):
    proj.write({"tests/test_sync.py": "def test_SYNC_7_1_ghost():\n    pass\n"})
    assert any("SYNC-7.1" in f.message for f in proj.findings("test-links-unknown-id"))


# PROFILE-6 Version PRD: added, deferred and dropped

def test_PROFILE_6_1_added_lands_at_approval(proj):
    prd = proj.root / "plan/1.0/prd.md"
    prd.write_text(prd.read_text().replace("ADDED: SYNC-1, SYNC-2", "ADDED: SYNC-1, SYNC-2, SYNC-3"))
    assert any("SYNC-3" in f.message for f in proj.findings("delta-applied"))


def test_PROFILE_6_2_draft_prd_may_name_ids_not_yet_written(proj):
    prd = proj.root / "plan/1.0/prd.md"
    text = prd.read_text().replace("status: stable", "status: draft")
    text = text.replace("ADDED: SYNC-1, SYNC-2", "ADDED: SYNC-1, SYNC-2, SYNC-3")
    prd.write_text(text.replace("| ST-2 | Conflicts | SYNC-2 |", "| ST-2 | Conflicts | SYNC-2, SYNC-3 |"))
    assert not proj.findings("delta-applied") and not proj.findings("no-dangling-links")


def test_PROFILE_6_3_deferred_moves_the_release(proj):
    prd = proj.root / "plan/1.0/prd.md"
    prd.write_text(prd.read_text().replace("## Stories", "- DEFERRED: SYNC-2 to V-1.1\n\n## Stories"))
    assert any("SYNC-2" in f.message for f in proj.findings("delta-applied"))
    proj.write({"docs/capabilities/sync.md": SYNC.replace(
        "### SYNC-2 Conflict notice\nRelease: V-1.0", "### SYNC-2 Conflict notice\nRelease: V-1.1")})
    assert not proj.findings("delta-applied")


def test_PROFILE_6_4_dropped_is_deleted_and_retired(proj):
    prd = proj.root / "plan/1.0/prd.md"
    prd.write_text(prd.read_text().replace("## Stories", "- DROPPED: SYNC-2\n\n## Stories"))
    assert proj.findings("delta-applied")
    cut = SYNC[:SYNC.index("### SYNC-2")].replace("retired: []", "retired: [SYNC-2]")
    proj.write({"docs/capabilities/sync.md": cut})
    assert not proj.findings("delta-applied")


# PROFILE-7 Modified and removed land with the story

V11 = fm("prd", "PRD-1.1", version="V-1.1") + """
# PRD-1.1

## Deltas

- MODIFIED: SYNC-1
- REMOVED: SYNC-2

## Stories

| ID | Title | Proves | Removes | Depends on |
| --- | --- | --- | --- | --- |
| ST-3 | Upload in batches | SYNC-1 | | |
| ST-4 | Drop notices | | SYNC-2 | |
"""


def shipped(proj):
    roadmap = proj.root / "docs/roadmap.md"
    roadmap.write_text(roadmap.read_text().replace("Status: active", "Status: shipped"))
    return proj.write({"plan/1.1/prd.md": V11})


def test_PROFILE_7_1_modified_waits_with_pending_marker(proj):
    shipped(proj)
    assert any("Pending: PRD-1.1" in f.message for f in proj.findings("delta-applied"))
    proj.write({"docs/capabilities/sync.md": SYNC.replace("Release: V-1.0", "Release: V-1.0 · Pending: PRD-1.1")})
    assert not proj.findings("delta-applied")


def test_PROFILE_7_2_finished_story_clears_the_marker(proj):
    shipped(proj).write({"docs/capabilities/sync.md": SYNC.replace("Release: V-1.0", "Release: V-1.0 · Pending: PRD-1.1")})
    proj.add_change("010-batches", change("ST-3", ["SYNC-1"], tasks=[True], living="- SYNC-1 wording"))
    assert any("clear `Pending: PRD-1.1`" in f.message for f in proj.findings("delta-applied"))


def test_PROFILE_7_3_removed_by_finished_story_is_retired(proj):
    shipped(proj).write({"docs/capabilities/sync.md": SYNC.replace("Release: V-1.0", "Release: V-1.0 · Pending: PRD-1.1")})
    proj.add_change("011-drop", change("ST-4", [], removes=["SYNC-2"], tasks=[True], living="- removed SYNC-2"))
    assert any("SYNC-2" in f.message and "retired" in f.message for f in proj.findings("delta-applied"))


def test_PROFILE_7_4_modified_needs_a_story(proj):
    shipped(proj)
    prd = proj.root / "plan/1.1/prd.md"
    prd.write_text(prd.read_text().replace("| ST-3 | Upload in batches | SYNC-1 |", "| ST-3 | Upload in batches | |"))
    assert any("SYNC-1" in f.message for f in proj.findings("delta-has-story"))


# PROFILE-8 Stories

def test_PROFILE_8_1_story_waits_for_its_dependencies(proj):
    p = proj.load()
    assert p.stories["ST-1"].status == "ready" and p.stories["ST-2"].status == "blocked"


def test_PROFILE_8_2_status_column_must_match(proj):
    prd = proj.root / "plan/1.0/prd.md"
    prd.write_text(prd.read_text().replace("| ST-1 | Offline edits | SYNC-1 | — | |",
                                           "| ST-1 | Offline edits | SYNC-1 | — | done |"))
    assert any("ST-1" in f.message for f in proj.findings("story-status-stale"))


def test_PROFILE_8_3_story_ids_are_unique(proj):
    prd = proj.root / "plan/1.0/prd.md"
    prd.write_text(prd.read_text().replace("| ST-2 |", "| ST-1 |"))
    assert any("ST-1" in f.message for f in proj.findings("unique-ids"))


def test_PROFILE_8_4_epics_hold_story_tables(proj):
    proj.write({"plan/1.0/epics/EP-1-offline.md": fm("epic", "EP-1") + """
# EP-1

## Stories

| ID | Title | Proves |
| --- | --- | --- |
| ST-9 | Upload once | SYNC-1.2 |
"""})
    p = proj.load()
    assert p.stories["ST-9"].epic == "EP-1"


# PROFILE-9 Phases

def phase(p, pid):
    return next(x for x in p.phases() if x["id"] == pid)


def test_PROFILE_9_1_inception_ends_with_approved_brief(proj):
    assert phase(proj.load(), 0)["state"] == "done"
    brief = proj.root / "docs/brief.md"
    brief.write_text(brief.read_text().replace("status: stable", "status: draft"))
    assert phase(proj.load(), 0)["open"] == ["approve BRIEF"]


def test_PROFILE_9_2_shape_needs_approved_prd(proj):
    prd = proj.root / "plan/1.0/prd.md"
    prd.write_text(prd.read_text().replace("status: stable", "status: draft"))
    assert phase(proj.load(), 1)["open"] == ["approve PRD-1.0"]


def test_PROFILE_9_3_foundation_needs_a_passing_test(proj):
    proj.write({"build/test-results/junit.xml": junit(test_SYNC_1_1_a="fail")})
    assert any("passing test" in o for o in phase(proj.load(), 2)["open"])


def test_PROFILE_9_4_release_follows_build(proj):
    proj.add_change("001-offline", change("ST-1", ["SYNC-1"], tasks=[True], living="- none"))
    proj.add_change("002-conflict", change("ST-2", ["SYNC-2"], tasks=[True], living="- none"))
    proj.write({"build/test-results/junit.xml": junit(test_SYNC_1_1_a="pass", test_SYNC_1_2_b="pass",
                                                      test_SYNC_2_c="pass")})
    p = proj.load()
    assert phase(p, 3)["state"] == "done"
    assert "write plan/1.0/release.md" in phase(p, 4)["open"]


def test_PROFILE_9_5_next_version_phase_needs_its_prd(proj):
    roadmap = proj.root / "docs/roadmap.md"
    roadmap.write_text(roadmap.read_text().replace("Status: active", "Status: shipped"))
    assert phase(proj.load(), 6)["open"] == ["write plan/1.1/prd.md"]
