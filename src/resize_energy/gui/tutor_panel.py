"""AI tutor window: chat, settings and 'copy the project into any chatbot' (PySide6)."""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from resize_energy.tutor import ai_settings
from resize_energy.tutor.ai import (
    PROVIDER_DEFAULTS,
    PROVIDER_LABELS,
    AIError,
    AISettings,
    Message,
    ask,
    build_chatbot_prompt,
    build_system_prompt,
)

MAX_HISTORY = 20  # messages sent with each question (keeps the cost low)

PRIVACY_NOTE = (
    "Your project values (never your key) are sent to the provider you choose; with a local "
    "Ollama model nothing leaves your computer. Answers can be wrong: check them against the "
    "formulas in the Why? panel."
)


_ACTIVE_WORKERS: set[QThread] = set()


class _Worker(QThread):
    """Runs one request off the interface thread, so the window stays responsive."""

    succeeded = Signal(str)
    failed = Signal(str)

    def __init__(self, settings: AISettings, system: str, messages: list[Message]) -> None:
        super().__init__()
        self._settings, self._system, self._messages = settings, system, messages

    def run(self) -> None:
        try:
            text = ask(self._settings, self._system, self._messages)
        except AIError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:
            self.failed.emit(f"Unexpected error: {exc}")
        else:
            self.succeeded.emit(text)


