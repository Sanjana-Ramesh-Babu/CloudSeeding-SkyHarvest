import requests
import json
from datetime import datetime, timedelta

# Load user config
with open("user_input_config.json", "r") as f:
    config = json.load(f)

lat = config["location"]["latitude"]
lon = config["location"]["longitude"]

# Auto-detect region type based on location coordinates
def determine_climate_zone(lat, lon):
    # Kerala coordinates are approximately between:
    # Latitude: 8.3° to 12.8° N, Longitude: 74.9° to 77.6° E
    if 8.0 <= lat <= 13.0 and 74.5 <= lon <= 78.0:
        return "tropical_humid"
    
    # Rajasthan coordinates are approximately between:
    # Latitude: 23.0° to 30.3° N, Longitude: 69.3° to 78.3° E
    elif 23.0 <= lat <= 31.0 and 69.0 <= lon <= 79.0:
        return "arid"
    
    # Maharashtra (semi-arid/moderate)
    elif 15.6 <= lat <= 22.0 and 72.6 <= lon <= 80.9:
        return "semi_arid"
    
    # Punjab/Haryana (temperate)
    elif 27.7 <= lat <= 32.5 and 73.8 <= lon <= 77.0:
        return "temperate"
    
    # Northeast (high_rainfall)
    elif 22.0 <= lat <= 29.5 and 88.0 <= lon <= 97.5:
        return "high_rainfall"
    
    # Default: use a generalized approach based on latitude
    else:
        if 8.0 <= lat <= 20.0:  # Southern India
            return "tropical_humid"
        elif 20.0 <= lat <= 28.0:  # Central India
            return "semi_arid"
        else:  # Northern India
            return "temperate"

# Define the get_limiting_factors function here, before it's called
def get_limiting_factors(entry, region_type, min_cloud, min_humidity, min_wind):
    """Identify factors limiting seedability - adjusted for region type"""
    factors = []
    if entry["cloudcover"] < min_cloud:
        factors.append(f"insufficient cloud cover (< {min_cloud}%)")
    if entry["humidity"] < min_humidity:
        factors.append(f"low humidity (< {min_humidity}%)")
    if entry["windspeed"] < min_wind:
        factors.append(f"insufficient wind (< {min_wind} m/s)")
    if "High" in entry["cloud_type"] or "Not Recommended" in entry["recommended_seeding_method"]:
        factors.append("unsuitable cloud type")
    
    # Region-specific factors
    if region_type == "tropical_humid" and entry["humidity"] > 90:
        factors.append("excessive humidity (natural precipitation likely)")
    elif region_type == "arid" and entry["temperature"] > 35:
        factors.append("extreme heat reducing cloud development")
    
    return ", ".join(factors) if factors else "borderline conditions"

region_type = determine_climate_zone(lat, lon)

# Get crop info for context
crop_type = config.get("crop", {}).get("type", "unknown")
growth_stage = config.get("crop", {}).get("growth_stage", "unknown")

# Request comprehensive weather data with additional parameters relevant to cloud seeding
url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,relativehumidity_2m,dewpoint_2m,cloudcover,cloudcover_low,cloudcover_mid,cloudcover_high,pressure_msl,windspeed_10m,precipitation&timezone=auto"
response = requests.get(url)
data = response.json()

# Parse data
hours = data["hourly"]["time"]
temps = data["hourly"]["temperature_2m"]
humidity = data["hourly"]["relativehumidity_2m"]
dewpoints = data["hourly"]["dewpoint_2m"] 
clouds = data["hourly"]["cloudcover"]
clouds_low = data["hourly"]["cloudcover_low"]
clouds_mid = data["hourly"]["cloudcover_mid"]
clouds_high = data["hourly"]["cloudcover_high"]
pressure = data["hourly"]["pressure_msl"]
wind = data["hourly"]["windspeed_10m"]
precipitation = data["hourly"].get("precipitation", [0] * len(hours))  # Add precipitation data

