"""Tkinter desktop chat shell for Arbora."""

from __future__ import annotations

import json
import threading
import tkinter as tk
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from arbora.cli.session import (
    approve_all,
    build_runtime,
    format_plan,
    hard_confirm_ids_for,
    list_provider_choices,
    persist_routines,
    provider_privacy_notice,
)
from arbora.core.audit_store import export_audit_payload
from arbora.core.types import ApprovalDecision, AuditEvent, ExecutionReport, Plan, TrustedRoutine
from arbora.schedules.runner import run_due_schedules
from arbora.schedules.store import (
    add_schedule,
    load_schedules,
    persist_schedules,
    remove_schedule,
    schedule_rows,
)
from arbora.memory.goal_history import list_recent_goals, record_goal
from arbora.memory.store import export_memory_payload, memory_status_rows
from arbora.voice.windows import listen_once, voice_input_available
from arbora.setup_status import (
    LIGHT_HEX,
    Light,
    ServiceStatus,
    first_run_checklist,
    install_playwright_chromium,
    probe_all,
)


# Forest / ink palette — product chrome, not generic AI purple.
COLORS = {
    "bg": "#0F2419",
    "panel": "#163026",
    "ink": "#F3EDE2",
    "muted": "#B7C4B8",
    "accent": "#52B788",
    "accent_dim": "#2D6A4F",
    "danger": "#E76F51",
    "input_bg": "#1B3A2F",
}


def format_schedule_list(memory, routines: list[TrustedRoutine]) -> list[str]:
    names = {routine.id: routine.name for routine in routines}
    return schedule_rows(load_schedules(memory), routine_names=names)


def format_routine_rows(routines: list[TrustedRoutine]) -> list[str]:
    """One listbox row per trusted routine."""
    return [f"{routine.name}  ({routine.id[:8]}…)" for routine in routines]


def format_routine_detail(routine: TrustedRoutine) -> str:
    goal = routine.goal_norm or "(no goal norm)"
    return (
        f"{routine.name}\n"
        f"id={routine.id}\n"
        f"fingerprint={routine.plan_fingerprint}  v{routine.version}\n"
        f"goal={goal}"
    )


