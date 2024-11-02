#!/usr/bin/env python
import os
import sys
import keyring
import getpass
import argparse
import secrets
import string

APP_ENV = os.getenv("APP_ENV","staging")

SERVICE_NAME = "AnsibleVault"
ACCOUNT_NAME = f"ansible_vault_password_supercortex_frontend_{APP_ENV}"

def get_vault_password():
    password = keyring.get_password(SERVICE_NAME, ACCOUNT_NAME)
    return password

def set_vault_password(generate=False):
    if generate:
        password = ''.join(secrets.choice(string.ascii_letters + string.digits + string.punctuation) for _ in range(32))
        print("Generated a new secure password.")
    else:
        password = getpass.getpass("Enter New Ansible Vault password: ")
    keyring.set_password(SERVICE_NAME, ACCOUNT_NAME, password)
    return password

def clear_vault_password():
    keyring.delete_password(SERVICE_NAME, ACCOUNT_NAME)
    print("Ansible Vault password has been cleared.")


def find_git_repo_info():
    import os
    from configparser import ConfigParser

    current_dir = os.getcwd()
    while current_dir != '/':
        git_config_path = os.path.join(current_dir, '.git', 'config')
        if os.path.exists(git_config_path):
            config = ConfigParser()
            config.read(git_config_path)
            url = config.get('remote "origin"', 'url')
            if url.startswith(("https://", "http://", "git@")):
                if url.startswith(("https://", "http://")):
                    url_parts = url.split('/')
                    owner = url_parts[-2]
                    repo = url_parts[-1].replace('.git', '')
                elif url.startswith("git@"):
                    url_parts = url.split(':')
                    owner_repo = url_parts[-1].split('/')
                    owner = owner_repo[0]
                    repo = owner_repo[1].replace('.git', '')
                return owner, repo
        current_dir = os.path.dirname(current_dir)
    raise FileNotFoundError("No .git/config found in the current directory or any parent directories.")

def save_to_drone(secret_name, secret_data):
    import requests
    drone_url = os.getenv("DRONE_SERVER")
    drone_token = os.getenv("DRONE_TOKEN")
    
    try:
        owner, repo = find_git_repo_info()
        response = requests.post(f"{drone_url}/api/repos/{owner}/{repo}/secrets", 
                                 headers={"Authorization": f"Bearer {drone_token}"}, 
                                 json={"name": secret_name, "data": secret_data})
        response.raise_for_status()
        print(f"Secret '{secret_name}' successfully saved to Drone.")
    except (requests.exceptions.RequestException, FileNotFoundError) as e:
        print(f"Failed to save secret to Drone: {e}")

def list_ssh_keys():
    import os
    ssh_dir = os.path.expanduser("~/.ssh")
    keys = [
        f for f in os.listdir(ssh_dir)
        if os.path.isfile(os.path.join(ssh_dir, f)) 
        and not f.endswith('.pub') 
        and f != 'known_hosts'
    ]
    return keys

def select_ssh_key():
    keys = list_ssh_keys()
    if not keys:
        print("No SSH keys found in ~/.ssh directory.")
        return None

    print("Select an SSH key by number:")
    for i, key in enumerate(keys):
        print(f"{i}: {key}")

    while True:
        try:
            choice = int(input("Enter the number of the SSH key: "))
            if 0 <= choice < len(keys):
                return keys[choice]
            else:
                print("Invalid choice. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")

def save_ssh_key_to_drone():
    ssh_key = select_ssh_key()
    if ssh_key:
        ssh_dir = os.path.expanduser("~/.ssh")
        with open(os.path.join(ssh_dir, ssh_key), 'r') as key_file:
            key_data = key_file.read()
        secret_name = f"ssh_key_{APP_ENV}"
        save_to_drone(secret_name, key_data)

    

if __name__ == "__main__":
    if len(sys.argv) == 1:
        password = get_vault_password()
        if not password:
            sys.stderr.write("No Ansible Vault password found. Please set or generate one.")
            sys.exit(1)
        print(password)
    else:
        parser = argparse.ArgumentParser(description="Manage Ansible Vault password")
        parser.add_argument("action", choices=["set", "generate", "clear", "save_ssh"], help="Action to perform")
        args = parser.parse_args()

        if args.action == "set":
            set_vault_password()
            print("Ansible Vault password has been set.")
        elif args.action == "generate":
            stored_password = keyring.get_password(SERVICE_NAME, ACCOUNT_NAME)
            if stored_password:
                print("Ansible Vault password already exists. Use set to set it, or clear to clear it.")
            else:
                set_vault_password(generate=True)
                print("Ansible Vault password has been set.")
        elif args.action == "clear":
            clear_vault_password()
        elif args.action == "save":
            secret_name = f"ansible_vault_password_{APP_ENV}"   
            save_to_drone(secret_name, get_vault_password())
        elif args.action == "save_ssh":
            save_ssh_key_to_drone()
