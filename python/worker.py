import sys
import io
from get_fpl_team import load_source_data, process_manager, get_top_players_by_position, get_gameweek_info_from_api
from update_source_data import fetch_new_source_data_from_gmail
from send_emails import send_email


def main():
    # Redirect stdout to a string buffer
    old_stdout = sys.stdout
    sys.stdout = buffer = io.StringIO()
    
    last_gameweek_api, next_gameweek_api, last_gameweek_api_deadline_date = get_gameweek_info_from_api()
    is_found, is_updated = fetch_new_source_data_from_gmail(next_gameweek_api, last_gameweek_api_deadline_date)
    
    df, all_players_df, matching_names_df, managers_df = load_source_data()
    next_gameweek_csv = int(df.columns[10])

    html_parts = []
    if next_gameweek_api == next_gameweek_csv:
            for index, row in managers_df.iterrows():
                if row.get('Include', False):
                    buffer = process_manager(buffer, row['ID'], row['Manager'], row.get('Wildcard', False), next_gameweek_csv, all_players_df, matching_names_df)

            buffer = get_top_players_by_position(buffer, all_players_df, next_gameweek_csv)
    else:
            print(f'Next gameweek from API ({next_gameweek_api}) does not match the next gameweek from CSV ({next_gameweek_csv}). No changes were made.')
    if not is_found:
        print(f'Email for gameweek {next_gameweek_api} was not found. No changes were made.')
    if is_updated:
        send_email('\n'.join(html_parts), next_gameweek_api)
        # Restore stdout
        sys.stdout = old_stdout
        print("Email was sent to the user with the updated results.")
    else:
        send_email(buffer.getvalue(), next_gameweek_api)
        # Restore stdout
        sys.stdout = old_stdout
        print('Source data is already up to date. No changes were made.')

if __name__ == "__main__":
    main()