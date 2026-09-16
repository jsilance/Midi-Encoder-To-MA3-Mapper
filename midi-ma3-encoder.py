import mido
import pyautogui
import win32api
import win32con
import time
import json
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
from screeninfo import get_monitors

pyautogui.PAUSE = 0.0001

DEFAULT_L1_Y = 965
DEFAULT_L2_Y = 900
DEFAULT_L3_Y = 835

DEFAULT_PAGES_POSITIONS = [
    # Page 1
    [(200, DEFAULT_L1_Y), (550, DEFAULT_L1_Y), (895, DEFAULT_L1_Y), (1240, DEFAULT_L1_Y)],
    # Page 2
    [(200, DEFAULT_L2_Y), (550, DEFAULT_L2_Y), (895, DEFAULT_L2_Y), (1240, DEFAULT_L2_Y)],
    # Page 3
    [(200, DEFAULT_L3_Y), (550, DEFAULT_L3_Y), (895, DEFAULT_L3_Y), (1240, DEFAULT_L3_Y)]
]

class EncoderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MA3 MIDI Controller - Multi Pages")
        self.root.geometry("400x610")
        self.root.resizable(False, False)

        self.running = False
        self.learning_target = None
        self.learning_btn = None
        self.monitors = get_monitors()
        self.midi_ports = mido.get_input_names()

        self.active_page_index = 0
        self.mapped_pages = []

        self.cc_entries_by_page = []
        self.x_entries_by_page = []
        self.y_entries_by_page = []
        self.learn_btns_by_page = []

        self.sync_x_vars = []
        self.sync_y_vars = []

        self.setup_ui()
        self.load_default_config()

    def setup_ui(self):
        # --- Hardware Configuration ---
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

        # --- Multi-Page Notebook ---
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="x", padx=10, pady=5)
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)

        for page_idx in range(3):
            page_frame = ttk.Frame(self.notebook, padding=8)
            self.notebook.add(page_frame, text=f"Page {page_idx + 1}")

            ttk.Label(page_frame, text="Encoder", font=('Helvetica', 8, 'bold')).grid(row=0, column=0, sticky="w")
            ttk.Label(page_frame, text="CC", font=('Helvetica', 8, 'bold')).grid(row=0, column=1)
            ttk.Label(page_frame, text="Assign", font=('Helvetica', 8, 'bold')).grid(row=0, column=2)
            ttk.Label(page_frame, text="X", font=('Helvetica', 8, 'bold')).grid(row=0, column=3)
            ttk.Label(page_frame, text="Y", font=('Helvetica', 8, 'bold')).grid(row=0, column=4)

            page_cc, page_x, page_y, page_btns = [], [], [], []

            for i in range(4):
                ttk.Label(page_frame, text=f"Encoder {i+1}:").grid(row=i+1, column=0, sticky="w", pady=2)

                default_cc = i + 1
                entry_cc = ttk.Entry(page_frame, width=5)
                entry_cc.insert(0, str(default_cc))
                entry_cc.grid(row=i+1, column=1, padx=3, pady=2)
                page_cc.append(entry_cc)

                btn_learn = tk.Button(
                    page_frame, text="Learn", font=('Helvetica', 8),
                    command=lambda p=page_idx, e=i: self.start_midi_learn(p, e)
                )
                btn_learn.grid(row=i+1, column=2, padx=3, pady=2)
                page_btns.append(btn_learn)

                entry_x = ttk.Entry(page_frame, width=6)
                entry_x.insert(0, str(DEFAULT_PAGES_POSITIONS[page_idx][i][0]))
                entry_x.grid(row=i+1, column=3, padx=3, pady=2)
                page_x.append(entry_x)

                entry_y = ttk.Entry(page_frame, width=6)
                entry_y.insert(0, str(DEFAULT_PAGES_POSITIONS[page_idx][i][1]))
                entry_y.grid(row=i+1, column=4, padx=3, pady=2)
                page_y.append(entry_y)

                entry_x.bind("<KeyRelease>", lambda event, p=page_idx, e=i: self.on_coord_change(p, e, 'x'))
                entry_y.bind("<KeyRelease>", lambda event, p=page_idx, e=i: self.on_coord_change(p, e, 'y'))

            sync_frame = ttk.Frame(page_frame)
            sync_frame.grid(row=5, column=0, columnspan=5, pady=6, sticky="w")

            var_sx = tk.BooleanVar(value=False)
            var_sy = tk.BooleanVar(value=True)
            self.sync_x_vars.append(var_sx)
            self.sync_y_vars.append(var_sy)

            chk_sx = ttk.Checkbutton(sync_frame, text="Sync X", variable=var_sx,
                                     command=lambda p=page_idx: self.apply_sync(p, 'x'))
            chk_sx.pack(side="left", padx=5)

            chk_sy = ttk.Checkbutton(sync_frame, text="Sync Y", variable=var_sy,
                                     command=lambda p=page_idx: self.apply_sync(p, 'y'))
            chk_sy.pack(side="left", padx=5)

            self.cc_entries_by_page.append(page_cc)
            self.x_entries_by_page.append(page_x)
            self.y_entries_by_page.append(page_y)
            self.learn_btns_by_page.append(page_btns)


        # --- Save / Load Profile ---
        frame_file = ttk.Frame(self.root)
        frame_file.pack(fill="x", padx=10, pady=2)
        btn_save = ttk.Button(frame_file, text="💾 Save Config", command=self.save_config)
        btn_save.pack(side="left", expand=True, fill="x", padx=2)
        btn_load = ttk.Button(frame_file, text="📂 Load Config", command=self.load_config)
        btn_load.pack(side="right", expand=True, fill="x", padx=2)

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

    def on_tab_change(self, event):
        self.active_page_index = self.notebook.index(self.notebook.select())

    def on_coord_change(self, page_idx, encoder_idx, axis):
        if axis == 'x' and self.sync_x_vars[page_idx].get():
            self.apply_sync(page_idx, 'x', source_idx=encoder_idx)
        elif axis == 'y' and self.sync_y_vars[page_idx].get():
            self.apply_sync(page_idx, 'y', source_idx=encoder_idx)

    def apply_sync(self, page_idx, axis, source_idx=0):
        entries = self.x_entries_by_page[page_idx] if axis == 'x' else self.y_entries_by_page[page_idx]
        val = entries[source_idx].get()
        for i, entry in enumerate(entries):
            if i != source_idx:
                entry.delete(0, tk.END)
                entry.insert(0, val)

    def load_default_config(self):
        if os.path.exists("default.json"):
            self._apply_json_data("default.json", show_messages=False)

    def _apply_json_data(self, file_path, show_messages=True):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)

            if "screen_index" in config_data and config_data["screen_index"] < len(self.monitors):
                self.screen_cb.current(config_data["screen_index"])
            if "midi_port" in config_data and config_data["midi_port"] in self.midi_ports:
                self.midi_var.set(config_data["midi_port"])

            self.val_up_entry.delete(0, tk.END)
            self.val_up_entry.insert(0, config_data.get("val_up", "65"))

            self.val_down_entry.delete(0, tk.END)
            self.val_down_entry.insert(0, config_data.get("val_down", "63"))

            for p, page_data in enumerate(config_data.get("pages", [])):
                if p >= 3:
                    break
                self.sync_x_vars[p].set(page_data.get("sync_x", False))
                self.sync_y_vars[p].set(page_data.get("sync_y", False))

                for i, enc in enumerate(page_data.get("encoders", [])):
                    if i >= 4:
                        break
                    self.cc_entries_by_page[p][i].delete(0, tk.END)
                    self.cc_entries_by_page[p][i].insert(0, str(enc.get("cc", "")))

                    self.x_entries_by_page[p][i].delete(0, tk.END)
                    self.x_entries_by_page[p][i].insert(0, str(enc.get("x", "")))

                    self.y_entries_by_page[p][i].delete(0, tk.END)
                    self.y_entries_by_page[p][i].insert(0, str(enc.get("y", "")))

            if show_messages:
                messagebox.showinfo("Success", "Configuration loaded successfully!")
        except Exception as e:
            if show_messages:
                messagebox.showerror("Error", f"Unable to load configuration : {e}")

    def save_config(self):
        config_data = {
            "screen_index": self.screen_cb.current(),
            "midi_port": self.midi_var.get(),
            "val_up": self.val_up_entry.get(),
            "val_down": self.val_down_entry.get(),
            "pages": []
        }

        for p in range(3):
            page_data = {
                "sync_x": self.sync_x_vars[p].get(),
                "sync_y": self.sync_y_vars[p].get(),
                "encoders": []
            }
            for i in range(4):
                page_data["encoders"].append({
                    "cc": self.cc_entries_by_page[p][i].get(),
                    "x": self.x_entries_by_page[p][i].get(),
                    "y": self.y_entries_by_page[p][i].get()
                })
            config_data["pages"].append(page_data)

        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(config_data, f, indent=4)
                messagebox.showinfo("Succès", "Configuration sauvegardée avec succès !")
            except Exception as e:
                messagebox.showerror("Erreur", f"Unable to save configuration : {e}")

    def load_config(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if file_path:
            self._apply_json_data(file_path, show_messages=True)

    def start_midi_learn(self, page_idx, encoder_idx):
        if self.running:
            return

        if self.learning_btn:
            self.learning_btn.config(text="Learn", bg="SystemButtonFace")

        btn = self.learn_btns_by_page[page_idx][encoder_idx]

        if self.learning_target == (page_idx, encoder_idx):
            self.learning_target = None
            self.learning_btn = None
            return

        self.learning_target = (page_idx, encoder_idx)
        self.learning_btn = btn
        btn.config(text="Waiting...", bg="#ffa500")

        threading.Thread(target=self._capture_midi_cc, daemon=True).start()

    def _capture_midi_cc(self):
        port_name = self.midi_var.get()
        if not port_name:
            self.root.after(0, lambda: messagebox.showerror("Error", "No MIDI port selected!"))
            self.root.after(0, self._reset_learn_button)
            return

        try:
            with mido.open_input(port_name) as inport:
                start_time = time.time()
                while self.learning_target and (time.time() - start_time < 10):
                    for msg in inport.iter_pending():
                        if msg.type == 'control_change':
                            cc_num = msg.control
                            page_idx, enc_idx = self.learning_target
                            self.root.after(0, self._apply_learned_cc, page_idx, enc_idx, cc_num)
                            return
                    time.sleep(0.01)
        except Exception as e:
            print(f"MIDI Learn Error: {e}")

        self.root.after(0, self._reset_learn_button)

    def _apply_learned_cc(self, page_idx, enc_idx, cc_num):
        entry = self.cc_entries_by_page[page_idx][enc_idx]
        entry.delete(0, tk.END)
        entry.insert(0, str(cc_num))
        self._reset_learn_button()

    def _reset_learn_button(self):
        if self.learning_btn:
            self.learning_btn.config(text="Learn", bg="SystemButtonFace")
        self.learning_target = None
        self.learning_btn = None

    def mouse_scroll(self, clicks):
        win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, clicks * 120, 0)

    def toggle_listening(self):
        if not self.running:
            if not self.midi_ports:
                messagebox.showerror("Error", "No MIDI device found!")
                return

            if self.learning_target:
                self._reset_learn_button()

            try:
                self.mapped_pages = []
                for p in range(3):
                    page_dict = {}
                    for i in range(4):
                        cc = int(self.cc_entries_by_page[p][i].get().strip())
                        x = int(self.x_entries_by_page[p][i].get().strip())
                        y = int(self.y_entries_by_page[p][i].get().strip())
                        page_dict[cc] = (x, y)
                    self.mapped_pages.append(page_dict)

                self.val_up = int(self.val_up_entry.get().strip())
                self.val_down = int(self.val_down_entry.get().strip())
            except ValueError:
                messagebox.showerror("Error", "Enter valid numbers.")
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
                self.learn_btns_by_page[p][i].config(state=state)

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

                            only_active = self.listen_active_only_var.get()
                            pages_to_check = [self.active_page_index] if only_active else range(3)

                            target_found = False
                            for p_idx in pages_to_check:
                                active_map = self.mapped_pages[p_idx]
                                if cc_num in active_map:
                                    local_x, local_y = active_map[cc_num]
                                    target_x = monitor.x + local_x
                                    target_y = monitor.y + local_y

                                    self.root.after(0, self.monitor_label.config, 
                                                    {"text": f"Page {p_idx + 1} | CC {cc_num} | Value : {val}"})

                                    pyautogui.moveTo(target_x, target_y)
                                    time.sleep(0.01)

                                    if val == self.val_up:
                                        self.mouse_scroll(1)
                                    elif val == self.val_down:
                                        self.mouse_scroll(-1)
                                    
                                    target_found = True
                                    break

                            if not target_found:
                                self.root.after(0, self.monitor_label.config, 
                                                {"text": f"Ignored CC {cc_num} | Value : {val}"})

                    time.sleep(0.001)
        except Exception as e:
            print(f"Error MIDI : {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = EncoderApp(root)
    root.mainloop()
