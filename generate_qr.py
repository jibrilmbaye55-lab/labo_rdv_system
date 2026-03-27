import qrcode
from PIL import Image

# Lien vers ton site
url = "http://127.0.0.1:5000"

# Création QR avec haute correction d’erreur
qr = qrcode.QRCode(
    version=None,
    error_correction=qrcode.constants.ERROR_CORRECT_H,
    box_size=10,
    border=4,
)

qr.add_data(url)
qr.make(fit=True)

img = qr.make_image(fill_color="black", back_color="white").convert('RGB')

# =========================
# AJOUT LOGO AU CENTRE
# =========================
logo = Image.open("logo.png")  # ⚠️ ton logo ici

# Redimensionner le logo
qr_width, qr_height = img.size
logo_size = qr_width // 4  # taille du logo

logo = logo.resize((logo_size, logo_size))

# Position centre
pos = ((qr_width - logo_size) // 2, (qr_height - logo_size) // 2)

img.paste(logo, pos)

# Sauvegarde
img.save("qr_labo_logo.png")

print("✅ QR Code avec logo généré !")