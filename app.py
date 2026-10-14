"""Interfaz gráfica Tkinter del Simulador de autómatas."""

from __future__ import annotations

import json
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from automatas import (
    EPSILON,
    format_equations,
    render_regex,
    solve_regular_expression,
    subset_construction,
    validate_automaton,
    verify_equivalence,
)

BASE_DIR = Path(__file__).resolve().parent


def read_sample(name: str) -> str:
    return (BASE_DIR / name).read_text(encoding="utf-8")


class AutomataApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Simulador gráfico de autómatas")
        self.root.geometry("1280x900")
        self.root.minsize(980, 700)
        self.root.option_add("*Font", "TkDefaultFont")
        self.source_automaton = None
        self.dfa = None
        self.steps = []
        self.step_index = -1
        self.regex_source = None
        self.regex_result = None
        self.canvas_specs = {}
        self.result_queue: queue.Queue = queue.Queue()

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        self.conversion_tab = ttk.Frame(self.notebook, padding=8)
        self.regex_tab = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(self.conversion_tab, text="AFND → AFD y verificación")
        self.notebook.add(self.regex_tab, text="Autómata → expresión regular")
        self._build_conversion_tab()
        self._build_regex_tab()
        self._set_editor(read_sample("caso1_afnd.json"))

    def _build_conversion_tab(self):
        toolbar = ttk.Frame(self.conversion_tab)
        toolbar.pack(fill="x", pady=(0, 8))
        ttk.Button(toolbar, text="Caso 1 del anexo", command=self.load_case1).pack(side="left", padx=3)
        ttk.Button(toolbar, text="Caso 2 del anexo", command=self.load_case2).pack(side="left", padx=3)
        ttk.Button(toolbar, text="Abrir JSON…", command=self.open_json).pack(side="left", padx=3)
        ttk.Button(toolbar, text="Guardar JSON…", command=self.save_json).pack(side="left", padx=3)
        ttk.Button(toolbar, text="Convertir AFND → AFD", command=self.convert).pack(side="left", padx=8)
        ttk.Button(toolbar, text="Usar AFD en módulo ER", command=self.use_dfa_for_regex).pack(side="left", padx=3)

        upper = ttk.Panedwindow(self.conversion_tab, orient="horizontal")
        upper.pack(fill="both", expand=True)
        editor_frame = ttk.LabelFrame(upper, text="Autómata de entrada (JSON)", padding=6)
        graph_frame = ttk.LabelFrame(upper, text="Diagramas", padding=6)
        upper.add(editor_frame, weight=1)
        upper.add(graph_frame, weight=2)

        editor_scroller = ttk.Frame(editor_frame)
        editor_scroller.pack(fill="both", expand=True)
        self.editor = tk.Text(editor_scroller, wrap="none", undo=True, font=("Consolas", 10), height=23, width=46)
        editor_y = ttk.Scrollbar(editor_scroller, orient="vertical", command=self.editor.yview)
        editor_x = ttk.Scrollbar(editor_scroller, orient="horizontal", command=self.editor.xview)
        self.editor.configure(yscrollcommand=editor_y.set, xscrollcommand=editor_x.set)
        self.editor.grid(row=0, column=0, sticky="nsew")
        editor_y.grid(row=0, column=1, sticky="ns")
        editor_x.grid(row=1, column=0, sticky="ew")
        editor_scroller.rowconfigure(0, weight=1)
        editor_scroller.columnconfigure(0, weight=1)
        ttk.Label(editor_frame, text="Usa ε como símbolo de transición vacía; no lo agregues al alfabeto.", wraplength=350).pack(fill="x", pady=(6, 0))

        graph_frame.columnconfigure(0, weight=1)
        graph_frame.columnconfigure(1, weight=1)
        graph_frame.rowconfigure(0, weight=1)
        self.nfa_canvas = tk.Canvas(graph_frame, background="white", highlightthickness=1, highlightbackground="#c7cbd1", height=310)
        self.dfa_canvas = tk.Canvas(graph_frame, background="white", highlightthickness=1, highlightbackground="#c7cbd1", height=310)
        self.nfa_canvas.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        self.dfa_canvas.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        self.nfa_canvas.bind("<Configure>", lambda _event: self._redraw(self.nfa_canvas))
        self.dfa_canvas.bind("<Configure>", lambda _event: self._redraw(self.dfa_canvas))
        self._draw_graph(self.nfa_canvas, None, "AFND de entrada")
        self._draw_graph(self.dfa_canvas, None, "AFD resultante")

        lower = ttk.Panedwindow(self.conversion_tab, orient="horizontal")
        lower.pack(fill="both", expand=True, pady=(8, 0))
        table_frame = ttk.LabelFrame(lower, text="Tabla de conversión", padding=6)
        verify_frame = ttk.LabelFrame(lower, text="Verificador de equivalencia", padding=6)
        lower.add(table_frame, weight=3)
        lower.add(verify_frame, weight=2)
        self.table = ttk.Treeview(table_frame, show="headings", height=8)
        table_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=table_scroll.set)
        self.table.pack(side="left", fill="both", expand=True)
        table_scroll.pack(side="right", fill="y")

        length_line = ttk.Frame(verify_frame)
        length_line.pack(fill="x")
        ttk.Label(length_line, text="Longitud máxima n (mínimo 6):").pack(side="left")
        self.length_var = tk.StringVar(value="6")
        ttk.Entry(length_line, textvariable=self.length_var, width=6).pack(side="left", padx=5)
        self.verify_button = ttk.Button(length_line, text="Verificar AFND, AFD y ER", command=self.verify)
        self.verify_button.pack(side="left", padx=5)
        self.verify_status = ttk.Label(verify_frame, text="Convierte el AFND y calcula la ER para iniciar.", wraplength=480)
        self.verify_status.pack(fill="x", pady=6)
        self.verify_output = tk.Text(verify_frame, height=7, wrap="word", state="disabled", font=("Segoe UI", 9))
        self.verify_output.pack(fill="both", expand=True)

        stepbar = ttk.Frame(self.conversion_tab)
        stepbar.pack(fill="x", pady=(6, 0))
        self.step_label = ttk.Label(stepbar, text="Paso a paso: convierte un autómata para ver los movimientos.", wraplength=850)
        self.step_label.pack(side="left", fill="x", expand=True)
        self.prev_button = ttk.Button(stepbar, text="Anterior", command=self.previous_step, state="disabled")
        self.next_button = ttk.Button(stepbar, text="Siguiente", command=self.next_step, state="disabled")
        self.prev_button.pack(side="right", padx=3)
        self.next_button.pack(side="right", padx=3)

    def _build_regex_tab(self):
        toolbar = ttk.Frame(self.regex_tab)
        toolbar.pack(fill="x", pady=(0, 8))
        ttk.Button(toolbar, text="Cargar AFD generado", command=self.use_dfa_for_regex).pack(side="left", padx=3)
        ttk.Button(toolbar, text="Resolver ecuaciones", command=self.solve_regex).pack(side="left", padx=3)
        self.regex_source_label = ttk.Label(toolbar, text="Fuente: todavía no se ha cargado un AFD.")
        self.regex_source_label.pack(side="left", padx=10)
        self.equations_text = tk.Text(self.regex_tab, wrap="word", font=("Consolas", 10), state="disabled")
        self.equations_text.pack(fill="both", expand=True)

    def _set_editor(self, content: str):
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", content.strip() + "\n")

    def _read_editor(self):
        try:
            parsed = json.loads(self.editor.get("1.0", "end"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"JSON inválido en línea {exc.lineno}, columna {exc.colno}: {exc.msg}") from exc
        return validate_automaton(parsed)

    def load_case1(self):
        self._set_editor(read_sample("caso1_afnd.json"))
        self.convert()

    def load_case2(self):
        self._set_editor(read_sample("caso2_af.json"))
        self.convert()
        if self.dfa:
            self.use_dfa_for_regex()
            self.solve_regex()
            self.notebook.select(self.regex_tab)

    def open_json(self):
        path = filedialog.askopenfilename(title="Abrir autómata", filetypes=[("JSON", "*.json"), ("Todos", "*.*")])
        if path:
            try:
                self._set_editor(Path(path).read_text(encoding="utf-8"))
            except OSError as exc:
                messagebox.showerror("No se pudo abrir", str(exc))

    def save_json(self):
        path = filedialog.asksaveasfilename(title="Guardar autómata", defaultextension=".json", filetypes=[("JSON", "*.json")])
        if path:
            try:
                automaton = self._read_editor()
                Path(path).write_text(json.dumps(automaton, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            except (OSError, ValueError) as exc:
                messagebox.showerror("No se pudo guardar", str(exc))

    def convert(self):
        try:
            nfa = self._read_editor()
            dfa, steps = subset_construction(nfa)
        except (ValueError, TypeError) as exc:
            messagebox.showerror("No se pudo convertir", str(exc))
            return
        self.source_automaton = nfa
        self.dfa = dfa
        self.steps = steps
        self.step_index = -1
        self.regex_source = None
        self.regex_result = None
        self._render_table(dfa)
        self._draw_graph(self.nfa_canvas, nfa, "AFND de entrada")
        self._draw_graph(self.dfa_canvas, dfa, "AFD resultante")
        self.step_label.configure(text=f"Conversión lista. Inicial del AFD: {dfa['initial']}. Hay {len(steps)} movimientos para revisar.")
        self.prev_button.configure(state="disabled")
        self.next_button.configure(state="normal" if steps else "disabled")
        self.verify_status.configure(text="AFD generado. Calcula la ER desde la pestaña de expresión regular o ejecuta el verificador.")

    def _render_table(self, dfa):
        columns = ["Estado del AFD", *dfa["alphabet"]]
        self.table.configure(columns=columns)
        self.table.heading(columns[0], text=columns[0])
        self.table.column(columns[0], width=170, anchor="w")
        for symbol in dfa["alphabet"]:
            self.table.heading(symbol, text=symbol)
            self.table.column(symbol, width=130, anchor="center")
        for item in self.table.get_children():
            self.table.delete(item)
        table = {}
        for edge in dfa["transitions"]:
            table.setdefault(edge["from"], {})[edge["symbol"]] = edge["to"]
        finals = set(dfa["finals"])
        for state in dfa["states"]:
            marker = " (inicial)" if state == dfa["initial"] else ""
            marker += " (final)" if state in finals else ""
            row = [state + marker]
            row.extend(table.get(state, {}).get(symbol, "—") for symbol in dfa["alphabet"])
            self.table.insert("", "end", values=row)

    def next_step(self):
        if not self.steps:
            return
        self.step_index = min(self.step_index + 1, len(self.steps) - 1)
        self._show_step()

    def previous_step(self):
        if not self.steps:
            return
        self.step_index = max(self.step_index - 1, 0)
        self._show_step()

    def _show_step(self):
        step = self.steps[self.step_index]
        current = "{" + ",".join(sorted(step["current"])) + "}" if step["current"] else "∅"
        moved = "{" + ",".join(sorted(step["moved"])) + "}" if step["moved"] else "∅"
        destination = "{" + ",".join(sorted(step["destination"])) + "}" if step["destination"] else "∅"
        closure_note = "" if step["moved"] == step["destination"] else f"; clausura-ε = {destination}"
        self.step_label.configure(
            text=f"Paso {self.step_index + 1}/{len(self.steps)}: procesar {current} con {step['symbol']!r}; movimiento = {moved}{closure_note}; destino = {destination}."
        )
        self.prev_button.configure(state="normal" if self.step_index > 0 else "disabled")
        self.next_button.configure(state="normal" if self.step_index < len(self.steps) - 1 else "disabled")

    def use_dfa_for_regex(self):
        if not self.dfa:
            messagebox.showinfo("Primero convierte", "Carga o edita un autómata y pulsa Convertir AFND → AFD.")
            return
        self.regex_source = self.dfa
        self.regex_result = None
        self.regex_source_label.configure(text=f"Fuente: AFD generado con {len(self.dfa['states'])} estados.")
        self.notebook.select(self.regex_tab)

    def solve_regex(self):
        if not self.regex_source:
            if self.dfa:
                self.regex_source = self.dfa
                self.regex_source_label.configure(text=f"Fuente: AFD generado con {len(self.dfa['states'])} estados.")
            else:
                messagebox.showinfo("Primero convierte", "Genera el AFD en la primera pestaña antes de resolver la ER.")
                return
        try:
            result = solve_regular_expression(self.regex_source)
        except (ValueError, TypeError) as exc:
            messagebox.showerror("No se pudo resolver la ER", str(exc))
            return
        self.regex_result = result
        lines = ["SISTEMA INICIAL (X_q representa las cadenas que llevan desde q hasta un estado final)", ""]
        lines.extend(format_equations(result["initial_equations"]))
        lines.append("")
        for number, step in enumerate(result["trace"], 1):
            lines.append(f"PASO {number} - despejar X_{step['state']}")
            lines.append(f"Regla: {step['rule']}")
            lines.append(f"A = {render_regex(step['loop'], 'X_')}; B = {render_regex(step['remainder'], 'X_')}")
            lines.append(f"X_{step['state']} = A*·B = {render_regex(step['solution'], 'X_')}")
            if step["substitutions"]:
                lines.append("Sustituciones y simplificación:")
                for substitution in step["substitutions"]:
                    lines.append(
                        f"  En X_{substitution['state']}: {render_regex(substitution['before'], 'X_')}"
                        f"  ⇒  {render_regex(substitution['after'], 'X_')}"
                    )
            lines.append("")
        lines.extend(["RESULTADO", result["regular_expression"]])
        self.equations_text.configure(state="normal")
        self.equations_text.delete("1.0", "end")
        self.equations_text.insert("1.0", "\n".join(lines))
        self.equations_text.configure(state="disabled")
        self.verify_status.configure(text="ER calculada. Ejecuta el verificador para comparar AFND, AFD y ER hasta la longitud indicada.")

    def verify(self):
        try:
            nfa = self._read_editor()
            max_length = int(self.length_var.get())
            if max_length < 6:
                raise ValueError("La longitud máxima n debe ser 6 o más.")
            dfa, _ = subset_construction(nfa)
            expression = solve_regular_expression(dfa)["expression"]
        except (ValueError, TypeError) as exc:
            messagebox.showerror("No se pudo verificar", str(exc))
            return
        self.source_automaton, self.dfa = nfa, dfa
        self.regex_source = dfa
        self.regex_result = {"expression": expression, "regular_expression": render_regex(expression)}
        self.verify_button.configure(state="disabled")
        self.verify_status.configure(text="Enumerando cadenas; puedes seguir usando la ventana…")
        self._write_verify_output("")

        def worker():
            try:
                result = verify_equivalence(nfa, dfa, expression, max_length)
                self.result_queue.put(("ok", result))
            except Exception as exc:  # Se informa en la ventana sin cerrar la aplicación.
                self.result_queue.put(("error", str(exc)))

        threading.Thread(target=worker, daemon=True).start()
        self.root.after(100, self._poll_verification)

    def _poll_verification(self):
        try:
            kind, result = self.result_queue.get_nowait()
        except queue.Empty:
            self.root.after(100, self._poll_verification)
            return
        self.verify_button.configure(state="normal")
        if kind == "error":
            self.verify_status.configure(text="La verificación encontró un error.")
            self._write_verify_output(result)
            return
        mismatches = result["mismatches"]
        if mismatches:
            self.verify_status.configure(text=f"Se revisaron {result['checked']} cadenas y hubo {len(mismatches)} discrepancias.")
            lines = []
            for item in mismatches[:100]:
                word = item["word"] if item["word"] else "λ (cadena vacía)"
                lines.append(f"{word}: AFND={item['nfa']}, AFD={item['dfa']}, ER={item['regex']}")
            if len(mismatches) > 100:
                lines.append(f"… y {len(mismatches) - 100} discrepancias más.")
            self._write_verify_output("\n".join(lines))
        else:
            self.verify_status.configure(
                text=f"Equivalencia confirmada: {result['checked']} cadenas, longitudes 0 a {result['max_length']}."
            )
            self._write_verify_output("AFND, AFD y ER aceptan exactamente las mismas cadenas enumeradas.")
        self._render_table(self.dfa)
        self._draw_graph(self.nfa_canvas, self.source_automaton, "AFND de entrada")
        self._draw_graph(self.dfa_canvas, self.dfa, "AFD resultante")

    def _write_verify_output(self, value: str):
        self.verify_output.configure(state="normal")
        self.verify_output.delete("1.0", "end")
        self.verify_output.insert("1.0", value)
        self.verify_output.configure(state="disabled")

    def _redraw(self, canvas):
        if canvas in self.canvas_specs:
            automaton, title = self.canvas_specs[canvas]
            self._draw_graph(canvas, automaton, title)

    def _draw_graph(self, canvas, automaton, title: str):
        self.canvas_specs[canvas] = (automaton, title)
        canvas.delete("all")
        width = max(canvas.winfo_width(), 300)
        height = max(canvas.winfo_height(), 240)
        canvas.create_text(width / 2, 16, text=title, font=("Segoe UI", 11, "bold"), fill="#253047")
        if not automaton:
            canvas.create_text(width / 2, height / 2, text="Sin autómata", fill="#727b89")
            return
        states = list(automaton["states"])
        center_x, center_y = width / 2, height / 2 + 12
        radius = max(35, min(width / 2 - 65, height / 2 - 45))
        positions = {}
        for index, state in enumerate(states):
            angle = -1.5708 + 2 * 3.141592653589793 * index / max(len(states), 1)
            positions[state] = (center_x + radius * __import__("math").cos(angle), center_y + radius * __import__("math").sin(angle))

        grouped = {}
        for edge in automaton["transitions"]:
            grouped.setdefault((edge["from"], edge["to"]), []).append(edge["symbol"])
        for (source, target), symbols in grouped.items():
            x1, y1 = positions[source]
            x2, y2 = positions[target]
            label = ",".join(sorted(symbols))
            if source == target:
                canvas.create_line(x1 - 16, y1 - 20, x1 - 23, y1 - 52, x1 + 18, y1 - 52, x1 + 16, y1 - 20,
                                   smooth=True, splinesteps=18, arrow=tk.LAST, width=1.5, fill="#3b526d")
                canvas.create_text(x1, y1 - 58, text=label, fill="#1e3551")
            else:
                dx, dy = x2 - x1, y2 - y1
                length = max((dx * dx + dy * dy) ** 0.5, 1)
                ux, uy = dx / length, dy / length
                start = (x1 + ux * 26, y1 + uy * 26)
                end = (x2 - ux * 29, y2 - uy * 29)
                canvas.create_line(*start, *end, arrow=tk.LAST, width=1.5, fill="#3b526d")
                canvas.create_text((start[0] + end[0]) / 2, (start[1] + end[1]) / 2 - 9, text=label, fill="#1e3551")

        final_states = set(automaton["finals"])
        for state, (x, y) in positions.items():
            if state == automaton["initial"]:
                canvas.create_line(x - 56, y, x - 30, y, arrow=tk.LAST, width=1.5, fill="#26384d")
            canvas.create_oval(x - 25, y - 25, x + 25, y + 25, fill="#f9fbff", outline="#26384d", width=1.5)
            if state in final_states:
                canvas.create_oval(x - 20, y - 20, x + 20, y + 20, outline="#26384d", width=1)
            label = state if len(state) <= 18 else state[:16] + "…"
            canvas.create_text(x, y, text=label, width=48, font=("Segoe UI", 8), fill="#172333")


def main():
    root = tk.Tk()
    AutomataApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
