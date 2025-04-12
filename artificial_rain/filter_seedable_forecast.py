import json

# Load full forecast
with open('seedable_forecast.json', 'r') as f:
    forecast = json.load(f)

# Filter seedable events
filtered = [
    {
        "datetime": entry["datetime"],
        "precipitation_potential_mm": entry["precipitation_potential_mm"],
        "precipitation_probability": entry["precipitation_probability"]
    }
    for entry in forecast if entry.get("is_seedable")
]

# Save the result
with open('filtered_seedable_forecast.json', 'w') as f:
    json.dump(filtered, f, indent=2)

print(f"✅ Rain Calendar data ready: {len(filtered)} seedable days saved.")
