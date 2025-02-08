import os
import json
import requests
import pandas as pd
import folium
import click
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def fetch_html(url):
    """
    Fetch HTML content using requests.
    """
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.text
    else:
        print(f"Failed to fetch {url}, Status Code: {response.status_code}")
        return None

def extract_json_ld(html_source):
    """
    Extract JSON-LD structured data from the page.
    """
    soup = BeautifulSoup(html_source, "html.parser")
    json_ld_tag = soup.find("script", type="application/ld+json")
    if json_ld_tag:
        try:
            return json.loads(json_ld_tag.string)
        except json.JSONDecodeError:
            print("Error decoding JSON-LD")
            return None
    return None

def format_property_data(json_data):
    """
    Format extracted JSON-LD data into a structured dictionary.
    """
    if not json_data:
        return None

    return {
        "Address": json_data.get("address", {}).get("streetAddress", "N/A"),
        "City": json_data.get("address", {}).get("addressRegion", "N/A"),
        "Neighborhood": json_data.get("address", {}).get("addressLocality", "N/A"),
        "Postal Code": json_data.get("address", {}).get("postalCode", "N/A"),
        "Latitude": float(json_data.get("geo", {}).get("latitude", 0)),
        "Longitude": float(json_data.get("geo", {}).get("longitude", 0)),
        "Price (€)": json_data.get("offers", {}).get("price", "N/A"),
        "Size (m²)": json_data.get("floorSize", {}).get("value", "N/A"),
        "Condition": json_data.get("itemCondition", {}).get("name", "N/A"),
        "Bedrooms": json_data.get("numberOfRooms", "N/A"),
        "Description": json_data.get("description", "N/A"),
        "URL": json_data.get("url", "N/A")
    }

def load_existing_urls(csv_path):
    """
    Load existing property URLs from the CSV file.
    """
    if os.path.exists(csv_path):
        df_existing = pd.read_csv(csv_path)
        return set(df_existing["URL"].tolist())  # Store URLs in a set for fast lookup
    return set()

@click.command()
@click.argument('url_file', type=click.Path(exists=True))
@click.option('--csv', default='properties.csv', help='Output CSV file name.')
@click.option('--map', default='index.html', help='Output HTML file for the map.')
def scrape_and_generate(url_file, csv, map):
    """
    Fetch property data from URLs in a given file, generate CSV and an interactive map.
    """
    # Read URLs from the file
    with open(url_file, 'r') as file:
        urls = [line.strip() for line in file if line.strip()]

    existing_urls = load_existing_urls(csv)
    data = []

    for url in urls:
        if url in existing_urls:
            print(f"Skipping already recorded URL: {url}")
            continue

        html = fetch_html(url)
        if html:
            json_ld_data = extract_json_ld(html)
            property_info = format_property_data(json_ld_data)
            if property_info:
                data.append(property_info)

    if not data:
        print("No new properties to add. Exiting.")
        return

    # Convert to DataFrame
    df_new = pd.DataFrame(data)

    # Append new data to CSV (or create if not exists)
    if os.path.exists(csv):
        df_existing = pd.read_csv(csv)
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
    else:
        df_combined = df_new

    df_combined.to_csv(csv, index=False)
    print(f"CSV file updated: {csv}")

    # Create a map centered in Finland
    m = folium.Map(location=[60.2, 24.8], zoom_start=10)

    # Add markers for each property
    for _, row in df_combined.iterrows():
        popup_text = f"""
        <b>{row["Address"]}</b><br>
        <b>City:</b> {row["City"]}<br>
        <b>Neighborhood:</b> {row["Neighborhood"]}<br>
        <b>Postal Code:</b> {row["Postal Code"]}<br>
        <b>Price:</b> €{row["Price (€)"]:,}<br>
        <b>Size:</b> {row["Size (m²)"]} m²<br>
        <b>Condition:</b> {row["Condition"]}<br>
        <b>Bedrooms:</b> {row["Bedrooms"]}<br>
        <b>Description:</b> {row["Description"][:160]}...<br>  <!-- Trimmed to 150 characters -->
        <a href='{row["URL"]}' target='_blank'>View Listing</a>
        """
        folium.Marker(
            location=[row["Latitude"], row["Longitude"]],
            popup=folium.Popup(popup_text, max_width=300),
            tooltip=row["Address"],
            icon=folium.Icon(color="blue", icon="home")
        ).add_to(m)

    # Save map to file
    m.save(map)
    print(f"Map file saved: {map}")

if __name__ == '__main__':
    scrape_and_generate()