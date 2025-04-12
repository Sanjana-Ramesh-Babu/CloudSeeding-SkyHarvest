import json
from datetime import datetime
import matplotlib.pyplot as plt

# Correct file paths
with open("seedable_forecast.json", "r") as f:
    all_forecasts = json.load(f)

with open("user_input_config.json", "r") as f:
    user_config = json.load(f)

# Extract crop & irrigation config
crop = user_config["crop"]["type"].capitalize()
growth_stage = user_config["crop"]["growth_stage"]
weekly_requirement = user_config["crop"]["water_requirement_mm_per_week"]
max_per_day = user_config["irrigation"]["max_capacity_mm_per_day"]

days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
plan = {day: 0 for day in days}

# Filter seedable options
seedable_options = [
    {
        "datetime": item["datetime"],
        "day": datetime.strptime(item["datetime"], "%Y-%m-%dT%H:%M").strftime("%A"),
        "rainfall_mm": item["precipitation_potential_mm"]
    }
    for item in all_forecasts if item.get("is_seedable", False)
]

# Calculate irrigation plan
if not seedable_options:
    remaining = weekly_requirement
    i = 0
    while remaining > 0:
        day = days[i % 7]
        water = min(remaining, max_per_day)
        plan[day] += water
        remaining -= water
        i += 1
    rain_day = None
    rainfall_mm = 0
else:
    selected = seedable_options[0]  # simulate first seedable cloud
    rain_day = selected["day"]
    rainfall_mm = selected["rainfall_mm"]
    plan[rain_day] = 0
    remaining = max(0, weekly_requirement - rainfall_mm)
    irrigation_days = [d for d in days if d != rain_day]
    i = 0
    while remaining > 0:
        day = irrigation_days[i % len(irrigation_days)]
        water = min(remaining, max_per_day)
        plan[day] += water
        remaining -= water
        i += 1

# Visualization
water_values = list(plan.values())
colors = ["skyblue" if day != rain_day else "deepskyblue" for day in days]

plt.figure(figsize=(10, 6))
bars = plt.bar(days, water_values, color=colors)

# Annotate rainfall
for i, day in enumerate(days):
    if day == rain_day:
        plt.text(i, water_values[i] + 1, f"Rain: {rainfall_mm}mm", ha='center', color='navy')

# Title and labels
plt.title(f"🌾 AI Irrigation Plan for {crop} ({growth_stage} Stage)", fontsize=14)
plt.xlabel("Day of the Week")
plt.ylabel("Watering (mm)")
plt.ylim(0, max(water_values + [rainfall_mm]) + 10)
plt.grid(axis='y', linestyle='--', alpha=0.7)

# Add water values on bars
for i, val in enumerate(water_values):
    if val > 0:
        plt.text(i, val + 0.5, f"{val}mm", ha='center', fontsize=9)

plt.tight_layout()
plt.show()
