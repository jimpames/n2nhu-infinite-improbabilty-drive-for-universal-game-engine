"""
N2NHU World Generator - Wizard UI
====================================
Seven-step wizard built on tkinter.
Zero dependencies beyond Python stdlib.
Same philosophy as the engine: runs anywhere Python runs.

N2NHU Labs for Applied Artificial Intelligence
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
import sys

# Ensure parent package is importable when run directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from world_model import PhysicsType, WorldTheme
from theme_engine import ThemeEngine
from physics_templates import PhysicsTemplateLibrary
from generator import WorldGenerator, GeneratorRequest

# ── Colour scheme ────────────────────────────────────────────
BG      = '#1A1A2E'
PANEL   = '#16213E'
ACCENT  = '#00B4D8'
GREEN   = '#06D60A'
GOLD    = '#FFC300'
WHITE   = '#F0F4F8'
LGRAY   = '#2A2A4A'
MGRAY   = '#607080'
RED     = '#E74C3C'
FONT    = ('Consolas', 10)
FONT_LG = ('Consolas', 13, 'bold')
FONT_SM = ('Consolas', 9)


class N2NHUGeneratorApp(tk.Tk):

    STEP_TITLES = [
        "Step 1  ▶  Name Your World",
        "Step 2  ▶  Name Your Characters",
        "Step 3  ▶  Choose World Size",
        "Step 4  ▶  Choose Physics & Effects",
        "Step 5  ▶  Configure Visuals",
        "Step 6  ▶  Review & Validate",
        "Step 7  ▶  Generate!",
    ]

    def __init__(self):
        super().__init__()
        self.title("N2NHU World Generator  v1.0  ·  N2NHU Labs")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.minsize(900, 680)

        self.theme_engine   = ThemeEngine()
        self.physics_lib    = PhysicsTemplateLibrary()
        self.generator      = WorldGenerator()

        # Wizard state
        self.current_step   = 0
        self.world_name_var = tk.StringVar()
        self.char_text      = None
        self.room_count_var = tk.IntVar(value=20)
        self.physics_vars   = {}   # PhysicsType -> BooleanVar
        self.sd_auto_var    = tk.BooleanVar(value=True)
        self.sd_suffix_var  = tk.StringVar()
        self.sd_neg_var     = tk.StringVar()
        self.sd_host_var    = tk.StringVar(value='127.0.0.1')
        self.sd_port_var    = tk.StringVar(value='7860')
        self.output_dir_var = tk.StringVar(value=os.path.expanduser('~/n2nhu_world'))

        self.preview_data   = {}
        self.last_result    = None

        self._build_ui()
        self._show_step(0)

    # ── UI Construction ──────────────────────────────────────

    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, bg=BG, pady=8)
        hdr.pack(fill='x')
        tk.Label(hdr, text="N2NHU WORLD GENERATOR",
                 font=('Consolas', 18, 'bold'),
                 fg=ACCENT, bg=BG).pack(side='left', padx=16)
        tk.Label(hdr, text="N2NHU Labs for Applied Artificial Intelligence",
                 font=FONT_SM, fg=MGRAY, bg=BG).pack(side='left', padx=8)

        # Progress bar
        self.progress_frame = tk.Frame(self, bg=LGRAY, height=4)
        self.progress_frame.pack(fill='x')
        self.progress_bar = tk.Frame(self.progress_frame, bg=ACCENT, height=4)
        self.progress_bar.place(x=0, y=0, relheight=1.0, relwidth=0.01)

        # Step title
        self.step_label = tk.Label(self, text="", font=FONT_LG, fg=WHITE, bg=BG, pady=8)
        self.step_label.pack(fill='x', padx=16)

        # Main content area
        self.content = tk.Frame(self, bg=BG)
        self.content.pack(fill='both', expand=True, padx=16, pady=4)

        # Step frames (one per step, stacked)
        self.step_frames = []
        builders = [
            self._build_step1, self._build_step2, self._build_step3,
            self._build_step4, self._build_step5, self._build_step6,
            self._build_step7,
        ]
        for build_fn in builders:
            frame = tk.Frame(self.content, bg=BG)
            build_fn(frame)
            self.step_frames.append(frame)

        # Nav buttons
        nav = tk.Frame(self, bg=BG, pady=8)
        nav.pack(fill='x', padx=16)
        self.back_btn = tk.Button(nav, text="◀  Back", command=self._back,
                                  font=FONT, bg=LGRAY, fg=WHITE,
                                  relief='flat', padx=20, pady=6,
                                  activebackground=MGRAY, cursor='hand2')
        self.back_btn.pack(side='left')
        self.next_btn = tk.Button(nav, text="Next  ▶", command=self._next,
                                  font=('Consolas', 10, 'bold'), bg=ACCENT, fg=WHITE,
                                  relief='flat', padx=20, pady=6,
                                  activebackground='#0090B0', cursor='hand2')
        self.next_btn.pack(side='right')

        # Status bar
        self.status_var = tk.StringVar(value="Ready. Enter a world name to begin.")
        sb = tk.Label(self, textvariable=self.status_var,
                      font=FONT_SM, fg=MGRAY, bg=BG, anchor='w')
        sb.pack(fill='x', padx=16, pady=4)

    # ── Step 1: World Name ───────────────────────────────────

    def _build_step1(self, frame):
        self._label(frame, 'What is the name of your world?', size=12, bold=True)
        self._label(frame, 'Type anything. The theme engine will classify it automatically.')

        entry = tk.Entry(frame, textvariable=self.world_name_var,
                         font=('Consolas', 16, 'bold'), bg=LGRAY, fg=WHITE,
                         insertbackground=ACCENT, relief='flat',
                         width=40)
        entry.pack(pady=8, anchor='w')
        entry.bind('<KeyRelease>', self._on_name_changed)
        entry.focus_set()

        self._label(frame, 'Examples:', color=MGRAY)
        examples = ['Barbie World', 'Area 51', "Hogan's Heroes", 'MASH 4077',
                    'Bewitched', 'Haunted Mansion', 'Indiana Jones', 'Zork']
        ef = tk.Frame(frame, bg=BG)
        ef.pack(anchor='w', pady=4)
        for ex in examples:
            btn = tk.Button(ef, text=ex, font=FONT_SM, bg=LGRAY, fg=ACCENT,
                            relief='flat', padx=8, pady=3, cursor='hand2',
                            command=lambda e=ex: self._set_example(e))
            btn.pack(side='left', padx=3)

        # Live preview panel
        self.preview_panel = tk.Frame(frame, bg=PANEL, padx=12, pady=10)
        self.preview_panel.pack(fill='x', pady=12)
        self.preview_theme_lbl  = self._label(self.preview_panel, "Theme: —", color=ACCENT)
        self.preview_flavor_lbl = self._label(self.preview_panel, "Flavor: —", color=WHITE)
        self.preview_sd_lbl     = self._label(self.preview_panel, "SD style: —", color=MGRAY, size=9)
        self.preview_phys_lbl   = self._label(self.preview_panel, "Default physics: —", color=GOLD, size=9)

    def _on_name_changed(self, event=None):
        name = self.world_name_var.get().strip()
        if len(name) < 2:
            return
        data = self.generator.preview(GeneratorRequest(world_name=name))
        self.preview_data = data
        self.preview_theme_lbl.config(text=f"Theme:   {data['theme_display']}")
        self.preview_flavor_lbl.config(text=f"Flavor:  {data['flavor']}")
        self.preview_sd_lbl.config(text=f"SD:      {data['sd_suffix'][:80]}...")
        self.preview_phys_lbl.config(text=f"Physics: {', '.join(data['default_physics'])}")

    def _set_example(self, name):
        self.world_name_var.set(name)
        self._on_name_changed()

    # ── Step 2: Characters ───────────────────────────────────

    def _build_step2(self, frame):
        self._label(frame, 'Who lives in your world?', size=12, bold=True)
        self._label(frame, 'Enter character names, one per line. '
                           'The engine infers role, stats, and behavior automatically.')

        examples_f = tk.Frame(frame, bg=BG)
        examples_f.pack(anchor='w', pady=4)
        self._label(examples_f, 'Examples: ', color=MGRAY, pack_side='left')
        for ex in ['Ken, Barbie, Skipper', 'Schultz, Klink, Hogan',
                   'Hawkeye, Radar, Potter, Frank', 'Alien, MIB Agent, Bob Lazar']:
            tk.Button(examples_f, text=ex, font=FONT_SM, bg=LGRAY, fg=ACCENT,
                      relief='flat', padx=6, pady=2, cursor='hand2',
                      command=lambda e=ex: self._set_chars(e)).pack(side='left', padx=3)

        self.char_text = scrolledtext.ScrolledText(
            frame, font=('Consolas', 12), bg=LGRAY, fg=WHITE,
            insertbackground=ACCENT, relief='flat', height=8, width=40)
        self.char_text.pack(pady=6, anchor='w')
        self.char_text.bind('<KeyRelease>', self._on_chars_changed)

        self.char_preview = tk.Frame(frame, bg=PANEL, padx=10, pady=6)
        self.char_preview.pack(fill='x')
        self.char_count_lbl = self._label(self.char_preview, "Characters: 0", color=ACCENT)
        self.char_roles_lbl = self._label(self.char_preview, "Roles will be inferred from names.", color=MGRAY)

    def _set_chars(self, names):
        self.char_text.delete('1.0', 'end')
        for name in names.split(','):
            self.char_text.insert('end', name.strip() + '\n')
        self._on_chars_changed()

    def _on_chars_changed(self, event=None):
        names = self._get_char_names()
        self.char_count_lbl.config(text=f"Characters: {len(names)}")
        self.char_roles_lbl.config(
            text=f"Names: {', '.join(names[:6])}{'...' if len(names) > 6 else ''}")

    def _get_char_names(self):
        if not self.char_text:
            return []
        raw = self.char_text.get('1.0', 'end').strip()
        names = []
        for line in raw.split('\n'):
            for part in line.split(','):
                n = part.strip()
                if n:
                    names.append(n)
        return names

    # ── Step 3: Room Count ───────────────────────────────────

    def _build_step3(self, frame):
        self._label(frame, 'How big is your world?', size=12, bold=True)
        self._label(frame, 'All rooms are guaranteed connected. No dead ends. No orphaned rooms.')

        sizes = [('Tiny',  5),  ('Small', 10), ('Medium', 20),
                 ('Large', 35), ('Epic',  60)]
        sf = tk.Frame(frame, bg=BG)
        sf.pack(anchor='w', pady=8)
        self.size_btns = {}
        for label, count in sizes:
            btn = tk.Button(sf, text=f"{label}\n({count} rooms)",
                            font=FONT, bg=LGRAY, fg=WHITE,
                            relief='flat', padx=16, pady=8, cursor='hand2',
                            command=lambda c=count, l=label: self._set_size(c, l))
            btn.pack(side='left', padx=5)
            self.size_btns[count] = btn

        self._label(frame, 'Or enter a custom size:', color=MGRAY)
        custom_f = tk.Frame(frame, bg=BG)
        custom_f.pack(anchor='w')
        tk.Spinbox(custom_f, from_=3, to=100, textvariable=self.room_count_var,
                   font=('Consolas', 14, 'bold'), bg=LGRAY, fg=WHITE,
                   insertbackground=ACCENT, relief='flat', width=6,
                   command=self._on_size_changed).pack(side='left')
        self._label(custom_f, ' rooms', pack_side='left', color=WHITE)

        self.size_info = self._label(frame, "", color=GOLD, pady=8)
        self._set_size(20, 'Medium')

    def _set_size(self, count, label=''):
        self.room_count_var.set(count)
        for c, btn in self.size_btns.items():
            btn.config(bg=ACCENT if c == count else LGRAY)
        self._on_size_changed()

    def _on_size_changed(self, *a):
        n = self.room_count_var.get()
        complexity = 'Tiny' if n <= 5 else 'Small' if n <= 10 else \
                     'Medium' if n <= 20 else 'Large' if n <= 35 else 'Epic'
        self.size_info.config(
            text=f"{n} rooms  ·  {complexity}  ·  "
                 f"Approx. {n * 3} objects  ·  "
                 f"~{max(1, n // 5)} sprites  ·  "
                 f"Guaranteed fully connected")

    # ── Step 4: Physics ──────────────────────────────────────

    def _build_step4(self, frame):
        self._label(frame, 'What special effects exist in your world?', size=12, bold=True)
        self._label(frame, 'Select any that apply. Each adds pre-validated transformation rules automatically.')

        grid = tk.Frame(frame, bg=BG)
        grid.pack(anchor='w', pady=8, fill='x')

        packages = self.physics_lib.all_packages()
        for i, pkg in enumerate(packages):
            var = tk.BooleanVar(value=False)
            self.physics_vars[pkg['type']] = var
            row, col = divmod(i, 2)
            cb_frame = tk.Frame(grid, bg=PANEL, padx=10, pady=6)
            cb_frame.grid(row=row, column=col, padx=4, pady=4, sticky='ew')
            cb = tk.Checkbutton(cb_frame, variable=var,
                                font=('Consolas', 10, 'bold'),
                                text=f"{pkg['emoji']}  {pkg['name']}",
                                bg=PANEL, fg=WHITE, selectcolor=LGRAY,
                                activebackground=PANEL, activeforeground=ACCENT,
                                command=self._on_physics_changed)
            cb.pack(anchor='w')
            tk.Label(cb_frame, text=pkg['desc'],
                     font=FONT_SM, fg=MGRAY, bg=PANEL,
                     wraplength=320, justify='left').pack(anchor='w', padx=20)
            grid.columnconfigure(col, weight=1)

        self.physics_summary = self._label(frame, "Selected: none (theme defaults will apply)", color=GOLD)

    def _on_physics_changed(self):
        selected = [p for p, v in self.physics_vars.items() if v.get()]
        if selected:
            names = [next(p['name'] for p in self.physics_lib.all_packages()
                         if p['type'] == s) for s in selected]
            self.physics_summary.config(text=f"Selected: {', '.join(names)}")
        else:
            self.physics_summary.config(text="Selected: none (theme defaults will apply)")

    # ── Step 5: Visuals ──────────────────────────────────────

    def _build_step5(self, frame):
        self._label(frame, 'Configure Visuals (Stable Diffusion)', size=12, bold=True)

        auto_f = tk.Frame(frame, bg=BG)
        auto_f.pack(anchor='w', pady=6)
        tk.Radiobutton(auto_f, text="AUTO — generate SD prompts from world theme",
                       variable=self.sd_auto_var, value=True,
                       font=FONT, bg=BG, fg=WHITE, selectcolor=LGRAY,
                       activebackground=BG, command=self._on_sd_auto_changed).pack(anchor='w')
        tk.Radiobutton(auto_f, text="CUSTOM — enter your own SD style keywords",
                       variable=self.sd_auto_var, value=False,
                       font=FONT, bg=BG, fg=WHITE, selectcolor=LGRAY,
                       activebackground=BG, command=self._on_sd_auto_changed).pack(anchor='w')

        self.sd_auto_preview = tk.Frame(frame, bg=PANEL, padx=10, pady=8)
        self.sd_auto_preview.pack(fill='x', pady=4)
        self.sd_preview_lbl = self._label(self.sd_auto_preview,
                                          "Set world name first to see SD preview.", color=MGRAY)

        self.sd_custom_frame = tk.Frame(frame, bg=BG)
        self._label(self.sd_custom_frame, 'Scene suffix (added to every room description):')
        tk.Entry(self.sd_custom_frame, textvariable=self.sd_suffix_var,
                 font=FONT, bg=LGRAY, fg=WHITE, insertbackground=ACCENT,
                 relief='flat', width=70).pack(anchor='w', pady=2)
        self._label(self.sd_custom_frame, 'Negative prompt:')
        tk.Entry(self.sd_custom_frame, textvariable=self.sd_neg_var,
                 font=FONT, bg=LGRAY, fg=WHITE, insertbackground=ACCENT,
                 relief='flat', width=70).pack(anchor='w', pady=2)

        self._label(frame, 'Stable Diffusion Server:', color=WHITE)
        srv_f = tk.Frame(frame, bg=BG)
        srv_f.pack(anchor='w', pady=4)
        self._label(srv_f, 'Host:', pack_side='left', color=MGRAY)
        tk.Entry(srv_f, textvariable=self.sd_host_var, font=FONT,
                 bg=LGRAY, fg=WHITE, insertbackground=ACCENT,
                 relief='flat', width=16).pack(side='left', padx=6)
        self._label(srv_f, 'Port:', pack_side='left', color=MGRAY)
        tk.Entry(srv_f, textvariable=self.sd_port_var, font=FONT,
                 bg=LGRAY, fg=WHITE, insertbackground=ACCENT,
                 relief='flat', width=8).pack(side='left', padx=6)

        self._label(frame, '⚠  SD section is always written as [SD1] and host/port as separate keys.',
                    color=GOLD, size=9)

        self._on_sd_auto_changed()

    def _on_sd_auto_changed(self):
        if self.sd_auto_var.get():
            self.sd_custom_frame.pack_forget()
            self.sd_auto_preview.pack(fill='x', pady=4)
            if self.preview_data:
                self.sd_preview_lbl.config(
                    text=f"Scene: {self.preview_data.get('sd_suffix','')[:80]}...\n"
                         f"Neg:   {self.preview_data.get('sd_negative','')[:80]}...")
        else:
            self.sd_auto_preview.pack_forget()
            self.sd_custom_frame.pack(fill='x', pady=4)

    # ── Step 6: Review ───────────────────────────────────────

    def _build_step6(self, frame):
        self._label(frame, 'Review & Validate', size=12, bold=True)
        self._label(frame, 'The validator runs 18 cross-reference checks. '
                           'All must pass before generation proceeds.')

        btn_f = tk.Frame(frame, bg=BG)
        btn_f.pack(anchor='w', pady=6)
        tk.Button(btn_f, text="▶ Run Validation Now",
                  font=('Consolas', 10, 'bold'), bg=ACCENT, fg=WHITE,
                  relief='flat', padx=16, pady=6, cursor='hand2',
                  command=self._run_validation).pack(side='left')

        self.validation_box = scrolledtext.ScrolledText(
            frame, font=FONT_SM, bg=LGRAY, fg=WHITE,
            relief='flat', height=16, state='disabled')
        self.validation_box.pack(fill='both', expand=True, pady=6)

        self._label(frame, 'Output directory:', color=MGRAY)
        dir_f = tk.Frame(frame, bg=BG)
        dir_f.pack(anchor='w', fill='x')
        tk.Entry(dir_f, textvariable=self.output_dir_var,
                 font=FONT, bg=LGRAY, fg=WHITE, insertbackground=ACCENT,
                 relief='flat', width=55).pack(side='left', padx=(0,6))
        tk.Button(dir_f, text="Browse", font=FONT_SM, bg=LGRAY, fg=ACCENT,
                  relief='flat', padx=8, cursor='hand2',
                  command=self._browse_dir).pack(side='left')

    def _run_validation(self):
        self._write_validation("Running 18-check validation...\n\n")
        request = self._build_request()
        # Run just the world build + validation (no file write) in thread
        def task():
            try:
                result = self.generator.generate(request)
                self.after(0, lambda: self._show_validation_result(result))
            except Exception as e:
                self.after(0, lambda: self._write_validation(f"ERROR: {e}"))
        threading.Thread(target=task, daemon=True).start()

    def _show_validation_result(self, result):
        lines = [f"World: {self.world_name_var.get()}",
                 f"Summary: {result.summary}",
                 f"Theme: {result.theme_used.value if result.theme_used else 'unknown'}",
                 ""]
        if result.success:
            lines.append("✅  ALL 18 CHECKS PASSED — READY TO GENERATE")
        else:
            lines.append(f"❌  {len(result.validation_errors)} ERRORS FOUND")
        lines.append("")
        lines += result.validation_errors
        if result.validation_warnings:
            lines.append("")
            lines += result.validation_warnings
        self._write_validation('\n'.join(lines))
        if result.success:
            self.status_var.set("✅ Validation passed — ready to generate!")
        else:
            self.status_var.set(f"❌ {len(result.validation_errors)} validation errors — review above")

    def _write_validation(self, text):
        self.validation_box.config(state='normal')
        self.validation_box.delete('1.0', 'end')
        self.validation_box.insert('end', text)
        self.validation_box.config(state='disabled')

    def _browse_dir(self):
        d = filedialog.askdirectory(title="Select output directory")
        if d:
            self.output_dir_var.set(d)

    # ── Step 7: Generate ─────────────────────────────────────

    def _build_step7(self, frame):
        self._label(frame, '🚀  Generate Your World', size=14, bold=True, color=ACCENT)
        self._label(frame, 'Writes all 6 INI files, then performs round-trip verification.')

        self.gen_status_lbl = self._label(frame, "Ready to generate.", color=MGRAY, size=11)

        self.gen_btn = tk.Button(frame, text="⚡  GENERATE WORLD",
                                 font=('Consolas', 14, 'bold'), bg=GREEN, fg=BG,
                                 relief='flat', padx=32, pady=14, cursor='hand2',
                                 command=self._do_generate)
        self.gen_btn.pack(pady=16)

        self.gen_progress = ttk.Progressbar(frame, mode='indeterminate', length=400)
        self.gen_progress.pack(pady=4)

        self.gen_output = scrolledtext.ScrolledText(
            frame, font=FONT_SM, bg=LGRAY, fg=WHITE,
            relief='flat', height=14, state='disabled')
        self.gen_output.pack(fill='both', expand=True, pady=6)

    def _do_generate(self):
        self.gen_btn.config(state='disabled', text="Generating...")
        self.gen_progress.start(10)
        self._write_gen_output("Starting generation pipeline...\n")

        request = self._build_request()

        def task():
            result = self.generator.generate(request)
            self.after(0, lambda: self._on_gen_complete(result))

        threading.Thread(target=task, daemon=True).start()

    def _on_gen_complete(self, result):
        self.gen_progress.stop()
        self.gen_btn.config(state='normal', text="⚡  GENERATE WORLD")
        self.last_result = result

        lines = [result.display_summary(), ""]

        if result.success:
            lines.append("FILES WRITTEN:")
            for name, path in result.written_files.items():
                lines.append(f"  ✅  {os.path.basename(path)}")
            lines.append("")
            lines.append(f"Output directory: {self.output_dir_var.get()}")
            lines.append("")
            lines.append("Copy these 6 files to your game engine's config/ folder.")
            lines.append("Launch the server. Your world is ready.")
            self.gen_status_lbl.config(
                text="✅  World generated successfully!", fg=GREEN)
            self.status_var.set(f"✅  {result.summary}")
            messagebox.showinfo("World Generated!",
                                f"{self.world_name_var.get()} is ready!\n\n"
                                f"{result.summary}\n\n"
                                f"Output: {self.output_dir_var.get()}")
        else:
            lines.append("ERRORS:")
            lines += result.validation_errors[:10]
            self.gen_status_lbl.config(
                text=f"❌  Generation failed — {len(result.validation_errors)} errors", fg=RED)
            self.status_var.set(f"❌  Generation failed")

        self._write_gen_output('\n'.join(lines))

    def _write_gen_output(self, text):
        self.gen_output.config(state='normal')
        self.gen_output.delete('1.0', 'end')
        self.gen_output.insert('end', text)
        self.gen_output.config(state='disabled')

    # ── Navigation ───────────────────────────────────────────

    def _show_step(self, step):
        for i, frame in enumerate(self.step_frames):
            frame.pack_forget()
        self.step_frames[step].pack(fill='both', expand=True)
        self.step_label.config(text=self.STEP_TITLES[step])
        self.current_step = step
        # Progress bar
        frac = (step + 1) / len(self.step_frames)
        self.progress_bar.place(relwidth=frac)
        # Button states
        self.back_btn.config(state='normal' if step > 0 else 'disabled')
        if step == len(self.step_frames) - 1:
            self.next_btn.config(text="✅  Done", command=self.destroy)
        else:
            self.next_btn.config(text="Next  ▶", command=self._next)
        # Auto-update SD preview on step 5
        if step == 4 and self.preview_data and self.sd_auto_var.get():
            self.sd_preview_lbl.config(
                text=f"Scene: {self.preview_data.get('sd_suffix','')[:90]}\n"
                     f"Neg:   {self.preview_data.get('sd_negative','')[:90]}")
        # Auto-run validation on step 6
        if step == 5:
            self.after(200, self._run_validation)

    def _next(self):
        if self.current_step < len(self.step_frames) - 1:
            if not self._validate_step(self.current_step):
                return
            self._show_step(self.current_step + 1)

    def _back(self):
        if self.current_step > 0:
            self._show_step(self.current_step - 1)

    def _validate_step(self, step) -> bool:
        if step == 0:
            if not self.world_name_var.get().strip():
                messagebox.showwarning("Missing Input", "Please enter a world name.")
                return False
        return True

    # ── Request Builder ──────────────────────────────────────

    def _build_request(self) -> GeneratorRequest:
        selected_physics = [p for p, v in self.physics_vars.items() if v.get()]
        sd_suffix  = '' if self.sd_auto_var.get() else self.sd_suffix_var.get()
        sd_neg     = '' if self.sd_auto_var.get() else self.sd_neg_var.get()
        try:
            port = int(self.sd_port_var.get())
        except ValueError:
            port = 7860

        return GeneratorRequest(
            world_name      = self.world_name_var.get().strip(),
            character_names = self._get_char_names(),
            room_count      = self.room_count_var.get(),
            physics_types   = selected_physics,
            output_dir      = self.output_dir_var.get(),
            sd_host         = self.sd_host_var.get(),
            sd_port         = port,
            sd_scene_suffix = sd_suffix,
            sd_negative_prompt = sd_neg,
        )

    # ── UI helpers ───────────────────────────────────────────

    def _label(self, parent, text, size=10, bold=False, color=None,
               pady=2, pack_side='top') -> tk.Label:
        font = ('Consolas', size, 'bold') if bold else ('Consolas', size)
        lbl = tk.Label(parent, text=text, font=font,
                       fg=color or MGRAY, bg=parent['bg'],
                       anchor='w', justify='left')
        lbl.pack(side=pack_side, anchor='w', pady=pady, padx=2)
        return lbl


def run_gui():
    app = N2NHUGeneratorApp()
    app.mainloop()
