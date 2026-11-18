import math
import sys
import threading
import time
from dataclasses import dataclass

import numpy as np
import sounddevice as sd
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)


SAMPLE_RATE = 44100
WHITE_PITCH_CLASSES = {0, 2, 4, 5, 7, 9, 11}
KEYBOARD_NOTES = {
    "q": 0,
    "z": 1,
    "s": 2,
    "e": 3,
    "d": 4,
    "f": 5,
    "t": 6,
    "g": 7,
    "y": 8,
    "h": 9,
    "u": 10,
    "j": 11,
}
NOTE_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")


@dataclass
class Voice:
    frequency: float
    phase: float
    started_at: int
    released_at: int = -1
    release_level: float = 1.0


class AudioEngine:
    def __init__(self):
        self.lock = threading.Lock()
        self.voices = {}
        self.frame = 0
        self.waveform = "Sinusoïdale"
        self.volume = 0.25
        self.stream = sd.OutputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            callback=self._render,
        )
        self.stream.start()

    def note_on(self, source, midi_note):
        frequency = 440.0 * 2 ** ((midi_note - 69) / 12)
        with self.lock:
            self.voices[source] = Voice(frequency, 0.0, self.frame)

    def note_off(self, source):
        with self.lock:
            voice = self.voices.get(source)
            if voice is not None and voice.released_at < 0:
                voice.released_at = self.frame
                elapsed = max(0, self.frame - voice.started_at)
                voice.release_level = min(1.0, elapsed / max(1, int(0.015 * SAMPLE_RATE)))

    def all_notes_off(self):
        with self.lock:
            for voice in self.voices.values():
                if voice.released_at < 0:
                    voice.released_at = self.frame
                    elapsed = max(0, self.frame - voice.started_at)
                    voice.release_level = min(1.0, elapsed / max(1, int(0.015 * SAMPLE_RATE)))

    def close(self):
        self.all_notes_off()
        self.stream.stop()
        self.stream.close()

    def _render(self, output, frames, _time_info, _status):
        with self.lock:
            start = self.frame
            self.frame += frames
            voices = list(self.voices.items())
            waveform = self.waveform
            volume = self.volume

        sample_frames = start + np.arange(frames)
        samples = np.zeros(frames, dtype=np.float64)
        finished = []
        attack_frames = max(1, int(0.015 * SAMPLE_RATE))
        release_frames = max(1, int(0.12 * SAMPLE_RATE))

        for source, voice in voices:
            phase_step = 2 * math.pi * voice.frequency / SAMPLE_RATE
            phase = voice.phase + phase_step * np.arange(frames)
            sine = np.sin(phase)
            if waveform == "Carrée":
                signal = np.where(sine >= 0, 1.0, -1.0)
            elif waveform == "Triangulaire":
                signal = (2 / math.pi) * np.arcsin(sine)
            elif waveform == "Dent de scie":
                cycle = np.mod(phase, 2 * math.pi) / (2 * math.pi)
                signal = 2 * cycle - 1
            else:
                signal = sine

            envelope = np.minimum(1.0, np.maximum(0.0, (sample_frames - voice.started_at) / attack_frames))
            if voice.released_at >= 0:
                release_elapsed = sample_frames - voice.released_at
                release = voice.release_level * np.maximum(0.0, 1.0 - release_elapsed / release_frames)
                envelope = np.where(sample_frames >= voice.released_at, release, envelope)
                if start + frames >= voice.released_at + release_frames:
                    finished.append(source)
            samples += signal * envelope
            voice.phase = (voice.phase + phase_step * frames) % (2 * math.pi)

        if voices:
            samples *= volume / math.sqrt(len(voices))
        output[:, 0] = np.clip(samples, -1.0, 1.0)

        if finished:
            with self.lock:
                for source in finished:
                    voice = self.voices.get(source)
                    if voice is not None and voice.released_at >= 0:
                        del self.voices[source]


