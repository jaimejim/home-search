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
        "Rakennusvuosi": "N/A",  # Added construction year
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

    # Get construction year from property details
    construction_year = property_details.get("Rakennusvuosi", "N/A")

    # Create formatted data with essential fields
    formatted_data = {
        "Address": json_data.get("address", {}).get("streetAddress", "N/A"),
        "Price (€)": json_data.get("offers", {}).get("price", "N/A"),
        "Size (m²)": json_data.get("floorSize", {}).get("value", "N/A"),
        "Construction Year": construction_year,
    }

    # Validate essential fields
    missing_fields = [
        field
        for field, value in formatted_data.items()
        if value == "N/A" or value is None
    ]

    if missing_fields:
        print(f"\nWarning: Missing essential fields for property:")
        print(f"URL: {json_data.get('url', 'N/A')}")
        print(f"Missing fields: {', '.join(missing_fields)}")
        print("Raw data:")
        print(f"Address: {json_data.get('address', {})}")
        print(f"Price: {json_data.get('offers', {})}")
        print(f"Size: {json_data.get('floorSize', {})}")
        print(f"Construction Year: {property_details.get('Rakennusvuosi', 'N/A')}")

    # Add the rest of the fields
    formatted_data.update(
        {
            "City": json_data.get("address", {}).get("addressRegion", "N/A"),
            "Neighborhood": json_data.get("address", {}).get("addressLocality", "N/A"),
            "Postal Code": json_data.get("address", {}).get("postalCode", "N/A"),
            "Latitude": float(json_data.get("geo", {}).get("latitude", 0)),
            "Longitude": float(json_data.get("geo", {}).get("longitude", 0)),
            "Condition": json_data.get("itemCondition", {}).get("name", "N/A"),
            "Bedrooms": json_data.get("numberOfRooms", "N/A"),
            "Description": json_data.get("description", "N/A"),
            "URL": json_data.get("url", "N/A"),
            "Hoitovastike": property_details.get("Hoitovastike", "N/A"),
            "Pääomavastike": property_details.get("Pääomavastike", "N/A"),
            "Erityisvastike": property_details.get("Erityisvastike", "N/A"),
            "Yhtiövastike yhteensä": property_details.get(
                "Yhtiövastike yhteensä", "N/A"
            ),
        }
    )

    return formatted_data


def load_existing_urls(csv_path):
    """
    Load existing property URLs from the CSV file.
    """
    if os.path.exists(csv_path):
        df_existing = pd.read_csv(csv_path)
        return set(df_existing["URL"].tolist())  # Store URLs in a set for fast lookup
    return set()


def update_property_data(existing_df, new_property, url):
    """
    Update property data based on different scenarios
    Returns: (updated_row, status)
    Status can be: 'new', 'price_increased', 'price_decreased', 'no_change', 'removed'
    """
    if existing_df.empty or url not in existing_df['URL'].values:
        new_property['icon'] = "home"  # Only new properties get home icon
        return new_property, 'new'

    # Check if property exists
    existing_row = existing_df[existing_df['URL'] == url]
    
    existing_price = float(existing_row['Price (€)'].iloc[0])
    new_price = float(new_property['Price (€)'])

    # Update the row with existing data
    updated_row = existing_row.iloc[0].to_dict()
    
    # Always update the construction year if it's available in new data
    if new_property.get('Construction Year') not in ['N/A', None]:
        updated_row['Construction Year'] = new_property['Construction Year']
    
    if new_price > existing_price:
        updated_row['Price (€)'] = new_price
        updated_row['icon'] = "arrow-up"
        return updated_row, 'price_increased'
    elif new_price < existing_price:
        updated_row['Price (€)'] = new_price
        updated_row['icon'] = "arrow-down"
        return updated_row, 'price_decreased'
    else:
        updated_row['icon'] = ""  # Blank icon for no changes
        return updated_row, 'no_change'

