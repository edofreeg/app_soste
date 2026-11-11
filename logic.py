"""Logica dati dell'app (senza dipendenze da Kivy, testabile da sola)."""
import csv
import json
import os
from datetime import datetime

FMT = "%d/%m/%Y %H:%M"
HEADER = ["autista", "luogo", "data_ora_arrivo", "data_ora_partenza", "intervallo_sosta"]


def parse_dt(data, ora):
    return datetime.strptime(f"{data.strip()} {ora.strip()}", FMT)


def fmt_dt(dt):
    return dt.strftime(FMT)


def intervallo(arrivo, partenza):
    minuti = int((partenza - arrivo).total_seconds() // 60)
    return f"{minuti // 60:02d}:{minuti % 60:02d}"


def _write_rows(path, rows):
    tmp = path + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=HEADER, delimiter=";")
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, path)


class Store:
    def __init__(self, folder):
        self.folder = folder
        os.makedirs(folder, exist_ok=True)
        self.csv_path = os.path.join(folder, "soste.csv")
        self.cfg_path = os.path.join(folder, "config.json")
        self.cfg = {"autisti": [], "luoghi": [], "ultimo_autista": ""}
        try:
            with open(self.cfg_path, encoding="utf-8") as f:
                self.cfg.update(json.load(f))
        except (OSError, ValueError):
            pass

    # ---- configurazione (liste autisti/luoghi, ultimo autista) ----
    def _save_cfg(self):
        tmp = self.cfg_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.cfg, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.cfg_path)

    def add_item(self, kind, nome):
        nome = nome.strip()
        lista = self.cfg[kind]
        if nome and nome not in lista:
            lista.append(nome)
            lista.sort(key=str.lower)
            self._save_cfg()

    def remove_item(self, kind, nome):
        if nome in self.cfg[kind]:
            self.cfg[kind].remove(nome)
            if kind == "autisti" and self.cfg["ultimo_autista"] == nome:
                self.cfg["ultimo_autista"] = ""
            self._save_cfg()

    # ---- soste ----
    def records(self):
        try:
            with open(self.csv_path, newline="", encoding="utf-8-sig") as f:
                return list(csv.DictReader(f, delimiter=";"))
        except FileNotFoundError:
            return []

    @staticmethod
    def _row(autista, luogo, arrivo, partenza):
        if partenza is not None and partenza < arrivo:
            raise ValueError("La partenza è precedente all'arrivo.")
        return {
            "autista": autista,
            "luogo": luogo,
            "data_ora_arrivo": fmt_dt(arrivo),
            "data_ora_partenza": fmt_dt(partenza) if partenza else "",
            "intervallo_sosta": intervallo(arrivo, partenza) if partenza else "",
        }

    def add_sosta(self, autista, luogo, arrivo, partenza=None):
        rows = self.records()
        rows.append(self._row(autista, luogo, arrivo, partenza))
        _write_rows(self.csv_path, rows)
        self.cfg["ultimo_autista"] = autista
        self._save_cfg()

    def open_soste(self):
        return [(i, r) for i, r in enumerate(self.records()) if not r["data_ora_partenza"]]

    def close_sosta(self, index, partenza):
        rows = self.records()
        r = rows[index]
        arrivo = datetime.strptime(r["data_ora_arrivo"], FMT)
        rows[index] = self._row(r["autista"], r["luogo"], arrivo, partenza)
        _write_rows(self.csv_path, rows)

    def export(self):
        """Crea il report CSV (separatore ';') e ne restituisce il percorso."""
        cartella = os.path.join(self.folder, "export")
        os.makedirs(cartella, exist_ok=True)
        nome = "report_soste_" + datetime.now().strftime("%Y%m%d_%H%M") + ".csv"
        path = os.path.join(cartella, nome)
        _write_rows(path, self.records())
        return path