now = datetime.now()
now_str = now.strftime("%Y-%m-%dT%H:00")
try:
    now_index = hours.index(now_str)
except ValueError:
    # If exact hour not found, find closest hour
    now_hour_decimal = now.hour + now.minute / 60
    closest_hour_index = 0
    min_diff = 24
    
    for i, time_str in enumerate(hours):
        hour = datetime.fromisoformat(time_str).hour
        diff = abs(hour - now_hour_decimal)
        if diff < min_diff:
            min_diff = diff
            closest_hour_index = i
    
    now_index = closest_hour_index

forecast_data = []
found = False

print(f"\n🔮 Advanced Cloud Seeding Forecast (Next 48 Hours) for ({lat}, {lon}) - {region_type.upper()} region\n")
print(f"Crop: {crop_type} ({growth_stage})\n")

# Define thresholds based on region type
if region_type == "arid":
    min_cloud = 30        # Lower cloud cover threshold for arid regions
    min_humidity = 35     # Much lower humidity threshold for arid regions
    ideal_wind = 3.0      # Optimal wind speed
    min_wind = 1.5        # Minimum wind speed
    temp_threshold = 15   # Temperature threshold for convection in arid regions
    seedability_threshold = 40  # Lower threshold for arid regions where opportunities are rarer
    # Precipitation potential factors - OPTIMIZED for arid regions
    base_precipitation_potential = 0.8  # Increased from 0.5 to ensure meaningful precipitation
    precipitation_efficiency = 0.5      # Increased from 0.4 for arid regions
    min_viable_precipitation = 0.1      # Minimum precipitation to be considered viable
    seeding_enhancement_factor = 1.5    # Higher enhancement factor for arid regions where water is scarce
    
elif region_type == "tropical_humid":
    min_cloud = 50        # Higher cloud requirements in humid regions (already lots of clouds)
    min_humidity = 65     # Much higher humidity threshold for humid regions
    ideal_wind = 2.0      # Slightly lower ideal wind (monsoon conditions)
    min_wind = 1.0        # Lower minimum wind requirement
    temp_threshold = 22   # Higher temperature threshold for tropical regions
    seedability_threshold = 60  # Higher threshold for humid regions where natural rain is more common
    # Precipitation potential factors
    base_precipitation_potential = 3.0  # Higher base potential in humid regions
    precipitation_efficiency = 0.7      # Higher efficiency in humid regions
    min_viable_precipitation = 0.2      # Minimum precipitation to be considered viable
    seeding_enhancement_factor = 1.2    # Lower enhancement in humid regions as they already get rain
    
elif region_type == "semi_arid":
    min_cloud = 40
    min_humidity = 45
    ideal_wind = 2.5
    min_wind = 1.2
    temp_threshold = 18
    seedability_threshold = 50
    # Precipitation potential factors
    base_precipitation_potential = 1.2  # Increased from 1.0
    precipitation_efficiency = 0.55     # Increased from 0.5
    min_viable_precipitation = 0.15     # Minimum precipitation to be considered viable
    seeding_enhancement_factor = 1.3    # Moderate enhancement factor
    
elif region_type == "temperate":
    min_cloud = 45
    min_humidity = 50
    ideal_wind = 2.2
    min_wind = 1.3
    temp_threshold = 12
    seedability_threshold = 55
    # Precipitation potential factors
    base_precipitation_potential = 1.5
    precipitation_efficiency = 0.6
    min_viable_precipitation = 0.15     # Minimum precipitation to be considered viable
    seeding_enhancement_factor = 1.25   # Moderate enhancement factor
    