def format_audit_events(events: list[AuditEvent]) -> str:
    """Human-readable session audit for the Trust UX dialog."""
    if not events:
        return "(audit log empty)\n"
    lines: list[str] = []
    for event in events:
        stamp = event.created_at.isoformat(timespec="seconds")
        lines.append(f"[{stamp}] {event.kind}")
        lines.append(f"  {event.message}")
        extras = {k: v for k, v in (event.payload or {}).items() if v is not None}
        if extras:
            kv = ", ".join(f"{k}={v}" for k, v in extras.items())
            lines.append(f"  {kv}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def format_memory_status(memory) -> str:
    """Human-readable local memory status for the Memory dialog."""
    return "\n".join(memory_status_rows(memory)) + "\n"


class ArboraChatApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Arbora")
        self.root.geometry("960x700")
        self.root.minsize(760, 540)
        self.root.configure(bg=COLORS["bg"])

        self.provider_var = tk.StringVar(value="echo")
        self.dry_run_var = tk.BooleanVar(value=True)
        self.promote_var = tk.BooleanVar(value=False)
        self.routine_name_var = tk.StringVar(value="")
        self._runtime = build_runtime(provider=None, seed_samples=True)
        if self._runtime.preferences.provider:
            self.provider_var.set(self._runtime.preferences.provider)
        self.dry_run_var.set(self._runtime.preferences.dry_run_default)
        self._plan: Plan | None = None
        self._matched_trusted = False
        self._status_dots: dict[str, tk.Canvas] = {}
        self._status_labels: dict[str, tk.StringVar] = {}
        self._setup_busy = False
        self._run_busy = False
        self._stop_var = tk.StringVar(value="")
        self._privacy_var = tk.StringVar(value="")

        self._build_style()
        self._build_ui()
        self._log(
            "Arbora ready.\nModels propose; the permission broker disposes.\n"
            f"Provider: {self._runtime.provider_name} | "
            f"Memory: {self._runtime.memory.key_backend}\n"
        )
        self._refresh_privacy_banner()
        self.refresh_status_lights()
        if self._runtime.preferences.run_due_schedules_on_start:
            threading.Thread(target=self._run_due_schedules_on_start, daemon=True).start()

    def _run_due_schedules_on_start(self) -> None:
        results = run_due_schedules(self._runtime)
        if not results:
            return
        lines = ["\nStartup schedules:"]
        for result in results:
            status = "skipped" if result.skipped else ("ok" if result.ok else "failed")
            lines.append(f"  {result.schedule_id}: {status} — {result.message}")
        lines.append("")
        self.root.after(0, lambda: self._log("\n".join(lines)))

    def _build_style(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        font_ui = ("Segoe UI Variable", 11)
        font_brand = ("Cascadia Mono", 28, "bold")
        font_mono = ("Cascadia Mono", 10)
        try:
            self.root.tk.call(
                "font", "create", "ArboraBrand", "-family", "Cascadia Mono", "-size", 28, "-weight", "bold"
            )
        except tk.TclError:
            font_brand = ("Consolas", 28, "bold")
            font_mono = ("Consolas", 10)
        self.font_ui = font_ui
        self.font_brand = font_brand
        self.font_mono = font_mono

        style.configure("TFrame", background=COLORS["bg"])
        style.configure("Panel.TFrame", background=COLORS["panel"])
        style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["ink"], font=font_ui)
        style.configure("Muted.TLabel", background=COLORS["bg"], foreground=COLORS["muted"], font=font_ui)
        style.configure("Brand.TLabel", background=COLORS["bg"], foreground=COLORS["accent"], font=font_brand)
        style.configure(
            "Accent.TButton",
            background=COLORS["accent_dim"],
            foreground=COLORS["ink"],
            font=font_ui,
            padding=8,
        )
        style.configure(
            "Danger.TButton",
            background=COLORS["danger"],
            foreground=COLORS["ink"],
            font=font_ui,
            padding=8,
        )
        style.map("Danger.TButton", background=[("active", "#C45B3E")])
        style.configure("TCheckbutton", background=COLORS["bg"], foreground=COLORS["ink"], font=font_ui)
        style.configure("TCombobox", fieldbackground=COLORS["input_bg"], foreground=COLORS["ink"])

    def _build_ui(self) -> None:
        header = ttk.Frame(self.root, style="TFrame")
        header.pack(fill="x", padx=24, pady=(20, 8))

        left = ttk.Frame(header, style="TFrame")
        left.pack(side="left", fill="x", expand=True)
        ttk.Label(left, text="Arbora", style="Brand.TLabel").pack(anchor="w")
        ttk.Label(
            left,
            text="Personal Windows assistant — plan, approve, execute under your rules.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(4, 0))

        # Corner status lights for connected local services.
        status_corner = tk.Frame(header, bg=COLORS["panel"], padx=12, pady=10)
        status_corner.pack(side="right", anchor="ne")
        tk.Label(
            status_corner,
            text="Connections",
            bg=COLORS["panel"],
            fg=COLORS["muted"],
            font=("Segoe UI", 9),
        ).pack(anchor="w")
        for name in ("Memory", "Ollama", "Playwright"):
            row = tk.Frame(status_corner, bg=COLORS["panel"])
            row.pack(anchor="w", pady=2)
            dot = tk.Canvas(row, width=12, height=12, bg=COLORS["panel"], highlightthickness=0)
            dot.pack(side="left", padx=(0, 8))
            dot.create_oval(1, 1, 11, 11, fill=LIGHT_HEX[Light.YELLOW], outline="")
            label_var = tk.StringVar(value=f"{name}: checking…")
            tk.Label(
                row,
                textvariable=label_var,
                bg=COLORS["panel"],
                fg=COLORS["ink"],
                font=("Segoe UI", 9),
            ).pack(side="left")
            self._status_dots[name] = dot
            self._status_labels[name] = label_var

        controls = ttk.Frame(self.root, style="TFrame")
        controls.pack(fill="x", padx=24, pady=8)
        ttk.Label(controls, text="Provider").pack(side="left")
        self._provider_combo = ttk.Combobox(
            controls,
            textvariable=self.provider_var,
            values=tuple(list_provider_choices()),
            width=10,
            state="readonly",
        )
        self._provider_combo.pack(side="left", padx=(8, 16))
        self._provider_combo.bind("<<ComboboxSelected>>", self._on_provider_change)
        ttk.Checkbutton(controls, text="Dry-run", variable=self.dry_run_var).pack(side="left", padx=(0, 16))
        ttk.Checkbutton(controls, text="Promote after success", variable=self.promote_var).pack(side="left")
        ttk.Button(controls, text="Refresh status", command=self.refresh_status_lights).pack(side="right", padx=(8, 0))
        ttk.Button(controls, text="Setup", style="Accent.TButton", command=self.open_setup).pack(side="right")

        privacy_row = ttk.Frame(self.root, style="TFrame")
        privacy_row.pack(fill="x", padx=24, pady=(0, 4))
        self._privacy_label = tk.Label(
            privacy_row,
            textvariable=self._privacy_var,
            bg=COLORS["danger"],
            fg=COLORS["ink"],
            font=("Segoe UI", 9, "bold"),
            anchor="w",
            padx=10,
            pady=6,
        )
        self._privacy_label.pack(fill="x")
        self._privacy_label.pack_forget()

        self.transcript = tk.Text(
            self.root,
            wrap="word",
            bg=COLORS["panel"],
            fg=COLORS["ink"],
            insertbackground=COLORS["ink"],
            selectbackground=COLORS["accent_dim"],
            relief="flat",
            padx=14,
            pady=12,
            font=self.font_mono,
            height=24,
        )
        self.transcript.pack(fill="both", expand=True, padx=24, pady=8)
        self.transcript.configure(state="disabled")

        entry_row = ttk.Frame(self.root, style="TFrame")
        entry_row.pack(fill="x", padx=24, pady=(4, 8))
        self.goal_entry = tk.Entry(
            entry_row,
            bg=COLORS["input_bg"],
            fg=COLORS["ink"],
            insertbackground=COLORS["ink"],
            relief="flat",
            font=self.font_ui,
        )
        self.goal_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 8))
        self.goal_entry.bind("<Return>", lambda _e: self.make_plan())
        ttk.Button(entry_row, text="History", command=self.show_goal_history).pack(side="left", padx=(0, 8))
        ttk.Button(entry_row, text="Voice", command=self.voice_goal).pack(side="left", padx=(0, 8))
        ttk.Button(entry_row, text="Plan", style="Accent.TButton", command=self.make_plan).pack(side="left")

        actions = ttk.Frame(self.root, style="TFrame")
        actions.pack(fill="x", padx=24, pady=(0, 20))
        self._approve_btn = ttk.Button(
            actions, text="Approve & run", style="Accent.TButton", command=self.approve_run
        )
        self._approve_btn.pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Reject", command=self.reject_plan).pack(side="left", padx=(0, 8))
        self._stop_btn = ttk.Button(
            actions, text="Stop", style="Danger.TButton", command=self.emergency_stop, state="disabled"
        )
        self._stop_btn.pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Routines", command=self.show_routines).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Schedules", command=self.show_schedules).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Audit", command=self.show_audit).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Memory", command=self.show_memory).pack(side="left")
        ttk.Label(actions, textvariable=self.routine_name_var, style="Muted.TLabel").pack(side="right")
        ttk.Label(actions, textvariable=self._stop_var, style="Muted.TLabel").pack(side="right", padx=(0, 12))

    def _set_light(self, status: ServiceStatus) -> None:
        dot = self._status_dots.get(status.name)
        label = self._status_labels.get(status.name)
        if dot is None or label is None:
            return
        color = LIGHT_HEX[status.light]
        dot.delete("all")
        dot.create_oval(1, 1, 11, 11, fill=color, outline="")
        label.set(f"{status.name}: {status.detail}")

    def refresh_status_lights(self) -> None:
        for name in self._status_labels:
            self._status_labels[name].set(f"{name}: checking…")
            dot = self._status_dots[name]
            dot.delete("all")
            dot.create_oval(1, 1, 11, 11, fill=LIGHT_HEX[Light.YELLOW], outline="")

        def work() -> None:
            results = probe_all()
            self.root.after(0, lambda: self._apply_status(results))

        threading.Thread(target=work, daemon=True).start()

    def _apply_status(self, results: list[ServiceStatus]) -> None:
        for status in results:
            self._set_light(status)

    def open_setup(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Arbora Setup")
        dialog.configure(bg=COLORS["bg"])
        dialog.transient(self.root)
        dialog.geometry("480x420")
        dialog.grab_set()

        ttk.Label(dialog, text="First-run checklist", style="Brand.TLabel").pack(
            anchor="w", padx=16, pady=(16, 4)
        )
        ttk.Label(
            dialog,
            text="Private-tester path: run scripts/first_run.ps1 once, then use this checklist.",
            style="Muted.TLabel",
            wraplength=440,
        ).pack(anchor="w", padx=16, pady=(0, 8))

        checklist_box = tk.Text(
            dialog,
            wrap="word",
            height=10,
            bg=COLORS["panel"],
            fg=COLORS["ink"],
            relief="flat",
            font=self.font_mono,
            padx=10,
            pady=8,
        )
        checklist_box.pack(fill="both", expand=True, padx=16, pady=4)
        checklist_box.configure(state="disabled")

        status_var = tk.StringVar(value="Ready.")
        ttk.Label(dialog, textvariable=status_var, style="Muted.TLabel").pack(anchor="w", padx=16)

        def render_checklist() -> None:
            steps = first_run_checklist()
            lines: list[str] = []
            for step in steps:
                mark = {"green": "[ok]", "yellow": "[..]", "red": "[!!]"}[step.status.light.value]
                req = "required" if step.required else "optional"
                lines.append(f"{mark} {step.title} ({req})")
                lines.append(f"    {step.status.detail}")
                if step.status.light != Light.GREEN:
                    lines.append(f"    fix: {step.status.fix_hint}")
                lines.append("")
            checklist_box.configure(state="normal")
            checklist_box.delete("1.0", "end")
            checklist_box.insert("1.0", "\n".join(lines).rstrip() + "\n")
            checklist_box.configure(state="disabled")
            for step in steps:
                self._set_light(step.status)

        def install_chromium() -> None:
            if self._setup_busy:
                return
            self._setup_busy = True
            status_var.set("Installing Chromium… (this can take a minute)")
            self._set_light(ServiceStatus("Playwright", Light.YELLOW, "installing…"))

            def work() -> None:
                ok, detail = install_playwright_chromium()

                def done() -> None:
                    self._setup_busy = False
                    if ok:
                        status_var.set("Chromium installed.")
                        self._log("Setup: Playwright Chromium installed.\n")
                        messagebox.showinfo("Arbora Setup", "Chromium is ready for browser actions.")
                    else:
                        status_var.set("Install failed.")
                        self._log(f"Setup failed:\n{detail}\n")
                        messagebox.showerror("Arbora Setup", detail[:1000] or "Install failed")
                    render_checklist()
                    self.refresh_status_lights()

                self.root.after(0, done)

            threading.Thread(target=work, daemon=True).start()

        def refresh() -> None:
            status_var.set("Refreshing checklist…")
            render_checklist()
            self.refresh_status_lights()
            status_var.set("Checklist updated.")

        btn_row = ttk.Frame(dialog, style="TFrame")
        btn_row.pack(fill="x", padx=16, pady=12)
        ttk.Button(btn_row, text="Install Chromium", style="Accent.TButton", command=install_chromium).pack(
            anchor="w", pady=4
        )
        ttk.Button(btn_row, text="Refresh checklist", command=refresh).pack(anchor="w", pady=4)
        ttk.Button(btn_row, text="Close", command=dialog.destroy).pack(anchor="w", pady=8)

        tip = (
            "Green = ready, yellow = partial, red = blocked.\n"
            "Full install guide: docs/install.md"
        )
        tk.Label(
            dialog,
            text=tip,
            bg=COLORS["bg"],
            fg=COLORS["muted"],
            justify="left",
            font=("Segoe UI", 9),
        ).pack(anchor="w", padx=16, pady=(0, 16))

        render_checklist()

    def _refresh_privacy_banner(self) -> None:
        notice = provider_privacy_notice(self._runtime.planner._provider)  # noqa: SLF001
        if notice:
            self._privacy_var.set(notice)
            self._privacy_label.pack(fill="x")
        else:
            self._privacy_var.set("")
            self._privacy_label.pack_forget()

    def _on_provider_change(self, _event=None) -> None:
        choice = self.provider_var.get()
        try:
            self._runtime = build_runtime(provider=choice, seed_samples=True)
        except ValueError as exc:
            messagebox.showerror("Provider", str(exc))
            self.provider_var.set(self._runtime.provider_name)
            return
        self._plan = None
        self._matched_trusted = False
        self._log(f"Switched provider to {self._runtime.provider_name}\n")
        self._refresh_privacy_banner()
        self.refresh_status_lights()

    def _log(self, text: str) -> None:
        self.transcript.configure(state="normal")
        self.transcript.insert("end", text if text.endswith("\n") else text + "\n")
        self.transcript.see("end")
        self.transcript.configure(state="disabled")

    def voice_goal(self) -> None:
        if not voice_input_available():
            messagebox.showinfo(
                "Voice input",
                "Voice input is only available on Windows in this prototype.",
                parent=self.root,
            )
            return
        self._log("Listening for goal (speak now)…\n")

        def work() -> None:
            result = listen_once()

            def finish() -> None:
                if result.ok:
                    self.goal_entry.delete(0, "end")
                    self.goal_entry.insert(0, result.text)
                    self._log(f"Heard: {result.text}\n")
                else:
                    messagebox.showwarning(
                        "Voice input",
                        result.error or "Voice recognition failed.",
                        parent=self.root,
                    )

            self.root.after(0, finish)

        threading.Thread(target=work, daemon=True).start()

    def show_goal_history(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Recent goals")
        dialog.configure(bg=COLORS["bg"])
        dialog.transient(self.root)
        dialog.geometry("520x320")
        dialog.grab_set()

        ttk.Label(dialog, text="Recent goals", style="Brand.TLabel").pack(
            anchor="w", padx=16, pady=(16, 4)
        )
        ttk.Label(
            dialog,
            text="Select a goal to refill the input field.",
            style="Muted.TLabel",
            wraplength=480,
        ).pack(anchor="w", padx=16, pady=(0, 8))

        listbox = tk.Listbox(
            dialog,
            bg=COLORS["panel"],
            fg=COLORS["ink"],
            selectbackground=COLORS["accent_dim"],
            relief="flat",
            font=self.font_mono,
            activestyle="none",
        )
        listbox.pack(fill="both", expand=True, padx=16, pady=4)
        goals = list_recent_goals(self._runtime.memory, limit=20)
        for goal in goals:
            listbox.insert("end", goal)
        if not goals:
            listbox.insert("end", "(no recent goals yet)")

        def use_selected() -> None:
            sel = listbox.curselection()
            if not sel or not goals:
                return
            chosen = goals[sel[0]]
            self.goal_entry.delete(0, "end")
            self.goal_entry.insert(0, chosen)
            dialog.destroy()

        btn_row = ttk.Frame(dialog, style="TFrame")
        btn_row.pack(fill="x", padx=16, pady=12)
        ttk.Button(btn_row, text="Use selected", style="Accent.TButton", command=use_selected).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(btn_row, text="Close", command=dialog.destroy).pack(side="left")
        listbox.bind("<Double-Button-1>", lambda _e: use_selected())

    def make_plan(self) -> None:
        goal = self.goal_entry.get().strip()
        if not goal:
            return
        record_goal(self._runtime.memory, goal)
        self._log(f"\nYou> {goal}\n")
        plan = self._runtime.planner.plan(goal)
        self._runtime.audit.record("plan_created", plan.rationale or plan.goal, plan_id=plan.id, goal=goal)
        matched = self._runtime.broker.find_matching_routine(plan)
        self._plan = plan
        self._matched_trusted = matched is not None
        self._log(format_plan(plan) + "\n")
        if matched is not None:
            self.routine_name_var.set(f"Trusted: {matched.name}")
            self._log(f"Trusted routine matched: '{matched.name}' — Approve runs without re-scoping.\n")
        else:
            self.routine_name_var.set("")
            self._log("Review the plan, then Approve & run or Reject.\n")

    def reject_plan(self) -> None:
        if self._plan is None:
            return
        self._runtime.audit.record("plan_rejected", "User rejected plan", plan_id=self._plan.id)
        self._log("Plan rejected.\n")
        self._plan = None
        self._matched_trusted = False
        self.routine_name_var.set("")

    def emergency_stop(self) -> None:
        if not self._run_busy:
            return
        self._runtime.broker.request_stop()
        self._stop_var.set("Stopping…")
        self._log("Emergency stop requested — remaining steps will be skipped.\n")

    def approve_run(self) -> None:
        plan = self._plan
        if plan is None:
            messagebox.showinfo("Arbora", "Create a plan first.")
            return
        if self._run_busy:
            messagebox.showinfo("Arbora", "A plan is already running. Use Stop to halt it.")
            return

        hard_ids = frozenset()
        if plan.has_hard_confirmation_steps:
            ok = messagebox.askyesno(
                "Hard confirmation",
                "This plan includes destructive/credential/financial steps.\n"
                "Explicitly confirm those sensitive steps?",
            )
            if ok:
                hard_ids = hard_confirm_ids_for(plan, True)
            else:
                hard_step_ids = {s.id for s in plan.steps if s.requires_hard_confirmation()}
                decision = ApprovalDecision(
                    plan_id=plan.id,
                    approved_step_ids=frozenset(s.id for s in plan.steps if s.id not in hard_step_ids),
                    rejected_step_ids=frozenset(hard_step_ids),
                )
                self._start_execution(plan, decision, hard_ids=frozenset(), promote=False, promote_name=None)
                return

        promote = self.promote_var.get() and not self._matched_trusted
        promote_name = None
        if promote:
            promote_name = self._ask_routine_name() or "unnamed-routine"

        decision = approve_all(plan, promote_to_trusted=promote, trusted_name=promote_name)
        self._start_execution(plan, decision, hard_ids=hard_ids, promote=promote, promote_name=promote_name)

    def _start_execution(
        self,
        plan: Plan,
        decision: ApprovalDecision,
        *,
        hard_ids: frozenset[str],
        promote: bool,
        promote_name: str | None,
    ) -> None:
        self._run_busy = True
        self._stop_var.set("Running…")
        self._approve_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal")
        dry_run = self.dry_run_var.get()

        def work() -> None:
            try:
                results = self._runtime.broker.execute_plan(
                    plan,
                    decision,
                    dry_run=dry_run,
                    hard_confirmed_step_ids=hard_ids,
                )
                report = ExecutionReport(plan_id=plan.id, results=results)
                if promote and not self._runtime.broker.stop_requested:
                    persist_routines(self._runtime)
                self._runtime.memory.set("last_goal", plan.goal)
                self._runtime.memory.set("last_plan_id", plan.id)
                stopped = any(
                    (r.error or "").startswith("Emergency stop") for r in results
                )
                self.root.after(0, lambda: self._finish_execution(report, stopped=stopped))
            except Exception as exc:
                self.root.after(0, lambda: self._finish_execution_error(str(exc)))

        threading.Thread(target=work, daemon=True).start()

    def _finish_execution(self, report: ExecutionReport, *, stopped: bool) -> None:
        self._run_busy = False
        self._approve_btn.configure(state="normal")
        self._stop_btn.configure(state="disabled")
        self._stop_var.set("Stopped." if stopped else "")
        self._print_report(report)
        if stopped:
            self._log("Plan halted by emergency stop.\n")
        self._plan = None
        self._matched_trusted = False
        self.routine_name_var.set("")

    def _finish_execution_error(self, message: str) -> None:
        self._run_busy = False
        self._approve_btn.configure(state="normal")
        self._stop_btn.configure(state="disabled")
        self._stop_var.set("")
        self._log(f"Execution error: {message}\n")
        messagebox.showerror("Arbora", message)

    def _ask_routine_name(self) -> str | None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Trusted routine")
        dialog.configure(bg=COLORS["bg"])
        dialog.transient(self.root)
        dialog.grab_set()
        ttk.Label(dialog, text="Routine name").pack(padx=16, pady=(16, 4))
        var = tk.StringVar(value="my-routine")
        entry = tk.Entry(dialog, textvariable=var, bg=COLORS["input_bg"], fg=COLORS["ink"], relief="flat")
        entry.pack(padx=16, pady=4, fill="x")
        entry.focus_set()
        result: dict[str, str | None] = {"name": None}

        def ok() -> None:
            result["name"] = var.get().strip()
            dialog.destroy()

        def cancel() -> None:
            dialog.destroy()

        row = ttk.Frame(dialog)
        row.pack(pady=12)
        ttk.Button(row, text="Save", style="Accent.TButton", command=ok).pack(side="left", padx=4)
        ttk.Button(row, text="Cancel", command=cancel).pack(side="left", padx=4)
        dialog.wait_window()
        return result["name"]

    def _print_report(self, report: ExecutionReport) -> None:
        lines = ["\nExecution report:"]
        for result in report.results:
            status = "OK" if result.ok else "FAIL"
            mode = "dry-run" if result.dry_run else "live"
            lines.append(f"  [{status}/{mode}] step={result.step_id}")
            if result.output:
                for line in result.output.splitlines()[:20]:
                    lines.append(f"    {line}")
            if result.error:
                lines.append(f"    error: {result.error}")
        lines.append(f"Overall: {'success' if report.all_ok else 'completed with failures'}\n")
        self._log("\n".join(lines))

    def show_routines(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Trusted routines")
        dialog.configure(bg=COLORS["bg"])
        dialog.transient(self.root)
        dialog.geometry("560x360")
        dialog.grab_set()

        ttk.Label(dialog, text="Trusted routines", style="Brand.TLabel").pack(
            anchor="w", padx=16, pady=(16, 4)
        )
        ttk.Label(
            dialog,
            text="Inspect and revoke routines. Hard-confirmation classes still apply after trust.",
            style="Muted.TLabel",
            wraplength=520,
        ).pack(anchor="w", padx=16, pady=(0, 8))

        list_frame = ttk.Frame(dialog, style="TFrame")
        list_frame.pack(fill="both", expand=True, padx=16, pady=4)
        listbox = tk.Listbox(
            list_frame,
            bg=COLORS["panel"],
            fg=COLORS["ink"],
            selectbackground=COLORS["accent_dim"],
            relief="flat",
            font=self.font_mono,
            activestyle="none",
        )
        listbox.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=listbox.yview)
        scroll.pack(side="right", fill="y")
        listbox.configure(yscrollcommand=scroll.set)

        detail_var = tk.StringVar(value="Select a routine.")
        ttk.Label(dialog, textvariable=detail_var, style="Muted.TLabel", wraplength=520).pack(
            anchor="w", padx=16, pady=4
        )

        routines_by_index: list = []

        def refresh() -> None:
            routines_by_index.clear()
            listbox.delete(0, "end")
            routines = self._runtime.broker.list_routines()
            if not routines:
                detail_var.set(
                    "No trusted routines. Promote a successful plan, or restart to restore "
                    "read-only samples (list downloads, diagnose disk space) if you wiped memory."
                )
                return
            for routine in routines:
                routines_by_index.append(routine)
                listbox.insert("end", format_routine_rows([routine])[0])
            detail_var.set(f"{len(routines)} trusted routine(s). Select one to inspect or revoke.")

        def on_select(_event=None) -> None:
            sel = listbox.curselection()
            if not sel:
                return
            routine = routines_by_index[sel[0]]
            detail_var.set(format_routine_detail(routine))

        def revoke_selected() -> None:
            sel = listbox.curselection()
            if not sel:
                messagebox.showinfo("Trusted routines", "Select a routine to revoke.", parent=dialog)
                return
            routine = routines_by_index[sel[0]]
            ok = messagebox.askyesno(
                "Revoke routine",
                f"Revoke trusted routine '{routine.name}'?\n\nFuture matching plans will need approval again.",
                parent=dialog,
            )
            if not ok:
                return
            if self._runtime.broker.revoke_routine(routine.id):
                persist_routines(self._runtime)
                self._log(f"Revoked trusted routine: {routine.name} ({routine.id})\n")
                refresh()
            else:
                messagebox.showerror("Trusted routines", "Routine not found.", parent=dialog)

        listbox.bind("<<ListboxSelect>>", on_select)

        btn_row = ttk.Frame(dialog, style="TFrame")
        btn_row.pack(fill="x", padx=16, pady=12)
        ttk.Button(btn_row, text="Revoke selected", style="Accent.TButton", command=revoke_selected).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(btn_row, text="Refresh", command=refresh).pack(side="left", padx=(0, 8))
        ttk.Button(btn_row, text="Close", command=dialog.destroy).pack(side="left")

        refresh()

    def show_schedules(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Routine schedules")
        dialog.configure(bg=COLORS["bg"])
        dialog.transient(self.root)
        dialog.geometry("680x400")
        dialog.grab_set()

        ttk.Label(dialog, text="Routine schedules", style="Brand.TLabel").pack(
            anchor="w", padx=16, pady=(16, 4)
        )
        ttk.Label(
            dialog,
            text="Time triggers for already-trusted routines only. Defaults to dry-run.",
            style="Muted.TLabel",
            wraplength=640,
        ).pack(anchor="w", padx=16, pady=(0, 8))

        list_frame = ttk.Frame(dialog, style="TFrame")
        list_frame.pack(fill="both", expand=True, padx=16, pady=4)
        listbox = tk.Listbox(
            list_frame,
            bg=COLORS["panel"],
            fg=COLORS["ink"],
            selectbackground=COLORS["accent_dim"],
            relief="flat",
            font=self.font_mono,
            activestyle="none",
        )
        listbox.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=listbox.yview)
        scroll.pack(side="right", fill="y")
        listbox.configure(yscrollcommand=scroll.set)

        detail_var = tk.StringVar(value="Select a schedule.")
        ttk.Label(dialog, textvariable=detail_var, style="Muted.TLabel", wraplength=640).pack(
            anchor="w", padx=16, pady=4
        )

        schedules_by_index: list = []

        def refresh() -> None:
            schedules_by_index.clear()
            listbox.delete(0, "end")
            schedules = load_schedules(self._runtime.memory)
            if not schedules:
                detail_var.set("No schedules yet. Add one for a trusted routine.")
                return
            routines = self._runtime.broker.list_routines()
            rows = format_schedule_list(self._runtime.memory, routines)
            for index, schedule in enumerate(schedules):
                schedules_by_index.append(schedule)
                listbox.insert("end", rows[index])
            detail_var.set(f"{len(schedules)} schedule(s). Select one to remove or toggle.")

        def on_select(_event=None) -> None:
            sel = listbox.curselection()
            if not sel:
                return
            schedule = schedules_by_index[sel[0]]
            state = "enabled" if schedule.enabled else "disabled"
            mode = "dry-run" if schedule.dry_run else "live"
            detail_var.set(f"{schedule.id}  routine={schedule.routine_id}  {state}  {mode}")

        def add_schedule_dialog() -> None:
            routines = self._runtime.broker.list_routines()
            if not routines:
                messagebox.showinfo(
                    "Routine schedules",
                    "Promote a trusted routine first (Routines dialog).",
                    parent=dialog,
                )
                return

            sub = tk.Toplevel(dialog)
            sub.title("Add schedule")
            sub.configure(bg=COLORS["bg"])
            sub.transient(dialog)
            sub.grab_set()

            ttk.Label(sub, text="Trusted routine").pack(anchor="w", padx=16, pady=(16, 4))
            routine_var = tk.StringVar(value=routines[0].id)
            routine_menu = ttk.Combobox(
                sub,
                textvariable=routine_var,
                values=[f"{routine.name} ({routine.id})" for routine in routines],
                state="readonly",
            )
            routine_menu.current(0)
            routine_menu.pack(fill="x", padx=16, pady=4)

            ttk.Label(sub, text="Time (HH:MM, 24-hour)").pack(anchor="w", padx=16, pady=(8, 4))
            time_var = tk.StringVar(value="08:00")
            tk.Entry(sub, textvariable=time_var, bg=COLORS["input_bg"], fg=COLORS["ink"], relief="flat").pack(
                fill="x", padx=16, pady=4
            )

            ttk.Label(sub, text="Weekdays (optional, e.g. mon,fri)").pack(anchor="w", padx=16, pady=(8, 4))
            days_var = tk.StringVar(value="")
            tk.Entry(sub, textvariable=days_var, bg=COLORS["input_bg"], fg=COLORS["ink"], relief="flat").pack(
                fill="x", padx=16, pady=4
            )

            live_var = tk.BooleanVar(value=False)
            ttk.Checkbutton(sub, text="Run live (not dry-run)", variable=live_var).pack(anchor="w", padx=16, pady=8)

            def save() -> None:
                selected = routine_menu.current()
                if selected < 0:
                    messagebox.showerror("Routine schedules", "Select a routine.", parent=sub)
                    return
                routine = routines[selected]
                try:
                    schedule = add_schedule(
                        self._runtime.memory,
                        routine_id=routine.id,
                        time_hhmm=time_var.get().strip(),
                        days=days_var.get().strip() or None,
                        dry_run=not live_var.get(),
                    )
                except ValueError as exc:
                    messagebox.showerror("Routine schedules", str(exc), parent=sub)
                    return
                self._log(f"Added schedule {schedule.id} for routine {routine.name}\n")
                sub.destroy()
                refresh()

            row = ttk.Frame(sub, style="TFrame")
            row.pack(pady=12)
            ttk.Button(row, text="Save", style="Accent.TButton", command=save).pack(side="left", padx=4)
            ttk.Button(row, text="Cancel", command=sub.destroy).pack(side="left", padx=4)

        def remove_selected() -> None:
            sel = listbox.curselection()
            if not sel:
                messagebox.showinfo("Routine schedules", "Select a schedule to remove.", parent=dialog)
                return
            schedule = schedules_by_index[sel[0]]
            if not messagebox.askyesno(
                "Remove schedule",
                f"Remove schedule {schedule.id}?",
                parent=dialog,
            ):
                return
            if remove_schedule(self._runtime.memory, schedule.id):
                self._log(f"Removed schedule {schedule.id}\n")
                refresh()
            else:
                messagebox.showerror("Routine schedules", "Schedule not found.", parent=dialog)

        def toggle_enabled() -> None:
            sel = listbox.curselection()
            if not sel:
                messagebox.showinfo("Routine schedules", "Select a schedule to toggle.", parent=dialog)
                return
            schedule = schedules_by_index[sel[0]]
            schedules = load_schedules(self._runtime.memory)
            updated = [
                replace(row, enabled=not row.enabled) if row.id == schedule.id else row
                for row in schedules
            ]
            persist_schedules(self._runtime.memory, updated)
            self._log(f"Toggled schedule {schedule.id} enabled={not schedule.enabled}\n")
            refresh()

        listbox.bind("<<ListboxSelect>>", on_select)

        btn_row = ttk.Frame(dialog, style="TFrame")
        btn_row.pack(fill="x", padx=16, pady=12)
        ttk.Button(btn_row, text="Add", style="Accent.TButton", command=add_schedule_dialog).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(btn_row, text="Toggle enabled", command=toggle_enabled).pack(side="left", padx=(0, 8))
        ttk.Button(btn_row, text="Remove", command=remove_selected).pack(side="left", padx=(0, 8))
        ttk.Button(btn_row, text="Refresh", command=refresh).pack(side="left", padx=(0, 8))
        ttk.Button(btn_row, text="Close", command=dialog.destroy).pack(side="left")

        refresh()

    def show_audit(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Audit log")
        dialog.configure(bg=COLORS["bg"])
        dialog.transient(self.root)
        dialog.geometry("640x420")
        dialog.grab_set()

        ttk.Label(dialog, text="Audit log", style="Brand.TLabel").pack(anchor="w", padx=16, pady=(16, 4))
        ttk.Label(
            dialog,
            text="Recent approvals, tool outcomes, and trust changes (persisted locally).",
            style="Muted.TLabel",
            wraplength=600,
        ).pack(anchor="w", padx=16, pady=(0, 8))

        text = tk.Text(
            dialog,
            wrap="word",
            bg=COLORS["panel"],
            fg=COLORS["ink"],
            relief="flat",
            font=self.font_mono,
            padx=10,
            pady=8,
        )
        text.pack(fill="both", expand=True, padx=16, pady=4)

        def refresh() -> None:
            events = self._runtime.audit.events()[-40:]
            text.configure(state="normal")
            text.delete("1.0", "end")
            text.insert("1.0", format_audit_events(events))
            text.configure(state="disabled")
            text.see("end")

        def export_audit() -> None:
            default_name = f"arbora-audit-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
            path = filedialog.asksaveasfilename(
                parent=dialog,
                title="Export audit log",
                defaultextension=".json",
                initialfile=default_name,
                filetypes=[("JSON", "*.json"), ("All files", "*.*")],
            )
            if not path:
                return
            payload = export_audit_payload(self._runtime.memory)
            out_path = Path(path)
            out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            messagebox.showinfo("Audit log", f"Exported {len(payload)} event(s) to:\n{out_path}", parent=dialog)

        btn_row = ttk.Frame(dialog, style="TFrame")
        btn_row.pack(fill="x", padx=16, pady=12)
        ttk.Button(btn_row, text="Export JSON", command=export_audit).pack(side="left", padx=(0, 8))
        ttk.Button(btn_row, text="Refresh", command=refresh).pack(side="left", padx=(0, 8))
        ttk.Button(btn_row, text="Close", command=dialog.destroy).pack(side="left")

        refresh()

    def show_memory(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Local memory")
        dialog.configure(bg=COLORS["bg"])
        dialog.transient(self.root)
        dialog.geometry("640x360")
        dialog.grab_set()

        ttk.Label(dialog, text="Local memory", style="Brand.TLabel").pack(anchor="w", padx=16, pady=(16, 4))
        ttk.Label(
            dialog,
            text="Encrypted on this machine. Export writes JSON without encryption keys.",
            style="Muted.TLabel",
            wraplength=600,
        ).pack(anchor="w", padx=16, pady=(0, 8))

        text = tk.Text(
            dialog,
            wrap="word",
            bg=COLORS["panel"],
            fg=COLORS["ink"],
            relief="flat",
            font=self.font_mono,
            padx=10,
            pady=8,
        )
        text.pack(fill="both", expand=True, padx=16, pady=4)

        def refresh() -> None:
            text.configure(state="normal")
            text.delete("1.0", "end")
            text.insert("1.0", format_memory_status(self._runtime.memory))
            text.configure(state="disabled")

        def export_memory() -> None:
            default_name = f"arbora-memory-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
            path = filedialog.asksaveasfilename(
                parent=dialog,
                title="Export local memory",
                defaultextension=".json",
                initialfile=default_name,
                filetypes=[("JSON", "*.json"), ("All files", "*.*")],
            )
            if not path:
                return
            payload = export_memory_payload(self._runtime.memory)
            out_path = Path(path)
            out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            count = len(payload.get("data", {}))
            messagebox.showinfo("Local memory", f"Exported {count} key(s) to:\n{out_path}", parent=dialog)

        btn_row = ttk.Frame(dialog, style="TFrame")
        btn_row.pack(fill="x", padx=16, pady=12)
        ttk.Button(btn_row, text="Export JSON", command=export_memory).pack(side="left", padx=(0, 8))
        ttk.Button(btn_row, text="Refresh", command=refresh).pack(side="left", padx=(0, 8))
        ttk.Button(btn_row, text="Close", command=dialog.destroy).pack(side="left")

        refresh()


def main() -> int:
    root = tk.Tk()
    ArboraChatApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
