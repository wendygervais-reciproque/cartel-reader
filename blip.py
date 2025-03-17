from transformers import BlipProcessor, BlipForConditionalGeneration
from PIL import Image

# Charger le modèle BLIP (version large pour plus de détails)
processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-large")
model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-large")

# Charger l’image
image = Image.open("JPEG/IMG_0966.jpg")

# Préparer l’entrée sans question pour activer le mode "image captioning"
inputs = processor(image, return_tensors="pt")

# Générer une description ULTRA détaillée
out = model.generate(
    **inputs, 
    max_length=150,  # Augmenter la longueur maximale de sortie
    min_length=50,   # Forcer une réponse plus longue
    do_sample=True, 
    top_p=0.95, 
    temperature=0.7,  # Garder une bonne diversité sans trop d'aléatoire
    repetition_penalty=1.2  # Éviter la répétition de mots
)

# Afficher la description proprement
response = processor.decode(out[0], skip_special_tokens=True)
print(response)