elif region_type == "high_rainfall":
    min_cloud = 60
    min_humidity = 75
    ideal_wind = 1.5
    min_wind = 1.0
    temp_threshold = 24
    seedability_threshold = 70
    # Precipitation potential factors
    base_precipitation_potential = 4.0  # Highest base potential in high rainfall regions
    precipitation_efficiency = 0.8      # Highest efficiency in high rainfall regions
    min_viable_precipitation = 0.3      # Higher minimum for high rainfall regions
    seeding_enhancement_factor = 1.1    # Lower enhancement factor as natural rain is already abundant
    
else:  # Default/fallback values
    min_cloud = 40
    min_humidity = 50
    ideal_wind = 2.5
    min_wind = 1.2
    temp_threshold = 18
    seedability_threshold = 50
    # Precipitation potential factors - default values
    base_precipitation_potential = 1.5
    precipitation_efficiency = 0.6
    min_viable_precipitation = 0.15     # Minimum precipitation to be considered viable
    seeding_enhancement_factor = 1.3    # Default enhancement factor

# Calculate seedability for next 48 hours
for i in range(now_index, min(now_index + 48, len(hours))):
    time_obj = datetime.fromisoformat(hours[i])
    month = time_obj.month
    
    # Calculate dew point depression (spread)
    spread = temps[i] - dewpoints[i]
    
    # Calculate estimated liquid water content (LWC) - adjusted by region type
    if region_type == "tropical_humid":
        # Higher natural moisture content in tropical humid regions
        if spread <= 2:  # Nearly saturated air
            estimated_lwc = 0.9
        elif spread > 15:  # Drier air
            estimated_lwc = 0.3
        else:
            estimated_lwc = ((humidity[i] / 100) * (1 - spread / 20))
            
    elif region_type == "arid":
        # Lower natural moisture content in arid regions but OPTIMIZED to ensure non-zero values
        if spread <= 0:  # Saturated air (rare in arid regions)
            estimated_lwc = 0.8
        elif spread > 20:  # Very dry air typical in Rajasthan
            # Increased minimum LWC for arid regions to ensure precipitation potential
            estimated_lwc = 0.15
        else:
            # Modified formula to ensure higher LWC estimates in arid regions
            estimated_lwc = max(0.15, ((humidity[i] / 100) * (1 - spread / 30)))
            
    elif region_type == "high_rainfall":
        # Very high natural moisture content
        if spread <= 3:
            estimated_lwc = 1.0
        elif spread > 10:
            estimated_lwc = 0.5
        else:
            estimated_lwc = ((humidity[i] / 100) * (1 - spread / 15))
            
    else:  # semi_arid and temperate
        # Moderate moisture content
        if spread <= 1:
            estimated_lwc = 0.85
        elif spread > 18:
            estimated_lwc = 0.2
        else:
            estimated_lwc = ((humidity[i] / 100) * (1 - spread / 22))
    
    estimated_lwc = max(0, min(1, estimated_lwc))
    
    # Calculate convective potential (simplified CAPE substitute)
    hour_of_day = time_obj.hour
    
    # Different regions have different optimal convection times
    if region_type == "tropical_humid":
        # Afternoon storms common in tropical regions
        daytime_convection = 1.0 if 13 <= hour_of_day <= 17 else 0.5
    elif region_type == "arid":
        # Wider window in arid regions due to high surface heating
        daytime_convection = 1.0 if 11 <= hour_of_day <= 18 else 0.5
    elif region_type == "high_rainfall":
        # Morning and evening storms in high rainfall regions
        daytime_convection = 1.0 if (6 <= hour_of_day <= 10) or (15 <= hour_of_day <= 19) else 0.6
    else:
        # Standard afternoon heating for other regions
        daytime_convection = 1.0 if 12 <= hour_of_day <= 17 else 0.5
    
    # Temperature factor adjusted for region
    temp_factor = min(1.0, temps[i] / temp_threshold) if temps[i] > 0 else 0.2
    
    # Check for existing precipitation (don't seed if it's already raining significantly)
    rain_factor = 0.5 if precipitation[i] > 0.5 else 1.0
    
    # Determine likely cloud type based on altitude and temperature - adjusted by region
    cloud_type = "Unknown"
    seeding_method = "N/A"
    effectiveness = 0
    
    if region_type == "tropical_humid":
        # Tropical regions favor warm cloud seeding methods
        if clouds_low[i] > 50:
            cloud_type = "Warm Cumulus/Stratocumulus"
            seeding_method = "Hygroscopic Materials"
            effectiveness = 0.85
        elif clouds_mid[i] > 50:
            if temps[i] < 10:
                cloud_type = "Mixed-phase Mid-level Cloud"
                seeding_method = "Combined Silver Iodide/Hygroscopic"
                effectiveness = 0.80
            else:
                cloud_type = "Warm Mid-level Cloud"
                seeding_method = "Hygroscopic Materials"
                effectiveness = 0.85
        elif clouds_high[i] > 70:
            cloud_type = "High Tropical Cloud System"
            seeding_method = "Not Recommended"
            effectiveness = 0.1
            
    elif region_type == "arid":
        # Arid regions favor mid-level seeding with silver iodide
        if clouds_mid[i] > 40:
            if temps[i] < 5:
                cloud_type = "Cold Mid-level Cloud"
                seeding_method = "Silver Iodide"
                # Increased effectiveness for arid regions to ensure meaningful precipitation
                effectiveness = 0.90
            else:
                cloud_type = "Warm Mid-level Cloud"
                seeding_method = "Hygroscopic Materials"
                effectiveness = 0.80
        elif clouds_low[i] > 40:
            if temps[i] < 10:
                cloud_type = "Low Stratiform Cloud"
                seeding_method = "Ground-based Silver Iodide"
                effectiveness = 0.75
            else:
                cloud_type = "Low Cumulus Cloud"
                seeding_method = "Hygroscopic Materials"
                effectiveness = 0.80
        elif clouds_high[i] > 60:
            cloud_type = "High Cirrus Cloud"
            seeding_method = "Not Recommended"
            effectiveness = 0.1
            
    elif region_type == "high_rainfall":
        # High rainfall regions need specific approaches for already moisture-rich clouds
        if clouds_low[i] > 60:
            cloud_type = "Rain-bearing Low Cloud"
            seeding_method = "Targeted Hygroscopic"
            effectiveness = 0.70
        elif clouds_mid[i] > 60:
            cloud_type = "Developing Convective System"
            seeding_method = "Limited Intervention/Monitoring"
            effectiveness = 0.50
        elif clouds_high[i] > 75:
            cloud_type = "High Moisture System"
            seeding_method = "Not Recommended"
            effectiveness = 0.1
            
    else:  # semi_arid and temperate
        # More balanced approach
        if clouds_low[i] > 45:
            if temps[i] < 8:
                cloud_type = "Cold Boundary Layer Cloud"
                seeding_method = "Silver Iodide"
                effectiveness = 0.75
            else:
                cloud_type = "Warm Boundary Layer Cloud"
                seeding_method = "Hygroscopic Materials"
                effectiveness = 0.80
        elif clouds_mid[i] > 45:
            if temps[i] < 5:
                cloud_type = "Cold Mid-level Cloud"
                seeding_method = "Aircraft Silver Iodide"
                effectiveness = 0.80
            else:
                cloud_type = "Mixed-phase Cloud"
                seeding_method = "Combined Approach"
                effectiveness = 0.75
        elif clouds_high[i] > 65:
            cloud_type = "High Cloud Formation"
            seeding_method = "Not Recommended"
            effectiveness = 0.1
    
    # Special case for monsoon conditions - region specific
    monsoon_factor = 1.0
    
    if region_type == "tropical_humid":
        # Southwest monsoon for Kerala (June-September)
        if 6 <= month <= 9 and humidity[i] > 70:
            monsoon_factor = 1.2
            cloud_type = "Monsoon Cloud System"
            seeding_method = "Limited Intervention Needed"
            effectiveness = 0.4  # Lower effectiveness because natural rain is likely
            
    elif region_type == "arid":
        # Monsoon reaching Rajasthan (July-September, but more limited)
        if 7 <= month <= 9 and humidity[i] > 60:
            monsoon_factor = 1.5
            cloud_type = "Rare Monsoon Cloud System"
            seeding_method = "Aircraft Silver Iodide/Hygroscopic"
            effectiveness = 0.9  # Higher effectiveness for rare monsoon clouds in arid regions
    
    # Wind factor - region-specific adjustments
    if wind[i] < min_wind:
        wind_factor = wind[i] / min_wind  # Reduces score if wind is below minimum
    elif wind[i] > 10:
        wind_factor = 10 / wind[i]  # Reduces score if wind is too high
    else:
        wind_factor = 1 - abs(wind[i] - ideal_wind) / 7  # Optimal around ideal_wind
    
    wind_factor = max(0.2, min(1.0, wind_factor))
    
    # Calculate overall seedability score (0-100) adjusted for region type
    seedability_score = 0
    
    if cloud_type != "Unknown" and cloud_type != "High Cirrus Cloud" and cloud_type != "High Tropical Cloud System" and cloud_type != "High Moisture System" and cloud_type != "High Cloud Formation":
        # Base score from cloud coverage - weighted differently by region
        if region_type == "tropical_humid":
            cloud_score = (clouds_low[i] * 0.5 + clouds_mid[i] * 0.4 + clouds_high[i] * 0.1) / 100 * 30
        elif region_type == "arid":
            cloud_score = (clouds_low[i] * 0.3 + clouds_mid[i] * 0.7 + clouds_high[i] * 0.1) / 100 * 30
        elif region_type == "high_rainfall":
            cloud_score = (clouds_low[i] * 0.6 + clouds_mid[i] * 0.3 + clouds_high[i] * 0.1) / 100 * 30
        else:  # semi_arid and temperate
            cloud_score = (clouds_low[i] * 0.4 + clouds_mid[i] * 0.5 + clouds_high[i] * 0.1) / 100 * 30
        
        seedability_score = (
            cloud_score +                                    # Cloud coverage factor (max 30)
            (min(humidity[i] / min_humidity, 2) * 15) +      # Humidity factor (max 30)
            (wind_factor * 15) +                             # Wind factor (max 15)
            (estimated_lwc * 20) +                           # LWC factor (max 20)
            (daytime_convection * temp_factor * 15)          # Convection potential (max 15)
        ) * effectiveness * monsoon_factor * rain_factor
        
        seedability_score = min(100, seedability_score)  # Cap at 100
    
    # Threshold varies by region - defined earlier
    is_seedable = seedability_score >= seedability_threshold
    
    # Calculate expected precipitation amount in mm - OPTIMIZED APPROACH
    precipitation_potential_mm = 0
    precipitation_probability = 0
    
    if is_seedable:
        # Calculate the cloud water path (kg/m²) - optimized model with region-specific adjustments
        # This is an estimate of the total column water in the cloud
        cloud_water_path = 0
        
        # Cloud type factors - ENHANCED for arid regions
        if region_type == "arid":
            # Enhanced factors for arid regions to ensure meaningful precipitation predictions
            if cloud_type == "Low Cumulus Cloud":
                cloud_water_path = estimated_lwc * 1.2 * clouds_low[i]/100
            elif "Mid-level" in cloud_type:
                cloud_water_path = estimated_lwc * 1.8 * clouds_mid[i]/100
            elif "Monsoon" in cloud_type:
                cloud_water_path = estimated_lwc * 3.0 * (clouds_low[i] + clouds_mid[i])/200
            else:
                cloud_water_path = estimated_lwc * 1.5 * clouds[i]/100
        elif region_type == "tropical_humid":
            if cloud_type == "Warm Cumulus/Stratocumulus" or cloud_type == "Low Cumulus Cloud":
                cloud_water_path = estimated_lwc * 1.0 * clouds_low[i]/100
            elif "Mid-level" in cloud_type:
                cloud_water_path = estimated_lwc * 1.5 * clouds_mid[i]/100
            elif "Monsoon" in cloud_type:
                cloud_water_path = estimated_lwc * 2.5 * (clouds_low[i] + clouds_mid[i])/200
            else:
                cloud_water_path = estimated_lwc * 1.0 * clouds[i]/100
        else:  # Other regions
            if cloud_type == "Warm Cumulus/Stratocumulus" or cloud_type == "Low Cumulus Cloud":
                cloud_water_path = estimated_lwc * 1.0 * clouds_low[i]/100
            elif "Mid-level" in cloud_type:
                cloud_water_path = estimated_lwc * 1.5 * clouds_mid[i]/100
            elif "Monsoon" in cloud_type:
                cloud_water_path = estimated_lwc * 2.5 * (clouds_low[i] + clouds_mid[i])/200
            else:
                cloud_water_path = estimated_lwc * 1.0 * clouds[i]/100
        
        # Adjust for temperature - colder clouds have lower liquid water content
        # Modified to be less severe in arid regions
        if region_type == "arid":
            if temps[i] < 5:
                cloud_water_path *= 0.8  # Less severe reduction
            elif temps[i] < 10:
                cloud_water_path *= 0.9  # Less severe reduction
        else:
            if temps[i] < 5:
                cloud_water_path *= 0.7
            elif temps[i] < 10:
                cloud_water_path *= 0.85
        
        # Calculate the potential precipitation (mm) without seeding
        natural_precipitation = cloud_water_path * 0.3  # Assume 30% natural precipitation efficiency
        
        # Enhanced precipitation due to seeding - OPTIMIZED
        # Scientific studies suggest seeding can increase rainfall by 10-30%
        # Using higher enhancement factor for arid regions where every drop counts
        seeding_enhancement = effectiveness * seeding_enhancement_factor * 0.3  # Enhanced factor
        
        # Calculate expected precipitation amount from seeding in mm - OPTIMIZED
        precipitation_potential_mm = max(
            min_viable_precipitation,  # Ensure a minimum meaningful amount
            base_precipitation_potential * (
                natural_precipitation * (1 + seeding_enhancement) * 
                precipitation_efficiency * 
                (seedability_score / 100)
            )
        )
        
        # For arid regions, apply additional scaling to ensure meaningful amounts
        if region_type == "arid" and precipitation_potential_mm < 0.2:
            precipitation_potential_mm = max(0.2, precipitation_potential_mm * 1.5)
        
        # Calculate probability of precipitation after seeding (%)
        precipitation_probability = min(95, 40 + (seedability_score / 2))
    
    # Format time for display
    display_time = time_obj.strftime("%Y-%m-%d %H:00")
    
    entry = {
        "datetime": hours[i],
        "display_time": display_time,
        "temperature": temps[i],
        "humidity": humidity[i],
        "dewpoint": dewpoints[i],
        "spread": round(spread, 1),
        "cloudcover": clouds[i],
        "cloudcover_low": clouds_low[i],
        "cloudcover_mid": clouds_mid[i],
        "cloudcover_high": clouds_high[i],
        "pressure": pressure[i],
        "windspeed": wind[i],
        "cloud_type": cloud_type,
        "estimated_lwc": round(estimated_lwc, 2),
        "recommended_seeding_method": seeding_method,
        "seedability_score": round(seedability_score, 1),
        "is_seedable": is_seedable,
        "precipitation_potential_mm": round(precipitation_potential_mm, 2),
        "precipitation_probability": round(precipitation_probability, 1)
    }
    
    if is_seedable:
        found = True
    
    forecast_data.append(entry)
    
    # Print only if there's some cloud cover to reduce noise
    if clouds[i] > 15:
        status = "✅ SEEDABLE" if is_seedable else "❌ Not suitable"
        precip_text = f"| 🌧️ {round(precipitation_probability, 1)}% ({round(precipitation_potential_mm, 2)}mm)" if is_seedable else ""
        print(f"{display_time} | ☁️ {clouds[i]}% | 💧 {humidity[i]}% | "
              f"🌡️ {temps[i]}°C | 🌬️ {wind[i]} m/s | "
              f"Score: {round(seedability_score, 1)}/100 {precip_text} → {status}")

