from google_auth_oauthlib.flow import InstalledAppFlow

flow = InstalledAppFlow.from_client_secrets_file(
    'google_oauth_credentials.json',
    scopes=['https://www.googleapis.com/auth/drive']
)
creds = flow.run_local_server(port=8080)

with open('google_oauth_token.json', 'w') as token:
    token.write(creds.to_json())

print("✅ Authorized! Token saved.")