class AISettingsDialog(QDialog):
    """Provider, model, address and API key."""

    def __init__(self, settings: AISettings, api_key: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("AI tutor settings")
        self.resize(520, 300)
        self._last_provider = settings.provider

        self.provider = QComboBox()
        for key, label in PROVIDER_LABELS.items():
            self.provider.addItem(label, key)
        self.provider.setCurrentIndex(max(0, list(PROVIDER_LABELS).index(settings.provider)))
        defaults = PROVIDER_DEFAULTS[settings.provider]
        self.model = QLineEdit(settings.model or defaults["model"])
        self.base_url = QLineEdit(settings.base_url or defaults["base_url"])
        self.key = QLineEdit(api_key)
        self.key.setEchoMode(QLineEdit.EchoMode.Password)
        self.key.setPlaceholderText("Paste your API key (not needed for Ollama)")
        self.remember = QCheckBox("Remember the key in the system keyring")
        self.remember.setChecked(bool(api_key))
        self.provider.currentIndexChanged.connect(self._provider_changed)

        info = QLabel(
            "The key is never written to a file. Without 'Remember' it is kept only until "
            "you close RESize. You can also set the ANTHROPIC_API_KEY or OPENAI_API_KEY "
            "environment variable. Model names change over time: edit the field if needed."
        )
        info.setWordWrap(True)
        info.setObjectName("hint")

        form = QFormLayout()
        form.addRow("Provider", self.provider)
        form.addRow("Model", self.model)
        form.addRow("Address", self.base_url)
        form.addRow("API key", self.key)
        form.addRow("", self.remember)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(info)
        layout.addWidget(buttons)

    def _provider_changed(self) -> None:
        """Swap model/address to the new provider's defaults if they were still the old ones."""
        new = self.provider.currentData()
        old_defaults = PROVIDER_DEFAULTS[self._last_provider]
        new_defaults = PROVIDER_DEFAULTS[new]
        if self.model.text().strip() in ("", old_defaults["model"]):
            self.model.setText(new_defaults["model"])
        if self.base_url.text().strip() in ("", old_defaults["base_url"]):
            self.base_url.setText(new_defaults["base_url"])
        self._last_provider = new

    def settings(self) -> AISettings:
        return AISettings(
            provider=self.provider.currentData(),
            model=self.model.text().strip(),
            base_url=self.base_url.text().strip(),
        )

    def api_key(self) -> str:
        return self.key.text().strip()

    def remember_key(self) -> bool:
        return self.remember.isChecked()


class TutorDialog(QDialog):
    """Chat with the tutor about the current project."""

    def __init__(self, context: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("RESize - AI tutor")
        self.resize(700, 620)
        self.context = context
        self.history: list[Message] = []
        self.transcript: list[tuple[str, str]] = []
        self.settings_ = ai_settings.load_settings()
        self.api_key = ai_settings.load_api_key(self.settings_.provider)
        self._worker: _Worker | None = None

        note = QLabel(PRIVACY_NOTE)
        note.setWordWrap(True)
        note.setObjectName("hint")
        self.chat = QTextBrowser()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Ask about your project, e.g. 'Why is the string limited to 22 modules?'")
        self.input.returnPressed.connect(self._send)
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self._send)

        settings_button = QPushButton("Settings...")
        settings_button.clicked.connect(self._open_settings)
        copy_button = QPushButton("Copy project for any chatbot")
        copy_button.setToolTip("Copies a ready-to-paste summary of your project")
        copy_button.clicked.connect(self._copy_context)
        clear_button = QPushButton("Clear chat")
        clear_button.clicked.connect(self._clear)

        row = QHBoxLayout()
        row.addWidget(self.input, 1)
        row.addWidget(self.send_button)
        tools = QHBoxLayout()
        tools.addWidget(settings_button)
        tools.addWidget(copy_button)
        tools.addWidget(clear_button)
        tools.addStretch(1)
        layout = QVBoxLayout(self)
        layout.addWidget(note)
        layout.addWidget(self.chat, 1)
        layout.addLayout(row)
        layout.addLayout(tools)
        self._render()

    # --- public -----------------------------------------------------------------
    def set_question(self, text: str) -> None:
        """Pre-fill the question box (the student presses Enter to send it)."""
        self.input.setText(text)
        self.input.setFocus()

    # --- conversation -------------------------------------------------------------
    def _add(self, kind: str, text: str) -> None:
        self.transcript.append((kind, text))
        self._render()

    def _render(self) -> None:
        if not self.transcript:
            self.chat.setMarkdown(
                "*Ask a question about your design. The tutor knows your inputs, results and "
                "design checks. No API key? Use 'Copy project for any chatbot' or a local "
                "Ollama model (Settings).*"
            )
            return
        parts: list[str] = []
        for kind, text in self.transcript:
            if kind == "you":
                quoted = "\n".join("> " + line for line in text.splitlines() or [""])
                parts.append(f"**You**\n\n{quoted}")
            elif kind == "tutor":
                parts.append(f"**Tutor**\n\n{text}")
            else:
                parts.append(f"*{text}*")
        self.chat.setMarkdown("\n\n---\n\n".join(parts))
        bar = self.chat.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _send(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            return
        text = self.input.text().strip()
        if not text:
            return
        if self.settings_.needs_key and not self.api_key:
            self._add("note", "No API key yet: open Settings, or use 'Copy project for any "
                              "chatbot', or choose a local Ollama model.")
            self._open_settings()
            if not self.api_key and self.settings_.needs_key:
                return
        self.input.clear()
        self._add("you", text)
        self.history.append(Message("user", text))
        self._add("note", "Thinking...")
        self.send_button.setEnabled(False)
        settings = AISettings(
            self.settings_.provider, self.settings_.model, self.settings_.base_url, self.api_key
        )
        self._worker = _Worker(
            settings, build_system_prompt(self.context), self.history[-MAX_HISTORY:]
        )
        worker = self._worker
        _ACTIVE_WORKERS.add(worker)  # keep it alive even if this window is closed meanwhile
        worker.finished.connect(lambda w=worker: _ACTIVE_WORKERS.discard(w))
        worker.succeeded.connect(self._on_answer)
        worker.failed.connect(self._on_error)
        worker.start()

    def _finish_pending(self) -> None:
        if self.transcript and self.transcript[-1] == ("note", "Thinking..."):
            self.transcript.pop()
        self.send_button.setEnabled(True)

    def _on_answer(self, text: str) -> None:
        self._finish_pending()
        self.history.append(Message("assistant", text))
        self._add("tutor", text)

    def _on_error(self, message: str) -> None:
        self._finish_pending()
        if self.history and self.history[-1].role == "user":
            pending = self.history.pop()  # let the student retry the same question
            self.input.setText(pending.content)
        self._add("note", f"Could not get an answer. {message}")

    def _clear(self) -> None:
        self.history.clear()
        self.transcript.clear()
        self._render()

    # --- tools --------------------------------------------------------------------
    def _copy_context(self) -> None:
        QApplication.clipboard().setText(build_chatbot_prompt(self.context))
        QMessageBox.information(
            self, "RESize",
            "Your project summary is on the clipboard.\nPaste it into any chatbot "
            "(Claude, ChatGPT, ...) and ask your questions there.",
        )

    def _open_settings(self) -> None:
        dialog = AISettingsDialog(self.settings_, self.api_key, self)
        if not dialog.exec():
            return
        self.settings_ = dialog.settings()
        self.api_key = dialog.api_key()
        ai_settings.save_settings(self.settings_)
        if self.api_key and dialog.remember_key():
            if not ai_settings.save_api_key(self.settings_.provider, self.api_key):
                self._add("note", "The system keyring is not available, so the key is kept "
                                  "only until you close RESize.")
        elif not dialog.remember_key():
            ai_settings.delete_api_key(self.settings_.provider)
        if not self.api_key:
            self.api_key = ai_settings.load_api_key(self.settings_.provider)
