"""
UART Monitor - Real-time temperature display GUI
Receives data from ATmega16 over UART (USB-to-Serial) and displays it
with color coding based on temperature thresholds (green/yellow/red).

Requires: pip install pyserial
"""

import tkinter as tk
from tkinter import ttk, messagebox, font
import serial
import serial.tools.list_ports
import threading
import queue
import time
import re

# ── Theme colors ─────────────────────────────────────────────────────
BG = "#1e1e2e"        # main background
SURFACE = "#2a2a3e"   # frame background
ACCENT = "#00d4aa"    # light green (connect button, highlight)
DANGER = "#ff6b6b"    # light red (disconnect)
FG = "#cdd6f4"        # main text
FG_DIM = "#6c7086"    # secondary text
TERMINAL = "#0d1117"  # log area background

# ── Text colors by temperature range ─────────────────────────────────
COLOR_COOL = "#39d353"  # green (below 30°C)
COLOR_WARM = "#ffdb58"  # yellow (30°C - 40°C)
COLOR_HOT = "#ff4d4d"   # red (above 40°C)


class UARTApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Temperature Monitor - UART")
        self.root.geometry("550x450")
        self.root.configure(bg=BG)
        self.root.minsize(450, 350)
        self.root.resizable(True, True)

        self.ser = None
        self.running = False
        self.rx_queue = queue.Queue()
        self.data_buffer = ""  # accumulates incoming data until a full line

        self._apply_style()
        self._build_ui()
        self.check_queue()

    # ── Global style ──────────────────────────────────────────────────
    def _apply_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TCombobox",
                         fieldbackground=SURFACE,
                         background=SURFACE,
                         foreground=FG,
                         selectbackground=ACCENT,
                         selectforeground=BG,
                         bordercolor=FG_DIM,
                         arrowcolor=FG)
        style.map("TCombobox", fieldbackground=[("readonly", SURFACE)])

    # ── Build UI ──────────────────────────────────────────────────────
    def _build_ui(self):
        header_frame = tk.Frame(self.root, bg=BG)
        header_frame.pack(pady=(15, 10), fill="x")

        tk.Label(header_frame, text="UART MONITOR",
                 font=("Courier New", 14, "bold"),
                 bg=BG, fg=ACCENT).pack()
        tk.Label(header_frame, text="ATmega16 · Temperature",
                 font=("Courier New", 9),
                 bg=BG, fg=FG_DIM).pack(pady=(2, 0))

        self._build_config_frame()
        self._build_rx_frame()
        self._build_status_bar()

    def _build_config_frame(self):
        frame = tk.Frame(self.root, bg=SURFACE, padx=15, pady=12)
        frame.pack(padx=15, pady=(0, 10), fill="x")
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(2, weight=1)

        # COM port
        com_sub_frame = tk.Frame(frame, bg=SURFACE)
        com_sub_frame.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        tk.Label(com_sub_frame, text="PORT", font=("Courier New", 8, "bold"),
                 bg=SURFACE, fg=FG_DIM).pack(anchor="w", pady=(0, 2))
        self.combo_port = ttk.Combobox(
            com_sub_frame,
            values=[p.device for p in serial.tools.list_ports.comports()],
            state="readonly")
        ports = [p.device for p in serial.tools.list_ports.comports()]
        if ports:
            self.combo_port.set(ports[0])
        self.combo_port.pack(fill="x")

        # Baudrate
        baud_sub_frame = tk.Frame(frame, bg=SURFACE)
        baud_sub_frame.grid(row=0, column=1, sticky="ew", padx=(0, 10))
        tk.Label(baud_sub_frame, text="BAUD RATE", font=("Courier New", 8, "bold"),
                 bg=SURFACE, fg=FG_DIM).pack(anchor="w", pady=(0, 2))
        self.combo_baud = ttk.Combobox(
            baud_sub_frame, values=[9600, 19200, 38400, 115200], state="readonly")
        self.combo_baud.set(9600)
        self.combo_baud.pack(fill="x")

        # Connect button
        self.btn_connect = tk.Button(
            frame, text=" CONNECT",
            font=("Courier New", 10, "bold"),
            bg=ACCENT, fg=BG, relief="flat",
            activebackground="#00b894", activeforeground=BG,
            cursor="hand2",
            command=self.toggle_connection)
        self.btn_connect.grid(row=0, column=2, sticky="nsew", pady=(14, 0))

    def _build_rx_frame(self):
        frame = tk.Frame(self.root, bg=SURFACE, padx=15, pady=12)
        frame.pack(padx=15, pady=(0, 15), fill="both", expand=True)
        tk.Label(frame, text="INCOMING DATA (LIVE LOG)",
                 font=("Courier New", 8, "bold"),
                 bg=SURFACE, fg=FG_DIM).pack(anchor="w", pady=(0, 6))

        txt_frame = tk.Frame(frame, bg=TERMINAL)
        txt_frame.pack(fill="both", expand=True)
        scrollbar = tk.Scrollbar(txt_frame, bg=SURFACE, troughcolor=SURFACE, width=12)
        scrollbar.pack(side="right", fill="y")

        custom_font = font.Font(family="JetBrains Mono", size=11)
        if "JetBrains Mono" not in font.families():
            custom_font = font.Font(family="Consolas", size=11)

        self.txt_receive = tk.Text(
            txt_frame,
            bg=TERMINAL,
            font=custom_font,
            insertbackground=FG,
            selectbackground=ACCENT, selectforeground=BG,
            relief="flat", bd=8,
            state="disabled",
            yscrollcommand=scrollbar.set)
        self.txt_receive.pack(fill="both", expand=True)
        scrollbar.config(command=self.txt_receive.yview)

        self.txt_receive.tag_configure("cool", foreground=COLOR_COOL)
        self.txt_receive.tag_configure("warm", foreground=COLOR_WARM)
        self.txt_receive.tag_configure("hot", foreground=COLOR_HOT)
        self.txt_receive.tag_configure("normal", foreground=FG)

    def _build_status_bar(self):
        bar = tk.Frame(self.root, bg=SURFACE, height=26)
        bar.pack(fill="x", side="bottom")
        self.lbl_status = tk.Label(
            bar, text="● Disconnected",
            font=("Courier New", 8),
            bg=SURFACE, fg=FG_DIM)
        self.lbl_status.pack(side="left", padx=12, pady=3)

    # ── Connect / disconnect ────────────────────────────────────────────
    def toggle_connection(self):
        if self.ser is None or not self.ser.is_open:
            try:
                port = self.combo_port.get()
                baud = self.combo_baud.get()
                if not port:
                    messagebox.showwarning("Warning", "Please select a COM port first!")
                    return
                self.ser = serial.Serial(port, int(baud), timeout=0.1)
                self.btn_connect.config(
                    text="■ DISCONNECT", bg=DANGER, activebackground="#e55555")
                self.lbl_status.config(
                    text=f"● Connected {port} @ {baud} baud", fg=ACCENT)
                self.running = True
                self.thread = threading.Thread(target=self.read_from_port, daemon=True)
                self.thread.start()
            except Exception as e:
                messagebox.showerror("Error", f"Could not connect: {e}")
        else:
            self.running = False
            self.ser.close()
            self.btn_connect.config(text=" CONNECT", bg=ACCENT, activebackground="#00b894")
            self.lbl_status.config(text="● Disconnected", fg=FG_DIM)

    # ── Read data from UART (runs in a separate thread) ──────────────────
    def read_from_port(self):
        while self.running:
            if self.ser and self.ser.is_open:
                try:
                    waiting = self.ser.in_waiting
                    if waiting > 0:
                        data = self.ser.read(waiting).decode('utf-8', errors='ignore')
                        self.rx_queue.put(data)
                except Exception as e:
                    print(f"UART read error: {e}")
            time.sleep(0.01)

    def check_queue(self):
        try:
            while True:
                data = self.rx_queue.get_nowait()
                self.data_buffer += data
                while "\n" in self.data_buffer:
                    line, self.data_buffer = self.data_buffer.split("\n", 1)
                    if line.strip():
                        self.update_rx_text(line + "\n")
        except queue.Empty:
            pass
        self.root.after(50, self.check_queue)

    # ── Parse temperature and color the live text ─────────────────────
    def update_rx_text(self, text):
        self.txt_receive.config(state='normal')
        match = re.search(r"[-+]?\d*\.\d+|\d+", text)
        chosen_tag = "normal"
        if match:
            try:
                temp_value = float(match.group())
                if temp_value < 30:
                    chosen_tag = "cool"   # green
                elif 30 <= temp_value <= 40:
                    chosen_tag = "warm"   # yellow
                else:
                    chosen_tag = "hot"    # red
            except ValueError:
                pass

        self.txt_receive.insert(tk.END, text, chosen_tag)
        self.txt_receive.see(tk.END)
        self.txt_receive.config(state='disabled')


if __name__ == "__main__":
    root = tk.Tk()
    app = UARTApp(root)
    root.mainloop()
