import json
import requests
from datetime import datetime, timezone, timedelta
import os

ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports"

def get_today_str():
    return datetime.now(timezone.utc).strftime("%Y%m%d")

def get_espn_schedule(espn_sport, espn_league, date_str):
    url = f"{ESPN_BASE}/{espn_sport}/{espn_league}/scoreboard?dates={date_str}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json().get("events", [])
    except Exception as e:
        print(f"Error fetching ESPN schedule for {espn_league}: {e}")
        return []

def parse_games(events, sport_config):
    games = []
    for event in events:
        try:
            game_id = event.get("id")
            name = event.get("name", "Unknown")
            short_name = event.get("shortName", name)
            date_str = event.get("date")
            
            if not date_str:
                continue
                
            # Parse game time
            game_time = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            
            # Skip games already started
            if game_time < now:
                continue
            
            # Calculate checkpoint times
            checkpoints = {
                "opening": None,  # Already captured at 9am
                "6hr": (game_time - timedelta(hours=6)).isoformat(),
                "2hr": (game_time - timedelta(hours=2)).isoformat(),
                "1hr": (game_time - timedelta(hours=1)).isoformat(),
                "15min_1": (game_time - timedelta(minutes=45)).isoformat(),
                "15min_2": (game_time - timedelta(minutes=30)).isoformat(),
                "15min_3": (game_time - timedelta(minutes=15)).isoformat(),
                "closing": game_time.isoformat()
            }
            
            # Get team abbreviations for matching
            competitions = event.get("competitions", [{}])[0]
            competitors = competitions.get("competitors", [])
            home = next((t for t in competitors if t["homeAway"] == "home"), {})
            away = next((t for t in competitors if t["homeAway"] == "away"), {})
            
            games.append({
                "espn_game_id": game_id,
                "name": name,
                "short_name": short_name,
                "sport": sport_config["name"],
                "kalshi_series": sport_config["kalshi_series"],
                "game_time_utc": game_time.isoformat(),
                "home_team": home.get("team", {}).get("abbreviation", ""),
                "away_team": away.get("team", {}).get("abbreviation", ""),
                "checkpoints": checkpoints,
                "result_captured": False
            })
        except Exception as e:
            print(f"Error parsing event: {e}")
            continue
    
    return games

def build_schedule():
    # Load sport configs
    with open("config/sports.json", "r") as f:
        config = json.load(f)
    
    today = get_today_str()
    all_games = []
    
    for sport in config["sports"]:
        if not sport["enabled"]:
            continue
        
        print(f"Fetching {sport['name']} schedule...")
        events = get_espn_schedule(
            sport["espn_sport"],
            sport["espn_league"],
            today
        )
        
        games = parse_games(events, sport)
        print(f"Found {len(games)} upcoming {sport['name']} games")
        all_games.extend(games)
    
    # Save schedule
    os.makedirs("data", exist_ok=True)
    schedule_path = "data/schedule_today.json"
    
    # Merge with existing schedule if it exists
    existing = []
    if os.path.exists(schedule_path):
        with open(schedule_path, "r") as f:
            existing = json.load(f)
        # Keep games from other sports already in schedule
        existing_ids = {g["espn_game_id"] for g in all_games}
        existing = [g for g in existing if g["espn_game_id"] not in existing_ids]
    
    final_schedule = existing + all_games
    
    with open(schedule_path, "w") as f:
        json.dump(final_schedule, f, indent=2)
    
    print(f"Schedule saved: {len(final_schedule)} total games today")
    return final_schedule

if __name__ == "__main__":
    schedule = build_schedule()
    for game in schedule:
        print(f"{game['sport'].upper()}: {game['short_name']} at {game['game_time_utc']}")
