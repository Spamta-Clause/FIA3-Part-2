import argparse
import shutil
import sqlite3
import tempfile
import timeit
from datetime import date, datetime
from pathlib import Path

import pytest

from datastore import Datastore

LIVE_DB = Path(__file__).parent / "TableTopGamers.db"


@pytest.fixture
def datastore(tmp_path):
    db_copy = tmp_path / "test.db"
    shutil.copy(LIVE_DB, db_copy)
    return Datastore(str(db_copy))


# ----- GET methods ----- #
def test_get_catalogue_shape(datastore):
    catalogue = datastore.get_catalogue()

    assert len(catalogue) == 36
    game_id, name, category, min_p, max_p, min_age, status, on_hold = catalogue[0]
    assert isinstance(game_id, int)
    assert isinstance(name, str)
    assert status == "Now" or status.startswith("Loaned on ")
    assert isinstance(on_hold, bool)


def test_get_catalogue_status_reflects_most_recent_loan(datastore):
    """Regression test: get_catalogue() used to take independent MAX(loan_date)
    and MAX(return_date) across every loan a game has ever had, so an old,
    already-returned loan could mask a game's current, still-open loan."""
    game_id = next(g[0] for g in datastore.get_games_available())

    loan_id_1 = datastore.add_loan(1)
    datastore.add_game_to_loan(loan_id_1, game_id)
    datastore.update_loan(game_id)  # borrow and return once, on record

    loan_id_2 = datastore.add_loan(1)
    datastore.add_game_to_loan(loan_id_2, game_id)  # borrow again, currently open

    game = next(g for g in datastore.get_catalogue() if g[0] == game_id)
    assert game[6] != "Now", "a game with a newer open loan must not show as available"


def test_get_game_name_filters_case_insensitively(datastore):
    results = datastore.get_game_name("gloom")

    assert any(g[1] == "Gloomhaven" for g in results)
    assert all("gloom" in g[1].lower() for g in results)


def test_get_games_players_filters_range(datastore):
    results = datastore.get_games_players(4)

    assert results
    assert all(g[3] <= 4 <= g[4] for g in results)


def test_get_games_age_filters(datastore):
    results = datastore.get_games_age(10)

    assert results
    assert all(g[5] <= 10 for g in results)


def test_get_games_available_returns_available_games(datastore):
    results = datastore.get_games_available()

    assert results  # regression: this used to always return []
    ids = {g[0] for g in results}
    assert 27 not in ids  # Jumanji is currently on loan
    assert all(g[6] == "Now" for g in results)


def test_get_games_on_hold(datastore):
    results = datastore.get_games_on_hold()

    ids = {g[0] for g in results}
    assert {1, 2, 8, 20}.issubset(ids)
    assert all(g[7] is True for g in results)


def test_get_members_only_active(datastore):
    ids = {m[0] for m in datastore.get_members()}

    assert 1 in ids  # Jane Kaczmarek, active
    assert 2 not in ids  # Adam Pascal, inactive


def test_get_all_members_includes_inactive(datastore):
    ids = {m[0] for m in datastore.get_all_members()}

    assert {1, 2}.issubset(ids)


def test_get_member_by_email(datastore):
    member = datastore.get_member_by_email("jkaczmarek@gmail.com")

    assert member is not None
    assert member[0] == 1
    assert datastore.get_member_by_email("nobody@example.com") is None


def test_get_games_dropdown(datastore):
    results = datastore.get_games()

    assert len(results) == 36
    assert all(len(g) == 2 for g in results)


def test_get_games_on_loan_excludes_returned(datastore):
    names = {g[0] for g in datastore.get_games_on_loan()}

    assert "Jumanji" in names  # currently open loan
    assert "Star Wars Rebellion" not in names  # regression: fully returned game


def test_get_categories(datastore):
    results = datastore.get_categories()

    assert len(results) == 9
    assert (1, "Strategy") in results


def test_get_members_games(datastore):
    assert datastore.get_members_games(19) == [(27, "Jumanji")]


def test_get_fees(datastore):
    fees = datastore.get_fees(1)

    assert (2020, False) in fees
    assert (2021, True) in fees


def test_get_latest_loan_id_increments(datastore):
    before = datastore.get_latest_loan_id()
    datastore.add_loan(1)

    assert datastore.get_latest_loan_id() == before + 1


def test_get_mem_held_games(datastore):
    results = datastore.get_mem_held_games()

    assert (1, 1) in results
    assert (2, 5) in results


