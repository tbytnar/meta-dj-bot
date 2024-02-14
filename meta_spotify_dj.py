import dxcam
import pytesseract
import cv2 
import json
import spotipy
import time
import os

class Request:
    requestor = str
    track = str

    def __init__(self, requestor, track):
        self.requestor = requestor
        self.track = track

    def __str__(self) -> str:
        return f"Request Object: Requestor = {self.requestor}, Track = {self.track}"
    

def JsonPrint(json_string):
    print(json.dumps(json_string, indent=4))

# Tesseract Variables
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# DxCamera Variables
camera = dxcam.create(output_color="GRAY")

# Spotify API Variables
spotify_client_id = "64a903b77e534d4aa4f91dfbc1d97311"
spotify_client_secret = "9cf8ce799a8b4ad9b0e52bd8cd206cee"
spotify_redirect_uri = "http://google.com/callback/"

def PreRunValidation():
    if spotify_client_id == "CHANGEME":
        raise BaseException("You need to set the client_id to your application's Client ID.  (See: https://developer.spotify.com/documentation/web-api/tutorials/getting-started#create-an-app  for more details.) ")

    if spotify_client_secret == "CHANGEME":
        raise BaseException("You need to set the client_id to your application's Client ID.  (See: https://developer.spotify.com/documentation/web-api/tutorials/getting-started#create-an-app  for more details.) ")

    if spotify_redirect_uri != "http://google.com/callback/":
        print("Despite what the Spotify Developer guide tells you, I highly recommend you set your redirect_uri to http://google.com/callback/ otherwise you will get errors!")


def GetSpotifyObject(client_id, client_secret, redirect_uri):
    print("Your browser will open and ask you to allow permissions for your custom app to access your account.  Upon clicking 'Allow', copy the URL that you are directed to.  Then paste it into the terminal window when prompted for it.")
    oauth_object = spotipy.SpotifyOAuth(client_id, client_secret, redirect_uri, scope=['playlist-modify-public','user-read-playback-state','user-modify-playback-state']) 
    token = oauth_object.get_access_token(as_dict=False)
    return spotipy.Spotify(auth=token) 
    

def GetAndSetSpotifyDevice(spotify_object):
    user = spotify_object.current_user() 
    devices = json.loads(json.dumps(spotify_object.devices()))
    devices_json = devices.get("devices", None)
    if len(devices_json) > 1:
        print(f"Hello {user['display_name']}!  Your Spotify Devices:")
        for n in range(0,len(devices_json)):
            device_name = devices_json[n].get("name", None)
            device_type = devices_json[n].get("type", None)
            print(f"{n+1} = {device_name} - {device_type}")

        device_choice = int(input("Enter which device you want to send tracks to:")) - 1
        device_id = devices_json[device_choice]
    else:
        print(f"Only one of your recently active devices was found.  Using it.  Info: {devices_json[0]['name']} ")
        device_id = devices_json[0]['id']

    return device_id


PreRunValidation()
spotify = GetSpotifyObject(spotify_client_id, spotify_client_secret, spotify_redirect_uri)
spotify_device_id = GetAndSetSpotifyDevice(spotify)


requests_buffer = []

while True:
    os.system('cls')
    print("DJ Bot is Running!")
    # img = np.array(Image.open("HW_DJ_Request_Test.png"))
    left, top = (1920 - 640) // 2, (1080 - 640) // 2
    right, bottom = left + 640, top + 640
    region = (left, top, right, bottom)
    img = camera.grab(region=region)
    
    #cv2.imshow("Shapes", img)
    #time.sleep(1)
    #cv2.destroyAllWindows()
    if img is not None:
        ret,thresh = cv2.threshold(img,50,255,0)
        contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        # print("Number of contours detected:", len(contours))
        chats = []
        for cnt in contours:
            x1,y1 = cnt[0][0]
            approx = cv2.approxPolyDP(cnt, 0.01*cv2.arcLength(cnt, True), True)
            if len(approx) == 4:
                x, y, w, h = cv2.boundingRect(cnt)
                ratio = float(w)/h
                if ratio != 1:
                    if w > 10:
                        cv2.putText(img, 'Rectangle', (x1, y1), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                        img = cv2.drawContours(img, [cnt], -1, (0,255,0), 3)
                        #print(x, y, w, h)
                        chats.append(cv2.boundingRect(cnt))

        current_requests = []
        for chat in chats:
            x, y, w, h = chat
            cropped_img = img[y:y+h, x:x+w]
            imgResized = cv2.resize(cropped_img, ( w*3, h*3))
            #inverted_img = np.invert(cropped_img)

            config = '--oem 3 --psm 11'
            txt = pytesseract.image_to_string(imgResized, config = config, lang='eng')

            if "djrequest:" in txt:
                delimited_txt = txt.replace("\n\n", "|").replace("djrequest:","")
                requestor = delimited_txt.split("|")[0]
                request_data = delimited_txt.split("|")[1:]
                requested_track = ""
                for segment in request_data:
                    requested_track += segment.replace("\n","") + " "

                new_request = Request(requestor, requested_track)

                # cv2.imshow("Shapes", imgResized)
                # cv2.waitKey(0)
                # cv2.destroyAllWindows()

                current_requests.append(new_request)

        for request in current_requests:
            buffer_search = next((x for x in requests_buffer if x.requestor == request.requestor and x.track == request.track), None)
            if buffer_search is None:
                print(f"{request.requestor} requested: {request.track}")
                results = spotify.search(request.track, 1, 0, "track") 
                songs_dict = results['tracks'] 
                song_items = songs_dict['items'] 
                song = song_items[0]['external_urls']['spotify'] 
                spotify.add_to_queue(song, spotify_device_id)
                print(f"Adding request {request}")
                requests_buffer.append(request)

        for request in requests_buffer:
            current_search = next((x for x in current_requests if x.requestor == request.requestor and x.track == request.track), None)
            if current_search is None: 
                print(f"Removing request {request}")
                requests_buffer.remove(request)
            print("Requests in buffer:")
            print(request)
    else:
        print("Waiting for screen to change...")

    time.sleep(1)
