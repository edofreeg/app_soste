import os
import shutil
from datetime import datetime

from kivy.app import App
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.utils import platform

from logic import Store, parse_dt

Window.softinput_mode = "below_target"

SCEGLI_AUTISTA = "Scegli autista"
SCEGLI_LUOGO = "Scegli luogo"


# ---------------------------------------------------------------- helper UI
def btn(text, cb, **kw):
    b = Button(text=text, size_hint_y=None, height=dp(48), **kw)
    b.bind(on_release=lambda *_: cb())
    return b


def titolo(text):
    return Label(text=text, bold=True, size_hint_y=None, height=dp(30))


def wrapped_label(text):
    lb = Label(text=text, size_hint_y=None, halign="left", valign="middle")
    lb.bind(width=lambda w, v: setattr(w, "text_size", (v, None)))
    lb.bind(texture_size=lambda w, v: setattr(w, "height", v[1] + dp(12)))
    return lb


def scroll_col():
    sv = ScrollView()
    col = GridLayout(cols=1, spacing=dp(8), padding=dp(10), size_hint_y=None)
    col.bind(minimum_height=col.setter("height"))
    sv.add_widget(col)
    return sv, col


def info(titolo_popup, messaggio):
    box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
    lb = Label(text=messaggio)
    lb.bind(width=lambda w, v: setattr(w, "text_size", (v, None)))
    box.add_widget(lb)
    pop = Popup(title=titolo_popup, content=box, size_hint=(0.9, None), height=dp(240))
    box.add_widget(btn("OK", pop.dismiss))
    pop.open()


class DateTimeRow(BoxLayout):
    """Data + ora modificabili a mano, con pulsante 'Adesso'."""

    def __init__(self, etichetta, **kw):
        super().__init__(orientation="vertical", size_hint_y=None,
                         height=dp(98), spacing=dp(4), **kw)
        self.etichetta = etichetta
        self.add_widget(Label(text=etichetta, size_hint_y=None, height=dp(24)))
        riga = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(4))
        self.data = TextInput(hint_text="GG/MM/AAAA", multiline=False, size_hint_x=0.4)
        self.ora = TextInput(hint_text="HH:MM", multiline=False, size_hint_x=0.25)
        b = Button(text="Adesso", size_hint_x=0.35)
        b.bind(on_release=lambda *_: self.adesso())
        for w in (self.data, self.ora, b):
            riga.add_widget(w)
        self.add_widget(riga)

    def adesso(self):
        n = datetime.now()
        self.data.text = n.strftime("%d/%m/%Y")
        self.ora.text = n.strftime("%H:%M")

    def svuota(self):
        self.data.text = ""
        self.ora.text = ""

    def valore(self):
        d, o = self.data.text.strip(), self.ora.text.strip()
        if not d and not o:
            return None
        try:
            return parse_dt(d, o)
        except ValueError:
            raise ValueError(f"{self.etichetta}: usa il formato GG/MM/AAAA e HH:MM.")


# ---------------------------------------------------------------- schermate
class Home(Screen):
    def __init__(self, app, **kw):
        super().__init__(name="home", **kw)
        self.app = app
        sv, col = scroll_col()
        self.col = col
        self.add_widget(sv)

        col.add_widget(titolo("Registra sosta"))
        self.sp_autista = Spinner(text=SCEGLI_AUTISTA, size_hint_y=None, height=dp(48))
        self.sp_luogo = Spinner(text=SCEGLI_LUOGO, size_hint_y=None, height=dp(48))
        col.add_widget(self.sp_autista)
        col.add_widget(self.sp_luogo)
        self.arrivo = DateTimeRow("Arrivo")
        self.partenza = DateTimeRow("Partenza (lascia vuoto se non è ancora partito)")
        col.add_widget(self.arrivo)
        col.add_widget(self.partenza)
        col.add_widget(btn("Salva", self.salva))

        col.add_widget(titolo("Soste aperte"))
        self.aperte = GridLayout(cols=1, spacing=dp(6), size_hint_y=None)
        self.aperte.bind(minimum_height=self.aperte.setter("height"))
        col.add_widget(self.aperte)

        col.add_widget(btn("Storico", lambda: setattr(app.sm, "current", "storico")))
        col.add_widget(btn("Gestisci liste", lambda: setattr(app.sm, "current", "liste")))
        col.add_widget(btn("Esporta CSV", self.esporta))

    def on_pre_enter(self, *_):
        self.refresh()

    def refresh(self):
        cfg = self.app.store.cfg
        self.sp_autista.values = cfg["autisti"]
        self.sp_luogo.values = cfg["luoghi"]
        ultimo = cfg.get("ultimo_autista", "")
        if self.sp_autista.text not in cfg["autisti"]:
            self.sp_autista.text = ultimo if ultimo in cfg["autisti"] else SCEGLI_AUTISTA
        if self.sp_luogo.text not in cfg["luoghi"]:
            self.sp_luogo.text = SCEGLI_LUOGO

        self.aperte.clear_widgets()
        aperte = self.app.store.open_soste()
        if not aperte:
            self.aperte.add_widget(wrapped_label("Nessuna sosta aperta."))
        for idx, r in aperte:
            self.aperte.add_widget(
                wrapped_label(f"{r['autista']} - {r['luogo']}\nArrivo: {r['data_ora_arrivo']}"))
            self.aperte.add_widget(btn("Registra partenza", lambda i=idx: self.chiudi(i)))

    def salva(self):
        cfg = self.app.store.cfg
        a, l = self.sp_autista.text, self.sp_luogo.text
        if a not in cfg["autisti"] or l not in cfg["luoghi"]:
            info("Mancano dati", "Scegli autista e luogo.\nPuoi aggiungerli in 'Gestisci liste'.")
            return
        try:
            arr = self.arrivo.valore()
            if arr is None:
                raise ValueError("L'arrivo è obbligatorio.")
            par = self.partenza.valore()
            self.app.store.add_sosta(a, l, arr, par)
        except ValueError as e:
            info("Errore", str(e))
            return
        self.arrivo.svuota()
        self.partenza.svuota()
        self.refresh()
        info("Salvato", "Sosta registrata.")

    def chiudi(self, idx):
        riga = DateTimeRow("Partenza")
        riga.adesso()
        box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        box.add_widget(riga)
        pop = Popup(title="Registra partenza", content=box,
                    size_hint=(0.95, None), height=dp(310))

        def conferma():
            try:
                par = riga.valore()
                if par is None:
                    raise ValueError("Inserisci la partenza.")
                self.app.store.close_sosta(idx, par)
            except ValueError as e:
                info("Errore", str(e))
                return
            pop.dismiss()
            self.refresh()

        box.add_widget(btn("Conferma", conferma))
        box.add_widget(btn("Annulla", pop.dismiss))
        pop.open()

    def esporta(self):
        if not self.app.store.records():
            info("Nessun dato", "Non ci sono ancora soste da esportare.")
            return
        path = self.app.store.export()
        box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        pop = Popup(title="Esporta CSV", content=box, size_hint=(0.9, None), height=dp(260))

        def salva_download():
            pop.dismiss()
            try:
                info("Fatto", "File salvato in: " + salva_in_download(path))
            except Exception as e:
                info("Errore", str(e))

        def condividi():
            pop.dismiss()
            try:
                condividi_file(path)
            except Exception as e:
                info("Errore", str(e))

        box.add_widget(btn("Salva in Download", salva_download))
        box.add_widget(btn("Condividi", condividi))
        box.add_widget(btn("Annulla", pop.dismiss))
        pop.open()


