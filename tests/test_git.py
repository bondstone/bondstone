"""The git layer, on throwaway repositories built in each test."""

import pytest
from conftest import Project

from bondstone.git import ADDED, DELETED, MODIFIED, Change, ChangedLines, GitRepository, Trailer
from bondstone.model import EnvironmentProblem


@pytest.fixture
def repo(project) -> Project:
    project.init().write("a.txt", "one\ntwo\nthree\n")
    project.commit("first")
    return project


def changes(project: Project, base: str = "HEAD") -> list[Change]:
    git = GitRepository(project.root)
    return git.changes(git.commit(base))


# --------------------------------------------------------------------------- repository and refs


def test_a_folder_outside_git_is_an_environment_problem(tmp_path):
    with pytest.raises(EnvironmentProblem, match="not inside a git repository"):
        GitRepository(tmp_path)


def test_commit_resolves_refs_and_returns_none_for_unknown_ones(repo):
    git = GitRepository(repo.root)
    head = repo.git("rev-parse", "HEAD")
    assert git.commit("HEAD") == head
    assert git.commit("main") == head
    assert git.commit(head[:8]) == head
    assert git.commit("origin/main") is None
    assert git.commit("--all") is None
    assert git.commit("") is None


def test_merge_base_is_where_the_branch_left_the_base(repo):
    fork = repo.git("rev-parse", "HEAD")
    repo.git("checkout", "--quiet", "-b", "feature")
    repo.write("b.txt", "b\n").commit("on the branch")
    repo.git("checkout", "--quiet", "main")
    repo.write("c.txt", "c\n").commit("main moved on")
    repo.git("checkout", "--quiet", "feature")
    assert GitRepository(repo.root).merge_base("main") == fork
    # so what main gained after the fork is not a change of this branch
    assert changes(repo, fork) == [Change("b.txt", ADDED)]


def test_merge_base_of_an_unknown_ref_is_an_environment_problem(repo):
    with pytest.raises(EnvironmentProblem, match="'origin/main' is not a commit"):
        GitRepository(repo.root).merge_base("origin/main")


def test_merge_base_without_commits_is_an_environment_problem(project):
    project.init()
    with pytest.raises(EnvironmentProblem):
        GitRepository(project.root).merge_base("HEAD")


def test_merge_base_of_unrelated_histories_is_an_environment_problem(repo):
    repo.git("checkout", "--quiet", "--orphan", "other")
    repo.commit("unrelated")
    with pytest.raises(EnvironmentProblem, match="no common commit"):
        GitRepository(repo.root).merge_base("main")


# --------------------------------------------------------------------------- changed files


def test_no_changes(repo):
    assert changes(repo) == []


def test_committed_and_uncommitted_changes_are_both_seen(repo):
    base = repo.git("rev-parse", "HEAD")
    repo.write("new.txt", "n\n").commit("add a file")
    repo.write("a.txt", "one\nTWO\nthree\n")  # not committed, not staged
    assert changes(repo, base) == [Change("a.txt", MODIFIED), Change("new.txt", ADDED)]


def test_untracked_files_are_added_and_ignored_files_are_left_out(repo):
    repo.write(".gitignore", "*.log\n").commit("ignore logs")
    repo.write("untracked.txt", "u\n").write("debug.log", "noise\n")
    assert changes(repo) == [Change("untracked.txt", ADDED)]


def test_deleted_files(repo):
    (repo.root / "a.txt").unlink()
    assert changes(repo) == [Change("a.txt", DELETED)]


def test_a_rename_is_a_modification_that_keeps_the_old_path(repo):
    repo.git("mv", "a.txt", "renamed.txt")
    assert changes(repo) == [Change("renamed.txt", MODIFIED, "a.txt")]


def test_paths_with_spaces_and_non_ascii_names(repo):
    repo.write("docs/zażółć gęślą.md", "x\n")
    assert changes(repo) == [Change("docs/zażółć gęślą.md", ADDED)]


def test_paths_are_relative_to_the_root_when_it_is_a_subfolder(repo):
    repo.write("sub/inner.txt", "1\n").write("outside.txt", "1\n")
    base = repo.commit("add")
    repo.write("sub/inner.txt", "2\n").write("outside.txt", "2\n").write("sub/new.txt", "n\n")
    git = GitRepository(repo.root / "sub")
    assert git.changes(base) == [Change("inner.txt", MODIFIED), Change("new.txt", ADDED)]
    assert git.file_at(base, "inner.txt") == "1\n"


# --------------------------------------------------------------------------- file contents and lines


def test_file_at_a_commit(repo):
    base = repo.git("rev-parse", "HEAD")
    repo.write("a.txt", "changed\n").commit("change")
    git = GitRepository(repo.root)
    assert git.file_at(base, "a.txt") == "one\ntwo\nthree\n"
    assert git.file_at("HEAD", "a.txt") == "changed\n"
    assert git.file_at(base, "missing.txt") is None


def lines(project: Project, change: Change) -> ChangedLines:
    git = GitRepository(project.root)
    return git.changed_lines(git.commit("HEAD"), change)


def test_changed_lines_of_an_edit(repo):
    repo.write("a.txt", "one\nTWO\nthree\nfour\n")
    assert lines(repo, Change("a.txt", MODIFIED)) == ChangedLines(frozenset({2, 4}), frozenset({2}))


def test_changed_lines_of_a_removal_are_lines_of_the_file_at_the_base(repo):
    repo.write("a.txt", "one\nthree\n")
    assert lines(repo, Change("a.txt", MODIFIED)) == ChangedLines(frozenset(), frozenset({2}))


def test_changed_lines_of_a_renamed_file(repo):
    repo.write("a.txt", "".join(f"line {n}\n" for n in range(1, 21))).commit("longer")
    repo.git("mv", "a.txt", "b.txt")
    repo.edit("b.txt", "line 7\n", "line seven\n")
    assert lines(repo, Change("b.txt", MODIFIED, "a.txt")) == ChangedLines(frozenset({7}), frozenset({7}))


# --------------------------------------------------------------------------- trailers


def test_trailers_of_the_commits_since_the_base_newest_first(repo):
    base = repo.git("rev-parse", "HEAD")
    first = repo.commit("Move code\n\nNo behaviour change.\n\nSpec-Impact: none (pure move)\nReviewed-by: Ann")
    repo.commit("Plain commit")
    last = repo.commit("Rename\n\nspec-impact: none [CAP-a, CAP-b] (rename only)")
    assert GitRepository(repo.root).trailers(base) == [
        Trailer(last, "spec-impact", "none [CAP-a, CAP-b] (rename only)"),
        Trailer(first, "Spec-Impact", "none (pure move)"),
        Trailer(first, "Reviewed-by", "Ann"),
    ]


def test_trailers_before_the_base_and_lines_in_the_body_do_not_count(repo):
    repo.commit("Old\n\nSpec-Impact: none (before the base)")
    base = repo.git("rev-parse", "HEAD")
    repo.commit("New\n\nNote: this line is in the body, not a trailer\n\nMore text at the end.")
    assert GitRepository(repo.root).trailers(base) == []


def test_a_folded_trailer_value_is_joined(repo):
    base = repo.git("rev-parse", "HEAD")
    commit = repo.commit("Move\n\nSpec-Impact: none (a reason that is long enough\n  to continue on a second line)")
    assert GitRepository(repo.root).trailers(base) == [
        Trailer(commit, "Spec-Impact", "none (a reason that is long enough to continue on a second line)")]
