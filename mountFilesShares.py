import requests
import os
import subprocess
import argparse

CREDENTIALS_FILE = "/etc/smbcredentials"

def get_token(tenant_id, client_id, client_secret, resource):
   url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/token"
   payload = {
      'grant_type': 'client_credentials',
      'client_id': client_id,
      'client_secret': client_secret,
      'resource': resource
   }

   response = requests.post(url, data=payload).json()
   return response.get('access_token')

def get_storage_accounts(token, subscription_id):
   url = f"https://management.azure.com/subscriptions/{subscription_id}/providers/Microsoft.Storage/storageAccounts?api-version=2019-06-01"
   headers = {
      'Authorization': f'Bearer {token}'
   }
   response = requests.get(url, headers=headers).json()
   return response['value']

def get_file_shares(token, storage_account, subscription_id):
   url = f"https://management.azure.com/{storage_account['id']}/fileServices/default/shares?api-version=2019-06-01"
   headers = {
      'Authorization': f'Bearer {token}'
   }
   response = requests.get(url, headers=headers).json()
   return response['value']

def mount_and_add_to_fstab(account_name, share_name, client_id, client_secret):
   credentials_path = f"{CREDENTIALS_FILE}/{share_name}.cred"
   with open(credentials_path, 'w') as f:
      f.write(f"username={client_id}\n")
      f.write(f"password={client_secret}\n")

   os.chmod(credentials_path, 0o600)

   mount_path = f"/mnt/azure-files/{share_name}"
   if not os.path.exists(mount_path):
      os.makedirs(mount_path)

   cmd_mount = f"sudo mount -t cifs //{account_name}.file.core.windows.net/{share_name} {mount_path} -o credentials={credentials_path},dir_mode=0777,file_mode=0777,serverino,nosharesock,actimeo=30"
   subprocess.run(cmd_mount, shell=True)
   print (cmd_mount)
   fstab_entry = f"//{account_name}.file.core.windows.net/{share_name} {mount_path} cifs vers=3.0,credentials={credentials_path},dir_mode=0777,file_mode=0777,serverino,nosharesock,actimeo=30\n"
   with open('/etc/fstab', 'a') as f:
      f.write(fstab_entry)

def main(args):
   token = get_token(args.tenant_id, args.client_id, args.client_secret, args.resource)
   storage_accounts = get_storage_accounts(token, args.subscription_id)

   if not os.path.exists(CREDENTIALS_FILE):
      os.makedirs(CREDENTIALS_FILE)
      os.chmod(CREDENTIALS_FILE, 0o700)

   for account in storage_accounts:
      shares = get_file_shares(token, account, args.subscription_id)
      for share in shares:
         mount_and_add_to_fstab(account['name'], share['name'], args.client_id, args.client_secret)

if __name__ == "__main__":
   parser = argparse.ArgumentParser(description="Mount all Azure Files accessible to a defined Service Principal.")
   parser.add_argument("--tenant_id", required=True, help="Azure Tenant ID")
   parser.add_argument("--client_id", required=True, help="Service Principal Client ID")
   parser.add_argument("--client_secret", required=True, help="Service Principal Client Secret")
   parser.add_argument("--subscription_id", required=True, help="Azure Subscription ID")
   parser.add_argument("--resource", default="https://management.azure.com/", help="Azure Resource Endpoint (default: https://management.azure.com/)")

   args = parser.parse_args()
   main(args)
