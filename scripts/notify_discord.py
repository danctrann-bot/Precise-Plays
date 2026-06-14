import os
import csv
import requests
from datetime import datetime, timezone, timedelta

DISCORD_WEBHOOK = os.environ["DISCORD_WEBHOOK_URL"]

def get_recent_rows():
    filepath = "data/mlb/markets.csv"
    if not os.path.exists(filepath):
        print("No data yet")
        return []
    
    rows = []
    with open(filepath, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    
    # Get unique tickers from last checkpoint
    seen = {}
    for row in reversed(rows):
        ticker = row.get("ticker")
        if ticker not in seen:
            seen[ticker] = row
    
    return list(seen.values())

def calculate_movement(ticker, all_rows):
    ticker_rows = [r for r in all_rows if r.get("ticker") == ticker]
    if len(ticker_rows) < 2:
        return None
    
    opening = next((r for r in ticker_rows if r.get("checkpoint") == "opening"), None)
    latest = ticker_rows[-1]
    
    if not opening or not latest:
        return None
    
    try:
        open_yes = float(opening.get("best_yes_price") or 0)
        current_yes = float(latest.get("best_yes_price") or 0)
        movement = round((current_yes - open_yes) * 100, 1)
        return movement
    except:
        return None

def get_historical_hit_rate(ticker_prefix, movement_direction):
    filepath = "data/mlb/markets.csv"
    if not os.path.exists(filepath):
        return None
    
    matches = 0
    hits = 0
    
    with open(filepath, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    # Group by ticker
    tickers = set(r.get("ticker") for r in rows)
    for ticker in tickers:
        ticker_rows = [r for r in rows if r.get("ticker") == ticker]
        opening = next((r for r in ticker_rows if r.get("checkpoint") == "opening"), None)
        latest = ticker_rows[-1]
        
        if not opening or not latest.get("result_winner"):
            continue
        
        try:
            open_yes = float(opening.get("best_yes_price") or 0)
            close_yes = float(latest.get("best_yes_price") or 0)
            move = close_yes - open_yes
            
            if movement_direction == "up" and move > 0:
                matches += 1
                if latest.get("result_winner"):
                    hits += 1
            elif movement_direction == "down" and move < 0:
                matches += 1
                if latest.get("result_winner"):
                    hits += 1
        except:
            continue
    
    if matches < 5:
        return None
    return round((hits / matches) * 100, 1)

def send_alert(markets_data, all_rows):
    if not markets_data:
        print("No markets to alert")
        return
    
    messages = []
    for market in markets_data:
        ticker = market.get("ticker")
        title = market.get("title", "Unknown")
        best_yes = market.get("best_yes_price")
        best_no = market.get("best_no_price")
        yes_vol = market.get("yes_volume")
        no_vol = market.get("no_volume")
        ratio = market.get("bid_ask_ratio")
        
        movement = calculate_movement(ticker, all_rows)
        direction = "up" if movement and movement > 0 else "down"
        hit_rate = get_historical_hit_rate(ticker, direction)
        
        msg = f"**{title}**\n"
        msg += f"YES: {best_yes} | NO: {best_no}\n"
        msg += f"Volume — YES: {yes_vol} | NO: {no_vol} | Ratio: {ratio}\n"
        
        if movement is not None:
            arrow = "📈" if movement > 0 else "📉"
            msg += f"Line Movement: {arrow} {movement:+.1f}¢ from open\n"
        
        if hit_rate:
            msg += f"Historical Hit Rate (same direction): **{hit_rate}%**\n"
        else:
            msg += f"Historical Hit Rate: *Building data...*\n"
        
        messages.append(msg)
    
    full_message = f"⚾ **MLB Kalshi Alert — 15 Min to First Pitch**\n{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n"
    full_message += "\n---\n".join(messages)
    
    payload = {"content": full_message}
    response = requests.post(DISCORD_WEBHOOK, json=payload)
    print(f"Discord response: {response.status_code}")

def main():
    filepath = "data/mlb/markets.csv"
    all_rows = []
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            reader = csv.DictReader(f)
            all_rows = list(reader)
    
    recent = get_recent_rows()
    send_alert(recent, all_rows)

if __name__ == "__main__":
    main()
