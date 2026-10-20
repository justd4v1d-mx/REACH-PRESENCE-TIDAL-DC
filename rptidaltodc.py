import time
import threading
import tkinter as tk
from pypresence import Presence
import pystray
from PIL import Image, ImageDraw, ImageTk
import os
import requests
import io


# CONFIG (PUT ID AND KEY HERE)

DISCORD_CLIENT_ID = 'PUT YOUR APP ID' #get app id in https://support-dev.discord.com/hc/en-us/articles/360028717192-Where-can-I-find-my-Application-Team-Server-ID
LASTFM_USERNAME = 'PUT LASTFM USER' #username https://lastfm.com
LASTFM_API_KEY = 'PUT LASTFMAPIKEY' #get lastfm api key in https://www.last.fm/api/authentication      


running = True

# state ui
ui_status = {
    "discord": "Waiting for Music",
    "song": "Waiting for Music...",
    "artist": "...",
    "album": "...",
    "artwork": "" 
}

window_open = False

def create_icon_image():
    width = 64; height = 64
    image = Image.new('RGB', (width, height), color=(0, 0, 0))
    dc = ImageDraw.Draw(image)
    dc.rectangle([20, 10, 44, 20], fill=(255, 255, 255))
    dc.rectangle([28, 20, 36, 54], fill=(255, 255, 255))
    return image

default_icon_img = create_icon_image()

# LASTFM API CALL
def get_now_playing():
    url = f"http://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&user={LASTFM_USERNAME}&api_key={LASTFM_API_KEY}&format=json&limit=1"
    
    try:
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            data = response.json()
            tracks = data.get("recenttracks", {}).get("track", [])
            
            if tracks:
                track = tracks[0]
                if track.get("@attr", {}).get("nowplaying") == "true":
                    
                    images = track.get("image", [])
                    artwork_url = ""
                    for img in images:
                        if img.get("size") == "extralarge" and img.get("#text"):
                            artwork_url = img.get("#text")
                            
                    return {
                        "status": "playing",
                        "song": track.get("name", "Desconocido"),
                        "artist": track.get("artist", {}).get("#text", "Desconocido"),
                        "album": track.get("album", {}).get("#text", "Álbum Desconocido"),
                        "artwork": artwork_url
                    }
    except Exception:
        pass 
        
    return {"status": "paused"}

