import pandas as pd
import requests
from transfer_recommendation import recommend_transfers_one_transfer
from transfer_recommendation import recommend_transfers_wildcard


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

def get_top_players_by_position(dataframe):
	"""Get the top 10 players for each position based on BCV values."""
	top_players_by_position = {}
	for position in dataframe['Position'].unique():
		top_players = dataframe[dataframe['Position'] == position].head(10)
		top_players_by_position[position] = top_players
	return top_players_by_position

def main():
	df = pd.read_csv('../source_data/TransferAlgorithm.csv', encoding='ISO-8859-1')
	df = extract_bcv_values(df)
	df = filter_dataframe(df)
	all_players_df = df.sort_values(by='BCV', ascending=False)

	top_players_by_position = get_top_players_by_position(all_players_df)

	matching_names_df = pd.read_csv('../source_data/matching_names.csv')
	managers_df = pd.read_csv('../source_data/manager_ids_2024.csv')


	last_gameweek = 2

	for index, row in managers_df.iterrows():
		manager_id = row['ID']
		manager_name = row['Manager']
		wildcard = row.get('Wildcard', False)

		your_team_df = read_team_from_api(manager_id, last_gameweek)

		current_bank_value, current_team_value = read_manager_info_from_api(manager_id)
		
		print(f"{manager_name}'s Team value:")
		print(current_team_value)

		print(f"{manager_name}'s current bank:")
		print(current_bank_value)

		# Merge with matching names to ensure all web names have a corresponding 'Player' column
		your_team_df = pd.merge(
			left=your_team_df,
			right=matching_names_df,
			how='left',
			left_on='web_name',
			right_on='web_name'
		)

		# Replace web_name with the correct 'Player' name from matching_names_df
		your_team_df['Player'] = your_team_df['Player'].combine_first(your_team_df['web_name'])

		# Now merge with all_players_df using the corrected 'Player' names
		merged_team_df = pd.merge(
			left=your_team_df,
			right=all_players_df,
			how='left',
			on='Player'
		)
	
		non_matching_rows = merged_team_df['BCV'].isna()
		merged_team_df.loc[non_matching_rows, ['Position', 'Team', ' Price ', 'BCV']] = [None, None, None, None]

		position_order = {"GK": 1, "D": 2, "M": 3, "F": 4}
		merged_team_df['PositionOrder'] = merged_team_df['Position'].map(position_order)
		merged_team_df_BCV = merged_team_df.sort_values(by=['PositionOrder', 'BCV'], ascending=[True, False]).drop(columns='PositionOrder')
		
		non_matching_players = merged_team_df[non_matching_rows]
		if not non_matching_players.empty:
			print("\nThe following players did not have matching data:")
			print(non_matching_players[['web_name']])
		
		print(f"\n{manager_name}'s Full Merged Team Data:")
		print(merged_team_df_BCV[['web_name', 'Position', 'Team', ' Price ', 'BCV', str(last_gameweek + 1), str(last_gameweek + 2), str(last_gameweek + 3)]])
		
		
		# Define FPL team position rules
		fpl_positions = {'GK': 1, 'D': 3, 'M': 4, 'F': 2}  # Minimum required players, added temp fix to prioritize midfielders and forwards
		starting_eleven = {'GK': [], 'D': [], 'M': [], 'F': []}
		bench = {'GK': [], 'D': [], 'M': [], 'F': []}

		# Sort players for the next gameweek and pick the starting 11 and bench players according to FPL rules
		sorted_players = merged_team_df.sort_values(by=str(last_gameweek + 1), ascending=False)
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
			selected_bench = selected_bench.sort_values(by=str(last_gameweek + 1), ascending=False)

		# Print the recommended starting eleven and bench
		print(f"\n{manager_name}'s Recommended Starting 11 for Gameweek {last_gameweek + 1}:")
		print(selected_starting_eleven[['element', 'web_name', 'Position', 'Team', ' Price ', 'BCV', str(last_gameweek + 1)]])

		print(f"\n{manager_name}'s Recommended Bench for Gameweek {last_gameweek + 1}:")
		print(selected_bench[['element', 'web_name', 'Position', 'Team', ' Price ', 'BCV', str(last_gameweek + 1)]])

		'''
		if wildcard:
			result_df = recommend_transfers_wildcard(all_players_df, current_bank_value, current_team_value)
			print(result_df)
		else:
			recommendations = recommend_transfers_one_transfer(all_players_df, current_bank_value, current_team_value, your_team_df)
			print(recommendations)
		'''

	print(top_players_by_position)



if __name__ == "__main__":
	main()
