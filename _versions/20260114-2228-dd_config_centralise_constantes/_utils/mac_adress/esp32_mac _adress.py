import network

# Crée une interface Wi-Fi (station)
sta = network.WLAN(network.STA_IF)
sta.active(True)

# Récupère l'adresse MAC (6 octets)
mac = sta.config('mac')

# Affiche sous forme hexadécimale lisible
print("Adresse MAC :", ":".join("{:02X}".format(b) for b in mac))

# Si tu veux un identifiant numérique unique
chip_id = int.from_bytes(mac, 'big')
print("Chip ID :", chip_id)