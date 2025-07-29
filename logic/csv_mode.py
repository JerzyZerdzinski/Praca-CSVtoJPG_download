import csv
from pathlib import Path
import requests
from tqdm import tqdm  # Pasek postępu
import re

# ────────────────────────── Ustawienia ────────────────────────── #
SCRIPT_DIR = Path(__file__).parent         # Folder, w którym jest skrypt
FILES_LIST = SCRIPT_DIR / "files.txt"      # Lista plików CSV
OUT_DIR    = SCRIPT_DIR / "images"         # Folder docelowy na obrazy


def download(url: str, dst: Path) -> None:
    """Pobiera plik z URL i zapisuje go do dst."""
    r = requests.get(url, stream=True)
    r.raise_for_status()                   # -> wyjątek przy 4xx/5xx
    with open(dst, "wb") as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)


def sanitize_filename(filename: str) -> str:
    # Zamień spacje na podkreślenia i usuń niedozwolone znaki dla Windows
    filename = filename.replace(" ", "_")
    # Usuwa / \ : * ? " < > | i inne nietypowe znaki
    return re.sub(r'[\\/:\*\?"<>\|]', '_', filename)


def process_csv(
    csv_path: Path,
    out_dir: Path,
    log_file: Path,
    progress_callback=None,
    error_callback=None,
    image_columns=None,
    filename_patterns=None
) -> tuple[int, int]:
    """
    Przetwarza pojedynczy plik CSV.

    Zwraca:
        (liczba_pobranych, liczba_bledow)
    """
    pobrane = 0
    bledy   = 0

    with csv_path.open(newline="", encoding="utf-8") as f, \
         log_file.open("a", encoding="utf-8") as log:

        reader = list(csv.DictReader(f))   # Zamieniamy na listę → znamy długość
        total = len(reader)
        for idx_row, row in enumerate(reader, 1):
            base = row.get("produkt_ean") or row.get("EAN") or row.get("ean") or ""

            # Brak EAN → log i dalej
            if base == "#N/A":
                indeks_handlowy = row.get("Indeks_handlowy")
                msg = f"Brak {indeks_handlowy or 'N/A'} w bazie danych\n"
                log.write(msg)
                if error_callback:
                    error_callback(msg.strip())
                bledy += 1
                if progress_callback:
                    progress_callback(idx_row, total)
                continue

            # Sprawdź czy wszystkie wybrane kolumny są "#N/A"
            columns_to_check = image_columns if image_columns else ("zdjecie", "zdjecie_opakowania")
            patterns = filename_patterns if filename_patterns else [f"{{EAN}}-{i+1}" for i in range(len(columns_to_check))]
            if all(row.get(col) == "#N/A" for col in columns_to_check):
                msg = f"{base}, wszystkie zdjęcia oznaczone jako \"#N/A\"\n"
                log.write(msg)
                if error_callback:
                    error_callback(msg.strip())
                bledy += 1
                if progress_callback:
                    progress_callback(idx_row, total)
                continue

            # Pobieranie zdjęć z wybranych kolumn i wzorów nazw
            for idx, col in enumerate(columns_to_check):
                url = row.get(col)
                if not url:
                    msg = f"{base}, brak \"{col}\"\n"
                    log.write(msg)
                    if error_callback:
                        error_callback(msg.strip())
                    bledy += 1
                    continue

                # Generowanie nazwy pliku na podstawie wzoru
                pattern = patterns[idx] if idx < len(patterns) else f"{{EAN}}-{idx+1}"
                # Zamień {NAZWA_KOLUMNY} na wartość z wiersza
                filename = pattern
                for key in row:
                    filename = filename.replace(f"{{{key}}}", str(row[key]))
                filename = filename.strip()
                filename = sanitize_filename(filename)
                if not filename.lower().endswith(".jpg"):
                    filename += ".jpg"

                try:
                    download(url, out_dir / filename)
                    pobrane += 1
                except requests.exceptions.RequestException as e:
                    msg = f"{base}, {col}, błąd pobierania: {e}\n"
                    log.write(msg)
                    if error_callback:
                        error_callback(msg.strip())
                    bledy += 1
            if progress_callback:
                progress_callback(idx_row, total)

    return pobrane, bledy


def main(files_list: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    error_log = out_dir / "errors.txt"

    n_pobrane = 0
    n_bledy   = 0

    with files_list.open("r", encoding="utf-8") as f:
        for line in f:
            csv_path = SCRIPT_DIR / line.strip()
            if csv_path.exists():
                p, b = process_csv(csv_path, out_dir, error_log)
                n_pobrane += p
                n_bledy   += b
            else:
                print(f"Plik {csv_path} nie istnieje.")

    print(f"Pobrano {n_pobrane} plików, {n_bledy} błędów. Zobacz log: {error_log}")


if __name__ == "__main__":
    main(FILES_LIST, OUT_DIR)
    input("Naciśnij Enter, aby zamknąć...")
