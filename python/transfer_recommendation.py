import pandas as pd

def recommend_transfers_one_transfer(all_players_df, current_bank_value, current_team_df):
    """
    Recommend a player transfer based on available players, bank value, and current team.

    Parameters:
    - all_players_df: DataFrame containing all available players.
    - current_bank_value: float, current bank value available for transfers.
    - current_team_df: DataFrame containing the current team members.

    Returns:
    Dictionary of recommended player transfers for each position.
    """
    
    # Exclude current team players from all available players
    df = all_players_df[~all_players_df['Player'].isin(current_team_df['Player'])]
    
    # Fetching all unique positions available in the dataframe
    positions = df['Position'].unique()
    
    recommendations = {}
    
    for position in positions:
        position_players = df[df['Position'] == position]
        
        if position_players.empty:
            continue
        
        # Sorting players based on the BCV in descending order to prioritize higher values
        sorted_players = position_players.sort_values(by='BCV', ascending=False)
        top_player = sorted_players.iloc[0]

        potential_transfers = []

        # Iterate through sorted players to find potential transfers
        for _, player_row in sorted_players.iterrows():
            if player_row['Player'] != top_player['Player']:
                price_difference = player_row['Price'] - top_player['Price']
                if price_difference <= current_bank_value:
                    potential_transfers.append((top_player['Player'], player_row['Player'], player_row['BCV'], price_difference))
        
        # Storing potential transfers for each position in the recommendations dictionary
        if potential_transfers:
            recommendations[position] = potential_transfers
    
    return recommendations

def pick_better_player(current_budget, position, selected_players_list, all_players_df):
    better_players = all_players_df[(all_players_df['Position'] == position) & (~all_players_df['Player'].isin([x['Player'] for x in selected_players_list]))]
    better_players = better_players.sort_values(by='BCV', ascending=False)
    for _, player in better_players.iterrows():
        if player['Price'] <= current_budget:
            selected_players_list.append({
                'Player': player['Player'],
                'Position': player['Position'],
                'BCV': player['BCV'],
                'Price': player['Price'],
                'Team': player['Team']  # Storing team information
            })
            current_budget -= player['Price']
            break
    return current_budget, selected_players_list

def recommend_transfers_wildcard(all_players_df, current_bank_value, current_team_value):
    positions = {"GK": 2, "D": 5, "M": 5, "F": 3}
    budget = current_bank_value + current_team_value
    threshold_budget = 1.0

    team_player_count = {}

    def get_cheap_players(position):
        return all_players_df[all_players_df['Position'] == position].nsmallest(1, 'Price').sort_values(by='BCV', ascending=False)

    def add_player_to_selected(player, position):
        nonlocal budget
        nonlocal positions
        nonlocal team_player_count
        
        selected_players_list.append({
            'Player': player['Player'],
            'Position': position,
            'BCV': player['BCV'],
            'Price': player['Price'],
            'Team': player['Team']
        })
        team = player['Team']
        team_player_count[team] = team_player_count.get(team, 0) + 1
        budget -= player['Price']
        positions[position] -= 1

    selected_players_list = []

    for pos in positions:
        cheap_players = get_cheap_players(pos)
        if not cheap_players.empty:
            top_cheap_player = cheap_players.iloc[0]
            if positions[pos] > 0 and top_cheap_player['Price'] <= budget:
                team = top_cheap_player['Team']
                if team_player_count.get(team, 0) < 3:
                    add_player_to_selected(top_cheap_player, pos)

    for pos, count in positions.items():
        position_players = all_players_df[
            (all_players_df['Position'] == pos) &
            (~all_players_df['Player'].isin([x['Player'] for x in selected_players_list]))
        ]
        position_players = position_players.sort_values(by='BCV', ascending=False)
        for _, player in position_players.iterrows():
            if positions[pos] > 0 and player['Price'] <= budget:
                team = player['Team']
                if team_player_count.get(team, 0) < 3:
                    add_player_to_selected(player, pos)

    while budget > threshold_budget:
        sorted_selected = sorted(selected_players_list, key=lambda x: (x['Price'], -x['BCV']))
        player_to_remove = sorted_selected[0]
        selected_players_list.remove(player_to_remove)
        budget += player_to_remove['Price']
        positions[player_to_remove['Position']] += 1

        team_player_count[player_to_remove['Team']] -= 1

        budget, selected_players_list = pick_better_player(budget, player_to_remove['Position'], selected_players_list, all_players_df)

    result_df = pd.DataFrame(selected_players_list)
    position_order = {"GK": 1, "D": 2, "M": 3, "F": 4}
    result_df['PositionOrder'] = result_df['Position'].map(position_order)
    result_df = result_df.sort_values(by=['PositionOrder', 'BCV'], ascending=[True, False]).drop(columns='PositionOrder')

    total_members = len(result_df)
    total_team_value = result_df['Price'].sum()
    print(f"Total Team Members: {total_members}")
    print(f"Total Team Value: {total_team_value}")
    print(f"Money Left in Bank: {budget}")

    return result_df


