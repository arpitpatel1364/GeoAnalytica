"""
Geo Utilities — country metadata, ISO code lookups, scope definitions.
"""
from typing import Dict, List, Optional, Tuple

# ─────────────────────────────────────────────────────────────
# Complete country list with ISO2, ISO3, coordinates
# ─────────────────────────────────────────────────────────────
ALL_COUNTRIES: List[dict] = [
    {"name": "Afghanistan", "iso2": "AF", "iso3": "AFG", "lat": 33.93, "lon": 67.71},
    {"name": "Albania", "iso2": "AL", "iso3": "ALB", "lat": 41.15, "lon": 20.17},
    {"name": "Algeria", "iso2": "DZ", "iso3": "DZA", "lat": 28.03, "lon": 1.66},
    {"name": "Angola", "iso2": "AO", "iso3": "AGO", "lat": -11.20, "lon": 17.87},
    {"name": "Argentina", "iso2": "AR", "iso3": "ARG", "lat": -38.42, "lon": -63.62},
    {"name": "Armenia", "iso2": "AM", "iso3": "ARM", "lat": 40.07, "lon": 45.04},
    {"name": "Australia", "iso2": "AU", "iso3": "AUS", "lat": -25.27, "lon": 133.78},
    {"name": "Austria", "iso2": "AT", "iso3": "AUT", "lat": 47.52, "lon": 14.55},
    {"name": "Azerbaijan", "iso2": "AZ", "iso3": "AZE", "lat": 40.14, "lon": 47.58},
    {"name": "Bahrain", "iso2": "BH", "iso3": "BHR", "lat": 26.02, "lon": 50.55},
    {"name": "Bangladesh", "iso2": "BD", "iso3": "BGD", "lat": 23.68, "lon": 90.36},
    {"name": "Belarus", "iso2": "BY", "iso3": "BLR", "lat": 53.71, "lon": 27.95},
    {"name": "Belgium", "iso2": "BE", "iso3": "BEL", "lat": 50.50, "lon": 4.47},
    {"name": "Bolivia", "iso2": "BO", "iso3": "BOL", "lat": -16.29, "lon": -63.59},
    {"name": "Bosnia and Herzegovina", "iso2": "BA", "iso3": "BIH", "lat": 43.92, "lon": 17.68},
    {"name": "Botswana", "iso2": "BW", "iso3": "BWA", "lat": -22.33, "lon": 24.68},
    {"name": "Brazil", "iso2": "BR", "iso3": "BRA", "lat": -14.24, "lon": -51.93},
    {"name": "Brunei", "iso2": "BN", "iso3": "BRN", "lat": 4.54, "lon": 114.73},
    {"name": "Bulgaria", "iso2": "BG", "iso3": "BGR", "lat": 42.73, "lon": 25.49},
    {"name": "Burkina Faso", "iso2": "BF", "iso3": "BFA", "lat": 12.36, "lon": -1.56},
    {"name": "Burundi", "iso2": "BI", "iso3": "BDI", "lat": -3.37, "lon": 29.92},
    {"name": "Cambodia", "iso2": "KH", "iso3": "KHM", "lat": 12.57, "lon": 104.99},
    {"name": "Cameroon", "iso2": "CM", "iso3": "CMR", "lat": 7.37, "lon": 12.35},
    {"name": "Canada", "iso2": "CA", "iso3": "CAN", "lat": 56.13, "lon": -106.35},
    {"name": "Central African Republic", "iso2": "CF", "iso3": "CAF", "lat": 6.61, "lon": 20.94},
    {"name": "Chad", "iso2": "TD", "iso3": "TCD", "lat": 15.45, "lon": 18.73},
    {"name": "Chile", "iso2": "CL", "iso3": "CHL", "lat": -35.68, "lon": -71.54},
    {"name": "China", "iso2": "CN", "iso3": "CHN", "lat": 35.86, "lon": 104.20},
    {"name": "Colombia", "iso2": "CO", "iso3": "COL", "lat": 4.57, "lon": -74.30},
    {"name": "Congo", "iso2": "CG", "iso3": "COG", "lat": -0.23, "lon": 15.83},
    {"name": "Costa Rica", "iso2": "CR", "iso3": "CRI", "lat": 9.75, "lon": -83.75},
    {"name": "Croatia", "iso2": "HR", "iso3": "HRV", "lat": 45.10, "lon": 15.20},
    {"name": "Cuba", "iso2": "CU", "iso3": "CUB", "lat": 21.52, "lon": -77.78},
    {"name": "Czech Republic", "iso2": "CZ", "iso3": "CZE", "lat": 49.82, "lon": 15.47},
    {"name": "Democratic Republic of the Congo", "iso2": "CD", "iso3": "COD", "lat": -4.04, "lon": 21.76},
    {"name": "Denmark", "iso2": "DK", "iso3": "DNK", "lat": 56.26, "lon": 9.50},
    {"name": "Dominican Republic", "iso2": "DO", "iso3": "DOM", "lat": 18.74, "lon": -70.16},
    {"name": "Ecuador", "iso2": "EC", "iso3": "ECU", "lat": -1.83, "lon": -78.18},
    {"name": "Egypt", "iso2": "EG", "iso3": "EGY", "lat": 26.82, "lon": 30.80},
    {"name": "El Salvador", "iso2": "SV", "iso3": "SLV", "lat": 13.79, "lon": -88.90},
    {"name": "Eritrea", "iso2": "ER", "iso3": "ERI", "lat": 15.18, "lon": 39.78},
    {"name": "Estonia", "iso2": "EE", "iso3": "EST", "lat": 58.60, "lon": 25.01},
    {"name": "Eswatini", "iso2": "SZ", "iso3": "SWZ", "lat": -26.52, "lon": 31.47},
    {"name": "Ethiopia", "iso2": "ET", "iso3": "ETH", "lat": 9.15, "lon": 40.49},
    {"name": "Finland", "iso2": "FI", "iso3": "FIN", "lat": 61.92, "lon": 25.75},
    {"name": "France", "iso2": "FR", "iso3": "FRA", "lat": 46.23, "lon": 2.21},
    {"name": "Gabon", "iso2": "GA", "iso3": "GAB", "lat": -0.80, "lon": 11.61},
    {"name": "Gambia", "iso2": "GM", "iso3": "GMB", "lat": 13.44, "lon": -15.31},
    {"name": "Georgia", "iso2": "GE", "iso3": "GEO", "lat": 42.32, "lon": 43.36},
    {"name": "Germany", "iso2": "DE", "iso3": "DEU", "lat": 51.17, "lon": 10.45},
    {"name": "Ghana", "iso2": "GH", "iso3": "GHA", "lat": 7.95, "lon": -1.02},
    {"name": "Greece", "iso2": "GR", "iso3": "GRC", "lat": 39.07, "lon": 21.82},
    {"name": "Guatemala", "iso2": "GT", "iso3": "GTM", "lat": 15.78, "lon": -90.23},
    {"name": "Guinea", "iso2": "GN", "iso3": "GIN", "lat": 9.95, "lon": -11.24},
    {"name": "Haiti", "iso2": "HT", "iso3": "HTI", "lat": 18.97, "lon": -72.29},
    {"name": "Honduras", "iso2": "HN", "iso3": "HND", "lat": 15.20, "lon": -86.24},
    {"name": "Hungary", "iso2": "HU", "iso3": "HUN", "lat": 47.16, "lon": 19.50},
    {"name": "India", "iso2": "IN", "iso3": "IND", "lat": 20.59, "lon": 78.96},
    {"name": "Indonesia", "iso2": "ID", "iso3": "IDN", "lat": -0.79, "lon": 113.92},
    {"name": "Iran", "iso2": "IR", "iso3": "IRN", "lat": 32.43, "lon": 53.69},
    {"name": "Iraq", "iso2": "IQ", "iso3": "IRQ", "lat": 33.22, "lon": 43.68},
    {"name": "Ireland", "iso2": "IE", "iso3": "IRL", "lat": 53.41, "lon": -8.24},
    {"name": "Israel", "iso2": "IL", "iso3": "ISR", "lat": 31.05, "lon": 34.85},
    {"name": "Italy", "iso2": "IT", "iso3": "ITA", "lat": 41.87, "lon": 12.57},
    {"name": "Ivory Coast", "iso2": "CI", "iso3": "CIV", "lat": 7.54, "lon": -5.55},
    {"name": "Jamaica", "iso2": "JM", "iso3": "JAM", "lat": 18.11, "lon": -77.30},
    {"name": "Japan", "iso2": "JP", "iso3": "JPN", "lat": 36.20, "lon": 138.25},
    {"name": "Jordan", "iso2": "JO", "iso3": "JOR", "lat": 30.59, "lon": 36.24},
    {"name": "Kazakhstan", "iso2": "KZ", "iso3": "KAZ", "lat": 48.02, "lon": 66.92},
    {"name": "Kenya", "iso2": "KE", "iso3": "KEN", "lat": -0.02, "lon": 37.91},
    {"name": "Kuwait", "iso2": "KW", "iso3": "KWT", "lat": 29.31, "lon": 47.48},
    {"name": "Kyrgyzstan", "iso2": "KG", "iso3": "KGZ", "lat": 41.20, "lon": 74.77},
    {"name": "Laos", "iso2": "LA", "iso3": "LAO", "lat": 19.86, "lon": 102.50},
    {"name": "Latvia", "iso2": "LV", "iso3": "LVA", "lat": 56.88, "lon": 24.60},
    {"name": "Lebanon", "iso2": "LB", "iso3": "LBN", "lat": 33.85, "lon": 35.86},
    {"name": "Liberia", "iso2": "LR", "iso3": "LBR", "lat": 6.43, "lon": -9.43},
    {"name": "Libya", "iso2": "LY", "iso3": "LBY", "lat": 26.34, "lon": 17.23},
    {"name": "Lithuania", "iso2": "LT", "iso3": "LTU", "lat": 55.17, "lon": 23.88},
    {"name": "Madagascar", "iso2": "MG", "iso3": "MDG", "lat": -18.77, "lon": 46.87},
    {"name": "Malawi", "iso2": "MW", "iso3": "MWI", "lat": -13.25, "lon": 34.30},
    {"name": "Malaysia", "iso2": "MY", "iso3": "MYS", "lat": 4.21, "lon": 108.01},
    {"name": "Mali", "iso2": "ML", "iso3": "MLI", "lat": 17.57, "lon": -3.99},
    {"name": "Mauritania", "iso2": "MR", "iso3": "MRT", "lat": 21.01, "lon": -10.94},
    {"name": "Mexico", "iso2": "MX", "iso3": "MEX", "lat": 23.63, "lon": -102.55},
    {"name": "Moldova", "iso2": "MD", "iso3": "MDA", "lat": 47.41, "lon": 28.37},
    {"name": "Mongolia", "iso2": "MN", "iso3": "MNG", "lat": 46.86, "lon": 103.85},
    {"name": "Morocco", "iso2": "MA", "iso3": "MAR", "lat": 31.79, "lon": -7.09},
    {"name": "Mozambique", "iso2": "MZ", "iso3": "MOZ", "lat": -18.67, "lon": 35.53},
    {"name": "Myanmar", "iso2": "MM", "iso3": "MMR", "lat": 21.92, "lon": 95.96},
    {"name": "Namibia", "iso2": "NA", "iso3": "NAM", "lat": -22.96, "lon": 18.49},
    {"name": "Nepal", "iso2": "NP", "iso3": "NPL", "lat": 28.39, "lon": 84.12},
    {"name": "Netherlands", "iso2": "NL", "iso3": "NLD", "lat": 52.13, "lon": 5.29},
    {"name": "New Zealand", "iso2": "NZ", "iso3": "NZL", "lat": -40.90, "lon": 174.89},
    {"name": "Nicaragua", "iso2": "NI", "iso3": "NIC", "lat": 12.87, "lon": -85.21},
    {"name": "Niger", "iso2": "NE", "iso3": "NER", "lat": 17.61, "lon": 8.08},
    {"name": "Nigeria", "iso2": "NG", "iso3": "NGA", "lat": 9.08, "lon": 8.68},
    {"name": "North Korea", "iso2": "KP", "iso3": "PRK", "lat": 40.34, "lon": 127.51},
    {"name": "North Macedonia", "iso2": "MK", "iso3": "MKD", "lat": 41.61, "lon": 21.75},
    {"name": "Norway", "iso2": "NO", "iso3": "NOR", "lat": 60.47, "lon": 8.47},
    {"name": "Oman", "iso2": "OM", "iso3": "OMN", "lat": 21.47, "lon": 55.97},
    {"name": "Pakistan", "iso2": "PK", "iso3": "PAK", "lat": 30.38, "lon": 69.35},
    {"name": "Panama", "iso2": "PA", "iso3": "PAN", "lat": 8.54, "lon": -80.78},
    {"name": "Papua New Guinea", "iso2": "PG", "iso3": "PNG", "lat": -6.31, "lon": 143.96},
    {"name": "Paraguay", "iso2": "PY", "iso3": "PRY", "lat": -23.44, "lon": -58.44},
    {"name": "Peru", "iso2": "PE", "iso3": "PER", "lat": -9.19, "lon": -75.02},
    {"name": "Philippines", "iso2": "PH", "iso3": "PHL", "lat": 12.88, "lon": 121.77},
    {"name": "Poland", "iso2": "PL", "iso3": "POL", "lat": 51.92, "lon": 19.15},
    {"name": "Portugal", "iso2": "PT", "iso3": "PRT", "lat": 39.40, "lon": -8.22},
    {"name": "Qatar", "iso2": "QA", "iso3": "QAT", "lat": 25.35, "lon": 51.18},
    {"name": "Romania", "iso2": "RO", "iso3": "ROU", "lat": 45.94, "lon": 24.97},
    {"name": "Russia", "iso2": "RU", "iso3": "RUS", "lat": 61.52, "lon": 105.32},
    {"name": "Rwanda", "iso2": "RW", "iso3": "RWA", "lat": -1.94, "lon": 29.87},
    {"name": "Saudi Arabia", "iso2": "SA", "iso3": "SAU", "lat": 23.89, "lon": 45.08},
    {"name": "Senegal", "iso2": "SN", "iso3": "SEN", "lat": 14.50, "lon": -14.45},
    {"name": "Serbia", "iso2": "RS", "iso3": "SRB", "lat": 44.02, "lon": 21.01},
    {"name": "Sierra Leone", "iso2": "SL", "iso3": "SLE", "lat": 8.46, "lon": -11.78},
    {"name": "Singapore", "iso2": "SG", "iso3": "SGP", "lat": 1.35, "lon": 103.82},
    {"name": "Slovakia", "iso2": "SK", "iso3": "SVK", "lat": 48.67, "lon": 19.70},
    {"name": "Slovenia", "iso2": "SI", "iso3": "SVN", "lat": 46.15, "lon": 14.99},
    {"name": "Somalia", "iso2": "SO", "iso3": "SOM", "lat": 5.15, "lon": 46.20},
    {"name": "South Africa", "iso2": "ZA", "iso3": "ZAF", "lat": -30.56, "lon": 22.94},
    {"name": "South Korea", "iso2": "KR", "iso3": "KOR", "lat": 35.91, "lon": 127.77},
    {"name": "South Sudan", "iso2": "SS", "iso3": "SSD", "lat": 6.88, "lon": 31.31},
    {"name": "Spain", "iso2": "ES", "iso3": "ESP", "lat": 40.46, "lon": -3.75},
    {"name": "Sri Lanka", "iso2": "LK", "iso3": "LKA", "lat": 7.87, "lon": 80.77},
    {"name": "Sudan", "iso2": "SD", "iso3": "SDN", "lat": 12.86, "lon": 30.22},
    {"name": "Sweden", "iso2": "SE", "iso3": "SWE", "lat": 60.13, "lon": 18.64},
    {"name": "Switzerland", "iso2": "CH", "iso3": "CHE", "lat": 46.82, "lon": 8.23},
    {"name": "Syria", "iso2": "SY", "iso3": "SYR", "lat": 34.80, "lon": 38.99},
    {"name": "Taiwan", "iso2": "TW", "iso3": "TWN", "lat": 23.70, "lon": 120.96},
    {"name": "Tajikistan", "iso2": "TJ", "iso3": "TJK", "lat": 38.86, "lon": 71.28},
    {"name": "Tanzania", "iso2": "TZ", "iso3": "TZA", "lat": -6.37, "lon": 34.89},
    {"name": "Thailand", "iso2": "TH", "iso3": "THA", "lat": 15.87, "lon": 100.99},
    {"name": "Timor-Leste", "iso2": "TL", "iso3": "TLS", "lat": -8.87, "lon": 125.73},
    {"name": "Togo", "iso2": "TG", "iso3": "TGO", "lat": 8.62, "lon": 0.82},
    {"name": "Tunisia", "iso2": "TN", "iso3": "TUN", "lat": 33.89, "lon": 9.54},
    {"name": "Turkey", "iso2": "TR", "iso3": "TUR", "lat": 38.96, "lon": 35.24},
    {"name": "Turkmenistan", "iso2": "TM", "iso3": "TKM", "lat": 38.97, "lon": 59.56},
    {"name": "Uganda", "iso2": "UG", "iso3": "UGA", "lat": 1.37, "lon": 32.29},
    {"name": "Ukraine", "iso2": "UA", "iso3": "UKR", "lat": 48.38, "lon": 31.17},
    {"name": "United Arab Emirates", "iso2": "AE", "iso3": "ARE", "lat": 23.42, "lon": 53.85},
    {"name": "United Kingdom", "iso2": "GB", "iso3": "GBR", "lat": 55.38, "lon": -3.44},
    {"name": "United States", "iso2": "US", "iso3": "USA", "lat": 37.09, "lon": -95.71},
    {"name": "Uruguay", "iso2": "UY", "iso3": "URY", "lat": -32.52, "lon": -55.77},
    {"name": "Uzbekistan", "iso2": "UZ", "iso3": "UZB", "lat": 41.38, "lon": 64.59},
    {"name": "Venezuela", "iso2": "VE", "iso3": "VEN", "lat": 6.42, "lon": -66.59},
    {"name": "Vietnam", "iso2": "VN", "iso3": "VNM", "lat": 14.06, "lon": 108.28},
    {"name": "Yemen", "iso2": "YE", "iso3": "YEM", "lat": 15.55, "lon": 48.52},
    {"name": "Zambia", "iso2": "ZM", "iso3": "ZMB", "lat": -13.13, "lon": 27.85},
    {"name": "Zimbabwe", "iso2": "ZW", "iso3": "ZWE", "lat": -19.02, "lon": 29.15},
]