def load_and_update_data(url_file, csv_path):
    """
    Load existing data and handle property updates
    """
    # Create empty DataFrame if file doesn't exist
    if os.path.exists(csv_path):
        df_existing = pd.read_csv(csv_path)
    else:
        df_existing = pd.DataFrame()

    # Add current timestamp
    current_time = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')

    updated_data = []
    status_counts = {
        'new': 0, 
        'price_increased': 0, 
        'price_decreased': 0, 
        'no_change': 0, 
        'removed': 0
    }

    # Read URLs from file
    with open(url_file, "r") as file:
        current_urls = {line.strip() for line in file if line.strip()}

    # First, handle existing properties not in current URLs
    if not df_existing.empty:
        for _, row in df_existing.iterrows():
            if row['URL'] not in current_urls:
                row_dict = row.to_dict()
                row_dict['icon'] = "house-user"  # Mark as removed
                updated_data.append(row_dict)
                status_counts['removed'] += 1

    # Process each current URL
    for url in current_urls:
        try:
            html = fetch_html(url)
            if html:
                json_ld_data = extract_json_ld(html)
                property_info = format_property_data(json_ld_data, html)
                if property_info:
                    updated_row, status = update_property_data(df_existing, property_info, url)
                    updated_data.append(updated_row)
                    status_counts[status] += 1
            else:
                # Handle removed properties (410 status code)
                existing_row = df_existing[df_existing['URL'] == url]
                if not existing_row.empty:
                    row_dict = existing_row.iloc[0].to_dict()
                    row_dict['icon'] = "house-user"  # Mark as removed
                    updated_data.append(row_dict)
                    status_counts['removed'] += 1

        except Exception as e:
            print(f"Error processing URL {url}: {str(e)}")
            continue

 # Create new DataFrame with updated data
    df_new = pd.DataFrame(updated_data)
    
    # Add last_updated column and clean data before saving
    if not df_new.empty:
        # Clean coordinates
        try:
            df_new['Latitude'] = pd.to_numeric(df_new['Latitude'].astype(str).str.extract(r'([-]?\d+\.?\d*)')[0])
            df_new['Longitude'] = pd.to_numeric(df_new['Longitude'].astype(str).str.extract(r'([-]?\d+\.?\d*)')[0])
            df_new = df_new.dropna(subset=['Latitude', 'Longitude'])
            
            # Round coordinates to 6 decimal places
            df_new['Latitude'] = df_new['Latitude'].round(6)
            df_new['Longitude'] = df_new['Longitude'].round(6)
        except Exception as e:
            print(f"Error cleaning coordinates before saving: {e}")
            print("Sample of problematic data:")
            print(df_new[['Latitude', 'Longitude']].head())
            raise

        # Add last_updated column
        df_new['last_updated'] = current_time
        df_new.to_csv(csv_path, index=False, encoding='utf-8', float_format='%.6f')
        
        print("\nUpdate Summary:")
        print(f"Last Updated: {current_time}")
        print(f"New properties: {status_counts['new']}")
        print(f"Price increases: {status_counts['price_increased']}")
        print(f"Price decreases: {status_counts['price_decreased']}")
        print(f"No changes: {status_counts['no_change']}")
        print(f"Removed properties: {status_counts['removed']}")
        print(f"\nTotal properties in database: {len(df_new)}")
    
    return df_new

def clean_coordinates(df):
    """Clean and validate coordinates for Finland"""
    df = df.copy()
    try:
        # Convert coordinates to numeric, replacing invalid values with NaN
        df['Latitude'] = pd.to_numeric(df['Latitude'].astype(str).str.extract(r'([-]?\d+\.?\d*)')[0])
        df['Longitude'] = pd.to_numeric(df['Longitude'].astype(str).str.extract(r'([-]?\d+\.?\d*)')[0])
        
        # Drop rows with invalid coordinates
        df = df.dropna(subset=['Latitude', 'Longitude'])
        
        # Validate coordinate ranges for Finland
        df = df[
            (df['Latitude'] >= 59.5) & (df['Latitude'] <= 70.0) &
            (df['Longitude'] >= 20.0) & (df['Longitude'] <= 31.5)
        ]
    except Exception as e:
        print(f"Error cleaning coordinates: {e}")
        print("Sample of problematic data:")
        print(df[['Latitude', 'Longitude']].head())
        raise

    if df.empty:
        raise ValueError("No valid coordinates found in the data")
    
    return df

