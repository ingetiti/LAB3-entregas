"""Pruebas de la ventana (lc10/gui.py). Necesitan tkinter y una pantalla; si no hay, se saltean.

En un equipo sin pantalla (por ejemplo un servidor):  xvfb-run -a python -m unittest tests.test_gui
"""
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

try:
    import tkinter as tk
    from lc10 import gui
except ImportError:                                   # sin tkinter
    tk = gui = None


def _display_ok() -> bool:
    if gui is None:
        return False
    try:
        tk.Tk().destroy()
        return True
    except tk.TclError:
        return False


HAY_PANTALLA = _display_ok()
ROOT = Path(__file__).resolve().parent.parent
ECO = """\
        .ORIG x3000
        GETC
        OUT
        GETC
        OUT
        HALT
        .END
"""
INFINITO = "        .ORIG x3000\nAQUI    BR AQUI\n        .END\n"


@unittest.skipUnless(HAY_PANTALLA, "sin tkinter o sin pantalla")
class GuiCase(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.geometry("1200x800+0+0")
        self.errors = []
        self.root.report_callback_exception = lambda *e: self.errors.append(e)
        self.boxes = {name: mock.patch.object(gui.messagebox, name, return_value=None).start()
                      for name in ("showinfo", "showerror", "askyesnocancel")}
        self.addCleanup(mock.patch.stopall)
        self.app = gui.App(self.root)
        self.ed = self.app.current_editor()
        self.pump()

    def tearDown(self):
        self.app._stop_running()
        self.app.cancel_pending()
        self.root.destroy()
        self.assertEqual(self.errors, [], "hubo excepciones dentro de callbacks de Tk")

    # --- ayudas
    def pump(self, n=5):
        for _ in range(n):
            self.root.update()

    def pump_for(self, seconds):
        """Deja correr el bucle de eventos de Tk durante `seconds` segundos y vuelve.

        No se usa `root.update()` en un bucle con reloj: `update()` no vuelve mientras haya eventos
        pendientes, y un programa en ejecución se reprograma con after(1) en cada porción, así que en
        algunas plataformas (Windows con Tk 9) la llamada no termina hasta que alguien detiene el
        programa. Una espera con `wait_variable` + un temporizador sí vuelve a tiempo en todas.
        """
        listo = tk.BooleanVar(master=self.root, value=False)
        self.root.after(int(seconds * 1000), lambda: listo.set(True))
        self.root.wait_variable(listo)

    def why(self):
        """Estado interno para el mensaje de un assert que falla (ayuda a diagnosticar en otra plataforma)."""
        a, s = self.app, self.app.session
        m = s.machine
        return (f"running={a.running} state={s.state!r} message={s.message!r} count={getattr(m, 'count', None)} "
                f"stale={a.stale} barra={a.status_var.get()!r} errores_tk={self.errors!r}")

    def wait_stop(self, limit=20):
        t = time.time()
        while self.app.running and time.time() - t < limit:
            self.root.update()
            time.sleep(0.005)
        self.pump()
        self.assertFalse(self.app.running, "el programa no terminó a tiempo")

    def set_source(self, text):
        self.ed.text.delete("1.0", "end")
        self.ed.text.insert("1.0", text)
        self.pump()

    def console(self):
        return self.app.console.text.get("1.0", "end-1c")

    def reg(self, name):
        return self.app.regs.hex[name].cget("text")


class TestBasics(GuiCase):
    def test_starts_with_example_tab_and_no_program(self):
        a = self.app
        self.assertEqual([e.name for e in a.editors], ["ejemplo.asm"])
        self.assertEqual(a.session.state, "empty")
        self.assertTrue(a.btn["stop"].instate(["disabled"]))
        self.assertTrue(a.btn["run"].instate(["!disabled"]))
        self.assertIn("Sin programa", a.mem.text.get("1.0", "end"))

    def test_assemble_shows_summary_listing_and_symbols(self):
        a = self.app
        self.assertTrue(a.assemble())
        self.assertIn("Ensamblado sin errores", a.messages.text.get("1.0", "end"))
        self.assertIn("EJEMPLO", a.messages.text.get("1.0", "end"))
        self.assertIn("LEA", a.listing.text.get("1.0", "end"))
        self.assertIn("EJEMPLO-LAZO", a.symbols.text.get("1.0", "end"))
        self.assertEqual(self.reg("PC"), "x3000")
        self.assertEqual(self.ed.pc_line, 3)                 # primera instrucción

    def test_syntax_colors_are_applied(self):
        self.ed.rehighlight()
        starts = [str(r) for r in self.ed.text.tag_ranges("mnemonic")]
        self.assertIn("3.8", starts)                         # MOVI en la línea 3, columna 8
        self.assertTrue(self.ed.text.tag_ranges("comment"))
        self.assertTrue(self.ed.text.tag_ranges("label_def"))

    def test_run_example_to_the_end(self):
        a = self.app
        a.cmd_run()
        self.wait_stop()
        self.assertEqual(a.session.state, "halted")
        self.assertIn("Hola LC10", self.console())
        self.assertIn("Programa terminado: 92 instrucciones (21 usuario + 71 SO)", self.console())
        self.assertEqual(self.reg("R1"), "x000F")            # 5+4+3+2+1
        self.assertIn("Terminó", a.status_var.get())
        self.assertEqual(a.counter_var.get(), "21 usuario + 71 SO = 92 instrucciones · 16 palabras · x3000–x301F")   # como la barra de la cátedra
        self.assertEqual(self.ed.pc_line, 11)                # el HALT
        self.assertTrue(a.btn["run"].instate(["!disabled"]))

    def test_running_again_after_the_end_restarts(self):
        a = self.app
        a.cmd_run(); self.wait_stop()
        a.cmd_run(); self.wait_stop()
        self.assertEqual(self.console().count("Hola LC10"), 1)   # la consola se limpió al reiniciar
        self.assertEqual(a.session.machine.user_count, 21)

    def test_reset_returns_to_first_instruction(self):
        a = self.app
        a.cmd_run(); self.wait_stop()
        a.cmd_reset()
        self.assertEqual(a.session.state, "ready")
        self.assertEqual(self.reg("PC"), "x3000")
        self.assertEqual(self.reg("R1"), "x0000")
        self.assertEqual(self.console(), "")
        self.assertEqual(self.ed.pc_line, 3)

    def test_step_highlights_changed_registers_and_flags(self):
        a = self.app
        a.cmd_step()                                          # ensambla y ejecuta MOVI R1, #0
        a.cmd_step()                                          # MOVI R2, #5
        self.assertEqual(a.regs.hex["R2"].cget("bg"), gui.T["changed"])
        self.assertEqual(a.regs.hex["R1"].cget("bg"), gui.T["panel"])
        self.assertEqual(a.regs.flags["P"].cget("highlightbackground"), gui.T["changed"])
        self.assertEqual(a.regs.flags["P"].cget("bg"), gui.T["flag_on"])
        self.assertEqual(self.reg("R2"), "x0005")
        self.assertEqual(self.ed.pc_line, 5)
        self.assertEqual(str(self.ed.text.tag_ranges("pcline")[0]), "5.0")
        self.assertTrue(a.regs.next.cget("text").startswith("ADD"))      # la instrucción que sigue

    def test_step_after_the_end_does_not_run(self):
        a = self.app
        a.cmd_run(); self.wait_stop()
        n = a.session.machine.count
        a.cmd_step()
        self.assertEqual(a.session.machine.count, n)
        self.assertIn("Reinicie", a.status_var.get())

    def test_exception_is_reported_in_console_and_status(self):
        self.set_source("        .ORIG x3000\n        MOVI R1, #1\n        JMP R1\n        .END\n")
        self.app.cmd_run(); self.wait_stop()
        self.assertEqual(self.app.session.state, "fault")
        self.assertIn("EXCEPCIÓN", self.console())
        self.assertIn("impar", self.app.status_var.get())
        self.assertEqual(self.ed.pc_line, 3)                 # la instrucción que falló


class TestBreakpoints(GuiCase):
    def test_only_lines_with_code_accept_a_breakpoint(self):
        self.ed.toggle_breakpoint(1)                         # comentario
        self.ed.toggle_breakpoint(2)                         # .ORIG: tiene "código" de ensamblador
        self.assertIn(2, self.ed.breakpoint_lines())
        self.ed.toggle_breakpoint(2)
        self.ed.toggle_breakpoint(15)                        # línea vacía
        self.assertEqual(self.ed.breakpoint_lines(), set())
        self.ed.toggle_breakpoint(8)
        self.assertEqual(self.ed.breakpoint_lines(), {8})
        self.ed.toggle_breakpoint(8)
        self.assertEqual(self.ed.breakpoint_lines(), set())

    def test_run_stops_before_the_line_and_continues(self):
        a = self.app
        self.ed.toggle_breakpoint(8)                         # ST R1, SUMA
        a.cmd_run(); self.wait_stop()
        self.assertEqual(a.session.state, "ready")
        self.assertEqual(self.ed.pc_line, 8)
        self.assertEqual(self.reg("R1"), "x000F")
        self.assertIn("Punto de parada", a.status_var.get())
        self.assertEqual(a.session.machine.mem[0x3012], 0)   # el ST todavía no se ejecutó
        a.cmd_run(); self.wait_stop()
        self.assertEqual(a.session.state, "halted")
        self.assertEqual(a.session.machine.mem[0x3012], 15)

    def test_breakpoint_moves_with_its_line(self):
        self.ed.toggle_breakpoint(8)
        self.ed.text.insert("3.0", "        NOP\n")
        self.pump()
        self.assertEqual(self.ed.breakpoint_lines(), {9})

    def test_changed_memory_is_highlighted_after_a_store(self):
        a = self.app
        self.ed.toggle_breakpoint(8)
        a.cmd_run(); self.wait_stop()
        a.cmd_step()                                          # ST R1, SUMA
        self.assertIn(0x3012, a.mem.last_changed)
        self.assertTrue(a.mem.text.tag_ranges("chg"))

    def test_clear_all_breakpoints(self):
        self.ed.toggle_breakpoint(5)
        self.ed.toggle_breakpoint(8)
        self.app.cmd_clear_bps()
        self.assertEqual(self.ed.breakpoint_lines(), set())

    def test_f9_style_toggle_uses_the_cursor_line(self):
        self.ed.text.mark_set("insert", "6.0")
        self.app.cmd_toggle_bp()
        self.assertEqual(self.ed.breakpoint_lines(), {6})


class TestErrorsAndStale(GuiCase):
    def test_assembly_error_marks_the_line_and_shows_a_link(self):
        a = self.app
        self.ed.text.insert("5.0", "        FOO R1\n")
        self.pump()
        self.assertFalse(a.assemble())
        self.assertEqual(str(self.ed.text.tag_ranges("errline")[0]), "5.0")
        msg = a.messages.text.get("1.0", "end")
        self.assertIn("Error de ensamblado", msg)
        self.assertIn("ejemplo.asm:5", msg)
        self.assertEqual(a.bottom.select(), str(a.messages))
        self.assertIn("Error", a.status_var.get())
        self.assertEqual(self.ed.text.index("insert"), "5.0")
        self.assertEqual(a.session.state, "empty")           # nada que ejecutar
        a.cmd_run()                                          # no ejecuta ni falla
        self.assertEqual(a.session.state, "empty")
        self.assertFalse(a.running)

    def test_fixing_the_error_clears_the_mark(self):
        a = self.app
        self.ed.text.insert("5.0", "        FOO R1\n")
        self.assertFalse(a.assemble())
        self.ed.text.delete("5.0", "6.0")
        self.pump()
        self.assertEqual(self.ed.text.tag_ranges("errline"), ())
        self.assertTrue(a.assemble())

    def test_error_without_line_number(self):
        self.set_source("        .ORIG x3000\n        HALT\n")        # falta .END
        self.assertFalse(self.app.assemble())
        self.assertIn("falta .END", self.app.messages.text.get("1.0", "end"))

    def test_editing_marks_stale_and_clears_the_pc_mark(self):
        a = self.app
        a.cmd_assemble()
        self.assertFalse(a.stale)
        self.assertEqual(self.ed.pc_line, 3)
        self.ed.text.insert("end", "; comentario\n")
        self.pump()
        self.assertTrue(a.stale)
        self.assertIsNone(self.ed.pc_line)
        self.assertEqual(self.ed.text.tag_ranges("pcline"), ())
        self.assertIn("●", a.notebook.tab(self.ed, "text"))

    def test_run_after_editing_reassembles(self):
        a = self.app
        a.cmd_assemble()
        self.ed.text.delete("4.0", "4.end")
        self.ed.text.insert("4.0", "        MOVI  R2, #2")
        self.pump()
        a.cmd_run(); self.wait_stop()
        self.assertEqual(self.reg("R1"), "x0003")            # 2 + 1


class TestRunControl(GuiCase):
    def test_stop_interrupts_an_infinite_loop(self):
        a = self.app
        self.set_source(INFINITO)
        a.cmd_run()
        self.pump_for(0.2)
        self.assertTrue(a.running, self.why())
        self.assertTrue(a.btn["run"].instate(["disabled"]))
        self.assertTrue(a.btn["stop"].instate(["!disabled"]))
        a.cmd_stop()
        self.assertFalse(a.running)
        self.assertEqual(a.session.state, "ready")
        self.assertGreater(a.session.machine.count, 100)
        self.assertIn("Detenido", a.status_var.get())
        self.assertTrue(a.btn["run"].instate(["!disabled"]))
        self.assertTrue(a.btn["stop"].instate(["disabled"]))
        a.cmd_step()                                          # se puede seguir paso a paso
        self.assertEqual(a.session.state, "ready")

    def test_run_stops_at_the_instruction_limit_and_f5_continues(self):
        a = self.app
        a.max_run = 5000
        self.set_source(INFINITO)
        a.cmd_run(); self.wait_stop()
        self.assertEqual(a.session.state, "ready")
        self.assertEqual(a.session.machine.count, 5000)
        self.assertIn("límite", a.status_var.get())
        self.assertIn("Detenido", self.console())
        self.assertTrue(a.btn["run"].instate(["!disabled"]))
        a.cmd_run(); self.wait_stop()                          # F5 sigue otro tanto
        self.assertEqual(a.session.machine.count, 10000)
        a.max_run = 0                                          # sin límite: sigue hasta que se lo detiene
        a.cmd_run()
        self.pump_for(0.1)
        self.assertTrue(a.running, self.why())
        a.cmd_stop()
        self.assertGreater(a.session.machine.count, 10000)

    def test_the_limit_has_a_default_and_can_be_changed_from_the_menu(self):
        a = self.app
        self.assertEqual(a.max_run, gui.MAX_RUN_DEFAULT)
        with mock.patch.object(gui.simpledialog, "askinteger", return_value=123) as ask:
            a.cmd_set_limit()
        self.assertEqual(a.max_run, 123)
        self.assertEqual(ask.call_args.kwargs["initialvalue"], gui.MAX_RUN_DEFAULT)
        with mock.patch.object(gui.simpledialog, "askinteger", return_value=None):
            a.cmd_set_limit()                                  # Cancelar no cambia nada
        self.assertEqual(a.max_run, 123)
        with mock.patch.object(gui.simpledialog, "askinteger", return_value=0):
            a.cmd_set_limit()
        self.assertEqual(a.max_run, 0)
        self.assertIn("Sin límite", a.status_var.get())

    def test_getc_reads_the_input_box(self):
        a = self.app
        self.set_source(ECO)
        a.input_var.set("hi")
        a.cmd_run(); self.wait_stop()
        self.assertIn("hi", self.console())

    def test_input_escapes(self):
        a = self.app
        self.set_source(ECO)
        a.input_var.set("a\\n")
        a.cmd_run(); self.wait_stop()
        self.assertTrue(self.console().startswith("a\n"))

    def test_reset_applies_the_new_input(self):
        a = self.app
        self.set_source(ECO)
        a.input_var.set("xy")
        a.cmd_run(); self.wait_stop()
        a.input_var.set("pq")
        a.cmd_reset()
        a.cmd_run(); self.wait_stop()
        self.assertIn("pq", self.console())

    def test_lots_of_output_is_trimmed(self):
        v = gui.Viewer(self.root, self.app.mono)
        for _ in range(200):
            v.append("x" * 100 + "\n", max_chars=1000)
        content = v.text.get("1.0", "end-1c")
        self.assertLessEqual(len(content), 1000)
        self.assertTrue(content.endswith("x" * 100 + "\n"))      # lo último se conserva
        self.assertTrue(content.startswith("x"))                 # y no queda una línea cortada


class TestMemoryPanel(GuiCase):
    def test_go_to_label_and_words_mode(self):
        a = self.app
        a.assemble()
        a.mem.addr_var.set("MSG")
        a.mem.go()
        self.assertEqual(a.mem.base, 0x3010)
        self.assertFalse(a.mem.follow.get())
        text = a.mem.text.get("1.0", "end")
        self.assertTrue(text.startswith("x3010"))
        self.assertIn("Hola", text)
        a.mem.mode.set("Palabras")
        a.mem.render()
        first = a.mem.text.get("1.0", "1.end")
        self.assertRegex(first, r"^x3010  [0-9A-F]{4} [0-9A-F]{4}  [0-9A-F]{4} [0-9A-F]{4}  ")

    def test_numbers_symbols_and_bad_addresses(self):
        a = self.app
        a.assemble()
        self.assertEqual(a.resolve_address("x3014"), 0x3014)
        self.assertEqual(a.resolve_address("12308"), 0x3014)
        self.assertEqual(a.resolve_address("lazo"), a.session.asm.symbols["EJEMPLO-LAZO"])
        self.assertEqual(a.resolve_address("EJEMPLO-MSG"), 0x3014)
        for bad in ("", "zzz", "NOEXISTE"):
            with self.assertRaises(ValueError):
                a.resolve_address(bad)
        a.mem.addr_var.set("zzz")
        a.mem.go()
        self.assertIn("No es un número", a.status_var.get())

    def test_pc_button_follows_the_program_counter(self):
        a = self.app
        a.assemble()
        a.mem.addr_var.set("x4000")
        a.mem.go()
        self.assertEqual(a.mem.base, 0x4000)
        a.mem.go_pc()
        self.assertTrue(a.mem.follow.get())
        self.assertTrue(a.mem.base <= a.session.machine.pc < a.mem.base + a.mem.window)

    def test_paging_stays_inside_memory(self):
        a = self.app
        a.assemble()
        a.mem.set_base(0)
        a.mem.page(-1)
        self.assertEqual(a.mem.base, 0)
        a.mem.set_base(0xFFFF)
        self.assertEqual(a.mem.base, 0x10000 - a.mem.window)
        a.mem.page(1)
        self.assertEqual(a.mem.base, 0x10000 - a.mem.window)
        self.assertIn("xFFF8", a.mem.text.get("1.0", "end"))


class TestFiles(GuiCase):
    def test_export_image_and_simulate_it_without_the_source(self):
        a = self.app
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "p.hex"
            with mock.patch.object(gui.filedialog, "asksaveasfilename", return_value=str(path)):
                a.cmd_export()
            self.assertTrue(path.exists())
            self.assertIn("Imagen guardada", a.status_var.get())
            self.assertTrue(a.load_image_path(path))
            self.assertEqual(a.origin, "image")
            self.assertIn("LEA", a.listing.text.get("1.0", "end"))      # desensamblado
            self.ed.text.insert("end", "; editar no debe reemplazar la imagen\n")
            a.cmd_run(); self.wait_stop()
            self.assertEqual(a.session.state, "halted")
            self.assertIn("Hola LC10", self.console())
            self.assertEqual(self.reg("R1"), "x000F")
            a.cmd_step()                                      # ya terminó
            self.assertIn("Reinicie", a.status_var.get())

    def test_export_all_formats(self):
        a = self.app
        with tempfile.TemporaryDirectory() as d:
            for fmt in ("hex", "bin", "dec", "bits"):
                path = Path(d) / f"p.{fmt}"
                with mock.patch.object(gui.filedialog, "asksaveasfilename", return_value=str(path)):
                    a.cmd_export()
                self.assertTrue(a.load_image_path(path), fmt)
                a.cmd_run(); self.wait_stop()
                self.assertEqual(a.session.state, "halted", fmt)

    def test_export_with_unknown_extension_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(gui.filedialog, "asksaveasfilename", return_value=str(Path(d) / "p.txt")):
                self.app.cmd_export()
            self.assertFalse((Path(d) / "p.txt").exists())
            self.boxes["showerror"].assert_called()

    def test_invalid_image_file_shows_an_error(self):
        with tempfile.TemporaryDirectory() as d:
            bad = Path(d) / "malo.hex"
            bad.write_text("esto no es una imagen\n")
            self.assertFalse(self.app.load_image_path(bad))
            self.boxes["showerror"].assert_called()
            self.assertEqual(self.app.session.state, "empty")

    def test_save_renames_the_tab_and_clears_modified(self):
        a = self.app
        self.ed.text.insert("end", "; cambio\n")
        self.pump()
        self.assertTrue(self.ed.modified)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "prog.asm"
            with mock.patch.object(gui.filedialog, "asksaveasfilename", return_value=str(path)):
                a.cmd_save()
            self.assertEqual(path.read_text(encoding="utf-8"), self.ed.get_text())
            self.assertEqual(self.ed.name, "prog.asm")
            self.assertFalse(self.ed.modified)
            self.assertEqual(a.notebook.tab(self.ed, "text"), "prog.asm")
            a.cmd_save()                                      # ya tiene ruta: no vuelve a preguntar
            a.open_paths([path])                              # no abre un duplicado
            self.assertEqual(len(a.editors), 1)

    def test_open_adds_tabs_and_reports_unreadable_files(self):
        a = self.app
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "otro.asm"
            p.write_text("        .END\n", encoding="utf-8")
            a.open_paths([p, Path(d) / "no_existe.asm"])
            self.assertEqual([e.name for e in a.editors], ["ejemplo.asm", "otro.asm"])
            self.boxes["showerror"].assert_called()


class TestTabsAndModules(GuiCase):
    def test_new_module_and_main_marker(self):
        a = self.app
        a.cmd_new()
        self.assertEqual([e.name for e in a.editors], ["ejemplo.asm", "modulo.asm"])
        self.assertEqual([a.tab_title(e) for e in a.editors], ["★ ejemplo.asm", "modulo.asm"])
        a.cmd_make_main()                                     # la pestaña actual es la nueva
        self.assertEqual([a.tab_title(e) for e in a.editors], ["ejemplo.asm", "★ modulo.asm"])
        self.assertEqual([n for n, _ in a.sources()], ["modulo.asm", "ejemplo.asm"])   # el principal va primero

    def test_unique_names(self):
        a = self.app
        a.cmd_new(); a.cmd_new()
        self.assertEqual([e.name for e in a.editors], ["ejemplo.asm", "modulo.asm", "modulo2.asm"])

    def test_closing_a_modified_tab_asks_first(self):
        a = self.app
        a.cmd_new()
        extra = a.current_editor()
        extra.text.insert("end", "; x\n")
        self.pump()
        self.boxes["askyesnocancel"].return_value = None     # cancelar
        self.assertFalse(a.close_editor(extra))
        self.assertEqual(len(a.editors), 2)
        self.boxes["askyesnocancel"].return_value = False    # no guardar
        self.assertTrue(a.close_editor(extra))
        self.assertEqual(len(a.editors), 1)

    def test_closing_the_main_tab_promotes_another(self):
        a = self.app
        a.cmd_new()
        a.close_editor(self.ed, ask=False)
        self.assertEqual([e.name for e in a.editors], ["modulo.asm"])
        self.assertIs(a.main_editor, a.editors[0])

    def test_division_example_runs_with_two_modules(self):
        a = self.app
        a.open_division_example()
        self.assertEqual([e.name for e in a.editors], ["main_division.asm", "division.asm"])
        self.assertIs(a.main_editor, a.editors[0])
        a.cmd_run(); self.wait_stop()
        self.assertEqual(a.session.state, "halted")
        self.assertEqual(self.reg("R0"), "x02C0")             # 5,5 / 2 = 2,75 en Q7.8
        self.assertEqual(a.session.machine.user_count, 151)
        self.assertIn("DIVISION-DIV_LONG", a.symbols.text.get("1.0", "end"))

    def test_breakpoint_inside_a_module_selects_its_tab(self):
        a = self.app
        a.open_division_example()
        mod = a.editor_by_name("division.asm")
        line = next(i for i, t in enumerate(mod.get_text().split("\n"), 1) if t.strip().startswith("LAZO"))
        mod.toggle_breakpoint(line)
        a.cmd_run(); self.wait_stop()
        self.assertEqual(a.current_editor(), mod)
        self.assertEqual(mod.pc_line, line)
        self.assertIn("division.asm", a.status_var.get())

    def test_error_in_a_module_opens_that_tab(self):
        a = self.app
        a.open_division_example()
        mod = a.editor_by_name("division.asm")
        mod.text.insert("5.0", "        FOO R1\n")
        a.notebook.select(a.editors[0])
        self.assertFalse(a.assemble())
        self.assertEqual(a.current_editor(), mod)
        self.assertEqual(str(mod.text.tag_ranges("errline")[0]), "5.0")


class TestFileNavigation(GuiCase):
    """Orientarse con muchos archivos abiertos: franja con el nombre, ◀ ▶, Ctrl+Tab y lista lateral."""

    def many(self, n=6):
        """Deja abiertos ejemplo.asm (principal) y mod1.asm ... modN.asm."""
        a = self.app
        for i in range(1, n + 1):
            a.new_editor(f"mod{i}.asm", "        .END\n")
        self.pump()
        return a

    def go(self, name):
        a = self.app
        a.notebook.select(a.editor_by_name(name))
        self.pump()

    def list_labels(self):
        return list(self.app.file_list.get(0, "end"))

    # --- franja
    def test_single_file_shows_only_its_name(self):
        a = self.app
        self.assertEqual(a.file_name_var.get(), "ejemplo.asm")
        self.assertEqual(a.file_info_var.get(), "")
        self.assertTrue(a.btn_prev.instate(["disabled"]) and a.btn_next.instate(["disabled"]))
        self.assertEqual(self.root.title(), "ejemplo.asm — LC10 · Grupo 10")

    def test_bar_shows_name_position_and_neighbours(self):
        a = self.many()                                       # 7 archivos
        self.go("mod3.asm")
        self.assertEqual(a.file_name_var.get(), "mod3.asm")
        self.assertEqual(a.file_info_var.get(), "módulo · 4 de 7")
        self.assertIn("mod2.asm", a.btn_prev.cget("text"))
        self.assertIn("mod4.asm", a.btn_next.cget("text"))
        self.assertEqual(self.root.title(), "mod3.asm (4 de 7) — LC10 · Grupo 10")
        self.assertTrue(a.btn_prev.instate(["!disabled"]) and a.btn_next.instate(["!disabled"]))

    def test_the_neighbours_wrap_around_at_the_ends(self):
        a = self.many()
        self.go("ejemplo.asm")
        self.assertEqual(a.file_name_var.get(), "★ ejemplo.asm")
        self.assertEqual(a.file_info_var.get(), "programa principal · 1 de 7")
        self.assertIn("mod6.asm", a.btn_prev.cget("text"))     # antes del primero va el último
        self.go("mod6.asm")
        self.assertIn("ejemplo.asm", a.btn_next.cget("text"))  # después del último va el primero

    def test_long_names_are_shortened_in_the_buttons_only(self):
        a = self.app
        a.new_editor("un_nombre_larguisimo_de_modulo_para_probar.asm")
        self.pump()
        self.go("ejemplo.asm")
        self.assertIn("…", a.btn_next.cget("text"))
        self.assertLessEqual(len(a.btn_next.cget("text")), gui.NAME_SHORT + 6)
        self.go("un_nombre_larguisimo_de_modulo_para_probar.asm")
        self.assertEqual(a.file_name_var.get(), "un_nombre_larguisimo_de_modulo_para_probar.asm")   # completo

    def test_modified_mark_follows_the_current_file(self):
        a = self.many(2)
        self.go("mod1.asm")
        a.current_editor().text.insert("end", "; x\n")
        self.pump()
        self.assertEqual(a.file_name_var.get(), "mod1.asm ●")
        self.assertIn("mod1.asm ●", self.list_labels())

    def test_buttons_move_to_the_neighbours(self):
        a = self.many()
        self.go("mod3.asm")
        a.btn_next.invoke(); self.pump()
        self.assertEqual(a.current_editor().name, "mod4.asm")
        a.btn_prev.invoke(); a.btn_prev.invoke(); self.pump()
        self.assertEqual(a.current_editor().name, "mod2.asm")
        self.assertEqual(a.file_info_var.get(), "módulo · 3 de 7")

    def test_stepping_wraps_and_moves_the_keyboard_focus(self):
        a = self.many(2)
        self.go("ejemplo.asm")
        a.current_editor().text.focus_force(); self.pump()
        a.cmd_file_step(-1); self.pump()
        last = a.current_editor()
        self.assertEqual(last.name, "mod2.asm")
        self.assertIs(self.root.focus_get(), last.text)        # lo que se escriba va al archivo a la vista
        a.cmd_file_step(1); self.pump()
        self.assertEqual(a.current_editor().name, "ejemplo.asm")

    def test_ctrl_tab_changes_file_and_does_not_type_a_tab(self):
        a = self.many(2)
        self.go("ejemplo.asm")
        before = self.ed.get_text()
        self.ed.text.focus_force(); self.pump()
        self.ed.text.event_generate("<Control-Tab>"); self.pump()
        self.assertEqual(a.current_editor().name, "mod1.asm")
        self.assertEqual(self.ed.get_text(), before)
        self.assertFalse(self.ed.modified)
        a.current_editor().text.event_generate("<Control-Shift-Tab>"); self.pump()
        self.assertEqual(a.current_editor().name, "ejemplo.asm")
        a.current_editor().text.event_generate("<Control-Next>"); self.pump()
        self.assertEqual(a.current_editor().name, "mod1.asm")
        a.current_editor().text.event_generate("<Control-Prior>"); self.pump()
        self.assertEqual(a.current_editor().name, "ejemplo.asm")

    def test_bar_follows_close_main_change_and_rename(self):
        a = self.many(3)
        self.go("mod2.asm")
        a.cmd_make_main()
        self.pump()
        self.assertEqual(a.file_name_var.get(), "★ mod2.asm")
        self.assertEqual(a.file_info_var.get(), "programa principal · 3 de 4")
        a.close_editor(a.editor_by_name("mod1.asm"), ask=False)
        self.pump()
        self.assertEqual(a.file_info_var.get(), "programa principal · 2 de 3")
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "renombrado.asm"
            with mock.patch.object(gui.filedialog, "asksaveasfilename", return_value=str(path)):
                a.cmd_save()
            self.pump()
            self.assertEqual(a.file_name_var.get(), "★ renombrado.asm")
            self.assertIn("★ renombrado.asm", self.list_labels())
            self.assertIn("renombrado.asm", self.root.title())

    # --- lista lateral
    def test_files_panel_is_hidden_at_first_and_toggles(self):
        a = self.app
        self.assertFalse(a._files_shown)
        self.assertFalse(a.files_panel.winfo_ismapped())
        a.toggle_files_panel(); self.pump()
        self.assertTrue(a._files_shown and a.files_panel.winfo_ismapped())
        self.assertTrue(a.show_files.get())
        a.toggle_files_panel(); self.pump()
        self.assertFalse(a.files_panel.winfo_ismapped())
        self.assertFalse(a.show_files.get())

    def test_ctrl_b_toggles_the_panel(self):
        a = self.app
        self.ed.text.focus_force(); self.pump()
        self.ed.text.event_generate("<Control-b>"); self.pump()
        self.assertTrue(a._files_shown)
        self.ed.text.event_generate("<Control-b>"); self.pump()
        self.assertFalse(a._files_shown)

    def test_panel_shows_by_itself_with_many_files_but_only_once(self):
        a = self.app
        for i in range(1, gui.AUTO_LIST_FROM):                # 4 archivos en total: todavía no
            a.new_editor(f"mod{i}.asm")
        self.assertFalse(a._files_shown)
        a.new_editor("mod9.asm")                              # el quinto
        self.pump()
        self.assertTrue(a._files_shown and a.files_panel.winfo_ismapped())
        a.set_files_panel(False)                              # el usuario la oculta: no vuelve sola
        a.new_editor("mod10.asm")
        self.assertFalse(a._files_shown)

    def test_list_has_every_file_and_marks_the_current_one(self):
        a = self.many()
        a.set_files_panel(True); self.pump()
        self.assertEqual(self.list_labels(), ["★ ejemplo.asm"] + [f"mod{i}.asm" for i in range(1, 7)])
        self.assertEqual(a.files_head_var.get(), "ARCHIVOS · 7")
        self.go("mod4.asm")
        self.assertEqual(a.file_list.curselection(), (4,))
        self.go("ejemplo.asm")
        self.assertEqual(a.file_list.curselection(), (0,))

    def test_clicking_a_file_in_the_list_opens_it(self):
        a = self.many()
        a.set_files_panel(True); self.pump()
        a.file_list.selection_clear(0, "end")
        a.file_list.selection_set(3)
        a.file_list.event_generate("<<ListboxSelect>>"); self.pump()
        self.assertEqual(a.current_editor().name, "mod3.asm")
        self.assertEqual(a.file_name_var.get(), "mod3.asm")

    def test_filter_narrows_the_list_and_enter_opens_the_first_match(self):
        a = self.many(12)
        a.set_files_panel(True); self.pump()
        a.file_filter.set("MOD1"); self.pump()                # sin distinguir mayúsculas
        self.assertEqual(self.list_labels(), ["mod1.asm", "mod10.asm", "mod11.asm", "mod12.asm"])
        self.assertEqual(a.files_head_var.get(), "ARCHIVOS · 4 de 13")
        a.file_filter.set("mod11"); self.pump()
        a._on_filter_enter(); self.pump()
        self.assertEqual(a.current_editor().name, "mod11.asm")
        self.assertEqual(a.file_list.curselection(), (0,))
        a.file_filter.set("nada"); self.pump()
        self.assertEqual(a.file_list.size(), 0)
        a.file_filter.set(""); self.pump()
        self.assertEqual(a.file_list.size(), 13)
        self.assertEqual(a.files_head_var.get(), "ARCHIVOS · 13")

    def test_the_list_follows_closing_and_opening(self):
        a = self.many(3)
        a.set_files_panel(True); self.pump()
        a.close_editor(a.editor_by_name("mod2.asm"), ask=False); self.pump()
        self.assertEqual(self.list_labels(), ["★ ejemplo.asm", "mod1.asm", "mod3.asm"])
        a.new_editor("nuevo.asm"); self.pump()
        self.assertEqual(self.list_labels()[-1], "nuevo.asm")
        self.assertEqual(a.file_list.curselection(), (3,))

    def test_whole_benchmark_from_the_window(self):
        """Lo que hace el usuario: abrir los 38 archivos de asm/opt10, elegir el principal y ejecutar."""
        a = self.app
        a.close_editor(self.ed, ask=False)
        files = sorted((ROOT / "asm" / "opt10").glob("*.asm"), key=lambda p: p.name.lower())
        self.assertEqual(len(files), 38)
        a.open_paths(files); self.pump()
        self.assertEqual(len(a.editors), 38)
        self.assertTrue(a._files_shown)                       # con tantos archivos la lista aparece sola
        self.assertEqual(a.file_list.size(), 38)
        a.notebook.select(a.editor_by_name("main_grupo27.asm"))
        a.cmd_make_main(); self.pump()
        self.assertEqual(a.file_info_var.get(), "programa principal · 38 de 38")
        a.cmd_run(); self.wait_stop()
        self.assertEqual(a.session.state, "halted", self.why())
        self.assertEqual(a.session.machine.user_count, 15822)
        self.assertEqual(a.counter_var.get(), "15.822 usuario + 10.901 SO = 26.723 instrucciones · 4963 palabras · x3000–x56C5")


CONTADOR = """\
        .ORIG x3000
        MOVI R1, #0
LAZO    ADD  R1, R1, #1
        BR   LAZO
        .END
"""
TRES_VUELTAS = """\
        .ORIG x3000
        MOVI R1, #3
LAZO    ADD  R1, R1, #-1        ; línea 3
        BRp  LAZO
        HALT
        .END
"""


class MenuCase(GuiCase):
    def submenu(self, *path):
        """Menú de la ventana al que se llega por los nombres de `path` (por ejemplo 'Programa', 'Velocidad de ejecución')."""
        menu = self.root.nametowidget(self.root.cget("menu"))
        for name in path:
            for i in range(menu.index("end") + 1):
                if menu.type(i) == "cascade" and menu.entrycget(i, "label") == name:
                    menu = menu.nametowidget(menu.entrycget(i, "menu"))
                    break
            else:
                self.fail(f"no hay un menú «{name}»")
        return menu

    def labels(self, menu):
        return [menu.entrycget(i, "label") for i in range(menu.index("end") + 1) if menu.type(i) != "separator"]


class TestOpenBenchmark(MenuCase):
    def test_menu_has_the_option(self):
        self.assertIn("Abrir benchmark", self.labels(self.submenu("Archivo")))

    def test_opens_main_first_as_principal_and_every_module(self):
        a = self.app
        a.cmd_open_benchmark(); self.pump()
        names = [e.name for e in a.editors]
        self.assertEqual(len(names), 38)
        self.assertEqual(names[0], "main_grupo27.asm")
        self.assertEqual(sorted(names[1:], key=str.lower), names[1:])          # los módulos, en orden
        self.assertNotIn("ejemplo.asm", names)                                   # reemplaza lo que había
        self.assertIs(a.main_editor, a.editors[0])
        self.assertIs(a.current_editor(), a.main_editor)
        self.assertEqual(a.file_name_var.get(), "★ main_grupo27.asm")
        self.assertEqual(a.file_info_var.get(), "programa principal · 1 de 38")
        self.assertTrue(a._files_shown)                                          # con tantos archivos aparece la lista
        self.assertIn("37 módulos", a.status_var.get())

    def test_it_is_ready_to_run_without_opening_anything_else(self):
        a = self.app
        a.cmd_open_benchmark(); self.pump()
        self.assertTrue(a.stale)                                                 # todavía no se ensambló
        self.assertTrue(a.assemble())
        self.assertEqual(len(a.session.asm.modules), 38)
        a.cmd_run(); self.wait_stop()
        self.assertEqual(a.session.state, "halted", self.why())
        self.assertEqual(a.session.machine.user_count, 15822)
        self.assertEqual(a.counter_var.get(), "15.822 usuario + 10.901 SO = 26.723 instrucciones · 4963 palabras · x3000–x56C5")
        self.assertIn("==MAXIMO COMUN DIVISOR==", self.console())

    def test_f5_alone_assembles_and_runs_it(self):
        a = self.app
        a.cmd_open_benchmark(); self.pump()
        a.cmd_run(); self.wait_stop()
        self.assertEqual(a.session.machine.user_count, 15822, self.why())

    def test_refuses_to_replace_unsaved_changes(self):
        a = self.app
        self.set_source("        .ORIG x3000\n        HALT\n        .END\n")
        self.assertTrue(self.ed.modified)
        a.cmd_open_benchmark(); self.pump()
        self.boxes["showinfo"].assert_called()
        self.assertEqual([e.name for e in a.editors], ["ejemplo.asm"])

    def test_missing_folder_is_reported(self):
        a = self.app
        with tempfile.TemporaryDirectory() as d, mock.patch.object(gui, "BENCHMARK_DIR", Path(d)):
            a.cmd_open_benchmark()
        self.boxes["showinfo"].assert_called()
        self.assertEqual([e.name for e in a.editors], ["ejemplo.asm"])

    def test_opening_it_twice_does_not_duplicate_files(self):
        a = self.app
        a.cmd_open_benchmark(); a.cmd_open_benchmark(); self.pump()
        self.assertEqual(len(a.editors), 38)
        self.assertEqual(a.editors[0].name, "main_grupo27.asm")


class TestSpeedLimit(MenuCase):
    def go(self, source, rate, seconds):
        """Ejecuta `source` a `rate` instrucciones por segundo durante `seconds` y devuelve (instrucciones, segundos reales)."""
        a = self.app
        self.set_source(source)
        a.speed.set(rate)
        t0 = time.perf_counter()
        a.cmd_run()
        self.pump_for(seconds)
        running = a.running
        a.cmd_stop()
        return a.session.machine.count, time.perf_counter() - t0, running

    def test_menu_offers_the_five_speeds_and_no_limit(self):
        menu = self.submenu("Programa", "Velocidad de ejecución")
        self.assertEqual(self.labels(menu), [
            "Sin límite (lo más rápido posible)",
            "100 instrucciones por segundo como máximo",
            "1.000 instrucciones por segundo como máximo",
            "2.000 instrucciones por segundo como máximo",
            "5.000 instrucciones por segundo como máximo",
            "10.000 instrucciones por segundo como máximo"])
        self.assertEqual(gui.SPEEDS, (0, 100, 1000, 2000, 5000, 10000))
        self.assertEqual(self.app.speed.get(), 0)                                # por defecto, sin límite

    def test_choosing_an_entry_sets_the_speed(self):
        a = self.app
        menu = self.submenu("Programa", "Velocidad de ejecución")
        menu.invoke(3)                                                           # 2.000
        self.assertEqual(a.speed.get(), 2000)
        self.assertIn("2.000", a.status_var.get())
        menu.invoke(0)
        self.assertEqual(a.speed.get(), 0)

    def test_without_limit_it_runs_as_fast_as_it_can(self):
        count, _, running = self.go(CONTADOR, 0, 0.3)
        self.assertTrue(running)
        self.assertGreater(count, 5000)

    def test_each_speed_is_a_maximum_and_is_close_to_it(self):
        for rate, seconds in ((100, 0.8), (1000, 0.6), (5000, 0.5)):
            with self.subTest(rate=rate):
                a = self.app
                a.cmd_reset() if a.session.state != "empty" else None
                count, elapsed, running = self.go(CONTADOR, rate, seconds)
                self.assertTrue(running)
                burst = max(1.0, rate * gui.BURST_S)
                self.assertLessEqual(count, rate * elapsed + burst + 2, f"{count} instrucciones en {elapsed:.2f} s")
                self.assertGreaterEqual(count, 0.3 * rate * seconds, f"{count} instrucciones en {elapsed:.2f} s")

    def test_a_limited_run_shows_the_program_moving(self):
        a = self.app
        self.set_source(CONTADOR)
        a.speed.set(1000)
        a.cmd_run()
        self.pump_for(0.3)
        self.assertTrue(a.running)
        self.assertIn("1.000 instrucciones por segundo", a.status_var.get())
        self.assertNotEqual(self.reg("R1"), "x0000")                             # los registros se ven cambiar
        self.assertIsNotNone(self.ed.pc_line)                                    # y la línea actual se marca
        self.assertIn(self.ed.pc_line, (3, 4))
        a.cmd_stop()
        self.assertFalse(a.running)
        self.assertIn("Detenido", a.status_var.get())

    def test_the_speed_can_change_while_running(self):
        a = self.app
        self.set_source(CONTADOR)
        a.speed.set(100)
        a.cmd_run()
        self.pump_for(0.3)
        slow = a.session.machine.count
        self.assertLess(slow, 100)
        a.speed.set(10000)
        a.on_speed_changed()
        self.assertIn("10.000", a.status_var.get())
        self.pump_for(0.3)
        self.assertGreater(a.session.machine.count, slow + 300)
        a.speed.set(0)
        a.on_speed_changed()
        self.pump_for(0.2)
        self.assertGreater(a.session.machine.count, slow + 5000)
        a.cmd_stop()

    def test_a_limited_run_ends_with_the_same_result(self):
        a = self.app
        a.cmd_run(); self.wait_stop()
        exact = (a.session.machine.count, self.console(), self.reg("R0"))
        self.assertEqual(a.session.state, "halted")
        a.cmd_reset()
        a.speed.set(10000)
        a.cmd_run(); self.wait_stop()
        self.assertEqual(a.session.state, "halted", self.why())
        self.assertEqual((a.session.machine.count, self.console(), self.reg("R0")), exact)

    def test_breakpoints_still_stop_a_limited_run_every_time(self):
        a = self.app
        self.set_source(TRES_VUELTAS)
        self.ed.toggle_breakpoint(3)
        a.speed.set(1000)
        for r1 in ("x0003", "x0002", "x0001"):                                   # antes de cada vuelta del lazo
            a.cmd_run(); self.wait_stop()
            self.assertEqual(a.session.state, "ready", self.why())
            self.assertEqual(self.ed.pc_line, 3)
            self.assertEqual(self.reg("R1"), r1)
        a.cmd_run(); self.wait_stop()
        self.assertEqual(a.session.state, "halted", self.why())

    def test_the_instruction_limit_still_applies_when_limited(self):
        a = self.app
        self.set_source(INFINITO)
        a.max_run = 200
        a.speed.set(10000)
        a.cmd_run(); self.wait_stop()
        self.assertEqual(a.session.machine.count, 200)
        self.assertIn("límite", a.status_var.get().lower())

    def test_pc_follows_the_run_through_different_files(self):
        a = self.app
        a.open_division_example(); self.pump()
        a.speed.set(2000)
        a.cmd_run()
        seen = set()
        t0 = time.time()
        while a.running and time.time() - t0 < 10:
            self.pump_for(0.02)
            seen.add(a.current_editor().name)
        self.assertEqual(a.session.state, "halted", self.why())
        self.assertEqual(seen, {"main_division.asm", "division.asm"})            # la ventana acompaña a la ejecución
        self.assertEqual(a.session.machine.user_count, 151)


@unittest.skipUnless(gui is not None, "sin tkinter")
class TestShortName(unittest.TestCase):
    def test_short_name(self):
        self.assertEqual(gui.short_name("abc.asm"), "abc.asm")
        self.assertEqual(gui.short_name("x" * 20), "x" * 20)
        self.assertEqual(gui.short_name("x" * 30), "x" * 19 + "…")
        self.assertEqual(len(gui.short_name("x" * 30)), gui.NAME_SHORT)


class TestEditorBehaviour(GuiCase):
    def test_return_keeps_indentation(self):
        self.set_source("        ADD R1, R1, R2")
        self.ed.text.mark_set("insert", "end-1c")
        self.ed._on_return(None)
        self.assertEqual(self.ed.get_text(), "        ADD R1, R1, R2\n        ")

    def test_tab_goes_to_the_next_multiple_of_8(self):
        self.set_source("AB")
        self.ed.text.mark_set("insert", "end-1c")
        self.ed._on_tab(None)
        self.assertEqual(self.ed.get_text(), "AB      ")
        self.ed._on_tab(None)
        self.assertEqual(self.ed.get_text(), "AB              ")

    def test_zoom_changes_the_code_font(self):
        a = self.app
        size = a.mono.cget("size")
        a.zoom(1)
        self.assertEqual(a.mono.cget("size"), size + 1)
        a.zoom(-30)
        self.assertEqual(a.mono.cget("size"), 7)

    def test_keyboard_shortcuts(self):
        a = self.app
        self.ed.text.focus_force()
        self.pump()
        self.ed.text.event_generate("<F7>")
        self.pump()
        self.assertEqual(a.session.state, "ready")
        self.ed.text.event_generate("<F10>")
        self.pump()
        self.assertEqual(a.session.machine.count, 1)
        self.ed.text.mark_set("insert", "8.0")
        self.ed.text.event_generate("<F9>")
        self.pump()
        self.assertEqual(self.ed.breakpoint_lines(), {8})
        self.ed.text.event_generate("<F5>")
        self.wait_stop()
        self.assertEqual(a.session.state, "ready")            # paró en el punto de parada
        self.ed.text.event_generate("<F6>")
        self.pump()
        self.assertEqual(a.session.machine.count, 0)

    def test_shift_f5_stops_a_running_program(self):
        a = self.app
        self.set_source(INFINITO)
        self.ed.text.focus_force()
        self.pump()
        self.ed.text.event_generate("<F5>")
        self.pump_for(0.1)
        self.assertTrue(a.running, self.why())
        self.ed.text.event_generate("<Shift-F5>")
        self.pump()
        self.assertFalse(a.running)
        self.assertEqual(a.session.state, "ready")

    def test_with_no_tabs_left_assembling_reports_an_error_and_new_starts_a_program(self):
        a = self.app
        a.close_editor(self.ed, ask=False)
        self.assertEqual(a.editors, [])
        self.assertIsNone(a.current_editor())
        self.assertFalse(a.assemble())
        self.assertIn("no hay archivos", a.messages.text.get("1.0", "end"))
        a.cmd_run(); a.cmd_step(); a.cmd_reset()               # no deben fallar
        a.cmd_new()
        self.assertEqual([e.name for e in a.editors], ["sin_titulo.asm"])
        self.assertIs(a.main_editor, a.editors[0])
        self.assertTrue(a.assemble())                          # la plantilla ensambla (solo HALT)

    def test_trace_checkbox(self):
        a = self.app
        a.trace_var.set(True)
        a.on_trace_toggle()
        a.cmd_run(); self.wait_stop()
        a.bottom.select(a.bottom.tabs()[-1])                  # pestaña Traza
        self.pump()
        text = a.trace.text.get("1.0", "end")
        self.assertIn("MOVI R1, #0", text)
        self.assertIn("HALT", text.replace("TRAP x25", "HALT"))

    def test_metrics_tab_refreshes_on_selection(self):
        a = self.app
        a.cmd_run(); self.wait_stop()
        a.bottom.select(a.metrics)
        self.pump()
        self.assertIn("Instrucciones ejecutadas: 92 (usuario 21 + SO 71)", a.metrics.text.get("1.0", "end"))


if __name__ == "__main__":
    unittest.main()
