# Installation du firmware *Micro Python* sur le *T-Display-S3 Amoled de Lilygo*

Pour l'installation du firmware se rendre dans le répertoire du projet : 
`C:\Users\jmetr\kDrive_jo\technique\_projets\DTD\_utils\lilygo_t-displa-s3-amoled`

Etapes : 

1. Se rendre dans le répertoire du projet : 
   `C:\Users\jmetr\kDrive_jo\technique\_projets\DTD\_doc\ESP32\LILYGO-T-DISPLAY-S3-AMOLED`
    et ouvrir une fenêtre de commande dans ce répertoire  en tapant `cmd + ENTER` dans la barre d'adresse 
2. Connecter le T-display au PC par un câble USB
3. Mettre le T-display en mode BOOT en maintenant le bouton BOOT pressé lors de l'appui sur RESET
4. Avec la gestion des périphériques, vérifier sur quel port COM le module T-display est connecté (COM7 dans mon cas)
5. Dans la fenêtre de commande ouverte en 1 
   1. Effacer la mémoire flash par la commande : 
      `python -m esptool --port COM7 erase-flash`
   2. Installer le firmware par la commande : 
      `python -m esptool --chip esp32s3 --port COM7 --baud 460800 write-flash --flash-mode dio --flash-freq 80m --flash-size 16MB -z 0x0 lilygo_Waveshare_Amoled_Micropython\firmware\firmware_2026_01_05.bin`
6. Faire un reset du module et vérifier sur quel port COM le module se trouve maintenant.
7. Avec Thonny, vérifier qu'on peut se connecter sur ce module par le port COM trouvé ci-dessus

Les fichiers source pour l'installation du firmware pour ce processeur se trouvent sur Github à l'adresse 
https://github.com/dobodu/Lilygo_Waveshare_Amoled_Micropython 
Un clone de ce Repository se trouve dans le dossier projet à l'adresse : `C:\Users\jmetr\kDrive_jo\technique\_projets\DTD\_utils\lilygo\Lilygo_Waveshare_Amoled_Micropython`



