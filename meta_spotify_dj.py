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
    

def CaptureScreen(camera):
    # img = np.array(Image.open("HW_DJ_Request_Test.png"))
    left, top = (1920 - 640) // 2, (1080 - 640) // 2
    right, bottom = left + 640, top + 640
    region = (left, top, right, bottom)
    img = camera.grab(region=region)
    # cv2.imshow("Shapes", img)
    # time.sleep(1)
    # cv2.destroyAllWindows()
    return img

def DetectChatWindows(img):
    # grayscale
    gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)

    # threshold
    ret,thresh = cv2.threshold(gray,65,255,0)
    
    # Fill rectangular contours
    cnts = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = cnts[0] if len(cnts) == 2 else cnts[1]
    for c in cnts:
        cv2.drawContours(thresh, [c], -1, (255,255,255), -1)

    # Morph open
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9,9))
    opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=4)

    # Draw rectangles, the 'area_treshold' value was determined empirically
    cnts = cv2.findContours(opening, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = cnts[0] if len(cnts) == 2 else cnts[1]
    area_min = 6000
    area_max = 25000
    chats = []
    for c in cnts:
        epsilon = 0.05*cv2.arcLength(c,True)
        approx = cv2.approxPolyDP(c,epsilon,True)
        if len(approx) == 4:
            if cv2.contourArea(c) > area_min and cv2.contourArea(c) < area_max:
                chats.append(cv2.boundingRect(c))
    return chats


def DetectDJRequests(img, chats):
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
    return current_requests


# Tesseract Variables
# NOTE: Tesseract (REQUIRED) for Windows can be downloaded here: https://github.com/UB-Mannheim/tesseract/wiki
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# DxCamera Variables
dx_camera = dxcam.create()

requests_buffer = []
spotify_manager = spotify.SpotifyManager()

running = True
while running:
    print("1 - Set Spotify Device")
    print("2 - Run DJ Bot")
    print("3 - Exit")
    menu_choice = input("What do you want to do?")
    
    if menu_choice == "1":
        print("Welcome to the spotify device section!")
        spotify_manager.GetAndSetSpotifyDevice()
    if menu_choice == "2":
        print("The DJ Bot is running.  Press Control-C to exit from here.")
        while running:
            spotify_manager.auth_manager, spotify_manager.spotify_connection = spotify_manager.Refresh_Spotify(spotify_manager.auth_manager, spotify_manager.spotify_connection)
            screen_image = CaptureScreen(dx_camera)
            if screen_image is not None:
                current_chats = DetectChatWindows(screen_image)
                current_requests = DetectDJRequests(screen_image, current_chats)
                for request in current_requests:
                    buffer_search = next((x for x in requests_buffer if x.requestor == request.requestor and x.track == request.track), None)
                    if buffer_search is None:
                        logging.info(f"{request.requestor} requested: {request.track}")
                        print(f"{request.requestor} requested: {request.track}")
                        results = spotify_manager.spotify_connection.search(request.track, 1, 0, "track") 
                        songs_dict = results['tracks'] 
                        song_items = songs_dict['items'] 
                        song = song_items[0]['external_urls']['spotify'] 
                        spotify_manager.spotify_connection.add_to_queue(song, spotify_manager.spotify_device_id)
                        requests_buffer.append(request)

                for request in requests_buffer:
                    current_search = next((x for x in current_requests if x.requestor == request.requestor and x.track == request.track), None)
                    if current_search is None: 
                        requests_buffer.remove(request)
                    time.sleep(5)
            else:
                time.sleep(5)
                print("Waiting for screen to change...")
    if menu_choice == "3":
        running = False
