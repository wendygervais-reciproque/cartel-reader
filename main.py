import os
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.ttk import Progressbar
from PIL import Image, ImageTk
import csv
import pytesseract
import numpy as np
import re
import threading
import queue
import requests
from PIL import Image
import piexif
from pillow_heif import register_heif_opener
from datetime import datetime
import locale
locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')  # Pour Linux et macOS
# locale.setlocale(locale.LC_TIME, 'French_France.1252')  # Pour Windows

BASE_ID = 'appKilnwj6AD0x6rC'
TABLE_NAME = 'Oeuvres'
URL = f'https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}'


def nettoyer_nom(nom):
    if nom:
        caracteres_interdits = r'[\/:*?"<>|]'
        return re.sub(caracteres_interdits, '_', nom)
    else:
        return ""

def image_to_text(filename):
    register_heif_opener()
    img = Image.open(filename).convert('RGB')
    img = img.resize((img.width // 2, img.height // 2), Image.Resampling.LANCZOS)
    img_np = np.array(img)
    text = pytesseract.image_to_string(img_np)

    artiste, titre, annee = None, None, None
    lignes = [ligne.strip() for ligne in text.splitlines() if ligne.strip()]

    if lignes:
        artiste = lignes[0]
        if len(lignes) > 1:
            titre = lignes[1]
        for ligne in lignes:
            annee_match = re.search(r'(\b\d{4}\b)', ligne)
            if annee_match and not annee:
                annee = annee_match.group(0)

    return artiste, titre, annee

def bouton():
    print("clic")

# def ajouter_exif(image_path, title, artist, date):
#     register_heif_opener()
#     image = Image.open(image_path)

#     exif_dict = piexif.load(image.info['exif'])

#     exif_dict["0th"][piexif.ImageIFD.Artist] = artist
#     exif_dict["0th"][piexif.ImageIFD.ImageDescription] = title
#     exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = date

#     exif_bytes = piexif.dump(exif_dict)

#     image.save(image_path, exif=exif_bytes)

class ImageRenamerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Outil cartels FFO-WGE")
        
        self.image_pairs = []

        self.oeuvres = []
        self.cartels = []

        self.current_index = 0

        self.current_oeuvre = 0
        self.current_cartel = 1

        self.csv_data = []
        
        self.queue = queue.Queue()

        self.setup_ui()

    def get_airtable_credentials(self):
        self.api_key = tk.simpledialog.askstring("API Key", "Entrez votre token Airtable (jeton d’accès personnel) :", show='*')
        
        if not self.api_key:
            messagebox.showwarning("Information manquante", "Entrez votre token Airtable (jeton d’accès personnel) :")
            return False
        
        return True

    def setup_ui(self):
        self.choix_label = tk.Label(self.root, text="Choisissez un dossier contenant toutes les images")
        self.choix_label.pack(pady=10)
        self.choix = tk.Button(self.root, text="Choisir...", command=self.choose_folder)
        self.choix.pack(pady=10)

        self.lieu_expo = tk.StringVar()
        self.date_expo = tk.StringVar()

        tk.Label(self.root, text="Lieu de l'exposition :").pack()
        tk.Entry(self.root, textvariable=self.lieu_expo).pack()
        tk.Label(self.root, text="Date de visite de l'exposition :").pack()
        tk.Entry(self.root, textvariable=self.date_expo).pack()
        
        self.canvas = tk.Canvas(self.root, width=900, height=400)
        self.canvas.pack()

        self.artist_var = tk.StringVar()
        self.title_var = tk.StringVar()
        self.date_var = tk.StringVar()
        frame_principal = tk.Frame(self.root)
        frame_principal.pack(pady=10)

        frame_boutons1 = tk.Frame(frame_principal)
        frame_boutons1.pack(side=tk.LEFT, padx=100) 

        self.button_previous_oeuvre = tk.Button(frame_boutons1, text="←", command=self.previous_oeuvre)
        self.button_previous_oeuvre.pack(side=tk.LEFT, padx=5)
        #self.button_previous_oeuvre["state"] = tk.DISABLED

        self.button_next_oeuvre = tk.Button(frame_boutons1, text="→", command=self.next_oeuvre)
        self.button_next_oeuvre.pack(side=tk.LEFT, padx=5)
        #self.button_next_oeuvre["state"] = tk.DISABLED

        frame_boutons2 = tk.Frame(frame_principal)
        frame_boutons2.pack(side=tk.LEFT, padx=100)

        self.button_previous_cartel = tk.Button(frame_boutons2, text="←", command=self.previous_cartel)
        self.button_previous_cartel.pack(side=tk.LEFT, padx=5)
        #self.button_previous_cartel["state"] = tk.DISABLED

        self.button_next_cartel = tk.Button(frame_boutons2, text="→", command=self.next_cartel)
        self.button_next_cartel.pack(side=tk.LEFT, padx=5)
        #self.button_next_cartel["state"] = tk.DISABLED

        tk.Label(self.root, text="Artiste :").pack()
        tk.Entry(self.root, textvariable=self.artist_var).pack()

        tk.Label(self.root, text="Titre :").pack()
        tk.Entry(self.root, textvariable=self.title_var).pack()
        
        tk.Label(self.root, text="Date :").pack()
        tk.Entry(self.root, textvariable=self.date_var).pack()

        self.progress_bar = Progressbar(self.root, length=500, mode='determinate',)
        self.progress_bar.pack(pady=10)
        self.progress_bar["value"] = 0 
        self.progress_bar.pack_forget()
        
        self.validation = tk.Button(self.root, text="Enregistrer et passer à l'oeuvre suivante", command=self.save_and_next)
        self.validation.pack(pady=30)
        self.validation.config(state=tk.DISABLED)
        tk.Label(self.root, text="En cliquant sur enregistrer, l'image sera renommée et les informations de l'oeuvre ajoutées à la BDD. \n Une fois toutes les images traitées, une fenêtre vous proposera d'enregistrer toutes les infos au format CSV, puis de pousser sur Airtable.").pack(pady=30)

    def previous_oeuvre(self):
        if self.current_oeuvre > 0:
            self.current_oeuvre -= 1
            self.show_images()

    def next_oeuvre(self):
        if self.current_oeuvre < len(self.oeuvres) - 1:
            self.current_oeuvre += 1
            self.show_images()

    def previous_cartel(self):
        if self.current_cartel > 0:
            self.current_cartel -= 1
            self.show_images()

    def next_cartel(self):
        if self.current_cartel < len(self.cartels) - 1:
            self.current_cartel += 1
            self.show_images()

    
    def choose_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.find_images(folder_path)
            print(self.image_pairs)
            if self.oeuvres and self.cartels:
                self.show_images()

                self.choix_label.pack_forget()
                self.choix.pack_forget()
                self.validation.config(state=tk.NORMAL)

                self.lieu_expo.set(folder_path.split("/")[-1])   

                mod_time = os.path.getmtime(folder_path)
                mod_time_obj = datetime.fromtimestamp(mod_time)
                mod_date = mod_time_obj.strftime('%B %Y')
                self.date_expo.set(mod_date)
                
            else:
                messagebox.showwarning("Avertissement", "Aucune paire d'images trouvée.")

    def find_image_pairs(self, folder_path):
        images = sorted([f for f in os.listdir(folder_path) if f.lower().endswith(('png', 'jpg', 'jpeg', 'heic'))])
        pairs = [(images[i], images[i + 1]) for i in range(0, len(images) - 1, 2)]
        return [(os.path.join(folder_path, p[0]), os.path.join(folder_path, p[1])) for p in pairs]

    def find_images(self, folder_path):
        images = sorted([f for f in os.listdir(folder_path) if f.lower().endswith(('png', 'jpg', 'jpeg', 'heic'))])
        image_paths = [os.path.join(folder_path, img) for img in images]
        self.oeuvres = image_paths.copy()
        self.cartels = image_paths.copy()



    def show_images(self):
        art_img = None
        label_img = None

        if self.current_oeuvre < len(self.oeuvres):
            art_img = self.load_image(self.oeuvres[self.current_oeuvre])

        if self.current_cartel < len(self.cartels):
            label_img = self.load_image(self.cartels[self.current_cartel])
            self.process_image(self.cartels[self.current_cartel])

        self.canvas.delete("all")

        if art_img:
            self.canvas.create_image(200, 250, anchor=tk.CENTER, image=art_img)
            self.art_img = art_img

        if label_img:
            self.canvas.create_image(750, 250, anchor=tk.CENTER, image=label_img)
            self.label_img = label_img



    def load_image(self, path):
        register_heif_opener()
        img = Image.open(path).resize((350,400))
        return ImageTk.PhotoImage(img)


    def process_image(self, label_path):
        artiste, titre, annee = image_to_text(label_path)
        self.queue.put((artiste, titre, annee))
        self.root.after(100, self.update_ui)


    def update_ui(self):
        if not self.queue.empty():
            artiste, titre, annee = self.queue.get()

            self.artist_var.set(artiste if artiste else "")
            self.title_var.set(titre if titre else "")
            self.date_var.set(annee if annee else "")

            self.update_progress_bar(100)


    def update_progress_bar(self, value):
        """Met à jour la barre de progression et masque/affiche en fonction de la valeur."""
        if value == 0 or value == 100:
            self.progress_bar.pack_forget()  # Masquer la barre de progression si à 0 ou 100
        else:
            self.progress_bar.pack(pady=10)  # Afficher la barre de progression
        self.progress_bar["value"] = value

    def save_and_next(self):
        if self.current_oeuvre >= len(self.oeuvres):
            self.finish_process()
            return

        art_path = self.oeuvres[self.current_oeuvre]
        artist = self.artist_var.get().strip()
        title = self.title_var.get().strip()
        date = self.date_var.get().strip()
        lieu = self.lieu_expo.get().strip()
        expodate = self.date_expo.get().strip()

        new_name = f"{os.path.basename(art_path).split('.')[0]}_{nettoyer_nom(title)}_{nettoyer_nom(artist)}_{nettoyer_nom(date)}.jpg"
        new_path = os.path.join(os.path.dirname(art_path), new_name)

        # ✅ Correction ici
        os.rename(art_path, new_path)
        self.oeuvres[self.current_oeuvre] = new_path  # Mettre à jour la référence au nouveau nom

        self.csv_data.append([title, artist, date, new_name, lieu, expodate])
        # ajouter_exif(new_path, title, artist, date)

        self.current_oeuvre += 2
        self.current_cartel += 2

        if self.current_oeuvre < len(self.oeuvres):
            self.show_images()
        else:
            self.finish_process()




    def finish_process(self):
        save_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if save_path:
            with open(save_path, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(["Titre", "Artiste", "Date", "Nom fichier", "Lieu expo", "Date expo"])
                writer.writerows(self.csv_data)
            
            messagebox.showinfo("Terminé", "CSV enregistré avec succès !")

        if self.get_airtable_credentials():
            HEADERS = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            for row in self.csv_data:
                record = {
                    "fields": {
                        "Titre": row[0],
                        "Artiste": row[1],
                        "Date": row[2],
                        "Nom fichier": row[3],
                        "Lieu expo": row[4],
                        "Date expo": row[5]
                    }
                }
                response = requests.post(URL, headers=HEADERS, json=record)
                
                if response.status_code != 200:
                    messagebox.showerror("Erreur", f"Échec de l'envoi à Airtable : {response.status_code}\n{response.json()}")
                    return
            
            messagebox.showinfo("Terminé", "Données envoyées à Airtable avec succès !")
        
        
        self.validation.config(state=tk.DISABLED)
        
        self.root.quit()


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageRenamerApp(root)
    root.mainloop()

