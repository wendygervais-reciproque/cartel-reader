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

def image_to_text(filename):
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

class ImageRenamerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Renamer")
        
        self.image_pairs = []
        self.current_index = 0
        self.csv_data = []
        
        self.queue = queue.Queue()

        self.setup_ui()

    def setup_ui(self):
        tk.Button(self.root, text="Choisir un dossier contenant toutes les images", command=self.choose_folder).pack(pady=30)
        
        self.canvas = tk.Canvas(self.root, width=1000, height=500)
        self.canvas.pack()

        self.progress_bar = Progressbar(self.root, length=200, mode='determinate')
        self.progress_bar.pack(pady=10)
        self.progress_bar["value"] = 0  # Valeur initiale de la barre à 0%

        # Masquer la barre de progression initialement
        self.progress_bar.pack_forget()

        # Variables pour les champs de saisie
        self.artist_var = tk.StringVar()
        self.title_var = tk.StringVar()
        self.date_var = tk.StringVar()
        
        tk.Label(self.root, text="Artiste :").pack()
        tk.Entry(self.root, textvariable=self.artist_var).pack()
        
        tk.Label(self.root, text="Titre :").pack()
        tk.Entry(self.root, textvariable=self.title_var).pack()
        
        tk.Label(self.root, text="Date :").pack()
        tk.Entry(self.root, textvariable=self.date_var).pack()
        
        # Bouton de validation
        self.validation = tk.Button(self.root, text="Enregistrer et passer à l'oeuvre suivante", command=self.save_and_next)
        self.validation.pack(pady=30)
        self.validation.config(state=tk.DISABLED)

    def choose_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.image_pairs = self.find_image_pairs(folder_path)
            if self.image_pairs:
                self.show_images()
            else:
                messagebox.showwarning("Avertissement", "Aucune paire d'images trouvée.")

    def find_image_pairs(self, folder_path):
        self.validation.config(state=tk.NORMAL)
        images = sorted([f for f in os.listdir(folder_path) if f.lower().endswith(('png', 'jpg', 'jpeg'))])
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

            # Lancer un thread pour traiter l'image et extraire le texte
            threading.Thread(target=self.process_image, args=(label_path, art_img, label_img), daemon=True).start()

    def load_image(self, path):
        img = Image.open(path).resize((400, 400))
        return ImageTk.PhotoImage(img)

    def process_image(self, label_path, art_img, label_img):
        # Traitement de l'image dans le thread secondaire
        artiste, titre, annee = image_to_text(label_path)

        # Mettre à jour la barre de progression
        for i in range(1, 101):
            self.progress_bar["value"] = i  # Augmenter la valeur de la barre (de 0% à 100%)
            self.root.after(10)  # Attendre un peu avant d'augmenter la valeur pour simuler l'avancement

        # Lorsque le traitement est terminé, mettre à jour l'interface avec les résultats
        self.queue.put((artiste, titre, annee, art_img, label_img))

        # Pour ne pas bloquer l'interface, nous utilisons la queue pour traiter les résultats dans le thread principal.
        self.root.after(100, self.update_ui)

    def update_ui(self):
        # Vérifier si des résultats sont dans la queue
        if not self.queue.empty():
            artiste, titre, annee, art_img, label_img = self.queue.get()

            # Mettre à jour les champs texte dans l'interface utilisateur
            self.artist_var.set(artiste if artiste else "")
            self.title_var.set(titre if titre else "")
            self.date_var.set(annee if annee else "")
            
            # Afficher les images dans le canevas
            self.canvas.delete("all")
            self.canvas.create_image(250, 250, anchor=tk.CENTER, image=art_img)
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
            new_name = f"{os.path.basename(art_path).split('.')[0]}_{artist}_{title}_{date}.jpg"
            new_path = os.path.join(os.path.dirname(art_path), new_name)
            os.rename(art_path, new_path)
            
            self.csv_data.append([artist, title, date, new_name])
            self.current_index += 1
            
            if self.current_index < len(self.image_pairs):
                self.show_images()
            else:
                self.finish_process()
        else:
            messagebox.showwarning("Champs vides", "Veuillez remplir tous les champs !")

    def finish_process(self):
        save_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if save_path:
            with open(save_path, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(["Artiste", "Titre", "Date", "Nom fichier"])
                writer.writerows(self.csv_data)
            
            messagebox.showinfo("Terminé", "CSV enregistré avec succès !")
        
        self.validation.config(state=tk.DISABLED)
        
        self.root.quit()


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageRenamerApp(root)
    root.mainloop()
