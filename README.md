# Property Scraper & Map Generator 🏡📍

A Python script that scrapes real estate listings from Oikotie.fi, saves data to CSV, and generates an interactive map.

## Features
- Extracts property details from JSON-LD.
- Saves listings to `properties.csv` (avoids duplicates).
- Generates `index.html` with interactive markers.


## Usage

```sh
poetry run python property_scraper.py urls.txt
```

Output

- properties.csv → Property data.
- index.html → Interactive map.