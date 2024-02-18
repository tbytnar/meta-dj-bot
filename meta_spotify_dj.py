import dxcam
import pytesseract
import cv2 
import sys
import time
import spotify_utilities as spotify
import logging
from datetime import datetime
from region_picker import RegionPicker
from PyQt5 import QtWidgets, QtCore, QtGui

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
    

def CaptureScreen(camera, region):
    # img = np.array(Image.open("HW_DJ_Request_Test.png"))

    img = camera.grab(region=region)
    # cv2.imshow("Shapes", img)
    # time.sleep(1)
    # cv2.destroyAllWindows()
    return img

def DetectChatWindows(img):
    ret,thresh = cv2.threshold(img,50,255,0)
    contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

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
                    chats.append(cv2.boundingRect(cnt))
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
dx_camera = dxcam.create(output_color="GRAY")

requests_buffer = []
spotify_manager = spotify.SpotifyManager()

left, top = (1920 - 640) // 2, (1080 - 640) // 2
right, bottom = left + 640, top + 640
capture_region = (left, top, right, bottom)

running = True
while running:
    print("1 - Set Spotify Device")
    print("2 - Set Capture Region")
    print("3 - Run DJ Bot")
    print("4 - Exit")
    menu_choice = input("What do you want to do?")
    if menu_choice == "1":
        print("Welcome to the spotify device section!")
        spotify_manager.GetAndSetSpotifyDevice()
    if menu_choice == "2":
        app = QtWidgets.QApplication(sys.argv)
        window = RegionPicker()
        window.show()
        capture_region = window.coords
        app.aboutToQuit.connect(app.deleteLater)
        app.exec_()
    if menu_choice == "3":
        print("The DJ Bot is running.  Press Control-C to exit from here.")
        while running:
            spotify_manager.auth_manager, spotify_manager.spotify_connection = spotify_manager.Refresh_Spotify(spotify_manager.auth_manager, spotify_manager.spotify_connection)
            screen_image = CaptureScreen(dx_camera, capture_region)
            if screen_image is not None:
                current_chats = DetectChatWindows(screen_image)
                current_requests = DetectDJRequests(screen_image, current_chats)
                for request in current_requests:
                    buffer_search = next((x for x in requests_buffer if x.requestor == request.requestor and x.track == request.track), None)
                    if buffer_search is None:
                        logging.warning(f"{request.requestor} requested: {request.track}")
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
    if menu_choice == "4":
        running = False