# Fast lookup indexes
_NAME_TO_ISO2: Dict[str, str] = {c["name"].lower(): c["iso2"] for c in ALL_COUNTRIES}
_NAME_TO_ISO3: Dict[str, str] = {c["name"].lower(): c["iso3"] for c in ALL_COUNTRIES}
_NAME_TO_COORDS: Dict[str, Tuple[float, float]] = {
    c["name"].lower(): (c["lat"], c["lon"]) for c in ALL_COUNTRIES
}
_ISO2_TO_META: Dict[str, dict] = {c["iso2"]: c for c in ALL_COUNTRIES}
_ISO3_TO_META: Dict[str, dict] = {c["iso3"]: c for c in ALL_COUNTRIES}

# ─────────────────────────────────────────────────────────────
# Scope definitions (ISO2 codes)
# ─────────────────────────────────────────────────────────────
SCOPE_COUNTRIES: Dict[str, List[str]] = {
    "g7": ["US", "GB", "FR", "DE", "IT", "CA", "JP"],
    "g20": [
        "AR", "AU", "BR", "CA", "CN", "FR", "DE", "IN", "ID",
        "IT", "JP", "MX", "RU", "SA", "ZA", "KR", "TR", "GB", "US",
    ],
    "brics": ["BR", "RU", "IN", "CN", "ZA"],
    "eu": [
        "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
        "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL",
        "PL", "PT", "RO", "SK", "SI", "ES", "SE",
    ],
    "africa": [
        "DZ", "AO", "BJ", "BW", "BF", "BI", "CM", "CF", "TD", "CG",
        "CD", "CI", "DJ", "EG", "ER", "ET", "GA", "GM", "GH", "GN",
        "KE", "LS", "LR", "LY", "MG", "MW", "ML", "MR", "MA", "MZ",
        "NA", "NE", "NG", "RW", "SN", "SL", "SO", "ZA", "SS", "SD",
        "SZ", "TZ", "TG", "TN", "UG", "ZM", "ZW",
    ],
    "asia": [
        "AF", "AM", "AZ", "BH", "BD", "BT", "BN", "KH", "CN", "GE",
        "IN", "ID", "IR", "IQ", "IL", "JP", "JO", "KZ", "KW", "KG",
        "LA", "LB", "MY", "MV", "MN", "MM", "NP", "KP", "OM", "PK",
        "PH", "QA", "SA", "SG", "KR", "LK", "SY", "TW", "TJ", "TH",
        "TL", "TR", "TM", "AE", "UZ", "VN", "YE",
    ],
    "sea": ["BN", "KH", "ID", "LA", "MY", "MM", "PH", "SG", "TH", "TL", "VN"],
    "middle_east": ["BH", "EG", "IR", "IQ", "IL", "JO", "KW", "LB", "OM", "QA", "SA", "SY", "AE", "YE"],
    "americas": [
        "AR", "BO", "BR", "CA", "CL", "CO", "CR", "CU", "DO", "EC",
        "SV", "GT", "HT", "HN", "JM", "MX", "NI", "PA", "PY", "PE",
        "TT", "US", "UY", "VE",
    ],
}


def name_to_iso2(name: str) -> Optional[str]:
    return _NAME_TO_ISO2.get(name.lower())


def name_to_iso3(name: str) -> Optional[str]:
    return _NAME_TO_ISO3.get(name.lower())


def name_to_coords(name: str) -> Optional[Tuple[float, float]]:
    return _NAME_TO_COORDS.get(name.lower())


def iso2_to_meta(iso2: str) -> Optional[dict]:
    return _ISO2_TO_META.get(iso2.upper())


def iso3_to_meta(iso3: str) -> Optional[dict]:
    return _ISO3_TO_META.get(iso3.upper())


def get_countries_by_scope(scope: str) -> List[dict]:
    codes = SCOPE_COUNTRIES.get(scope, [])
    return [c for c in ALL_COUNTRIES if c["iso2"] in codes]
