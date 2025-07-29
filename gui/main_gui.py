import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
import csv
from logic.csv_mode import process_csv

def center_window(win, width=None, height=None):
    win.update_idletasks()
    if width is None or height is None:
        width = win.winfo_width()
        height = win.winfo_height()
    x = (win.winfo_screenwidth() // 2) - (width // 2)
    y = (win.winfo_screenheight() // 2) - (height // 2)
    win.geometry(f"{width}x{height}+{x}+{y}")

def start_gui():
    root = tk.Tk()
    root.title("Pobieranie zdjęć z CSV")
    root.geometry("440x320")
    root.minsize(440, 320)
    root.resizable(False, False)
    root.configure(bg="#f5f6fa")
    center_window(root, 440, 320)

    csv_path = tk.StringVar()
    folder_path = tk.StringVar()
    selected_columns = []
    filename_patterns = []

    style = ttk.Style()
    style.theme_use('clam')
    style.configure("TButton", font=("Segoe UI", 11), padding=6)
    style.configure("TLabel", font=("Segoe UI", 11), background="#f5f6fa")
    style.configure("TEntry", font=("Segoe UI", 11))

    def wybierz_csv():
        path = filedialog.askopenfilename(filetypes=[("Pliki CSV", "*.csv")])
        if path:
            csv_path.set(path)
            podglad_csv(path)

    def podglad_csv(path):
        # Odczytaj nagłówki i 3 pierwsze wiersze
        with open(path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            rows = [row for _, row in zip(range(3), reader)]

        preview_win = tk.Toplevel(root)
        preview_win.title("Podgląd pliku CSV")
        preview_win.geometry("1000x340")
        preview_win.minsize(600, 380)
        preview_win.grab_set()
        center_window(preview_win, 1000, 340)

        tk.Label(preview_win, text="Zaznacz kolumny i wpisz wzór nazwy pliku dla każdej:", font=("Segoe UI", 11, "bold")).pack(pady=(10, 5))

        # Ramka na całość (pola + tabela)
        content_frame = tk.Frame(preview_win)
        content_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Canvas + header_frame (pola i checkboxy)
        outer_canvas = tk.Canvas(content_frame, height=120)
        outer_canvas.pack(fill="x", expand=False)
        header_frame = tk.Frame(outer_canvas)
        header_window = outer_canvas.create_window((0, 0), window=header_frame, anchor="nw")

        def on_header_configure(event):
            outer_canvas.configure(scrollregion=outer_canvas.bbox("all"))
        header_frame.bind("<Configure>", on_header_configure)

        # Checkboxy i pola wzoru nazw plików dla kolumn w jednej linii, szerokość dopasowana do nazwy kolumny
        col_vars = {}
        pattern_vars = {}

        for idx, col in enumerate(headers):
            pattern_var = tk.StringVar()
            default_pattern = f"{{produkt_ean}}-{idx+1}"
            pattern_var.set(default_pattern if col.lower().startswith("zdjecie") else "")
            entry_width = max(len(col) + 4, 10)
            entry = tk.Entry(header_frame, textvariable=pattern_var, width=entry_width, font=("Segoe UI", 9))
            entry.grid(row=0, column=idx, padx=2, pady=(0,2), sticky="nsew")
            pattern_vars[col] = pattern_var

        for idx, col in enumerate(headers):
            var = tk.BooleanVar(value=col.lower().startswith("zdjecie"))
            cb = tk.Checkbutton(header_frame, text=col, variable=var, font=("Segoe UI", 10))
            cb.grid(row=1, column=idx, padx=2, pady=(0,2), sticky="nsew")
            col_vars[col] = var

        # Dodaj wycentrowany tekst pod polami do wpisania nazwy, przy lewej krawędzi nad pierwszą kolumną
        info_label = tk.Label(content_frame, text='"{}" --> odwołanie do wartości z tabeli', font=("Segoe UI", 10, "italic"))
        info_label.place(x=0, y=outer_canvas.winfo_height() + 60, anchor="nw")

        # Tabela pod spodem
        table_frame = tk.Frame(content_frame)
        table_frame.pack(fill="both", expand=True, pady=(0,0))
        style = ttk.Style()
        style.configure("Custom.Treeview", rowheight=22)
        style.layout("Custom.Treeview", [
            ('Treeview.field', {'sticky': 'nswe', 'children': [
                ('Treeview.padding', {'sticky': 'nswe', 'children': [
                    ('Treeview.treearea', {'sticky': 'nswe'})
                ]})
            ]})
        ])
        style.configure("Custom.Treeview.Heading", borderwidth=1, relief="raised")
        style.map("Custom.Treeview.Heading", relief=[('active', 'groove'), ('pressed', 'sunken')])

        table = ttk.Treeview(
            table_frame,
            columns=headers,
            show="headings",
            height=3,
            style="Custom.Treeview"
        )
        table.pack(side="left", fill="both", expand=True)
        table_scroll = ttk.Scrollbar(table_frame, orient="horizontal", command=table.xview)
        table_scroll.pack(side="bottom", fill="x")
        table.configure(xscrollcommand=table_scroll.set)

        for col in headers:
            col_width = max(len(col) * 10 + 30, 80)
            table.heading(col, text=col)
            table.column(col, width=col_width, anchor="w", minwidth=col_width, stretch=False)
        for row in rows:
            table.insert("", "end", values=[row.get(col, "") for col in headers])

        # Synchronizacja scrolla nagłówków i tabeli
        def sync_scroll(*args):
            outer_canvas.xview(*args)
            table.xview(*args)
        def sync_table_scroll(*args):
            table.xview(*args)
            outer_canvas.xview_moveto(table.xview()[0])
        # Scrollbar tylko na dole okna
        xscroll = tk.Scrollbar(preview_win, orient="horizontal")
        xscroll.pack(side="bottom", fill="x")
        outer_canvas.config(xscrollcommand=xscroll.set)
        xscroll.config(command=sync_scroll)
        table_scroll.config(command=sync_table_scroll)
        table.configure(xscrollcommand=table_scroll.set)

        # Rozciąganie kolumn
        for idx, col in enumerate(headers):
            header_frame.grid_columnconfigure(idx, minsize=max(len(col) * 10 + 30, 80))

        def zapisz_wybor():
            selected_columns.clear()
            filename_patterns.clear()
            for col in headers:
                if col_vars[col].get():
                    selected_columns.append(col)
                    filename_patterns.append(pattern_vars[col].get())
            preview_win.destroy()

        ttk.Button(preview_win, text="Zatwierdź wybór", command=zapisz_wybor).pack(pady=10)

    def wybierz_folder():
        # Ukryj tymczasowo główne okno, aby wymusić natywne okno wyboru folderu na Macu
        temp_root = tk.Tk()
        temp_root.withdraw()
        path = filedialog.askdirectory(parent=temp_root)
        temp_root.destroy()
        if path:
            folder_path.set(path)

    def uruchom():
        if not csv_path.get() or not folder_path.get():
            messagebox.showwarning("Błąd", "Wybierz plik CSV i folder!")
            return
        if not selected_columns or not filename_patterns:
            messagebox.showwarning("Błąd", "Wybierz kolumny i wzory nazw plików (kliknij 'Przeglądaj...' przy pliku CSV)!")
            return

        # Okno postępu
        progress_win = tk.Toplevel(root)
        progress_win.title("Postęp pobierania")
        progress_win.geometry("480x340")
        progress_win.resizable(False, False)
        progress_win.configure(bg="#f5f6fa")
        center_window(progress_win, 480, 340)

        tk.Label(progress_win, text="Postęp pobierania zdjęć:", font=("Segoe UI", 12, "bold"), bg="#f5f6fa").pack(pady=(18, 7))
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(progress_win, variable=progress_var, maximum=100, length=420)
        progress_bar.pack(padx=25, pady=5)

        status_label = tk.Label(progress_win, text="", font=("Segoe UI", 10), bg="#f5f6fa")
        status_label.pack(pady=(0, 10))

        error_frame = ttk.LabelFrame(progress_win, text="Błędy", padding=(10, 8))
        error_frame.pack(fill="both", expand=True, padx=18, pady=(0, 10))
        error_box = tk.Text(error_frame, height=7, width=56, state="disabled", wrap="word", font=("Consolas", 9))
        error_box.pack(fill="both", expand=True)

        progress_win.grab_set()  # Blokuje główne okno

        def progress_callback(current, total):
            percent = (current / total) * 100 if total else 0
            progress_var.set(percent)
            status_label.config(text=f"Przetworzono: {current} / {total}")
            progress_win.update_idletasks()

        def error_callback(msg):
            error_box.config(state="normal")
            error_box.insert("end", msg + "\n")
            error_box.see("end")
            error_box.config(state="disabled")
            progress_win.update_idletasks()

        def run_download():
            try:
                csv_p = Path(csv_path.get())
                out_dir = Path(folder_path.get())
                out_dir.mkdir(parents=True, exist_ok=True)
                log_file = out_dir / "errors.txt"
                pobrane, bledy = process_csv(
                    csv_p, out_dir, log_file,
                    progress_callback=progress_callback,
                    error_callback=error_callback,
                    image_columns=selected_columns,
                    filename_patterns=filename_patterns
                )
                messagebox.showinfo(
                    "Sukces",
                    f"Pobrano {pobrane} zdjęć, {bledy} błędów.\nZobacz log: {log_file}"
                )
            except Exception as e:
                messagebox.showerror("Błąd", f"Wystąpił błąd:\n{e}")
            finally:
                progress_win.destroy()

        import threading
        threading.Thread(target=run_download, daemon=True).start()

    # Sekcja wyboru pliku
    file_frame = ttk.LabelFrame(root, text="Wybierz plik CSV", padding=(15, 10))
    file_frame.pack(fill="x", padx=25, pady=(25, 10))

    file_entry = ttk.Entry(file_frame, textvariable=csv_path, width=38)
    file_entry.pack(side="left", padx=(0, 8))
    ttk.Button(file_frame, text="Przeglądaj...", command=wybierz_csv).pack(side="left")

    # Sekcja wyboru folderu
    folder_frame = ttk.LabelFrame(root, text="Wybierz folder docelowy", padding=(15, 10))
    folder_frame.pack(fill="x", padx=25, pady=(0, 10))

    folder_entry = ttk.Entry(folder_frame, textvariable=folder_path, width=38)
    folder_entry.pack(side="left", padx=(0, 8))
    ttk.Button(folder_frame, text="Przeglądaj...", command=wybierz_folder).pack(side="left")

    # Przycisk startowy
    ttk.Button(root, text="Pobierz zdjęcia", command=uruchom, width=22).pack(pady=(18, 0))

    # Stopka
    tk.Label(root, text="© 2024 Pobieranie zdjęć z CSV", font=("Segoe UI", 9), bg="#f5f6fa", fg="#888").pack(side="bottom", pady=8)

    root.mainloop()