def recommend_transfers_free_hit(all_players_df, current_bank_value, current_team_value, next_gameweek):
    positions = {"GK": 2, "D": 5, "M": 5, "F": 3}
    budget = current_bank_value + current_team_value
    threshold_budget = 1.0

    team_player_count = {}

    def get_cheap_players(position):
        return all_players_df[all_players_df['Position'] == position].nsmallest(1, 'Price').sort_values(by=str(next_gameweek), ascending=False)

    def add_player_to_selected(player, position):
        nonlocal budget
        nonlocal positions
        nonlocal team_player_count
        
        selected_players_list.append({
            'Player': player['Player'],
            'Position': position,
            str(next_gameweek): player[str(next_gameweek)],
            'Price': player['Price'],
            'Team': player['Team']
        })
        team = player['Team']
        team_player_count[team] = team_player_count.get(team, 0) + 1
        budget -= player['Price']
        positions[position] -= 1

    selected_players_list = []

    for pos in positions:
        cheap_players = get_cheap_players(pos)
        if not cheap_players.empty:
            top_cheap_player = cheap_players.iloc[0]
            if positions[pos] > 0 and top_cheap_player['Price'] <= budget:
                team = top_cheap_player['Team']
                if team_player_count.get(team, 0) < 3:
                    add_player_to_selected(top_cheap_player, pos)

    for pos, count in positions.items():
        position_players = all_players_df[
            (all_players_df['Position'] == pos) &
            (~all_players_df['Player'].isin([x['Player'] for x in selected_players_list]))
        ]
        position_players = position_players.sort_values(by=str(next_gameweek), ascending=False)
        for _, player in position_players.iterrows():
            if positions[pos] > 0 and player['Price'] <= budget:
                team = player['Team']
                if team_player_count.get(team, 0) < 3:
                    add_player_to_selected(player, pos)

    while budget > threshold_budget:
        sorted_selected = sorted(selected_players_list, key=lambda x: (x['Price'], x[str(next_gameweek)]))
        player_to_remove = sorted_selected[0]
        selected_players_list.remove(player_to_remove)
        budget += player_to_remove['Price']
        positions[player_to_remove['Position']] += 1

        team_player_count[player_to_remove['Team']] -= 1

        budget, selected_players_list = pick_better_player(budget, player_to_remove['Position'], selected_players_list, all_players_df)

    result_df = pd.DataFrame(selected_players_list)
    position_order = {"GK": 1, "D": 2, "M": 3, "F": 4}
    result_df['PositionOrder'] = result_df['Position'].map(position_order)
    result_df = result_df.sort_values(by=['PositionOrder', str(next_gameweek)], ascending=[True, False]).drop(columns='PositionOrder')

    total_members = len(result_df)
    total_team_value = result_df['Price'].sum()
    print(f"Total Team Members: {total_members}")
    print(f"Total Team Value: {total_team_value}")
    print(f"Money Left in Bank: {budget}")

    return result_df
