# Property Scraper & Map Generator 🏡📍

A Python script that scrapes real estate listings from Oikotie.fi, saves data to CSV, and generates an interactive map.

## Features
- Extracts property details from JSON-LD.
- Saves listings to `properties.csv` (avoids duplicates).
- Generates `index.html` with interactive markers.


## Usage

```sh
poetry run python property_scraper.py \
https://asunnot.oikotie.fi/myytavat-asunnot/espoo/22100228 \
--csv properties.csv --map index.html
```

Output

- properties.csv → Property data.
- index.html → Interactive map.



poetry run python property-scrapper.py \
https://asunnot.oikotie.fi/myytavat-asunnot/espoo/22100228 \
https://asunnot.oikotie.fi/myytavat-asunnot/vantaa/22490946 \
--csv properties.csv --map property_map.html