# ----- ADD methods ----- #
def test_add_members_inserts_row(datastore):
    datastore.add_members("Test", "User", "testuser@example.com", "pw", "0000000", 0)

    member = datastore.get_member_by_email("testuser@example.com")
    assert member is not None
    assert member[1:3] == ("Test", "User")
    assert member[6] == 1  # active


def test_add_loan_returns_new_loan_id(datastore):
    before = datastore.get_latest_loan_id()

    assert datastore.add_loan(1) == before + 1


def test_add_game_to_loan(datastore):
    loan_id = datastore.add_loan(1)
    datastore.add_game_to_loan(loan_id, 5)

    assert (5, "Scrabble") in datastore.get_members_games(1)


def test_add_game(datastore):
    datastore.add_game("New Game", 1, 2, 4, 8, None)

    matches = datastore.get_game_name("New Game")
    assert len(matches) == 1
    assert matches[0][6] == "Now"


def test_add_annual_fees_creates_fee_for_every_active_member(datastore):
    datastore.add_annual_fees(2999, 150)

    assert (2999, False) in datastore.get_fees(1)


def test_add_annual_fees_duplicate_raises_integrity_error(datastore):
    datastore.add_annual_fees(2998, 150)

    with pytest.raises(sqlite3.IntegrityError):
        datastore.add_annual_fees(2998, 150)


# ----- UPDATE methods ----- #
def test_update_hold_toggles(datastore):
    already_held = {1, 2, 8, 20}
    game_id = next(
        g[0] for g in datastore.get_games_available() if g[0] not in already_held
    )

    datastore.update_hold(6, game_id)
    assert (game_id, 6) in datastore.get_mem_held_games()

    datastore.update_hold(6, game_id)
    assert (game_id, 6) not in datastore.get_mem_held_games()


def test_update_loan_only_closes_open_loan(datastore):
    """Regression test: update_loan() used to update every games_loaned row
    for a game_id, corrupting already-closed historical loan rows."""
    game_id = next(g[0] for g in datastore.get_games_available())

    loan_id_1 = datastore.add_loan(1)
    datastore.add_game_to_loan(loan_id_1, game_id)
    datastore.cursor.execute(
        "UPDATE games_loaned SET return_date = '2000-01-01' WHERE loan_id = ? AND game_id = ?",
        (loan_id_1, game_id),
    )
    datastore.connection.commit()

    loan_id_2 = datastore.add_loan(1)
    datastore.add_game_to_loan(loan_id_2, game_id)

    datastore.update_loan(game_id)

    datastore.cursor.execute(
        "SELECT loan_id, return_date FROM games_loaned WHERE game_id = ?", (game_id,)
    )
    rows = dict(datastore.cursor.fetchall())
    assert rows[loan_id_1] == "2000-01-01"
    assert rows[loan_id_2] == datastore.date_today()


def test_update_member_status_toggles(datastore):
    active_ids = {m[0] for m in datastore.get_members()}
    assert 1 in active_ids

    datastore.update_member_status(1)
    assert 1 not in {m[0] for m in datastore.get_members()}

    datastore.update_member_status(1)
    assert 1 in {m[0] for m in datastore.get_members()}


def test_update_fees_marks_paid(datastore):
    assert (2020, False) in datastore.get_fees(1)

    datastore.update_fees(2020, 1)
    assert (2020, True) in datastore.get_fees(1)


def test_update_password(datastore):
    datastore.update_password(1, "newhash")

    member = datastore.get_member_by_email("jkaczmarek@gmail.com")
    assert member[4] == "newhash"


# ----- DELETE methods ----- #
def test_delete_game_removes_row(datastore):
    datastore.delete_game(5)

    assert datastore.get_game_name("Scrabble") == []


# ----- misc ----- #
def test_date_today_format(datastore):
    assert datastore.date_today() == date.today().strftime("%Y-%m-%d")


# ----- performance benchmark (not collected by pytest) ----- #
READ_ITERATIONS = 200


def _fresh_datastore(tmp_dir: Path) -> Datastore:
    db_copy = tmp_dir / "benchmark.db"
    shutil.copy(LIVE_DB, db_copy)
    return Datastore(str(db_copy))