class Storico(Screen):
    def __init__(self, app, **kw):
        super().__init__(name="storico", **kw)
        self.app = app
        sv, self.col = scroll_col()
        self.add_widget(sv)

    def on_pre_enter(self, *_):
        self.col.clear_widgets()
        self.col.add_widget(btn("Indietro", lambda: setattr(self.app.sm, "current", "home")))
        righe = self.app.store.records()
        if not righe:
            self.col.add_widget(wrapped_label("Nessuna sosta registrata."))
        for r in reversed(righe):
            par = r["data_ora_partenza"] or "in corso"
            sosta = r["intervallo_sosta"] or "-"
            self.col.add_widget(wrapped_label(
                f"{r['autista']} | {r['luogo']}\n{r['data_ora_arrivo']} -> {par}\nSosta: {sosta}"))


class Liste(Screen):
    def __init__(self, app, **kw):
        super().__init__(name="liste", **kw)
        self.app = app
        sv, self.col = scroll_col()
        self.add_widget(sv)

    def on_pre_enter(self, *_):
        self.rebuild()

    def rebuild(self):
        self.col.clear_widgets()
        self.col.add_widget(btn("Indietro", lambda: setattr(self.app.sm, "current", "home")))
        self._sezione("autisti", "Autisti")
        self._sezione("luoghi", "Luoghi")

    def _sezione(self, kind, nome):
        store = self.app.store
        self.col.add_widget(titolo(nome))
        campo = TextInput(hint_text="Nuovo elemento", multiline=False,
                          size_hint_y=None, height=dp(44))
        self.col.add_widget(campo)

        def aggiungi():
            store.add_item(kind, campo.text)
            self.rebuild()

        self.col.add_widget(btn("Aggiungi", aggiungi))
        for voce in store.cfg[kind]:
            riga = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(4))
            riga.add_widget(Label(text=voce))
            b = Button(text="Elimina", size_hint_x=0.3)

            def elimina(*_, v=voce):
                store.remove_item(kind, v)
                self.rebuild()

            b.bind(on_release=elimina)
            riga.add_widget(b)
            self.col.add_widget(riga)


# ---------------------------------------------------------------- export
def salva_in_download(path):
    if platform == "android":
        from jnius import autoclass
        from androidstorage4kivy import SharedStorage
        env = autoclass("android.os.Environment")
        SharedStorage().copy_to_shared(path, collection=env.DIRECTORY_DOWNLOADS)
        return "Download/" + os.path.basename(path)
    dest = os.path.join(os.path.expanduser("~"), "Downloads")
    os.makedirs(dest, exist_ok=True)
    return shutil.copy(path, dest)


def condividi_file(path):
    if platform == "android":
        from androidstorage4kivy import ShareSheet
        ShareSheet().share_file(path)
    else:
        info("Condividi", "Disponibile solo su Android.\nFile: " + path)


# ---------------------------------------------------------------- app
class SosteApp(App):
    title = "Soste Autisti"

    def build(self):
        self.store = Store(self.user_data_dir)
        self.sm = ScreenManager()
        for s in (Home(self), Storico(self), Liste(self)):
            self.sm.add_widget(s)
        Window.bind(on_keyboard=self._back)
        return self.sm

    def _back(self, window, key, *_):
        if key == 27 and self.sm.current != "home":
            self.sm.current = "home"
            return True
        return False


if __name__ == "__main__":
    SosteApp().run()
