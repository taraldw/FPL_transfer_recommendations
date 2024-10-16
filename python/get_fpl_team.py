import pandas as pd
import requests
import os
from datetime import datetime

def load_source_data():
    source_data_path = get_source_data_path()
    df = pd.read_csv(f'{source_data_path}/TransferAlgorithm.csv', encoding='ISO-8859-1')
    df = extract_bcv_values(df)
    df = filter_dataframe(df)
    all_players_df = df.sort_values(by='BCV', ascending=False)
    matching_names_df = pd.read_csv(f'{source_data_path}/matching_names.csv')
    managers_df = pd.read_csv(f'{source_data_path}/manager_ids_2024.csv')
    return df, all_players_df, matching_names_df, managers_df

def process_manager(buffer, manager_id, manager_name, wildcard, next_gameweek, all_players_df, matching_names_df):
   
    your_team_df = read_team_from_api(manager_id, next_gameweek - 1)
    current_bank_value, current_team_value = read_manager_info_from_api(manager_id)
    print(f"{manager_name}'s Team value: {current_team_value}")
    print(f"{manager_name}'s current bank: {current_bank_value}")
    your_team_df = merge_with_matching_names(your_team_df, matching_names_df)
    merged_team_df = merge_with_all_players(your_team_df, all_players_df)
    non_matching_rows = merged_team_df['BCV'].isna()
    merged_team_df.loc[non_matching_rows, ['Position', 'Team', ' Price ', 'BCV']] = [None, None, None, None]

    position_order = {"GK": 1, "D": 2, "M": 3, "F": 4}
    merged_team_df['PositionOrder'] = merged_team_df['Position'].map(position_order)
    merged_team_df_BCV = merged_team_df.sort_values(by=['PositionOrder', 'BCV'], ascending=[True, False]).drop(columns='PositionOrder')
    
    non_matching_players = merged_team_df[non_matching_rows]
    if not non_matching_players.empty:
        print("\nThe following players did not have matching data:")
        non_matching_players.to_html(columns = ['web_name'], index=False, buf = buffer)
    
    print(f"\n{manager_name}'s Full Merged Team Data:")
    #html_parts.append(buffer.getvalue())
    merged_team_df_BCV.to_html(columns = ['web_name', 'Position', 'Team', ' Price ', 'BCV', str(next_gameweek), str(next_gameweek + 1), str(next_gameweek + 2)], index=False, buf=buffer)
    #html_parts.append(html_table)
    # Define FPL team position rules
    fpl_positions = {'GK': 1, 'D': 3, 'M': 4, 'F': 2}  # Minimum required players, added temp fix to prioritize midfielders and forwards
    starting_eleven = {'GK': [], 'D': [], 'M': [], 'F': []}
    bench = {'GK': [], 'D': [], 'M': [], 'F': []}

    # Sort players for the next gameweek and pick the starting 11 and bench players according to FPL rules
    sorted_players = merged_team_df.sort_values(by=str(next_gameweek), ascending=False)
    # Populate the starting eleven and bench
    for position, min_count in fpl_positions.items():
        position_players = sorted_players[sorted_players['Position'] == position]
        starting_players = position_players.head(min_count)
        bench_players = position_players.iloc[min_count:]
        starting_eleven[position].extend(starting_players.to_dict('records'))  # Extend the list of dicts
        bench[position].extend(bench_players.to_dict('records'))  # Extend the list of dicts

    # Count the total players in starting eleven
    total_starting_players = sum(len(players) for players in starting_eleven.values())

    # Add additional players to the starting eleven if less than 11
    additional_players_needed = 11 - total_starting_players
    if additional_players_needed > 0:
        for position in sorted(fpl_positions, key=fpl_positions.get, reverse=True):
            if additional_players_needed == 0:
                break
            available_bench_players = [player for player in bench[position] if player not in starting_eleven[position]]
            additional_players = available_bench_players[:additional_players_needed]
            starting_eleven[position].extend(additional_players)
            additional_players_needed -= len(additional_players)
            # Remove the additional players from the bench
            bench[position] = [player for player in bench[position] if player not in additional_players]

    # Flatten the starting_eleven and bench dictionaries to create a combined list of DataFrames
    starting_eleven_df_list = [pd.DataFrame(starting_eleven[pos]) for pos in starting_eleven if starting_eleven[pos]]
    bench_df_list = [pd.DataFrame(bench[pos]) for pos in bench if bench[pos]]

    # Concatenate the starting eleven and bench dataframes
    selected_starting_eleven = pd.concat(starting_eleven_df_list) if starting_eleven_df_list else pd.DataFrame()
    selected_bench = pd.concat(bench_df_list) if bench_df_list else pd.DataFrame()

    # If DataFrames are not empty, sort them by 'PositionOrder'
    if not selected_starting_eleven.empty:
        selected_starting_eleven['PositionOrder'] = selected_starting_eleven['Position'].map(position_order)
        selected_starting_eleven = selected_starting_eleven.sort_values(by='PositionOrder')

    if not selected_bench.empty:
        selected_bench = selected_bench.sort_values(by=str(next_gameweek), ascending=False)

    # Print the recommended starting eleven and bench
    print(f"\n{manager_name}'s Recommended Starting 11 for Gameweek {next_gameweek}:")
    selected_starting_eleven.to_html(columns = ['element', 'web_name', 'Position', 'Team', ' Price ', 'BCV', str(next_gameweek)], index=False, buf=buffer)

    print(f"\n{manager_name}'s Recommended Bench for Gameweek {next_gameweek}:")
    selected_bench.to_html(columns=['element', 'web_name', 'Position', 'Team', ' Price ', 'BCV', str(next_gameweek)], index=False, buf=buffer)

    '''
    if wildcard:
        result_df = recommend_transfers_wildcard(all_players_df, current_bank_value, current_team_value)
        print(result_df)
    else:
        recommendations = recommend_transfers_one_transfer(all_players_df, current_bank_value, current_team_value, your_team_df)
        print(recommendations)
    '''

    return buffer

    

