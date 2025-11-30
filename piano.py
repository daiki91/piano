import numpy as np
import sounddevice as sd

# Définir les paramètres de base
SAMPLING_RATE = 44100  # Taux d'échantillonnage
DURATION = 0.5  # Durée d'une note en secondes

# Fréquences des notes (octave 4 comme référence)
NOTES = {
    'C': 261.63,
    'D': 293.66,
    'E': 329.63,
    'F': 349.23,
    'G': 392.00,
    'A': 440.00,
    'B': 493.88,
}

def generate_sine_wave(frequency, duration, sampling_rate):
    """Génère une onde sinusoïdale pour une fréquence donnée."""
    t = np.linspace(0, duration, int(sampling_rate * duration), endpoint=False)
    wave = 0.5 * np.sin(2 * np.pi * frequency * t)
    return wave

def play_tone(frequency, duration=0.5):
    """Joue une tonalité pour une fréquence et une durée données."""
    wave = generate_sine_wave(frequency, duration, SAMPLING_RATE)
    sd.play(wave, SAMPLING_RATE)
    sd.wait()

def piano():
    """Simule un piano simple."""
    print("Piano (tapez une lettre pour jouer une note, 'Q' pour quitter) :")
    print("Notes disponibles :", ', '.join(NOTES.keys()))
    
    while True:
        note = input("Note: ").upper()
        if note == 'Q':
            print("Au revoir!")
            break
        elif note in NOTES:
            play_tone(NOTES[note], DURATION)
        else:
            print("Note non reconnue. Essayez encore.")

if __name__ == "__main__":
    piano()
