import json
import spotipy

def Create_Spotify(client_id, client_secret, redirect_uri):
    auth_manager = spotipy.SpotifyOAuth(
        scope=['playlist-modify-public','user-read-playback-state','user-modify-playback-state'],
        redirect_uri=redirect_uri,
        client_id=client_id,
        client_secret=client_secret)

    spotify = spotipy.Spotify(auth_manager=auth_manager)

    return auth_manager, spotify

class SpotifyManager:
    client_id = str
    client_secret = str
    redirect_uri = str
    auth_manager = object
    spotify_connection = object
    spotify_device_id = str

    def __init__(self):
        with open("dj_config.json", "r") as config_file:
            config_json = json.loads(config_file.read())
            spotify_config = config_json.get("spotify")
            self.client_id = spotify_config.get("client_id")
            self.client_secret = spotify_config.get("client_secret")
            self.redirect_uri = spotify_config.get("redirect_uri")
            self.auth_manager,self.spotify_connection = Create_Spotify(self.client_id, self.client_secret, self.redirect_uri)
            self.spotify_device_id = self.GetAndSetSpotifyDevice()
            
    def Refresh_Spotify(self, authManager, spotify):
        token_info = authManager.cache_handler.get_cached_token()
        if authManager.is_token_expired(token_info):
            authManager, spotify = Create_Spotify(self.client_id, self.client_secret, self.redirect_uri)
        return authManager, spotify

    def GetAndSetSpotifyDevice(self):
        user = self.spotify_connection.current_user() 
        devices = json.loads(json.dumps(self.spotify_connection.devices()))
        devices_json = devices.get("devices", None)
        if len(devices_json) > 1:
            print(f"Hello {user['display_name']}!  Your Spotify Devices:")
            for n in range(0,len(devices_json)):
                device_name = devices_json[n].get("name", None)
                device_type = devices_json[n].get("type", None)
                print(f"{n+1} = {device_name} - {device_type}")

            device_choice = int(input("Enter which device you want to send tracks to:")) - 1
            device_id = devices_json[device_choice]['id']
        else:
            print(f"Only one of your recently active devices was found.  Using it.  Info: {devices_json[0]['name']} ")
            device_id = devices_json[0]['id']

        return device_id
