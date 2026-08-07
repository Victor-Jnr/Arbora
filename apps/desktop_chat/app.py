"""Tkinter desktop chat shell for Arbora."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from arbora.cli.session import (
    approve_all,
    build_runtime,
    format_plan,
    hard_confirm_ids_for,
    persist_routines,
)
from arbora.core.types import ApprovalDecision, ExecutionReport, Plan


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


class ArboraChatApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Arbora")
        self.root.geometry("920x680")
        self.root.minsize(720, 520)
        self.root.configure(bg=COLORS["bg"])

        self.provider_var = tk.StringVar(value="echo")
        self.dry_run_var = tk.BooleanVar(value=True)
        self.promote_var = tk.BooleanVar(value=False)
        self.routine_name_var = tk.StringVar(value="")
        self._runtime = build_runtime(provider=self.provider_var.get())
        self._plan: Plan | None = None
        self._matched_trusted = False

        self._build_style()
        self._build_ui()
        self._log(
            "Arbora ready.\nModels propose; the permission broker disposes.\n"
            f"Provider: {self._runtime.provider_name} | "
            f"Memory: {self._runtime.memory.key_backend}\n"
        )

    def _build_style(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        font_ui = ("Segoe UI Variable", 11)
        font_brand = ("Cascadia Mono", 28, "bold")
        font_mono = ("Cascadia Mono", 10)
        # Fallbacks if Cascadia missing.
        try:
            self.root.tk.call("font", "create", "ArboraBrand", "-family", "Cascadia Mono", "-size", 28, "-weight", "bold")
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
        style.map("Accent.TButton", background=[("active", COLORS["accent"])])
        style.configure("TCheckbutton", background=COLORS["bg"], foreground=COLORS["ink"], font=font_ui)
        style.configure("TCombobox", fieldbackground=COLORS["input_bg"], foreground=COLORS["ink"])

    def _build_ui(self) -> None:
        header = ttk.Frame(self.root, style="TFrame")
        header.pack(fill="x", padx=24, pady=(20, 8))
        ttk.Label(header, text="Arbora", style="Brand.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Personal Windows assistant — plan, approve, execute under your rules.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(4, 0))

        controls = ttk.Frame(self.root, style="TFrame")
        controls.pack(fill="x", padx=24, pady=8)
        ttk.Label(controls, text="Provider").pack(side="left")
        provider = ttk.Combobox(
            controls,
            textvariable=self.provider_var,
            values=("echo", "ollama"),
            width=10,
            state="readonly",
        )
        provider.pack(side="left", padx=(8, 16))
        provider.bind("<<ComboboxSelected>>", self._on_provider_change)
        ttk.Checkbutton(controls, text="Dry-run", variable=self.dry_run_var).pack(side="left", padx=(0, 16))
        ttk.Checkbutton(controls, text="Promote after success", variable=self.promote_var).pack(side="left")

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
        ttk.Button(entry_row, text="Plan", style="Accent.TButton", command=self.make_plan).pack(side="left")

        actions = ttk.Frame(self.root, style="TFrame")
        actions.pack(fill="x", padx=24, pady=(0, 20))
        ttk.Button(actions, text="Approve & run", style="Accent.TButton", command=self.approve_run).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(actions, text="Reject", command=self.reject_plan).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Routines", command=self.show_routines).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Audit", command=self.show_audit).pack(side="left")
        ttk.Label(actions, textvariable=self.routine_name_var, style="Muted.TLabel").pack(side="right")

    def _on_provider_change(self, _event=None) -> None:
        self._runtime = build_runtime(provider=self.provider_var.get())
        self._plan = None
        self._matched_trusted = False
        self._log(f"Switched provider to {self._runtime.provider_name}\n")

    def _log(self, text: str) -> None:
        self.transcript.configure(state="normal")
        self.transcript.insert("end", text if text.endswith("\n") else text + "\n")
        self.transcript.see("end")
        self.transcript.configure(state="disabled")

    def make_plan(self) -> None:
        goal = self.goal_entry.get().strip()
        if not goal:
            return
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

    def approve_run(self) -> None:
        plan = self._plan
        if plan is None:
            messagebox.showinfo("Arbora", "Create a plan first.")
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
                results = self._runtime.broker.execute_plan(
                    plan,
                    decision,
                    dry_run=self.dry_run_var.get(),
                    hard_confirmed_step_ids=frozenset(),
                )
                self._print_report(ExecutionReport(plan_id=plan.id, results=results))
                return

        promote = self.promote_var.get() and not self._matched_trusted
        promote_name = None
        if promote:
            promote_name = self._ask_routine_name() or "unnamed-routine"

        decision = approve_all(plan, promote_to_trusted=promote, trusted_name=promote_name)
        results = self._runtime.broker.execute_plan(
            plan,
            decision,
            dry_run=self.dry_run_var.get(),
            hard_confirmed_step_ids=hard_ids,
        )
        report = ExecutionReport(plan_id=plan.id, results=results)
        if promote:
            persist_routines(self._runtime)
        self._runtime.memory.set("last_goal", plan.goal)
        self._runtime.memory.set("last_plan_id", plan.id)
        self._print_report(report)
        self._plan = None
        self._matched_trusted = False
        self.routine_name_var.set("")

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
        routines = self._runtime.broker.list_routines()
        if not routines:
            self._log("(no trusted routines)\n")
            return
        lines = ["Trusted routines:"]
        for routine in routines:
            lines.append(f"  {routine.id}  {routine.name}  fp={routine.plan_fingerprint}")
        self._log("\n".join(lines) + "\n")

    def show_audit(self) -> None:
        events = self._runtime.audit.events()[-15:]
        if not events:
            self._log("(audit log empty)\n")
            return
        lines = ["Recent audit:"]
        for event in events:
            lines.append(f"  [{event.kind}] {event.message}")
        self._log("\n".join(lines) + "\n")


def main() -> int:
    root = tk.Tk()
    ArboraChatApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
