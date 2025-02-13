# Property Scraper & Map Generator 🏡📍

A Python script that scrapes real estate listings from Oikotie.fi, saves data to CSV, and generates an interactive map.

## Features
- Extracts property details from JSON-LD.
- Saves listings to `properties.csv` (avoids duplicates).
- Generates `index.html` with interactive markers.
- Uses Stadia Maps API for map tile generation.

## Usage

```sh
poetry run python scraper.py <url_file> [--csv OUTPUT_CSV] [--map OUTPUT_HTML]
```

Where:
- `<url_file>` is a text file containing URLs to scrape (required)
- `--csv` specifies the output CSV file name (default: properties.csv)
- `--map` specifies the output HTML map file name (default: index.html)

Example:
```sh
poetry run python scraper.py urls.txt --csv my_properties.csv --map my_map.html
```

## Output

- properties.csv → Property data.
- index.html → Interactive map.