def show_status_window(icon, item):
    global window_open
    if window_open: return
    window_open = True

    def on_force_close():
        global window_open
        window_open = False
        try: window.destroy()
        except: pass

    current_image_url = ""
    img_reference = None 

    def update_labels():
        nonlocal current_image_url, img_reference
        if not window_open: return
        try:
            lbl_discord.config(text=f"Discord: {ui_status['discord']}", fg="#00ff00" if "Conectado" in ui_status['discord'] else "#ff0000")
            lbl_song.config(text=f"Canción: {ui_status['song']}")
            lbl_artist.config(text=f"Artista: {ui_status['artist']}")
            lbl_album.config(text=f"Álbum: {ui_status['album']}")
            
            new_url = ui_status['artwork']
            if new_url != current_image_url:
                current_image_url = new_url
                if new_url.startswith("http"):
                    try:
                        resp = requests.get(new_url, timeout=2)
                        img_data = Image.open(io.BytesIO(resp.content))
                        
                        img_data = img_data.resize((150, 150))
                        
                        img_reference = ImageTk.PhotoImage(img_data)
                        lbl_image.config(image=img_reference, text="")
                    except:
                        lbl_image.config(image='', text="Sin Portada")
                else:
                    lbl_image.config(image='', text="Tidal Logo")
            
            window.after(1000, update_labels)
        except:
            on_force_close()

    try:
        window = tk.Tk()
        window.title("Estado Tidal RPC")
        
        window.geometry("500x220") 
        
        window.resizable(False, False)
        window.configure(bg="#121212")
        window.protocol("WM_DELETE_WINDOW", on_force_close)
        window.eval('tk::PlaceWindow . center')

        style_lbl = {"bg": "#121212", "fg": "white", "font": ("Segoe UI", 9)}
        style_header = {"bg": "#121212", "fg": "cyan", "font": ("Segoe UI", 11, "bold")}

        tk.Label(window, text="Monitor Tidal RPC (Last.fm)", **style_header).pack(pady=5)
        tk.Frame(window, height=1, bg="#333333").pack(fill="x", padx=10, pady=5)

        main_frame = tk.Frame(window, bg="#121212")
        main_frame.pack(fill="both", expand=True, padx=10, pady=5)

        left_frame = tk.Frame(main_frame, bg="#121212")
        left_frame.pack(side="left", fill="both", expand=True)

        right_frame = tk.Frame(main_frame, bg="#121212")
        right_frame.pack(side="right", padx=15) 

        lbl_discord = tk.Label(left_frame, text="Discord: ...", **style_lbl); lbl_discord.pack(anchor="w")
        lbl_song = tk.Label(left_frame, text="Canción: ...", **style_lbl); lbl_song.pack(anchor="w", pady=(5,0))
        lbl_artist = tk.Label(left_frame, text="Artista: ...", **style_lbl); lbl_artist.pack(anchor="w")
        lbl_album = tk.Label(left_frame, text="Álbum: ...", **style_lbl); lbl_album.pack(anchor="w")

        lbl_image = tk.Label(right_frame, bg="#121212", fg="#aaaaaa", text="Cargando portada...")
        lbl_image.pack()

        update_labels()
        window.mainloop()
    except:
        window_open = False

def on_quit(icon, item):
    global running
    running = False 
    icon.stop()
    os._exit(0) 

def run_icon():
    menu = pystray.Menu(
        pystray.MenuItem('Ver Estado', lambda icon, item: threading.Thread(target=show_status_window, args=(icon, item), daemon=True).start()),
        pystray.MenuItem('Salir', on_quit)
    )
    icon = pystray.Icon("TidalRPC", default_icon_img, "Tidal RPC", menu)
    icon.run()

def main():
    global running
    print("INICIANDO TIDAL REACH PRESENCE...")
    
    ui_status["discord"] = "Conectando..."

    icon_thread = threading.Thread(target=run_icon)
    icon_thread.daemon = True 
    icon_thread.start()

    try:
        RPC = Presence(DISCORD_CLIENT_ID)
        RPC.connect()
        print(" Discord Online.")
        ui_status["discord"] = "Online "
    except Exception as e:
        print(f" Error Discord: {e}")
        ui_status["discord"] = f"Error: {e}"
        return

    start_time = None
    last_track_id = ""

    while running:
        info = get_now_playing()

        if info['status'] == 'playing':
            track_signature = f"{info['song']}-{info['artist']}"
            
            ui_status["song"] = info['song']
            ui_status["artist"] = info['artist']
            ui_status["album"] = info['album']
            ui_status["artwork"] = info['artwork'] if info['artwork'] else "tidal_logo"

            if track_signature != last_track_id:
                start_time = time.time()
                last_track_id = track_signature
                print(f"\U0001F3B5 {info['song']} | \U0001F465 {info['artist']}")

            s_state = f"{info['artist']} | \U0001F4BF {info['album']}"
            if len(s_state) > 120:
                s_state = s_state[:117] + "..."
            
            try:
                RPC.update(
                    details=info['song'],
                    state=s_state,               
                    large_image=ui_status["artwork"],   
                    large_text="Tidal",          
                    start=start_time
                )
            except:
                pass

        else: 
            ui_status["song"] = "Esperando música..."
            ui_status["artist"] = "..."
            ui_status["album"] = "..."
            ui_status["artwork"] = ""
            last_track_id = ""
            RPC.clear()

        time.sleep(5)
    
    RPC.close()

if __name__ == "__main__":
    main()
