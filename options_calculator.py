"""
Options Strategy Calculator
Visualiza el P&L de estrategias combinando las 4 posiciones básicas de opciones.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

OPTION_TYPES = ["Long Call", "Short Call", "Long Put", "Short Put"]

PRESETS = {
    "Long Call": {"type": "Long Call", "legs": [
        {"type": "Long Call", "strike": 100, "premium": 5, "qty": 1}
    ]},
    "Long Put": {"type": "Long Put", "legs": [
        {"type": "Long Put", "strike": 100, "premium": 5, "qty": 1}
    ]},
    "Bull Call Spread": {"legs": [
        {"type": "Long Call",  "strike": 95,  "premium": 8, "qty": 1},
        {"type": "Short Call", "strike": 105, "premium": 3, "qty": 1},
    ]},
    "Bear Put Spread": {"legs": [
        {"type": "Long Put",  "strike": 105, "premium": 8, "qty": 1},
        {"type": "Short Put", "strike": 95,  "premium": 3, "qty": 1},
    ]},
    "Straddle": {"legs": [
        {"type": "Long Call", "strike": 100, "premium": 5, "qty": 1},
        {"type": "Long Put",  "strike": 100, "premium": 5, "qty": 1},
    ]},
    "Strangle": {"legs": [
        {"type": "Long Call", "strike": 105, "premium": 3, "qty": 1},
        {"type": "Long Put",  "strike": 95,  "premium": 3, "qty": 1},
    ]},
    "Covered Call": {"legs": [
        {"type": "Short Call", "strike": 105, "premium": 5, "qty": 1},
    ]},
    "Iron Condor": {"legs": [
        {"type": "Long Put",   "strike": 90,  "premium": 2, "qty": 1},
        {"type": "Short Put",  "strike": 95,  "premium": 4, "qty": 1},
        {"type": "Short Call", "strike": 105, "premium": 4, "qty": 1},
        {"type": "Long Call",  "strike": 110, "premium": 2, "qty": 1},
    ]},
    "Butterfly Call": {"legs": [
        {"type": "Long Call",  "strike": 90,  "premium": 12, "qty": 1},
        {"type": "Short Call", "strike": 100, "premium": 5,  "qty": 2},
        {"type": "Long Call",  "strike": 110, "premium": 1,  "qty": 1},
    ]},
}

TYPE_COLORS = {
    "Long Call":  "#2196F3",
    "Short Call": "#F44336",
    "Long Put":   "#4CAF50",
    "Short Put":  "#FF9800",
}


def payoff(option_type: str, S: np.ndarray, strike: float, premium: float) -> np.ndarray:
    if option_type == "Long Call":
        return np.maximum(0, S - strike) - premium
    elif option_type == "Short Call":
        return premium - np.maximum(0, S - strike)
    elif option_type == "Long Put":
        return np.maximum(0, strike - S) - premium
    elif option_type == "Short Put":
        return premium - np.maximum(0, strike - S)
    return np.zeros_like(S)


class OptionsApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Options Strategy Calculator")
        self.geometry("1150x700")
        self.resizable(True, True)
        self.configure(bg="#1e1e2e")

        self.legs: list[dict] = []
        self._build_ui()
        self._update_chart()

    # ── UI construction ──────────────────────────────────────────────────────

    def _build_ui(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame",        background="#1e1e2e")
        style.configure("TLabel",        background="#1e1e2e", foreground="#cdd6f4", font=("Segoe UI", 10))
        style.configure("Header.TLabel", background="#1e1e2e", foreground="#cba6f7", font=("Segoe UI", 11, "bold"))
        style.configure("TEntry",        fieldbackground="#313244", foreground="#cdd6f4", insertcolor="#cdd6f4")
        style.configure("TCombobox",     fieldbackground="#313244", foreground="#cdd6f4", background="#313244")
        style.map("TCombobox",           fieldbackground=[("readonly", "#313244")],
                                         foreground=[("readonly", "#cdd6f4")])
        style.configure("Accent.TButton", background="#cba6f7", foreground="#1e1e2e", font=("Segoe UI", 10, "bold"))
        style.map("Accent.TButton",       background=[("active", "#b4befe")])
        style.configure("Treeview",       background="#313244", foreground="#cdd6f4",
                                          fieldbackground="#313244", rowheight=26)
        style.configure("Treeview.Heading", background="#45475a", foreground="#cdd6f4",
                                            font=("Segoe UI", 10, "bold"))
        style.map("Treeview", background=[("selected", "#585b70")])

        main = ttk.Frame(self)
        main.pack(fill="both", expand=True, padx=10, pady=10)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        # ── Left panel ──
        left = ttk.Frame(main, width=340)
        left.grid(row=0, column=0, sticky="ns", padx=(0, 10))
        left.grid_propagate(False)
        self._build_left(left)

        # ── Right panel (chart) ──
        right = ttk.Frame(main)
        right.grid(row=0, column=1, sticky="nsew")
        self._build_chart(right)

    def _build_left(self, parent):
        # ── Presets ──
        ttk.Label(parent, text="Estrategias predefinidas", style="Header.TLabel").pack(anchor="w", pady=(0, 4))
        preset_frame = ttk.Frame(parent)
        preset_frame.pack(fill="x", pady=(0, 10))

        names = list(PRESETS.keys())
        for i, name in enumerate(names):
            btn = tk.Button(
                preset_frame, text=name, bg="#45475a", fg="#cdd6f4",
                activebackground="#585b70", relief="flat", font=("Segoe UI", 9),
                cursor="hand2",
                command=lambda n=name: self._load_preset(n),
            )
            btn.grid(row=i // 3, column=i % 3, padx=2, pady=2, sticky="ew")
        for c in range(3):
            preset_frame.columnconfigure(c, weight=1)

        ttk.Separator(parent).pack(fill="x", pady=8)

        # ── Add option form ──
        ttk.Label(parent, text="Añadir posición", style="Header.TLabel").pack(anchor="w", pady=(0, 6))

        form = ttk.Frame(parent)
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)

        def row(label, row_idx):
            ttk.Label(form, text=label).grid(row=row_idx, column=0, sticky="w", pady=3, padx=(0, 8))

        row("Tipo:", 0)
        self.var_type = tk.StringVar(value=OPTION_TYPES[0])
        cb = ttk.Combobox(form, textvariable=self.var_type, values=OPTION_TYPES,
                          state="readonly", width=16)
        cb.grid(row=0, column=1, sticky="ew", pady=3)

        row("Strike (K):", 1)
        self.var_strike = tk.StringVar(value="100")
        ttk.Entry(form, textvariable=self.var_strike).grid(row=1, column=1, sticky="ew", pady=3)

        row("Prima:", 2)
        self.var_premium = tk.StringVar(value="5")
        ttk.Entry(form, textvariable=self.var_premium).grid(row=2, column=1, sticky="ew", pady=3)

        row("Cantidad:", 3)
        self.var_qty = tk.StringVar(value="1")
        ttk.Entry(form, textvariable=self.var_qty).grid(row=3, column=1, sticky="ew", pady=3)

        btn_add = tk.Button(
            parent, text="+ Añadir posición", bg="#cba6f7", fg="#1e1e2e",
            activebackground="#b4befe", relief="flat", font=("Segoe UI", 10, "bold"),
            cursor="hand2", pady=6,
            command=self._add_leg,
        )
        btn_add.pack(fill="x", pady=(10, 0))

        ttk.Separator(parent).pack(fill="x", pady=10)

        # ── Legs table ──
        ttk.Label(parent, text="Posiciones activas", style="Header.TLabel").pack(anchor="w", pady=(0, 4))

        cols = ("Tipo", "K", "Prima", "Qty")
        self.tree = ttk.Treeview(parent, columns=cols, show="headings", height=7)
        widths = (110, 55, 60, 45)
        for col, w in zip(cols, widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor="center")
        self.tree.pack(fill="both", expand=True)

        btn_row = ttk.Frame(parent)
        btn_row.pack(fill="x", pady=(6, 0))

        tk.Button(
            btn_row, text="Eliminar seleccionada", bg="#f38ba8", fg="#1e1e2e",
            activebackground="#eba0ac", relief="flat", font=("Segoe UI", 9),
            cursor="hand2", pady=4,
            command=self._remove_leg,
        ).pack(side="left", fill="x", expand=True, padx=(0, 4))

        tk.Button(
            btn_row, text="Limpiar todo", bg="#45475a", fg="#cdd6f4",
            activebackground="#585b70", relief="flat", font=("Segoe UI", 9),
            cursor="hand2", pady=4,
            command=self._clear_legs,
        ).pack(side="left", fill="x", expand=True)

        # ── Price range ──
        ttk.Separator(parent).pack(fill="x", pady=8)
        ttk.Label(parent, text="Rango de precio subyacente", style="Header.TLabel").pack(anchor="w", pady=(0, 4))

        rng = ttk.Frame(parent)
        rng.pack(fill="x")
        rng.columnconfigure((1, 3), weight=1)

        ttk.Label(rng, text="Mín:").grid(row=0, column=0, sticky="w", padx=(0, 4))
        self.var_smin = tk.StringVar(value="50")
        ttk.Entry(rng, textvariable=self.var_smin, width=8).grid(row=0, column=1, sticky="ew")
        ttk.Label(rng, text="  Máx:").grid(row=0, column=2, sticky="w", padx=(8, 4))
        self.var_smax = tk.StringVar(value="150")
        ttk.Entry(rng, textvariable=self.var_smax, width=8).grid(row=0, column=3, sticky="ew")

        tk.Button(
            parent, text="Actualizar gráfico", bg="#89b4fa", fg="#1e1e2e",
            activebackground="#74c7ec", relief="flat", font=("Segoe UI", 10, "bold"),
            cursor="hand2", pady=6,
            command=self._update_chart,
        ).pack(fill="x", pady=(10, 0))

    def _build_chart(self, parent):
        self.fig = Figure(figsize=(7, 5), dpi=100, facecolor="#1e1e2e")
        self.ax = self.fig.add_subplot(111)
        self._style_axes()
        self.canvas = FigureCanvasTkAgg(self.fig, master=parent)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def _style_axes(self):
        self.ax.set_facecolor("#181825")
        self.ax.tick_params(colors="#cdd6f4")
        for spine in self.ax.spines.values():
            spine.set_color("#45475a")
        self.ax.title.set_color("#cdd6f4")
        self.ax.xaxis.label.set_color("#cdd6f4")
        self.ax.yaxis.label.set_color("#cdd6f4")

    # ── Logic ────────────────────────────────────────────────────────────────

    def _parse_form(self):
        try:
            strike  = float(self.var_strike.get())
            premium = float(self.var_premium.get())
            qty     = int(self.var_qty.get())
            if qty <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Strike y Prima deben ser números positivos.\nCantidad debe ser un entero positivo.")
            return None
        return {"type": self.var_type.get(), "strike": strike, "premium": premium, "qty": qty}

    def _add_leg(self):
        leg = self._parse_form()
        if leg is None:
            return
        self.legs.append(leg)
        self._refresh_tree()
        self._update_chart()

    def _remove_leg(self):
        sel = self.tree.selection()
        if not sel:
            return
        idx = self.tree.index(sel[0])
        self.legs.pop(idx)
        self._refresh_tree()
        self._update_chart()

    def _clear_legs(self):
        self.legs.clear()
        self._refresh_tree()
        self._update_chart()

    def _load_preset(self, name: str):
        self.legs = [dict(leg) for leg in PRESETS[name]["legs"]]
        self._refresh_tree()
        self._update_chart()

    def _refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        for leg in self.legs:
            tag = leg["type"].replace(" ", "_")
            self.tree.insert("", "end",
                             values=(leg["type"], leg["strike"], leg["premium"], leg["qty"]),
                             tags=(tag,))
        for opt_type, color in TYPE_COLORS.items():
            self.tree.tag_configure(opt_type.replace(" ", "_"), foreground=color)

    def _update_chart(self):
        try:
            s_min = float(self.var_smin.get())
            s_max = float(self.var_smax.get())
            if s_min >= s_max:
                raise ValueError
        except ValueError:
            s_min, s_max = 50, 150

        S = np.linspace(s_min, s_max, 500)

        self.ax.clear()
        self._style_axes()

        total = np.zeros_like(S)

        for leg in self.legs:
            p = payoff(leg["type"], S, leg["strike"], leg["premium"]) * leg["qty"]
            total += p
            label = f"{leg['qty']}× {leg['type']}  K={leg['strike']}  Prima={leg['premium']}"
            color = TYPE_COLORS.get(leg["type"], "#cdd6f4")
            self.ax.plot(S, p, linestyle="--", linewidth=1.2, color=color, alpha=0.55, label=label)

        if self.legs:
            self.ax.plot(S, total, linewidth=2.5, color="#f5c2e7", label="P&L Total")
            self.ax.fill_between(S, total, 0,
                                 where=(total >= 0), alpha=0.18, color="#a6e3a1", interpolate=True)
            self.ax.fill_between(S, total, 0,
                                 where=(total < 0),  alpha=0.18, color="#f38ba8", interpolate=True)
            # breakeven markers
            signs = np.sign(total)
            crossings = np.where(np.diff(signs))[0]
            for i in crossings:
                be = S[i] + (S[i+1] - S[i]) * (-total[i]) / (total[i+1] - total[i])
                self.ax.axvline(be, color="#fab387", linestyle=":", linewidth=1.2, alpha=0.8)
                self.ax.annotate(
                    f"BE: {be:.2f}",
                    xy=(be, 0), xytext=(6, 12), textcoords="offset points",
                    color="#fab387", fontsize=8,
                )

        self.ax.axhline(0, color="#585b70", linewidth=1)
        self.ax.set_xlabel("Precio del subyacente (S)", fontsize=10)
        self.ax.set_ylabel("Beneficio / Pérdida", fontsize=10)
        self.ax.set_title("Diagrama de rentabilidad a vencimiento", fontsize=12, pad=12)
        self.ax.set_xlim(s_min, s_max)

        if self.legs:
            legend = self.ax.legend(
                loc="upper left", fontsize=8,
                facecolor="#313244", edgecolor="#585b70", labelcolor="#cdd6f4",
            )

        self.fig.tight_layout(pad=1.5)
        self.canvas.draw()


if __name__ == "__main__":
    app = OptionsApp()
    app.mainloop()
