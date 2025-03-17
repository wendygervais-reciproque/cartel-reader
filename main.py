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

BASE_ID = 'appKilnwj6AD0x6rC'
TABLE_NAME = 'Oeuvres'
URL = f'https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}'


def nettoyer_nom(nom):
    return re.sub(r'[^a-zA-Z0-9_]', '_', nom)

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

def ajouter_exif(image_path, title, artist, date):
    # Ouvrir l'image
    register_heif_opener()
    image = Image.open(image_path)

    # Récupérer les métadonnées EXIF existantes
    exif_dict = piexif.load(image.info['exif'])

    # Ajouter ou modifier les champs EXIF spécifiques
    exif_dict["0th"][piexif.ImageIFD.Artist] = artist
    exif_dict["0th"][piexif.ImageIFD.ImageDescription] = title
    exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = date

    # Convertir les métadonnées EXIF modifiées en bytes
    exif_bytes = piexif.dump(exif_dict)

    # Enregistrer l'image avec les nouvelles métadonnées EXIF
    image.save(image_path, exif=exif_bytes)

class ImageRenamerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Renamer")
        
        self.image_pairs = []
        self.current_index = 0
        self.csv_data = []
        
        self.queue = queue.Queue()

        self.setup_ui()

    def get_airtable_credentials(self):
        self.api_key = tk.simpledialog.askstring("API Key", "Entrez votre clé API Airtable :", show='*')
        
        if not self.api_key:
            messagebox.showwarning("Information manquante", "Entrez votre clé API Airtable")
            return False
        
        return True

    def setup_ui(self):
        self.choix_label = tk.Label(self.root, text="Choisissez un dossier contenant les images dans l'ordre suivant : \n oeuvre1-cartel1-oeuvre2-cartel2...oeuvreN-cartelN.")
        self.choix_label.pack(pady=10)
        self.choix = tk.Button(self.root, text="Choisir un dossier contenant toutes les images", command=self.choose_folder)
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

        # Première paire de boutons
        frame_boutons1 = tk.Frame(frame_principal)
        frame_boutons1.pack(side=tk.LEFT, padx=100)  # Espacement entre les paires

        tk.Button(frame_boutons1, text="←", command=self.previous_oeuvre).pack(side=tk.LEFT, padx=5)
        tk.Button(frame_boutons1, text="→", command=self.next_oeuvre).pack(side=tk.LEFT, padx=5)

        # Deuxième paire de boutons
        frame_boutons2 = tk.Frame(frame_principal)
        frame_boutons2.pack(side=tk.LEFT, padx=100)

        tk.Button(frame_boutons2, text="←", command=self.previous_cartel).pack(side=tk.LEFT, padx=5)
        tk.Button(frame_boutons2, text="→", command=self.next_cartel).pack(side=tk.LEFT, padx=5)


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
        tk.Label(self.root, text="En cliquant sur enregistrer, l'image sera renommée et les informations de l'oeuvre ajoutées à la BDD. \n Une fois toutes les images traitées, une fenêtre vous proposera d'enregistrer toutes les infos au format CSV.").pack(pady=30)

    def previous_oeuvre(self):
        print("-1")
    
    def next_oeuvre(self):
        print("+1")
    
    def previous_cartel(self):
        print("-2")

    def next_cartel(self):
        print("+2")

    def choose_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.image_pairs = self.find_image_pairs(folder_path)
            if self.image_pairs:
                self.show_images()
                self.choix_label.pack_forget()
                self.choix.pack_forget()
                self.validation.config(state=tk.NORMAL)
                self.lieu_expo.set(folder_path.split("/")[-1])
                

            else:
                messagebox.showwarning("Avertissement", "Aucune paire d'images trouvée.")

    def find_image_pairs(self, folder_path):
        images = sorted([f for f in os.listdir(folder_path) if f.lower().endswith(('png', 'jpg', 'jpeg', 'heic'))])
        pairs = [(images[i], images[i + 1]) for i in range(0, len(images) - 1, 2)]
        return [(os.path.join(folder_path, p[0]), os.path.join(folder_path, p[1])) for p in pairs]

    def show_images(self):
        if self.current_index < len(self.image_pairs):
            art_path, label_path = self.image_pairs[self.current_index]
            
            art_img = self.load_image(art_path)
            label_img = self.load_image(label_path)

            # Afficher la barre de progression pendant le traitement
            self.progress_bar["value"] = 0
            self.progress_bar.pack(pady=10)  # Afficher la barre de progression
            self.update_progress_bar(1)  # Lancer l'incrémentation

            threading.Thread(target=self.process_image, args=(label_path, art_img, label_img), daemon=True).start()

    def load_image(self, path):
        register_heif_opener()
        img = Image.open(path).resize((350,400))
        return ImageTk.PhotoImage(img)

    def process_image(self, label_path, art_img, label_img):
        artiste, titre, annee = image_to_text(label_path)

        for i in range(1, 101):
            self.progress_bar["value"] = i  
            self.root.after(10) 

        self.queue.put((artiste, titre, annee, art_img, label_img))

        self.root.after(100, self.update_ui)

    def update_ui(self):
        if not self.queue.empty():
            artiste, titre, annee, art_img, label_img = self.queue.get()

            self.artist_var.set(artiste if artiste else "")
            self.title_var.set(titre if titre else "")
            self.date_var.set(annee if annee else "")
            
            self.canvas.delete("all")

            self.canvas.create_image(200, 250, anchor=tk.CENTER, image=art_img)
            self.canvas.create_image(750, 250, anchor=tk.CENTER, image=label_img)
            
            self.art_img = art_img  # Garder les références pour éviter la collecte de déchets
            self.label_img = label_img

            # Cacher la barre de progression si elle est à 100%
            self.update_progress_bar(100)

    def update_progress_bar(self, value):
        """Met à jour la barre de progression et masque/affiche en fonction de la valeur."""
        if value == 0 or value == 100:
            self.progress_bar.pack_forget()  # Masquer la barre de progression si à 0 ou 100
        else:
            self.progress_bar.pack(pady=10)  # Afficher la barre de progression
        self.progress_bar["value"] = value

    def save_and_next(self):
        art_path, _ = self.image_pairs[self.current_index]
        artist = self.artist_var.get().strip()
        title = self.title_var.get().strip()
        date = self.date_var.get().strip()
        
        if artist and title and date:
            new_name = f"{os.path.basename(art_path).split('.')[0]}_{nettoyer_nom(title)}_{nettoyer_nom(artist)}_{nettoyer_nom(date)}.jpg"
            new_path = os.path.join(os.path.dirname(art_path), new_name)
            os.rename(art_path, new_path)
            
            self.csv_data.append([title, artist, date, new_name])
            ajouter_exif(new_path, title, artist, date)
            self.current_index += 1
            
            if self.current_index < len(self.image_pairs):
                self.show_images()
            else:
                self.finish_process()
        else:
            messagebox.showwarning("Champs vides", "Veuillez remplir tous les champs")

    def finish_process(self):
        save_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if save_path:
            with open(save_path, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(["Titre", "Artiste", "Date", "Nom fichier"])
                writer.writerows(self.csv_data)
            
            messagebox.showinfo("Terminé", "CSV enregistré avec succès !")

        if self.get_airtable_credentials():
            # Push to Airtable
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
                        "Nom fichier": row[3]
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

