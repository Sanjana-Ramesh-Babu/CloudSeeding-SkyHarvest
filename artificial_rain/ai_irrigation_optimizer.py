import json
from datetime import datetime

# Load forecast data
with open("seedable_forecast.json", "r") as f:
    all_forecasts = json.load(f)

# Load user config
with open("user_input_config.json", "r") as f:
    user_config = json.load(f)

# Extract user crop and irrigation data
crop = user_config["crop"]["type"].capitalize()
growth_stage = user_config["crop"]["growth_stage"]
weekly_requirement = user_config["crop"]["water_requirement_mm_per_week"]
max_per_day = user_config["irrigation"]["max_capacity_mm_per_day"]

# Days of the week and empty plan
days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
plan = {day: 0 for day in days}

# Filter seedable cloud options
seedable_options = [
    {
        "datetime": item["datetime"],
        "day": datetime.strptime(item["datetime"], "%Y-%m-%dT%H:%M").strftime("%A"),
        "rainfall_mm": item["precipitation_potential_mm"]
    }
    for item in all_forecasts if item.get("is_seedable", False)
]

if not seedable_options:
    print("❌ No seedable clouds available. Showing full irrigation plan instead.")
    # Distribute full requirement equally under max_per_day
    remaining = weekly_requirement
    i = 0
    while remaining > 0:
        day = days[i % 7]
        water = min(remaining, max_per_day)
        plan[day] += water
        remaining -= water
        i += 1
else:
    # Show seedable options to user
    print("\n🌥️ Available Seedable Cloud Options:\n")
    for i, option in enumerate(seedable_options):
        print(f"{i + 1}. {option['datetime']} ({option['day']}) - Rainfall: {option['rainfall_mm']}mm")

    # Get user choice
    selected_index = int(input("\nSelect a cloud seeding option (enter number): ")) - 1
    selected = seedable_options[selected_index]

    rain_day = selected["day"]
    rainfall_mm = selected["rainfall_mm"]
    plan[rain_day] = 0  # No irrigation on rainfall day

    # Calculate remaining water needed
    remaining = weekly_requirement - rainfall_mm
    remaining = max(0, remaining)

    # Distribute across other days
    irrigation_days = [d for d in days if d != rain_day]
    i = 0
    while remaining > 0:
        day = irrigation_days[i % len(irrigation_days)]
        water = min(remaining, max_per_day)
        plan[day] += water
        remaining -= water
        i += 1

# Final output
print(f"\n📋 AI Optimized Irrigation Plan for Crop: {crop} ({growth_stage} stage)")
print(f"💧 Weekly Requirement: {weekly_requirement}mm | 🚿 Max/Day: {max_per_day}mm")
if seedable_options:
    print(f"🌧️ Cloud Seeding on {rain_day}: {rainfall_mm}mm\n")
else:
    print("⚠️ No Rainfall Included\n")

for day in days:
    if plan[day] > 0:
        print(f"✅ {day}: Irrigate {plan[day]}mm")
    elif seedable_options and day == rain_day:
        print(f"🌧️ {day}: Rainfall expected ({rainfall_mm}mm) - No irrigation")
    else:
        print(f"➖ {day}: No irrigation needed")
