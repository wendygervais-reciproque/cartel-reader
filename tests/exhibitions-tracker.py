#!/usr/bin/env python3

from PIL import Image, ImageTk
import pytesseract
import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox, Text
import os
import re
import csv
import threading

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


def choisir_dossier():
    dossier_path = filedialog.askdirectory()
    if dossier_path:
        window_dossier.destroy()
        run_images(dossier_path)


def nettoyer_nom(nom):
    return re.sub(r'[^a-zA-Z0-9_]', '_', nom)


def run_images(dossier_path):
    window_principal = tk.Tk()
    window_principal.title("Outil cartels")

    extensions_image = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".heic")
    fichiers_images = sorted([f for f in os.listdir(dossier_path) if f.lower().endswith(extensions_image)])
    image_index = 0
    lignes_csv = []

    def ajouter_au_csv(nom_image, artiste, titre, annee):
        lignes_csv.append([nom_image, artiste, titre, annee])

    def sauvegarder_modifications():
        artiste = input_artiste.get("1.0", tk.END).strip()
        titre = input_titre.get("1.0", tk.END).strip()
        annee = input_annee.get("1.0", tk.END).strip()
        nom_image_renomme = f"{nettoyer_nom(fichiers_images[image_index])}_{nettoyer_nom(artiste)}_{nettoyer_nom(titre)}_{nettoyer_nom(annee)}"
        if lignes_csv and len(lignes_csv) > image_index // 2:
            lignes_csv[image_index // 2] = [nom_image_renomme, artiste, titre, annee]
        else:
            ajouter_au_csv(nom_image_renomme, artiste, titre, annee)
            chemin_renomme = os.path.join(dossier_path, nom_image_renomme)
            
    def afficher_images():
        def process_images():
            nonlocal image_index
            if image_index >= len(fichiers_images) - 1:
                window_principal.after(0, lambda: messagebox.showinfo("Fin", "Vous avez terminé de traiter toutes les images."))
                window_principal.after(0, proposer_export_csv)
                return

            image1_path = os.path.join(dossier_path, fichiers_images[image_index])
            image2_path = os.path.join(dossier_path, fichiers_images[image_index + 1])

            image1 = Image.open(image1_path)
            image2 = Image.open(image2_path)

            image1.thumbnail((400, 400), Image.Resampling.LANCZOS)
            image2.thumbnail((400, 400), Image.Resampling.LANCZOS)

            img1_tk = ImageTk.PhotoImage(image1)
            img2_tk = ImageTk.PhotoImage(image2)
            artiste, titre, annee = image_to_text(image2_path)

            window_principal.after(0, lambda: update_ui(img1_tk, img2_tk, artiste, titre, annee))

        def update_ui(img1_tk, img2_tk, artiste, titre, annee):
            label_img1.config(image=img1_tk)
            label_img1.image = img1_tk

            label_img2.config(image=img2_tk)
            label_img2.image = img2_tk

            input_artiste.delete("1.0", "end")
            input_artiste.insert("1.0", artiste or "")

            input_titre.delete("1.0", "end")
            input_titre.insert("1.0", titre or "")

            input_annee.delete("1.0", "end")
            input_annee.insert("1.0", annee or "")

        threading.Thread(target=process_images).start()

    def proposer_export_csv():
        export_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[["CSV files", "*.csv"]])
        if export_path:
            try:
                with open(export_path, mode="w", newline="") as file:
                    writer = csv.writer(file)
                    writer.writerow(["Nom image", "Artiste", "Titre", "Année"])
                    writer.writerows(lignes_csv)
                messagebox.showinfo("Succès", f"Le fichier CSV a été exporté vers {export_path}")
            except Exception as e:
                messagebox.showerror("Erreur", f"Une erreur est survenue lors de l'exportation : {e}")

    def valider():
        nonlocal image_index
        sauvegarder_modifications()

        if image_index + 2 >= len(fichiers_images):
            messagebox.showinfo("Fin", "Vous avez terminé de traiter toutes les images.")
            proposer_export_csv()
        else:
            image_index += 2
            afficher_images()

    label_img1 = tk.Label(window_principal)
    label_img1.grid(row=1, column=0, padx=10, pady=10, rowspan=3)

    label_img2 = tk.Label(window_principal)
    label_img2.grid(row=1, column=1, padx=10, pady=10, rowspan=3)

    label_artiste = tk.Label(window_principal, text="Artiste :")
    label_artiste.grid(row=0, column=2, padx=10, pady=10, sticky="e")

    input_artiste = Text(window_principal, height=2, width=50, wrap="word")
    input_artiste.grid(row=0, column=3, padx=10, pady=10, sticky="w")

    label_titre = tk.Label(window_principal, text="Titre :")
    label_titre.grid(row=1, column=2, padx=10, pady=10, sticky="e")

    input_titre = Text(window_principal, height=2, width=50, wrap="word")
    input_titre.grid(row=1, column=3, padx=10, pady=10, sticky="w")

    label_annee = tk.Label(window_principal, text="Année :")
    label_annee.grid(row=2, column=2, padx=10, pady=10, sticky="e")

    input_annee = Text(window_principal, height=2, width=50, wrap="word")
    input_annee.grid(row=2, column=3, padx=10, pady=10, sticky="w")

    bouton_valider = tk.Button(window_principal, text="Enregistrer et passer à l'oeuvre suivante", command=valider)
    bouton_valider.grid(row=8, column=3, columnspan=2, pady=20)

    afficher_images()
    window_principal.mainloop()

window_dossier = tk.Tk()
window_dossier.title("Cartel reader")

label_explanation = tk.Label(window_dossier, text="Veuillez sélectionner un dossier contenant les images à traiter.")
label_explanation.pack(padx=10, pady=5)

btn_choisir_dossier = tk.Button(window_dossier, text="Choisir un dossier", command=choisir_dossier)
btn_choisir_dossier.pack(padx=10, pady=10)

window_dossier.mainloop()