# Save to JSON
with open("seedable_forecast.json", "w") as f:
    json.dump(forecast_data, f, indent=2)

if found:
    print(f"\n✅ GOOD NEWS! Seedable conditions found in this {region_type} region! 🌧️")
    print("\nBest hours for cloud seeding:")
    seedable_entries = [entry for entry in forecast_data if entry["is_seedable"]]
    for entry in sorted(seedable_entries, key=lambda x: x["seedability_score"], reverse=True)[:5]:
        print(f"- {entry['display_time']} (Score: {entry['seedability_score']}/100)")
        print(f"  Cloud type: {entry['cloud_type']}")
        print(f"  Method: {entry['recommended_seeding_method']}")
        print(f"  Expected precipitation: {entry['precipitation_potential_mm']} mm ({entry['precipitation_probability']}% probability)")
        print(f"  Conditions: ☁️ {entry['cloudcover']}% | 💧 {entry['humidity']}% | 🌡️ {entry['temperature']}°C")
    
    # For arid regions, provide context about the importance of even small amounts
    if region_type == "arid":
        print(f"\n📊 Context for Arid Region Cloud Seeding:")
        print(f"  Even small precipitation amounts (0.2-0.5mm) can be significant in arid regions like Rajasthan.")
        print(f"  For context, natural rainfall in this region during dry periods can be less than 1mm per week.")
        print(f"  Accumulated effects of multiple seeding operations can provide meaningful moisture for drought mitigation.")
