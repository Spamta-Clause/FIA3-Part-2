# datastore.py Performance Benchmark

Generated: 2026-10-05 11:05:33

| Method | Iterations | Avg time (ms) | Total time (ms) | Running total (ms) |
|---|---|---|---|---|
| `add_members` | 1 | 0.8476 | 0.8476 | 0.8476 |
| `add_game_to_loan` | 1 | 0.5334 | 0.5334 | 1.3810 |
| `update_hold` | 1 | 0.4640 | 0.4640 | 1.8450 |
| `update_loan` | 1 | 0.4535 | 0.4535 | 2.2985 |
| `update_member_status` | 1 | 0.4496 | 0.4496 | 2.7481 |
| `update_fees` | 1 | 0.4301 | 0.4301 | 3.1782 |
| `update_password` | 1 | 0.4295 | 0.4295 | 3.6077 |
| `add_annual_fees` | 1 | 0.4294 | 0.4294 | 4.0371 |
| `add_game` | 1 | 0.4150 | 0.4150 | 4.4521 |
| `add_loan` | 1 | 0.3709 | 0.3709 | 4.8230 |
| `delete_game` | 1 | 0.3128 | 0.3128 | 5.1359 |
| `get_game_name` | 200 | 0.0814 | 16.2865 | 21.4224 |
| `get_games_players` | 200 | 0.0734 | 14.6755 | 36.0980 |
| `get_catalogue` | 200 | 0.0516 | 10.3282 | 46.4261 |
| `get_all_members` | 200 | 0.0352 | 7.0444 | 53.4705 |
| `get_games_age` | 200 | 0.0350 | 6.9916 | 60.4622 |
| `get_games_available` | 200 | 0.0346 | 6.9267 | 67.3889 |
| `get_members` | 200 | 0.0188 | 3.7562 | 71.1451 |
| `get_games_on_hold` | 200 | 0.0131 | 2.6190 | 73.7641 |
| `get_games` | 200 | 0.0130 | 2.5990 | 76.3632 |
| `get_fees` | 200 | 0.0109 | 2.1899 | 78.5531 |
| `get_games_on_loan` | 200 | 0.0078 | 1.5603 | 80.1134 |
| `get_member_by_email` | 200 | 0.0067 | 1.3304 | 81.4438 |
| `get_categories` | 200 | 0.0062 | 1.2343 | 82.6781 |
| `get_mem_held_games` | 200 | 0.0058 | 1.1616 | 83.8397 |
| `get_members_games` | 200 | 0.0055 | 1.1025 | 84.9423 |
| `get_latest_loan_id` | 200 | 0.0042 | 0.8338 | 85.7761 |
| `date_today` | 200 | 0.0030 | 0.5902 | 86.3663 |