class PianoKeyboard(QWidget):
    notePressed = Signal(int)
    noteReleased = Signal(int)

    def __init__(self, first_note=48, last_note=84):
        super().__init__()
        self.first_note = first_note
        self.last_note = last_note
        self.active_notes = set()
        self.held_mouse_note = None
        self.setMinimumHeight(190)
        self.setMouseTracking(True)

    def set_active_notes(self, notes):
        self.active_notes = set(notes)
        self.update()

    def _white_notes(self):
        return [
            note
            for note in range(self.first_note, self.last_note + 1)
            if note % 12 in WHITE_PITCH_CLASSES
        ]

    def _note_at(self, x, y):
        white_notes = self._white_notes()
        white_width = self.width() / len(white_notes)
        black_width = white_width * 0.62
        black_height = self.height() * 0.62

        for note in range(self.first_note, self.last_note + 1):
            if note % 12 not in WHITE_PITCH_CLASSES:
                preceding_white = max(n for n in white_notes if n < note)
                key_x = (white_notes.index(preceding_white) + 1) * white_width - black_width / 2
                if key_x <= x <= key_x + black_width and y <= black_height:
                    return note

        if y >= self.height() * 0.62:
            index = min(int(x / white_width), len(white_notes) - 1)
            return white_notes[max(0, index)]
        return None

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        white_notes = self._white_notes()
        white_width = self.width() / len(white_notes)
        black_width = white_width * 0.62
        black_height = self.height() * 0.62

        for index, note in enumerate(white_notes):
            rect_x = index * white_width
            color = QColor("#8ad8ff") if note in self.active_notes else QColor("#ffffff")
            painter.fillRect(int(rect_x), 0, math.ceil(white_width), self.height(), color)
            painter.setPen(QPen(QColor("#30343b"), 1))
            painter.drawRect(int(rect_x), 0, int(white_width), self.height())
            painter.setPen(QColor("#28323c"))
            painter.drawText(int(rect_x + 5), self.height() - 9, NOTE_NAMES[note % 12])

        for note in range(self.first_note, self.last_note + 1):
            if note % 12 in WHITE_PITCH_CLASSES:
                continue
            preceding_white = max(n for n in white_notes if n < note)
            key_x = (white_notes.index(preceding_white) + 1) * white_width - black_width / 2
            color = QColor("#44b5e8") if note in self.active_notes else QColor("#20242a")
            painter.fillRect(int(key_x), 0, int(black_width), int(black_height), color)
            painter.setPen(QPen(QColor("#111418"), 1))
            painter.drawRect(int(key_x), 0, int(black_width), int(black_height))
            painter.setPen(QColor("#ffffff"))
            painter.drawText(int(key_x + 4), int(black_height - 8), NOTE_NAMES[note % 12])

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            note = self._note_at(int(event.position().x()), int(event.position().y()))
            if note is not None:
                self.held_mouse_note = note
                self.notePressed.emit(note)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.held_mouse_note is not None:
            self.noteReleased.emit(self.held_mouse_note)
            self.held_mouse_note = None


