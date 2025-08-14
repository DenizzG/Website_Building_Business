import pandas as pd

# 1. Read all tables from the Wikipedia page
url = "https://en.wikipedia.org/wiki/List_of_United_States_cities_by_population"
tables = pd.read_html(url)

print(f"Found {len(tables)} tables on the page")

# 2. Find the correct table by inspecting each one
df = None
for i, table in enumerate(tables):
    print(f"\nTable {i} columns: {table.columns.tolist()}")
    print(f"Table {i} shape: {table.shape}")
    
    # Look for a table with city names and population data
    has_city_col = any('city' in str(col).lower() for col in table.columns)
    has_pop_col = any('estimate' in str(col).lower() or 'population' in str(col).lower() for col in table.columns)
    
    if has_city_col and has_pop_col and table.shape[0] > 50:  # Should have many cities
        print(f"Using table {i} as it has city and population columns")
        df = table
        break

if df is None:
    print("Could not find a suitable table with city and population data")
    exit(1)

# Find the city and population columns
city_col = None
population_col = None

for col in df.columns:
    if 'city' in str(col).lower():
        city_col = col
    if 'estimate' in str(col).lower() or 'population' in str(col).lower():
        population_col = col

print(f"Using city column: '{city_col}'")
print(f"Using population column: '{population_col}'")

if city_col is None or population_col is None:
    print("Could not find both city and population columns")
    print("Available columns:", df.columns.tolist())
    exit(1)

# 3. Clean the population data: remove footnote markers and commas
df[population_col] = (
    df[population_col]
    .astype(str)
    .str.replace(r"\[.*?\]", "", regex=True)  # Remove reference annotations
    .str.replace(",", "", regex=False)        # Remove commas
    .str.replace("−", "0", regex=False)       # Handle any minus signs
)

# Convert to numeric, handling any remaining non-numeric values
df[population_col] = pd.to_numeric(df[population_col], errors='coerce')

# Drop rows where population couldn't be converted
df = df.dropna(subset=[population_col])

print(f"Total cities with valid population data: {len(df)}")

# 4. Filter cities with population between 100k and 300k
filtered = df[(df[population_col] >= 100_000) & (df[population_col] <= 300_000)]

cities = filtered[city_col].tolist()
print(f"\nFound {len(cities)} cities with population 100k-300k:")
for city in cities[:20]:  # Show first 20
    print(f"  {city}")
if len(cities) > 20:
    print(f"  ... and {len(cities) - 20} more")

# Save to a text file for easy copying
with open('cities_100k_300k.txt', 'w') as f:
    for city in cities:
        f.write(f'"{city}",\n')
print(f"\nSaved {len(cities)} cities to cities_100k_300k.txt")
