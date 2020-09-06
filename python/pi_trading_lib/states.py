NAME_TO_ABBRV = {
    "alabama": "AL",
    "alaska": "AK",
    "arizona": "AZ",
    "arkansas": "AR",
    "california": "CA",
    "colorado": "CO",
    "connecticut": "CT",
    "delaware": "DE",
    "district of columbia": "DC",
    "florida": "FL",
    "georgia": "GA",
    "hawaii": "HI",
    "idaho": "ID",
    "illinois": "IL",
    "indiana": "IN",
    "iowa": "IA",
    "kansas": "KS",
    "kentucky": "KY",
    "louisiana": "LA",
    "maine": "ME",
    "maryland": "MD",
    "massachusetts": "MA",
    "michigan": "MI",
    "minnesota": "MN",
    "mississippi": "MS",
    "missouri": "MO",
    "montana": "MT",
    "nebraska": "NE",
    "nevada": "NV",
    "new hampshire": "NH",
    "new jersey": "NJ",
    "new mexico": "NM",
    "new york": "NY",
    "north carolina": "NC",
    "north dakota": "ND",
    "ohio": "OH",
    "oklahoma": "OK",
    "oregon": "OR",
    "pennsylvania": "PA",
    "rhode island": "RI",
    "south carolina": "SC",
    "south dakota": "SD",
    "tennessee": "TN",
    "texas": "TX",
    "utah": "UT",
    "vermont": "VT",
    "virginia": "VA",
    "washington": "WA",
    "west virginia": "WV",
    "wisconsin": "WI",
    "wyoming": "WY",
}

ABBRV_TO_NAME = {val: key for key, val in NAME_TO_ABBRV.items()}

EC_SPECIAL_DISTRICTS = ['ME-1', 'ME-2', 'NE-1', 'NE-2', 'NE-3']


def get_state_abbrv_pres(state_name):
    """
    Maps state name to abbreviation for presidential election electoral college

    Wyoming -> WY
    wyoming -> WY
    ME-1 -> ME-1
    """

    if state_name.lower() in NAME_TO_ABBRV:
        return NAME_TO_ABBRV[state_name.lower()]
    if state_name in EC_SPECIAL_DISTRICTS:
        return state_name
    return None