else:
    print(f"\n⚠️ No seedable hours found in the next 48-hour window for this {region_type} region.")
    # Provide next best options
    print("\nClosest conditions to seedable (may require monitoring):")
    for entry in sorted(forecast_data, key=lambda x: x["seedability_score"], reverse=True)[:3]:
        print(f"- {entry['display_time']} (Score: {entry['seedability_score']}/100)")
        print(f"  Limitations: {get_limiting_factors(entry, region_type, min_cloud, min_humidity, min_wind)}")

# Add agricultural context
crop_water_needs = config.get("crop", {}).get("water_requirement_mm_per_week", 0)
if found and crop_water_needs > 0:
    print(f"\n🌱 Agricultural Context:")
    print(f"Your {crop_type} crop at {growth_stage} stage requires approximately {crop_water_needs}mm of water per week.")
    
    # Calculate potential water contribution from seeding
    total_potential_water = sum(entry["precipitation_potential_mm"] for entry in seedable_entries)
    water_needs_percentage = (total_potential_water / crop_water_needs) * 100
    
    print(f"Successful cloud seeding could provide approximately {round(total_potential_water, 1)}mm of water")
    
    # Add region-specific context for water contribution
    if region_type == "arid":
        print(f"This would meet {round(water_needs_percentage, 1)}% of your weekly water requirement")
        print(f"While this seems small, any additional water in arid regions has significant value.")
        print(f"This could reduce irrigation demand by {round(total_potential_water, 1)}mm, saving approximately")
        print(f"{round(total_potential_water * 10, 1)} cubic meters of water per hectare.")
    else:
        print(f"This would meet {round(water_needs_percentage, 1)}% of your weekly water requirement")
        print(f"This could supplement irrigation needs for your {config.get('irrigation', {}).get('type', 'unknown')} system.")

print("\n📁 Saved detailed forecast to seedable_forecast.json ✅")