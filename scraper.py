import os
import json
import requests
import pandas as pd
import folium
import folium.plugins as plugins
import click
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
stadia_api_key = os.getenv("STADIA_MAPS_KEY")


def fetch_html(url):
    """
    Fetch HTML content using requests.
    """
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        html = response.text
        with open("debug.html", "w", encoding="utf-8") as file:
            file.write(html)  # Save the HTML to a file
        return html
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


def extract_property_details(html_source):
    """
    Extract property details (fees and price-related information) from the HTML source.
    """
    soup = BeautifulSoup(html_source, "html.parser")

    # Initialize a dictionary to store results
    property_details = {
        "Velaton hinta": "N/A",
        "Myyntihinta": "N/A",
        "Lainaosuuden maksu": "N/A",
        "Neliöhinta": "N/A",
        "Velkaosuus": "N/A",
        "Hoitovastike": "N/A",
        "Pääomavastike": "N/A",
        "Erityisvastike": "N/A",
        "Yhtiövastike yhteensä": "N/A",
        "Lämmityskustannukset": "N/A",
        "Muut kustannukset": "N/A",
    }

    # Look for all `dl` elements and parse each row
    dl_elements = soup.find_all("dl", class_="info-table")

    for dl in dl_elements:
        rows = dl.find_all("div", class_="info-table__row")
        for row in rows:
            dt = row.find("dt", class_="info-table__title")  # Field title
            dd = row.find("dd", class_="info-table__value")  # Field value

            if dt and dd:
                title = dt.text.strip()
                value = dd.text.strip()

                # Match titles to corresponding fields
                if title in property_details:
                    property_details[title] = value

    return property_details


def format_property_data(json_data, html_source):
    """
    Format extracted JSON-LD data into a structured dictionary, including detailed fees and costs.
    """
    if not json_data:
        return None

    # Extract property-specific details
    property_details = extract_property_details(html_source)

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
        "URL": json_data.get("url", "N/A"),
        **property_details,  # Add all extracted details
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
@click.argument("url_file", type=click.Path(exists=True))
@click.option("--csv", default="properties.csv", help="Output CSV file name.")
@click.option("--map", default="index.html", help="Output HTML file for the map.")
def scrape_and_generate(url_file, csv, map):
    """
    Fetch property data from URLs in a given file, generate CSV and an interactive map.
    """
    with open(url_file, "r") as file:
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
            property_info = format_property_data(json_ld_data, html)
            if property_info:
                data.append(property_info)

    if not data:
        print("No new properties to add. Exiting.")
        return

    df_new = pd.DataFrame(data)
    df_new.to_csv(csv, index=False, encoding="utf-8")
    print(f"CSV file updated: {csv}")

    m = folium.Map(
        location=[60.2, 24.8], zoom_start=12, tiles=None  # Start with no default tiles
    )

    stadia_toner = folium.TileLayer(
        tiles=f"https://tiles.stadiamaps.com/tiles/stamen_toner/{{z}}/{{x}}/{{y}}.png?api_key={stadia_api_key}",
        name="Stamen Toner",
        attr="Tiles © Stadia Maps, © OpenMapTiles, © OpenStreetMap contributors",
    )

    stadia_toner.add_to(m)  # This ensures it is the first added layer

    # folium.TileLayer(
    #     tiles=f"https://tiles.stadiamaps.com/tiles/alidade_smooth/{{z}}/{{x}}/{{y}}.png?api_key={stadia_api_key}",
    #     name="Stadia Smooth",
    #     attr="Tiles © Stadia Maps, © OpenMapTiles, © OpenStreetMap contributors",
    # ).add_to(m)

    # folium.TileLayer(
    #     tiles=f"https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{{z}}/{{x}}/{{y}}.png?api_key={stadia_api_key}",
    #     name="Stadia Smooth Dark",
    #     attr="Tiles © Stadia Maps, © OpenMapTiles, © OpenStreetMap contributors",
    # ).add_to(m)

    # folium.TileLayer(
    #     tiles="OpenStreetMap", name="OpenStreetMap", attr="© OpenStreetMap contributors"
    # ).add_to(m)

    # folium.LayerControl().add_to(m)

    for _, row in df_new.iterrows():
        popup_text = f"""
        <b>{row['Address']}</b><br>
        <b>City:</b> {row['City']}<br>
        <b>Neighborhood:</b> {row['Neighborhood']}<br>
        <b>Postal Code:</b> {row['Postal Code']}<br>
        <b>Price:</b> €{row['Price (€)']}<br>
        <b>Size:</b> {row['Size (m²)']} m²<br>
        <b>Condition:</b> {row['Condition']}<br>
        <b>Bedrooms:</b> {row['Bedrooms']}<br>
        <b>Maintenance charge:</b> {row['Hoitovastike']}<br>
        <b>Capital charge:</b> {row['Pääomavastike']}<br>
        <b>Special charge:</b> {row['Erityisvastike']}<br>
        <b>Total company charge:</b> {row['Yhtiövastike yhteensä']}<br>
        <a href='{row['URL']}' target='_blank'>View Listing</a>
        """
        folium.Marker(
            location=[row["Latitude"], row["Longitude"]],
            popup=folium.Popup(popup_text, max_width=300),
            icon=plugins.BeautifyIcon(
                #icon="home",  # Change to another FontAwesome icon if needed
                icon_shape="marker",
                border_color="#0000FF",  # Orange (stands out well)
                text_color="white",  # White text for contrast
                background_color="white",  # Dark Blue (contrasts against grayscale)
                border_width=5
            )
        ).add_to(m)

    m.save(map)
    print(f"Map file saved: {map}")


if __name__ == "__main__":
    scrape_and_generate()
