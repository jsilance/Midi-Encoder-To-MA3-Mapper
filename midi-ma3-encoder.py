import mido
import pyautogui
import win32api
import win32con
import time
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from screeninfo import get_monitors

pyautogui.PAUSE = 0.0001

# Configuration par défaut des 3 pages
DEFAULT_PAGES_POSITIONS = [
    # Page 1
    [(200, 965), (550, 965), (895, 965), (1240, 965)],
    # Page 2
    [(200, 900), (550, 900), (895, 900), (1240, 900)],
    # Page 3
    [(200, 835), (550, 835), (895, 835), (1240, 835)]
]

class EncoderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MA3 MIDI Controller - Multi Pages")
        self.root.geometry("380x440")
        self.root.resizable(False, False)

        self.running = False
        self.monitors = get_monitors()
        self.midi_ports = mido.get_input_names()

        self.cc_entries_by_page = []
        self.x_entries_by_page = []
        self.y_entries_by_page = []

        self.setup_ui()

    def setup_ui(self):
        frame_config = ttk.LabelFrame(self.root, text=" Hardware Configuration ", padding=8)
        frame_config.pack(fill="x", padx=10, pady=5)

        ttk.Label(frame_config, text="Target Screen :").grid(row=0, column=0, sticky="w", pady=2)
        self.screen_var = tk.StringVar()
        screen_options = [f"Screen {i+1} ({m.width}x{m.height})" for i, m in enumerate(self.monitors)]
        self.screen_cb = ttk.Combobox(frame_config, textvariable=self.screen_var, values=screen_options, state="readonly", width=25)
        if screen_options:
            self.screen_cb.current(0)
        self.screen_cb.grid(row=0, column=1, pady=2, columnspan=3)

        ttk.Label(frame_config, text="MIDI Port :").grid(row=1, column=0, sticky="w", pady=2)
        self.midi_var = tk.StringVar()
        self.midi_cb = ttk.Combobox(frame_config, textvariable=self.midi_var, values=self.midi_ports, state="readonly", width=25)
        if self.midi_ports:
            self.midi_cb.current(0)
        self.midi_cb.grid(row=1, column=1, pady=2, columnspan=3)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="x", padx=10, pady=5)

        for page_idx in range(3):
            page_frame = ttk.Frame(self.notebook, padding=8)
            self.notebook.add(page_frame, text=f"Page {page_idx + 1}")

            ttk.Label(page_frame, text="Encoder", font=('Helvetica', 8, 'bold')).grid(row=0, column=0, sticky="w")
            ttk.Label(page_frame, text="CC", font=('Helvetica', 8, 'bold')).grid(row=0, column=1)
            ttk.Label(page_frame, text="X", font=('Helvetica', 8, 'bold')).grid(row=0, column=2)
            ttk.Label(page_frame, text="Y", font=('Helvetica', 8, 'bold')).grid(row=0, column=3)

            page_cc = []
            page_x = []
            page_y = []

            for i in range(4):
                ttk.Label(page_frame, text=f"Encoder {i+1}:").grid(row=i+1, column=0, sticky="w", pady=2)

                default_cc = (page_idx * 4) + (i + 1)
                entry_cc = ttk.Entry(page_frame, width=5)
                entry_cc.insert(0, str(default_cc))
                entry_cc.grid(row=i+1, column=1, padx=3, pady=2)
                page_cc.append(entry_cc)

                entry_x = ttk.Entry(page_frame, width=6)
                entry_x.insert(0, str(DEFAULT_PAGES_POSITIONS[page_idx][i][0]))
                entry_x.grid(row=i+1, column=2, padx=3, pady=2)
                page_x.append(entry_x)

                entry_y = ttk.Entry(page_frame, width=6)
                entry_y.insert(0, str(DEFAULT_PAGES_POSITIONS[page_idx][i][1]))
                entry_y.grid(row=i+1, column=3, padx=3, pady=2)
                page_y.append(entry_y)

            self.cc_entries_by_page.append(page_cc)
            self.x_entries_by_page.append(page_x)
            self.y_entries_by_page.append(page_y)

        # --- MIDI Values Configuration ---
        frame_values = ttk.LabelFrame(self.root, text=" MIDI Values ", padding=8)
        frame_values.pack(fill="x", padx=10, pady=2)

        ttk.Label(frame_values, text="Increment (+):").grid(row=0, column=0, sticky="w", pady=2)
        self.val_up_entry = ttk.Entry(frame_values, width=6)
        self.val_up_entry.insert(0, "65")
        self.val_up_entry.grid(row=0, column=1, padx=3, pady=2)

        ttk.Label(frame_values, text="Decrement (-):").grid(row=0, column=2, sticky="w", pady=2)
        self.val_down_entry = ttk.Entry(frame_values, width=6)
        self.val_down_entry.insert(0, "63")
        self.val_down_entry.grid(row=0, column=3, padx=3, pady=2)

        # --- MIDI Monitor ---
        frame_monitor = ttk.LabelFrame(self.root, text=" MIDI Monitor ", padding=8)
        frame_monitor.pack(fill="x", padx=10, pady=5)

        self.monitor_label = ttk.Label(frame_monitor, text="Last msg : None", font=('Consolas', 9), foreground="#007acc")
        self.monitor_label.pack(anchor="w")

        self.btn_toggle = tk.Button(self.root, text="START", bg="#2ed573", fg="white", font=('Helvetica', 11, 'bold'), command=self.toggle_listening)
        self.btn_toggle.pack(pady=10, fill='x', padx=10)

    def mouse_scroll(self, clicks):
        win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, clicks * 120, 0)

    def toggle_listening(self):
        if not self.running:
            if not self.midi_ports:
                messagebox.showerror("Error", "No MIDI device found!")
                return

            try:
                self.mapped_pages = []
                for p in range(3):
                    page_dict = {}
                    for i in range(4):
                        cc = int(self.cc_entries_by_page[p][i].get())
                        x = int(self.x_entries_by_page[p][i].get())
                        y = int(self.y_entries_by_page[p][i].get())
                        page_dict[cc] = (x, y)
                    self.mapped_pages.append(page_dict)

                self.val_up = int(self.val_up_entry.get())
                self.val_down = int(self.val_down_entry.get())
            except ValueError:
                messagebox.showerror("Error", "Please enter valid integers for CC, X/Y positions, and MIDI values.")
                return

            self.running = True
            self.btn_toggle.config(text="STOP", bg="#ff4757")
            self.lock_inputs(True)

            self.thread = threading.Thread(target=self.midi_loop, daemon=True)
            self.thread.start()
        else:
            self.running = False
            self.btn_toggle.config(text="START", bg="#2ed573")
            self.lock_inputs(False)

    def lock_inputs(self, lock):
        state = "disabled" if lock else "normal"
        cb_state = "disabled" if lock else "readonly"
        self.screen_cb.config(state=cb_state)
        self.midi_cb.config(state=cb_state)
        self.val_up_entry.config(state=state)
        self.val_down_entry.config(state=state)

        for p in range(3):
            for i in range(4):
                self.cc_entries_by_page[p][i].config(state=state)
                self.x_entries_by_page[p][i].config(state=state)
                self.y_entries_by_page[p][i].config(state=state)

    def midi_loop(self):
        selected_screen_idx = self.screen_cb.current()
        monitor = self.monitors[selected_screen_idx]

        port_name = self.midi_var.get()

        try:
            with mido.open_input(port_name) as inport:
                while self.running:
                    for msg in inport.iter_pending():
                        if msg.type == 'control_change':
                            cc_num = msg.control
                            val = msg.value

                            # Récupération dynamique de la page sélectionnée dans l'interface
                            active_page_idx = self.notebook.index(self.notebook.select())
                            active_map = self.mapped_pages[active_page_idx]

                            self.root.after(0, self.monitor_label.config, 
                                            {"text": f"Page {active_page_idx + 1} | CC {cc_num} | Value : {val}"})

                            if cc_num in active_map:
                                local_x, local_y = active_map[cc_num]
                                target_x = monitor.x + local_x
                                target_y = monitor.y + local_y

                                pyautogui.moveTo(target_x, target_y)
                                time.sleep(0.01)

                                if val == self.val_up:
                                    self.mouse_scroll(1)
                                elif val == self.val_down:
                                    self.mouse_scroll(-1)
                    time.sleep(0.001)
        except Exception as e:
            print(f"Erreur MIDI : {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = EncoderApp(root)
    root.mainloop()