def create_tooltip_and_popup(row):
    """Create tooltip and popup HTML for a property"""
    construction_year = row.get('Construction Year', 'N/A')
    if pd.isna(construction_year):
        construction_year = 'N/A'

    tooltip_text = f"""
    <b>{row['Address']}</b><br>
    <b>Price:</b> €{row['Price (€)']}<br>
    <b>Size:</b> {row['Size (m²)']} m²<br>
    <b>Year:</b> {construction_year}
    """

    popup_text = f"""
    <b>{row['Address']}</b><br>
    <b>City:</b> {row['City']}<br>
    <b>Neighborhood:</b> {row['Neighborhood']}<br>
    <b>Postal Code:</b> {row['Postal Code']}<br>
    <b>Price:</b> €{row['Price (€)']}<br>
    <b>Size:</b> {row['Size (m²)']} m²<br>
    <b>Construction Year:</b> {construction_year}<br>
    <b>Condition:</b> {row['Condition']}<br>
    <b>Bedrooms:</b> {row['Bedrooms']}<br>
    <b>Maintenance charge:</b> {row['Hoitovastike']}<br>
    <b>Capital charge:</b> {row['Pääomavastike']}<br>
    <b>Special charge:</b> {row['Erityisvastike']}<br>
    <b>Total company charge:</b> {row['Yhtiövastike yhteensä']}<br>
    <a href='{row['URL']}' target='_blank'>View Listing</a>
    """
    
    return tooltip_text, popup_text

def create_legend():
    """Create the legend HTML"""
    return '''
    <div style="position: fixed; 
                bottom: 50px; right: 50px; width: 150px; height: 160px; 
                border:2px solid grey; z-index:9999; font-size:14px;
                background-color:white;
                padding: 10px;
                border-radius: 5px;
                ">
        <p style="margin-top: 0;"><b>Legend</b></p>
        <p style="margin: 0;">
        <i class="fa fa-home"></i> New listing<br>
        <i class="fa fa-arrow-up"></i> Price increased<br>
        <i class="fa fa-arrow-down"></i> Price decreased<br>
        <i class="fa fa-house-user"></i> Removed<br>
        <i class="fa fa-map-marker"></i> No change
        </p>
    </div>
    '''

def create_map(df):
    """Create a map with property markers and legend"""
    # Clean and validate coordinates
    df = clean_coordinates(df)
    
    # Calculate center point
    center_lat = df['Latitude'].mean()
    center_lon = df['Longitude'].mean()

    # Create the base map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=11,
        tiles=None
    )

    # Add tile layer
    stadia_toner = folium.TileLayer(
        tiles=f"https://tiles.stadiamaps.com/tiles/stamen_toner/{{z}}/{{x}}/{{y}}.png?api_key={stadia_api_key}",
        name="Stamen Toner",
        attr="Tiles © Stadia Maps, © OpenMapTiles, © OpenStreetMap contributors",
    )
    stadia_toner.add_to(m)

    # Add markers for all properties
    for _, row in df.iterrows():
        tooltip_text, popup_text = create_tooltip_and_popup(row)
        icon = row.get('icon', '')  # Default to empty if no icon specified
        
        folium.Marker(
            location=[row['Latitude'], row['Longitude']],
            popup=folium.Popup(popup_text, max_width=300),
            tooltip=folium.Tooltip(tooltip_text),
            icon=plugins.BeautifyIcon(
                icon=icon if icon else None,
                icon_shape="marker",
                border_color="#black",
                background_color="white",
                border_width=3
            )
        ).add_to(m)

    # Add legend
    m.get_root().html.add_child(folium.Element(create_legend()))

    return m


@click.command()
@click.argument("url_file", type=click.Path(exists=True))
@click.option("--csv", default="properties.csv", help="Output CSV file name.")
@click.option("--map", default="index.html", help="Output HTML file for the map.")
def scrape_and_generate(url_file, csv, map):
    """
    Fetch property data from URLs in a given file, generate CSV and an interactive map.
    """
    # Load existing data and append new properties
    df_new = load_and_update_data(url_file, csv)

    if df_new.empty:
        print("No properties to add to the map")
        return

    # Load the complete dataset for mapping
    df_all = pd.read_csv(csv)
    
    # Clean coordinates before creating map
    try:
        df_all['Latitude'] = pd.to_numeric(df_all['Latitude'].astype(str).str.extract(r'([-]?\d+\.?\d*)')[0])
        df_all['Longitude'] = pd.to_numeric(df_all['Longitude'].astype(str).str.extract(r'([-]?\d+\.?\d*)')[0])
        df_all = df_all.dropna(subset=['Latitude', 'Longitude'])
    except Exception as e:
        print(f"Error cleaning coordinates in final dataset: {e}")
        print("Sample of problematic data:")
        print(df_all[['Latitude', 'Longitude']].head())
        raise

    # Create map with all properties
    m = create_map(df_all)
    m.save(map)
    print(f"Map file saved: {map} with {len(df_all)} properties")


if __name__ == "__main__":
    scrape_and_generate()