def merge_with_matching_names(your_team_df, matching_names_df):
    your_team_df = pd.merge(
        left=your_team_df,
        right=matching_names_df,
        how='left',
        left_on='web_name',
        right_on='web_name'
    )
    your_team_df['Player'] = your_team_df['Player'].combine_first(your_team_df['web_name'])
    return your_team_df

def merge_with_all_players(your_team_df, all_players_df):
    merged_team_df = pd.merge(
        left=your_team_df,
        right=all_players_df,
        how='left',
        on='Player'
    )
    return merged_team_df

def read_team_from_api(manager_id, gameweek):
	# Fetch the team data for the given manager_id and gameweek
	team_url = f"https://fantasy.premierleague.com/api/entry/{manager_id}/event/{gameweek}/picks/"
	team_response = requests.get(team_url)
	team_response.raise_for_status()
	team_data = team_response.json()
	team_df = pd.DataFrame(team_data['picks'])[['element']]

	# Fetch the static bootstrap data with player information
	bootstrap_url = "https://fantasy.premierleague.com/api/bootstrap-static/"
	bootstrap_response = requests.get(bootstrap_url)
	bootstrap_response.raise_for_status()
	bootstrap_data = bootstrap_response.json()
	players_df = pd.DataFrame(bootstrap_data['elements'])[['id', 'web_name']]

	# Merge the dataframes based on the player 'id' and the 'element' from the team
	merged_df = pd.merge(team_df, players_df, left_on='element', right_on='id')[['element', 'web_name']]

	return merged_df

def read_manager_info_from_api(manager_id):
	# Fetch manager data using the given manager_id
	manager_url = f"https://fantasy.premierleague.com/api/entry/{manager_id}/"
	manager_response = requests.get(manager_url)
	manager_response.raise_for_status()
	manager_data = manager_response.json()

	# Extract necessary information and divide by 10
	current_bank_value = manager_data["last_deadline_bank"] / 10
	current_team_value = manager_data["last_deadline_value"] / 10

	return current_bank_value, current_team_value

def get_gameweek_info_from_api():
    response = requests.get('https://fantasy.premierleague.com/api/bootstrap-static/')
    data = response.json()
    last_gameweek_api = None
    next_gameweek_api = None
        
    for gameweek in data['events']:
        if gameweek['is_current']:
            last_gameweek_api = gameweek['id']
            deadline_time = gameweek['deadline_time']
            deadline_date = deadline_time.split('T')[0]  # Extract the date part
            date_object = datetime.strptime(deadline_date, '%Y-%m-%d')  # Convert to datetime object
            last_gameweek_api_deadline_date = date_object.strftime('%d-%b-%Y').upper()  # Format the date
        elif gameweek['is_next']:
            next_gameweek_api = gameweek['id']

    return last_gameweek_api, next_gameweek_api, last_gameweek_api_deadline_date


def read_team_from_csv(file_path):
	"""Read the team from a CSV file and categorize players."""
	df = pd.read_csv(file_path)
	
	# Group players by category
	categories = df['Position'].unique()
	category_to_players = {}

	for category in categories:
		players = df[df['Position'] == category]
		category_to_players[category] = players

	# Calculate the total number of team members
	num_team_members = df.shape[0]

	return category_to_players, num_team_members

def extract_bcv_values(dataframe):
	"""Extract BCV values from the dataframe."""
	dataframe['BCV'] = dataframe[' BCV '].str.extract(r'([-+]?\d*\.\d+|\d+)').astype(float)
	dataframe['BCV'] = dataframe['BCV'].abs()
	return dataframe

def filter_dataframe(dataframe):
	"""Filter out players with BCV equal to 1.00 and remove rows with 'nan' position type."""
	dataframe = dataframe[dataframe['BCV'] != 1.00]
	dataframe = dataframe[dataframe['Position'].notna()]
	dataframe = dataframe[dataframe['Player'] != 'Wood'] # Removes the defender Wood from the source data since the web_name Wood in the FPL api matches the forward
	return dataframe

def get_top_players_by_position(buffer, all_players_df, next_gameweek):
    """Get the top 10 players for each position based on BCV values."""
    top_players_by_position = {}
    for position in all_players_df['Position'].unique():
        top_players = all_players_df[all_players_df['Position'] == position].head(10)
        top_players_by_position[position] = top_players
    
    position_keys = {"GK": "goalkeepers", "D": "defenders", "M": "midfielders", "F": "forwards"}
    for position_key in top_players_by_position:
        print(f"\nTop 10 {position_keys[position_key]} by BCV for Gameweek {next_gameweek}:")
        top_players_df = top_players_by_position[position_key]
        top_players_df.to_html(columns = ['BCV', 'Player', 'Position', 'Team', ' Price ', str(next_gameweek), str(next_gameweek + 1), str(next_gameweek + 2)], index=False, buf=buffer)
    return buffer

def get_source_data_path():
    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Construct the path to the 'source_data' folder relative to the script
    source_data_path = os.path.join(script_dir, '../source_data')

    # Return the absolute path
    return os.path.abspath(source_data_path)