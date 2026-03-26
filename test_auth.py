import pydata_google_auth

print("Starting auth...")
creds = pydata_google_auth.get_user_credentials(
    ["https://www.googleapis.com/auth/bigquery"],
    auth_local_webserver=False,
)
print("Auth done!")
