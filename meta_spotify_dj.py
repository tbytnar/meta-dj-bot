import dxcam
import pytesseract
import cv2 
import json
import time
import spotify_utilities as spotify
import logging
from datetime import datetime

logging.basicConfig(filename="meta_spotify_dj.log", encoding="utf-8", level=logging.DEBUG)
logging.info(f"\n\nMeta Spotify DJ Began Running @ {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

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
# NOTE: Tesseract (REQUIRED) for Windows can be downloaded here: https://github.com/UB-Mannheim/tesseract/wiki
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# DxCamera Variables
camera = dxcam.create(output_color="GRAY")

requests_buffer = []
spotify_manager = spotify.SpotifyManager()
spotify_device_id = spotify.GetAndSetSpotifyDevice(spotify_manager.spotify_connection)

print("DJ Bot is Running! Control-C to exit.")
while True:
    spotify_manager.auth_manager, spotify_manager.spotify_connection = spotify_manager.Refresh_Spotify(spotify_manager.auth_manager, spotify_manager.spotify_connection)

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
                spotify.add_to_queue(song, spotify.spotify_device_id)
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
