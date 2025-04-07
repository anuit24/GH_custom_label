import os
import datetime
import argparse
import logging
import requests

INPUT_FILE_DELIMITER = "::" 

SOURCE_GITHUB_TOKEN = os.getenv('TOKEN')
#if not SOURCE_GITHUB_TOKEN:
#    raise ValueError("SOURCE_GITHUB_TOKEN environment variable not set.")
    
DEST_GITHUB_TOKEN = os.getenv('TOKEN')
#if not DEST_GITHUB_TOKEN:
#    raise ValueError("DEST_GITHUB_TOKEN environment variable not set.")

source_headers = {
    'Authorization': f'token {SOURCE_GITHUB_TOKEN}',
    'Accept': 'application/vnd.github.v3+json'
}
destination_headers = {
    'Authorization': f'token {DEST_GITHUB_TOKEN}',
    'Accept': 'application/vnd.github.v3+json'
}

# List of default GitHub labels to exclude
DEFAULT_LABELS = ['bug', 'documentation', 'duplicate', 'enhancement', 'good first issue', 'help wanted', 'invalid', 'question', 'wontfix']

# Get source & target repositiroes 
# <1 repo> DELIMITOR <2 repo>  
def load_repositories_from_file(repo_file_path):
    repos = []
    try:
        with open(repo_file_path, "r", encoding='utf-8-sig') as file:
            for line in file:
                source_repo, dest_repo = line.strip().split(INPUT_FILE_DELIMITER)
                repos.append(( source_repo, dest_repo))
    except Exception as e:
        log_and_print(f"...Error reading the file {repo_file_path}: {e}", "error")
    return repos

def log_and_print(message, log_level='info'):
    RED = '\033[31m'
    GREEN = '\033[32m'
    ORANGE = '\033[38;5;214m' 
    RESET = '\033[0m'
    # Get the current datetime with seconds
    log_datetime = datetime.datetime.now().strftime('%d%b%Y_%H%M%S')
    # Log the message to the file based on the log level
    if log_level == 'error':
        logging.error(f": {message}")
        print(f"{RED}{log_datetime}: {message} {RESET}") # Print the message to the console with the formatted datetime & color 
    elif log_level == 'success':
        logging.info(f":{message}")  
        print(f"{GREEN}{log_datetime}: {message} {RESET}") # Print the message to the console with the formatted datetime & color
    elif log_level == 'warning':
        logging.warning(f":{message}")  
        print(f"{ORANGE}{log_datetime}: {message} {RESET}") # Print the message to the console with the formatted datetime & color
    else:
        logging.info(f": {message}")
        print(f"{log_datetime}: {message}") # Print the message to the console with formatted datetime

def get_labels(repo_url):
    logging.info(f'Fetching labels from {repo_url}')
    try:
        response = requests.get(repo_url, headers=source_headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching labels from {repo_url}: {e}")
        return []

def create_or_update_label(repo_url, label):
    label_url = f"{repo_url}/{label['name']}"
    try:
        response = requests.get(label_url, headers=destination_headers)
        if response.status_code == 200:
            logging.info(f"Updating label '{label['name']}' in {repo_url}")
            response = requests.patch(label_url, headers=destination_headers, json=label)
        else:
            logging.info(f"Creating label '{label['name']}' in {repo_url}")
            response = requests.post(repo_url, headers=destination_headers, json=label)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error creating/updating label '{label['name']}' in {repo_url}: {e}")
        return None


def sync_labels(source_url, target_url):
    labels = get_labels(source_url)
    if not labels:
        logging.error(f"No labels fetched from {source_url}. Skipping sync.")
        return
    for label in labels:
        if label['name'].lower() in DEFAULT_LABELS:
            logging.info(f"Skipping default label '{label['name']}'")
            continue
        label_data = {
            'name': label['name'],
            'color': label['color'],
            'description': label.get('description', '')
        }
        result = create_or_update_label(target_url, label_data)
        if result:
            logging.info(f"Label '{label['name']}' synced successfully.")
        else:
            logging.error(f"Failed to sync label '{label['name']}'.")


def main():
    # Setup argument parser for command-line flags
    parser = argparse.ArgumentParser(description=f"...Process POST migration validation for repositories...")
    parser.add_argument('-r', '--repo_file', type=str, required=True, help="Path to the CSV file containing list of repositories")
    parser.add_argument('-o', '--output_folder', type=str, default='./output', help="Path to the folder where the migration summary will be saved (default: './output').")
    args = parser.parse_args()

    # Get the migration CSV filename from the argument
    list_repos_file_path = args.repo_file
    output_log_folder = args.output_folder

    # Get the current date and time, and format it
    current_datetime = datetime.datetime.now().strftime('%d%b%Y_%H%M')


    # Get the input path of the filename from the argument
    list_repos_file_path = args.repo_file

    # Extract the base filename without the extension
    base_filename = os.path.splitext(os.path.basename(list_repos_file_path))[0]

   
    # Log file name 
    migration_log_file = f"{output_log_folder}/LOG_{base_filename}_{current_datetime}.log"
    
    # Extract the directory part of the path
    log_directory = os.path.dirname(migration_log_file)
    
    # Check if the directory exists, and if not, create it
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)

    # Set up the logger
    logging.basicConfig(filename=f"{migration_log_file}", level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    log_and_print(f"... Input details file path = {list_repos_file_path}")

    repos_input_details = load_repositories_from_file(list_repos_file_path)
    # log_and_print(f" --- Input details  = {repos_input_details}")

    if not repos_input_details:
        log_and_print(f"...No repositories found in the file {list_repos_file_path}...", "error")
    else:
        for index, (source_repo, target_repo) in enumerate(repos_input_details, start=1):
            try:
                log_and_print(f"{index}...Syncing custom labels from '{source_repo}' to '{target_repo}' ")
                source_url = f'https://api.github.com/repos/{source_repo}/labels'
                target_url = f'https://api.github.com/repos/{target_repo}/labels'
                sync_labels(source_url, target_url)

            except Exception as e:
                log_and_print(f"{index}...Failed to sync label from '{source_repo}' to '{target_repo}' due to error: {str(e)}")
            
            

    log_and_print("********* Custom Label Migration Completed... *********")

if __name__ == '__main__':
    main()