class PianoStudio(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Piano Python — Studio")
        self.resize(960, 440)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.audio = AudioEngine()
        self.octave = 4
        self.keyboard_sources = {}
        self.mouse_sources = {}
        self.recording = False
        self.recording_started_at = 0.0
        self.recording_events = []
        self.recording_sources = {}
        self.playback_events = []
        self.playback_sources = {}
        self.playback_started_at = 0.0
        self.playback_timer = QTimer(self)
        self.playback_timer.setInterval(10)
        self.playback_timer.timeout.connect(self._playback_tick)

        central = QWidget()
        layout = QVBoxLayout(central)
        header = QHBoxLayout()
        header.addWidget(QLabel("<h2>Piano Python — Studio</h2>"))
        header.addStretch()

        self.waveform = QComboBox()
        self.waveform.addItems(["Sinusoïdale", "Carrée", "Triangulaire", "Dent de scie"])
        self.waveform.currentTextChanged.connect(self._set_waveform)
        header.addWidget(QLabel("Onde"))
        header.addWidget(self.waveform)

        self.volume = QSlider(Qt.Orientation.Horizontal)
        self.volume.setRange(0, 100)
        self.volume.setValue(25)
        self.volume.setFixedWidth(120)
        self.volume.valueChanged.connect(lambda value: setattr(self.audio, "volume", value / 100))
        header.addWidget(QLabel("Volume"))
        header.addWidget(self.volume)
        layout.addLayout(header)

        self.status = QLabel("Clique une touche ou joue au clavier.")
        layout.addWidget(self.status)

        self.piano = PianoKeyboard()
        self.piano.notePressed.connect(self._mouse_note_on)
        self.piano.noteReleased.connect(self._mouse_note_off)
        layout.addWidget(self.piano, 1)

        controls = QHBoxLayout()
        self.octave_label = QLabel()
        self._update_octave_label()
        down = QPushButton("Octave −")
        down.clicked.connect(lambda: self._change_octave(-1))
        up = QPushButton("Octave +")
        up.clicked.connect(lambda: self._change_octave(1))
        record = QPushButton("● Enregistrer (P)")
        record.clicked.connect(self.toggle_recording)
        play = QPushButton("▶ Lecture / arrêt (Espace)")
        play.clicked.connect(self.toggle_playback)
        stop = QPushButton("Arrêter (Échap)")
        stop.clicked.connect(self.stop_all)
        for button in (down, up, record, play, stop):
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            controls.addWidget(button)
        controls.insertWidget(2, self.octave_label)
        layout.addLayout(controls)

        layout.addWidget(QLabel(
            "Notes : Q Z S E D F T G Y H U J (Do à Si) · "
            "Maj : octave supérieure · Octave − / + pour transposer · "
            "P : enregistrer · Espace : lecture/arrêt · Échap : arrêter"
        ))
        self.setCentralWidget(central)
        QApplication.instance().installEventFilter(self)
        self._set_waveform(self.waveform.currentText())

    def _set_waveform(self, waveform):
        self.audio.waveform = waveform

    def _update_octave_label(self):
        self.octave_label.setText(f"Octave clavier : {self.octave}")

    def _change_octave(self, delta):
        self.octave = max(1, min(7, self.octave + delta))
        self._update_octave_label()
        self.piano.first_note = self.octave * 12
        self.piano.last_note = self.piano.first_note + 36
        self.piano.update()
        self.status.setText(f"Clavier transposé à l'octave {self.octave}.")

    def _record_event(self, action, source, midi_note):
        if self.recording:
            elapsed = time.monotonic() - self.recording_started_at
            if action == "on":
                self.recording_events.append((elapsed, action, source, midi_note))
                self.recording_sources[source] = midi_note
            elif source in self.recording_sources:
                self.recording_events.append((elapsed, action, source, midi_note))
                self.recording_sources.pop(source, None)

    def _note_on(self, source, midi_note):
        self.audio.note_on(source, midi_note)
        self._record_event("on", source, midi_note)
        self._refresh_active_notes()

    def _note_off(self, source, midi_note):
        self.audio.note_off(source)
        self._record_event("off", source, midi_note)
        self._refresh_active_notes()

    def _refresh_active_notes(self):
        active = (
            set(self.keyboard_sources.values())
            | set(self.mouse_sources.values())
            | set(self.playback_sources.values())
        )
        self.piano.set_active_notes(active)

    def _mouse_note_on(self, midi_note):
        source = f"mouse-{midi_note}"
        self.mouse_sources[source] = midi_note
        self._note_on(source, midi_note)

    def _mouse_note_off(self, midi_note):
        source = f"mouse-{midi_note}"
        self.mouse_sources.pop(source, None)
        self._note_off(source, midi_note)

    def _key_note_on(self, key, octave_shift=False):
        if key in self.keyboard_sources:
            return
        octave_offset = 12 if octave_shift else 0
        midi_note = (self.octave + 1) * 12 + octave_offset + KEYBOARD_NOTES[key]
        source = f"key-{key}"
        self.keyboard_sources[key] = midi_note
        self._note_on(source, midi_note)

    def _key_note_off(self, key):
        midi_note = self.keyboard_sources.pop(key, None)
        if midi_note is not None:
            self._note_off(f"key-{key}", midi_note)

    def eventFilter(self, watched, event):
        if isinstance(watched, QWidget) and watched.window() is self and event.type() in (
            event.Type.KeyPress,
            event.Type.KeyRelease,
        ):
            if event.isAutoRepeat():
                return True
            if event.type() == event.Type.KeyPress:
                key = event.text().lower()
                if key in KEYBOARD_NOTES:
                    octave_shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
                    self._key_note_on(key, octave_shift)
                    return True
                if event.key() == Qt.Key.Key_Space:
                    self.toggle_playback()
                    return True
                if key == "p":
                    self.toggle_recording()
                    return True
                if event.key() == Qt.Key.Key_Escape:
                    self.stop_all()
                    return True
                if key in ("+", "="):
                    self._change_octave(1)
                    return True
                if key in ("-", "_"):
                    self._change_octave(-1)
                    return True
            else:
                key = event.text().lower()
                if key in KEYBOARD_NOTES:
                    self._key_note_off(key)
                    return True
        return super().eventFilter(watched, event)

    def toggle_recording(self):
        if self.recording:
            now = time.monotonic() - self.recording_started_at
            for source, midi_note in list(self.recording_sources.items()):
                self.recording_events.append((now, "off", source, midi_note))
            self.recording_sources.clear()
            self.recording = False
            self.status.setText(f"Enregistrement terminé : {len(self.recording_events) // 2} note(s).")
            return
        self.stop_playback()
        self.recording_events = []
        self.recording_sources = {}
        self.recording_started_at = time.monotonic()
        self.recording = True
        self.status.setText("Enregistrement en cours… Appuie sur P pour terminer.")

    def toggle_playback(self):
        if self.recording:
            self.status.setText("Termine l'enregistrement avec P avant la lecture.")
        elif self.playback_timer.isActive():
            self.stop_playback()
        elif self.recording_events:
            self.playback_events = sorted(self.recording_events, key=lambda event: event[0])
            self.playback_sources.clear()
            self.playback_started_at = time.monotonic()
            self.playback_timer.start()
            self.status.setText("Lecture de la séquence…")
            self._playback_tick()
        else:
            self.status.setText("Aucune séquence enregistrée. Appuie sur P pour enregistrer.")

    def _playback_tick(self):
        elapsed = time.monotonic() - self.playback_started_at
        while self.playback_events and self.playback_events[0][0] <= elapsed:
            _, action, source, midi_note = self.playback_events.pop(0)
            playback_source = f"playback-{source}"
            if action == "on":
                self.audio.note_on(playback_source, midi_note)
                self.playback_sources[playback_source] = midi_note
            else:
                self.audio.note_off(playback_source)
                self.playback_sources.pop(playback_source, None)
            self._refresh_active_notes()
        if not self.playback_events:
            self.stop_playback()
            self.status.setText("Lecture terminée.")

    def stop_playback(self):
        self.playback_timer.stop()
        with self.audio.lock:
            for source, voice in self.audio.voices.items():
                if source.startswith("playback-") and voice.released_at < 0:
                    voice.released_at = self.audio.frame
                    voice.release_level = 1.0
        self.playback_events = []
        self.playback_sources.clear()
        self._refresh_active_notes()

    def stop_all(self):
        self.stop_playback()
        for key in list(self.keyboard_sources):
            self._key_note_off(key)
        for source, midi_note in list(self.mouse_sources.items()):
            self.mouse_sources.pop(source, None)
            self._note_off(source, midi_note)
        self.audio.all_notes_off()
        self.piano.set_active_notes(set())
        self.status.setText("Lecture arrêtée.")

    def closeEvent(self, event):
        QApplication.instance().removeEventFilter(self)
        self.audio.close()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    try:
        window = PianoStudio()
    except Exception as error:
        QMessageBox.critical(
            None,
            "Piano Python — Studio",
            f"Impossible d'initialiser la sortie audio :\n{error}\n\n"
            "Vérifie qu'un périphérique audio est disponible.",
        )
        return 1
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
