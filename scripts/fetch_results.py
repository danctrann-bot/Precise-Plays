import os
import csv
import requests
from datetime import datetime, timezone, timedelta

ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard"

def get_yesterdays_results():
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y%m%d")
    response = requests.get(f"{ESPN_BASE}?dates={yesterday}")
    games = response.json().get("events", [])
    results = {}
    for game in games:
        try:
            competitions = game.get("competitions", [{}])[0]
            competitors = competitions.get("competitors", [])
            home = next(t for t in competitors if t["homeAway"] == "home")
            away = next(t for t in competitors if t["homeAway"] == "away")
            home_team = home["team"]["abbreviation"]
            away_team = away["team"]["abbreviation"]
            home_score = int(home["score"])
            away_score = int(away["score"])
            winner = home_team if home_score > away_score else away_team
            total = home_score + away_score
            results[f"{away_team}@{home_team}"] = {
                "home_team": home_team,
                "away_team": away_team,
                "home_score": home_score,
                "away_score": away_score,
                "winner": winner,
                "total": total,
                "game_date": yesterday
            }
        except Exception as e:
            print(f"Error parsing game: {e}")
    return results

def match_and_update():
    filepath = "data/mlb/markets.csv"
    if not os.path.exists(filepath):
        print("No markets CSV found")
        return

    results = get_yesterdays_results()
    rows = []

    with open(filepath, "r") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        if "result_winner" not in fieldnames:
            fieldnames = fieldnames + ["result_winner", "result_total", "result_home_score", "result_away_score"]
        for row in reader:
            if not row.get("result_winner"):
                title = row.get("title", "")
                for matchup, result in results.items():
                    home = result["home_team"].lower()
                    away = result["away_team"].lower()
                    if home in title.lower() or away in title.lower():
                        row["result_winner"] = result["winner"]
                        row["result_total"] = result["total"]
                        row["result_home_score"] = result["home_score"]
                        row["result_away_score"] = result["away_score"]
                        break
            rows.append(row)

    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print("Results matched and updated")

if __name__ == "__main__":
    match_and_update()
