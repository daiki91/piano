# Piano Python — Studio

Un petit synthétiseur desktop en Python : clavier virtuel, jeu au clavier AZERTY, synthèse polyphonique et enregistrement de séquences.

## Fonctionnalités

- Clavier virtuel sur deux octaves, jouable à la souris.
- Notes jouables au clavier physique, avec touches actives mises en évidence.
- Polyphonie et transposition de l'octave du clavier.
- Quatre formes d'onde : sinusoïdale, carrée, triangulaire et dent de scie.
- Réglage du volume et enveloppe simple pour éviter les coupures abruptes.
- Enregistrement d'une séquence jouée et lecture/arrêt.

## Prérequis

- Python 3.10 ou plus récent.
- Un périphérique de sortie audio.

## Installation

Depuis la racine du projet, crée un environnement virtuel puis active-le avec la commande correspondant à ton terminal.

**Invite de commandes Windows (cmd) :**

```bat
py -m venv .venv
.\.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
```

**PowerShell :**

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Après activation, le préfixe `(.venv)` doit apparaître dans l'invite. Si tu ne peux pas activer l'environnement, installe les dépendances en appelant directement son interpréteur : `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`.

## Lancer le studio

```bash
python studio.py
```

### Raccourcis

| Action | Raccourci |
| --- | --- |
| Jouer les notes de Do à Si | `A Q Z S E R D T F Y G U` |
| Transposer d'une octave vers le bas / le haut | Boutons `Octave −` / `Octave +` |
| Enregistrer / terminer l'enregistrement | `P` |
| Lire / arrêter la séquence | `Espace` |
| Arrêter toutes les notes et la lecture | `Échap` |

Les notes blanches utilisent `A Z E R T Y U`; les notes noires sont intercalées sur `Q S D F G`. Les touches `+` et `-` transposent également le clavier.

## Anciens modes console

Les scripts d'origine restent disponibles :

```bash
python piano.py   # piano en console
python piano1.py  # piano temps réel (nécessite les droits clavier de la bibliothèque keyboard)
```

## Périmètre actuel

Cette version constitue une première étape vers une station musicale : elle fournit l'interface et les outils de jeu/enregistrement de base. L'export WAV/MIDI, les effets (réverbération, délai, chorus), les instruments échantillonnés et le MIDI externe ne sont pas encore implémentés.
