import requests
import pandas as pd

# Define the API URL
api_url = "https://fantasy.premierleague.com/api/entry/3602494/event/5/picks/"

try:
    # Send a GET request to the API URL
    response = requests.get(api_url)

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Parse the JSON response
        data = response.json()

        # Create a Pandas DataFrame from the data
        df = pd.DataFrame(data["picks"])

        # Print the DataFrame
        print("Team Data:")
        print(df)

except requests.exceptions.RequestException as e:
    print(f"Error: {e}")
