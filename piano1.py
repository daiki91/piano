import numpy as np
import sounddevice as sd
import keyboard  # Nécessaire pour détecter les touches en temps réel

# Définir les paramètres de base
SAMPLING_RATE = 44100  # Taux d'échantillonnage
DURATION = 0.5  # Durée d'une note en secondes

# Fréquences des notes (octave 4 comme référence)
NOTES = {
    'a': 861.63,  # C
    'z': 893.66,  # D
    'e': 729.63,  # E
    'r': 749.23,  # F
    't': 792.00,  # G
    'y': 640.00,  # A
    'u': 693.88,  # B
}

def generate_sine_wave(frequency, duration, sampling_rate):
    """Génère une onde sinusoïdale pour une fréquence donnée."""
    t = np.linspace(0, duration, int(sampling_rate * duration), endpoint=False)
    wave = 0.1 * np.sin(2 * np.pi * frequency * t)
    return wave

def play_tone(frequency, duration=0.5):
    """Joue une tonalité pour une fréquence et une durée données."""
    wave = generate_sine_wave(frequency, duration, SAMPLING_RATE)
    sd.play(wave, SAMPLING_RATE)
    sd.wait()

def piano_real_time():
    """Simule un piano jouable en temps réel."""
    print("Piano (appuyez sur les touches pour jouer des notes, 'ESC' pour quitter) :")
    print("Touches disponibles :")
    for key, freq in NOTES.items():
        print(f"  - '{key.upper()}': {freq} Hz")
    
    try:
        while True:
            for key, freq in NOTES.items():
                if keyboard.is_pressed(key):  # Détecte si une touche est pressée
                    play_tone(freq, DURATION)
                    while keyboard.is_pressed(key):  # Attendre que la touche soit relâchée
                        pass
            if keyboard.is_pressed('esc'):  # Quitter avec 'ESC'
                print("Au revoir!")
                break
    except KeyboardInterrupt:
        print("Interrompu par l'utilisateur.")

if __name__ == "__main__":
    piano_real_time()