def run_benchmark():
    from rich.console import Console
    from rich.table import Table

    console = Console()
    results = []  # (label, iterations, avg_ms, total_ms)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        db = _fresh_datastore(tmp_path)

        read_benchmarks = [
            ("get_catalogue", lambda: db.get_catalogue()),
            ("get_game_name", lambda: db.get_game_name("a")),
            ("get_games_players", lambda: db.get_games_players(4)),
            ("get_games_age", lambda: db.get_games_age(10)),
            ("get_games_available", lambda: db.get_games_available()),
            ("get_games_on_hold", lambda: db.get_games_on_hold()),
            ("get_members", lambda: db.get_members()),
            ("get_all_members", lambda: db.get_all_members()),
            ("get_member_by_email", lambda: db.get_member_by_email("jkaczmarek@gmail.com")),
            ("get_games", lambda: db.get_games()),
            ("get_games_on_loan", lambda: db.get_games_on_loan()),
            ("get_categories", lambda: db.get_categories()),
            ("get_members_games", lambda: db.get_members_games(19)),
            ("get_fees", lambda: db.get_fees(1)),
            ("get_latest_loan_id", lambda: db.get_latest_loan_id()),
            ("get_mem_held_games", lambda: db.get_mem_held_games()),
            ("date_today", lambda: db.date_today()),
        ]

        for label, func in read_benchmarks:
            elapsed = timeit.timeit(func, number=READ_ITERATIONS)
            results.append((
                label,
                READ_ITERATIONS,
                elapsed / READ_ITERATIONS * 1000,  # avg ms per call
                elapsed * 1000,                    # total ms for all calls
            ))

        # Mutating methods change state on every call, so repeating them
        # thousands of times either fails outright (duplicate keys) or
        # measures something unrealistic. Each gets a fresh copy of the
        # database and is timed for a single representative call instead.
        mutating_benchmarks = [
            ("add_members", lambda: db.add_members("Bench", "Mark", "bench@example.com", "pw", "000", 0)),
            ("add_loan", lambda: db.add_loan(1)),
            ("add_game_to_loan", lambda: db.add_game_to_loan(db.get_latest_loan_id(), 5)),
            ("add_game", lambda: db.add_game("Bench Game", 1, 1, 4, 8, None)),
            ("add_annual_fees", lambda: db.add_annual_fees(2500, 100)),
            ("update_hold", lambda: db.update_hold(1, 6)),
            ("update_loan", lambda: db.update_loan(27)),
            ("update_member_status", lambda: db.update_member_status(1)),
            ("update_fees", lambda: db.update_fees(2020, 1)),
            ("update_password", lambda: db.update_password(1, "hashed")),
            ("delete_game", lambda: db.delete_game(5)),
        ]

        for label, func in mutating_benchmarks:
            db.connection.close()  # release the previous copy's file handle (Windows)
            db = _fresh_datastore(tmp_path)
            elapsed = timeit.timeit(func, number=1)
            results.append((label, 1, elapsed * 1000, elapsed * 1000))

        db.connection.close()

    # slowest first, then add a running total down the sorted rows
    sorted_results = sorted(results, key=lambda r: -r[2])

    rows = []
    running_ms = 0
    for label, iterations, avg_ms, total_ms in sorted_results:
        running_ms += total_ms
        rows.append((label, iterations, avg_ms, total_ms, running_ms))

    table = Table(title="datastore.py performance")
    table.add_column("Method")
    table.add_column("Iterations", justify="right")
    table.add_column("Avg time (ms)", justify="right")
    table.add_column("Total time (ms)", justify="right")
    table.add_column("Running total (ms)", justify="right")

    for label, iterations, avg_ms, total_ms, running_ms in rows:
        table.add_row(
            label,
            str(iterations),
            f"{avg_ms:.4f}",
            f"{total_ms:.4f}",
            f"{running_ms:.4f}",
        )

    console.print(table)

    report_path = Path(__file__).parent / "test_results" / "benchmark_results.md"
    report_path.parent.mkdir(exist_ok=True)
    lines = [
        "# datastore.py Performance Benchmark",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "| Method | Iterations | Avg time (ms) | Total time (ms) | Running total (ms) |",
        "|---|---|---|---|---|",
    ]
    lines += [
        f"| `{label}` | {iterations} | {avg_ms:.4f} | {total_ms:.4f} | {running_ms:.4f} |"
        for label, iterations, avg_ms, total_ms, running_ms in rows
    ]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    console.print(f"Markdown report written to {report_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="datastore.py test/benchmark program")
    parser.add_argument(
        "--benchmark", action="store_true", help="run the performance benchmark"
    )
    args = parser.parse_args()

    if args.benchmark:
        run_benchmark()
    else:
        print("Run correctness tests with: pytest test_datastore.py")
        print("Run the performance benchmark with: python test_datastore.py --benchmark")
