from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk
from PIL import Image

from app.constants import (
    APP_NAME,
    APP_TITLE,
    BUNDLED_LOGO_PATH,
    DEFAULT_SHEET_NAME,
    LOGO_PATH,
    MANUAL_STATUSES,
    MASTER_CATEGORY_PIPELINE_STATUS,
    MASTER_CATEGORY_PRIORITY_STAGE,
    MASTER_CATEGORY_TASK_STATUS,
    PALETTE,
    PIPELINE_STATUSES,
    PRIORITY_STAGES,
    TASK_PRIORITIES,
)
from app.database import DatabaseManager
from app.services.core import (
    DashboardService,
    ExcelImportService,
    MasterDataService,
    OpportunityService,
    TaskService,
    UserService,
    ValidationError,
)


ctk.set_appearance_mode("light")


def join_meta(*parts: str) -> str:
    return " | ".join(part for part in parts if part)


def title_case_health(health: str) -> str:
    return health if health else "No Status"


def truncate_text(text: str | None, limit: int) -> str:
    clean = " ".join((text or "").split())
    if len(clean) <= limit:
        return clean
    return clean[: max(0, limit - 3)].rstrip() + "..."


def bind_click(widget, callback):
    widget.bind("<Button-1>", callback)


def resolve_logo_path() -> Path | None:
    for candidate in (BUNDLED_LOGO_PATH, LOGO_PATH):
        if Path(candidate).exists():
            return Path(candidate)
    return None


class HoverTip:
    def __init__(self, widget, text: str):
        self.widget = widget
        self.text = text
        self.tip_window: tk.Toplevel | None = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, _event=None):
        if self.tip_window or not self.text.strip():
            return
        root_x = self.widget.winfo_rootx()
        root_y = self.widget.winfo_rooty()
        height = self.widget.winfo_height()
        self.tip_window = tk.Toplevel(self.widget)
        self.tip_window.wm_overrideredirect(True)
        self.tip_window.configure(bg=PALETTE["ink_900"])
        self.tip_window.geometry(f"+{root_x + 12}+{root_y + height + 8}")
        label = tk.Label(
            self.tip_window,
            text=self.text,
            justify="left",
            bg=PALETTE["ink_900"],
            fg="white",
            padx=10,
            pady=6,
            wraplength=420,
        )
        label.pack()

    def hide(self, _event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


class TaskMNGApp(ctk.CTk):
    def __init__(self, db: DatabaseManager | None = None):
        super().__init__()
        self.db = db or DatabaseManager()
        self.db.initialize()
        self.title(APP_TITLE)
        self.geometry("1500x920")
        self.minsize(1220, 800)
        self.configure(fg_color=PALETTE["surface_1"])

        self.dashboard_service = DashboardService(self.db)
        self.opportunity_service = OpportunityService(self.db)
        self.task_service = TaskService(self.db)
        self.user_service = UserService(self.db)
        self.import_service = ExcelImportService(self.db)
        self.master_data_service = MasterDataService(self.db)

        self.current_view: str | None = None
        self.views: dict[str, BaseView] = {}
        self.toast_frame: ctk.CTkFrame | None = None
        self.toast_after_id: str | None = None
        self.sidebar_collapsed = False
        self.nav_button_labels = {
            "dashboard": ("Dashboard", "D"),
            "opportunities": ("Opportunities", "O"),
            "board": ("Task Board", "T"),
            "settings": ("Settings", "S"),
        }
        self.window_icon = None
        self.brand_logo_large = None
        self.brand_logo_small = None

        self._load_brand_assets()
        self._build_shell()
        self.show_view("dashboard")

    def _load_brand_assets(self):
        logo_path = resolve_logo_path()
        if not logo_path:
            return
        self.window_icon = tk.PhotoImage(file=str(logo_path))
        self.iconphoto(False, self.window_icon)
        image = Image.open(logo_path)
        self.brand_logo_large = ctk.CTkImage(light_image=image, dark_image=image, size=(76, 76))
        self.brand_logo_small = ctk.CTkImage(light_image=image, dark_image=image, size=(34, 34))

    def apply_window_icon(self, window):
        if self.window_icon is not None:
            window.iconphoto(False, self.window_icon)

    def _build_shell(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0, fg_color=PALETTE["surface_0"])
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        self.sidebar_top = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.sidebar_top.pack(fill="x", padx=18, pady=(16, 10))
        self.sidebar_top.grid_columnconfigure(0, weight=1)
        self.toggle_button = ctk.CTkButton(
            self.sidebar_top,
            text="<<",
            width=38,
            height=34,
            corner_radius=12,
            fg_color=PALETTE["surface_2"],
            text_color=PALETTE["ink_900"],
            command=self.toggle_sidebar,
        )
        self.toggle_button.grid(row=0, column=1, sticky="e")

        self.brand = ctk.CTkFrame(self.sidebar, fg_color=PALETTE["primary_700"], corner_radius=24)
        self.brand.pack(fill="x", padx=18, pady=(0, 14))
        self.brand.grid_columnconfigure(1, weight=1)

        self.brand_logo = ctk.CTkLabel(self.brand, text="", image=self.brand_logo_large)
        self.brand_logo.grid(row=0, column=0, rowspan=2, padx=(18, 14), pady=18, sticky="w")
        self.brand_title = ctk.CTkLabel(
            self.brand,
            text=APP_NAME,
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="white",
        )
        self.brand_title.grid(row=0, column=1, sticky="sw", padx=(0, 18), pady=(18, 4))
        self.brand_subtitle = ctk.CTkLabel(
            self.brand,
            text="Local-first desktop workflow",
            font=ctk.CTkFont(size=13),
            text_color="#EEF0FF",
            justify="left",
        )
        self.brand_subtitle.grid(row=1, column=1, sticky="nw", padx=(0, 18), pady=(0, 18))

        self.nav_buttons: dict[str, ctk.CTkButton] = {}
        for key, (label, _short) in self.nav_button_labels.items():
            button = ctk.CTkButton(
                self.sidebar,
                text=label,
                anchor="w",
                height=42,
                corner_radius=14,
                fg_color="transparent",
                hover_color=PALETTE["surface_2"],
                text_color=PALETTE["ink_900"],
                command=lambda name=key: self.show_view(name),
            )
            button.pack(fill="x", padx=16, pady=4)
            self.nav_buttons[key] = button

        self.footer = ctk.CTkLabel(
            self.sidebar,
            text="Theme: violet to lilac\nData: local SQLite",
            justify="left",
            text_color=PALETTE["ink_700"],
        )
        self.footer.pack(side="bottom", anchor="w", padx=18, pady=18)

        self.content = ctk.CTkFrame(self, fg_color=PALETTE["surface_1"], corner_radius=0)
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        self.views["dashboard"] = DashboardView(self.content, self)
        self.views["opportunities"] = OpportunitiesView(self.content, self)
        self.views["board"] = BoardView(self.content, self)
        self.views["settings"] = SettingsView(self.content, self)

        for view in self.views.values():
            view.grid(row=0, column=0, sticky="nsew")

    def toggle_sidebar(self):
        self.sidebar_collapsed = not self.sidebar_collapsed
        collapsed = self.sidebar_collapsed
        self.sidebar.configure(width=92 if collapsed else 250)
        self.toggle_button.configure(text=">>" if collapsed else "<<")
        self.brand_logo.configure(image=self.brand_logo_small if collapsed else self.brand_logo_large)
        self.brand_title.configure(text="E" if collapsed else APP_NAME, font=ctk.CTkFont(size=20 if collapsed else 24, weight="bold"))
        self.brand_subtitle.configure(text="" if collapsed else "Local-first desktop workflow")
        self.footer.configure(text="" if collapsed else "Theme: violet to lilac\nData: local SQLite")
        for key, button in self.nav_buttons.items():
            full, short = self.nav_button_labels[key]
            button.configure(text=short if collapsed else full, anchor="center" if collapsed else "w")
        self.update_idletasks()

    def show_view(self, name: str):
        self.current_view = name
        self.views[name].tkraise()
        self.views[name].refresh()
        for key, button in self.nav_buttons.items():
            button.configure(
                fg_color=PALETTE["primary_500"] if key == name else "transparent",
                text_color="white" if key == name else PALETTE["ink_900"],
            )

    def refresh_views(self, *names: str):
        targets = names or tuple(self.views.keys())
        for name in targets:
            if name in self.views:
                self.views[name].refresh()

    def show_toast(self, message: str, level: str = "info"):
        colors = {
            "info": (PALETTE["primary_700"], "white"),
            "success": (PALETTE["success"], "white"),
            "warning": (PALETTE["warning"], PALETTE["ink_900"]),
            "error": (PALETTE["danger"], "white"),
        }
        bg_color, text_color = colors.get(level, colors["info"])
        if self.toast_after_id:
            self.after_cancel(self.toast_after_id)
            self.toast_after_id = None
        if self.toast_frame:
            self.toast_frame.destroy()
            self.toast_frame = None

        self.toast_frame = ctk.CTkFrame(self.content, fg_color=bg_color, corner_radius=18)
        self.toast_frame.place(relx=1.0, x=-24, y=20, anchor="ne")
        ctk.CTkLabel(
            self.toast_frame,
            text=message,
            text_color=text_color,
            justify="left",
            wraplength=460,
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(padx=18, pady=12)

        def _hide():
            if self.toast_frame:
                self.toast_frame.destroy()
                self.toast_frame = None
            self.toast_after_id = None

        self.toast_after_id = self.after(10000, _hide)


class BaseView(ctk.CTkFrame):
    def __init__(self, master, app: TaskMNGApp):
        super().__init__(master, fg_color=PALETTE["surface_1"], corner_radius=0)
        self.app = app

    def refresh(self):
        return None

    def toast(self, message: str, level: str = "info"):
        self.app.show_toast(message, level)


class DashboardView(BaseView):
    def __init__(self, master, app: TaskMNGApp):
        super().__init__(master, app)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.hero = ctk.CTkFrame(self, fg_color=PALETTE["primary_700"], corner_radius=28)
        self.hero.grid(row=0, column=0, padx=24, pady=(24, 18), sticky="ew")
        self.hero.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            self.hero,
            text="Daily control center",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="white",
        ).grid(row=0, column=0, sticky="w", padx=24, pady=(20, 6))
        ctk.CTkLabel(
            self.hero,
            text="Track overdue work, due-soon actions, and recent momentum in one place.",
            text_color="#EEF0FF",
        ).grid(row=1, column=0, sticky="w", padx=24, pady=(0, 20))

        self.kpi_row = ctk.CTkFrame(self, fg_color="transparent")
        self.kpi_row.grid(row=1, column=0, padx=24, sticky="ew")
        self.kpi_row.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.kpi_labels: dict[str, ctk.CTkLabel] = {}
        for idx, label in enumerate(("Opportunities", "Tasks", "Overdue", "Due Soon")):
            card = ctk.CTkFrame(self.kpi_row, fg_color=PALETTE["surface_0"], border_width=1, border_color=PALETTE["border_soft"])
            card.grid(row=0, column=idx, padx=(0 if idx == 0 else 12, 0), pady=8, sticky="nsew")
            ctk.CTkLabel(card, text=label, text_color=PALETTE["ink_700"]).pack(anchor="w", padx=18, pady=(16, 8))
            value = ctk.CTkLabel(card, text="0", font=ctk.CTkFont(size=26, weight="bold"), text_color=PALETTE["ink_900"])
            value.pack(anchor="w", padx=18, pady=(0, 16))
            self.kpi_labels[label] = value

        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.grid(row=2, column=0, padx=24, pady=(10, 24), sticky="nsew")
        self.body.grid_columnconfigure((0, 1), weight=1)
        self.body.grid_rowconfigure(0, weight=1)

        self.overdue_panel = ItemListPanel(self.body, "Overdue Tasks")
        self.overdue_panel.grid(row=0, column=0, padx=(0, 12), sticky="nsew")
        self.recent_panel = ItemListPanel(self.body, "Recent Tasks")
        self.recent_panel.grid(row=0, column=1, padx=(12, 0), sticky="nsew")

    def refresh(self):
        metrics = self.app.dashboard_service.metrics()
        self.kpi_labels["Opportunities"].configure(text=str(metrics["opportunity_count"]))
        self.kpi_labels["Tasks"].configure(text=str(metrics["task_count"]))
        self.kpi_labels["Overdue"].configure(text=str(metrics["overdue_count"]))
        self.kpi_labels["Due Soon"].configure(text=str(metrics["due_soon_count"]))
        self.overdue_panel.render_items(metrics["overdue_tasks"], mode="health")
        self.recent_panel.render_items(metrics["recent_tasks"], mode="status")


class OpportunitiesView(BaseView):
    def __init__(self, master, app: TaskMNGApp):
        super().__init__(master, app)
        self.selected_opportunity_id: int | None = None
        self.selected_stage_id: int | None = None
        self.selected_task_id: int | None = None
        self.current_tasks: list[dict] = []
        self.current_opportunity: dict | None = None
        self.current_stages: list[dict] = []
        self.search_var = tk.StringVar()

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=2, padx=24, pady=(24, 12), sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="Opportunities", font=ctk.CTkFont(size=28, weight="bold"), text_color=PALETTE["ink_900"]).grid(
            row=0, column=0, sticky="w"
        )
        actions = ctk.CTkFrame(header, fg_color="transparent")
        actions.grid(row=0, column=1, sticky="e")
        action_specs = (
            ("Import Excel", self.import_excel, True),
            ("New Opportunity", self.open_new_opportunity, True),
            ("Add Stage-Status", self.open_new_stage, False),
            ("Add Task", self.open_new_task, False),
        )
        for idx, (label, command, primary) in enumerate(action_specs):
            ctk.CTkButton(
                actions,
                text=label,
                height=36,
                corner_radius=14,
                fg_color=PALETTE["primary_500"] if primary else PALETTE["surface_0"],
                text_color="white" if primary else PALETTE["ink_900"],
                border_width=0 if primary else 1,
                border_color=PALETTE["border_soft"],
                command=command,
            ).grid(row=0, column=idx, padx=(0, 10))

        self.list_panel = ctk.CTkFrame(self, fg_color=PALETTE["surface_0"], border_width=1, border_color=PALETTE["border_soft"])
        self.list_panel.grid(row=1, column=0, padx=(24, 12), pady=(0, 24), sticky="nsew")
        self.list_panel.grid_columnconfigure(0, weight=1)
        self.list_panel.grid_rowconfigure(2, weight=1)
        ctk.CTkLabel(self.list_panel, text="Opportunity List", font=ctk.CTkFont(size=18, weight="bold"), text_color=PALETTE["ink_900"]).grid(
            row=0, column=0, sticky="w", padx=18, pady=(18, 10)
        )
        self.search_entry = ctk.CTkEntry(self.list_panel, textvariable=self.search_var, placeholder_text="Search opportunity")
        self.search_entry.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 10))
        self.search_entry.bind("<KeyRelease>", lambda _event: self.render_opportunities())
        self.list_scroll = ctk.CTkScrollableFrame(self.list_panel, fg_color=PALETTE["surface_1"])
        self.list_scroll.grid(row=2, column=0, padx=12, pady=(0, 12), sticky="nsew")

        self.detail_panel = ctk.CTkFrame(self, fg_color=PALETTE["surface_0"], border_width=1, border_color=PALETTE["border_soft"])
        self.detail_panel.grid(row=1, column=1, padx=(12, 24), pady=(0, 24), sticky="nsew")
        self.detail_panel.grid_columnconfigure(0, weight=1)
        self.detail_panel.grid_rowconfigure(5, weight=1)

        self.summary_title = ctk.CTkLabel(
            self.detail_panel,
            text="Select an opportunity",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=PALETTE["ink_900"],
        )
        self.summary_title.grid(row=0, column=0, sticky="w", padx=18, pady=(18, 6))
        self.summary_meta = ctk.CTkLabel(self.detail_panel, text="", text_color=PALETTE["ink_700"], justify="left")
        self.summary_meta.grid(row=1, column=0, sticky="w", padx=18)

        self.detail_actions = ctk.CTkFrame(self.detail_panel, fg_color="transparent")
        self.detail_actions.grid(row=2, column=0, sticky="ew", padx=18, pady=(14, 10))
        self.detail_actions.grid_columnconfigure(6, weight=1)
        self.edit_opp_button = ctk.CTkButton(self.detail_actions, text="Edit Opportunity", command=self.open_edit_opportunity)
        self.edit_opp_button.grid(row=0, column=0, padx=(0, 8))
        self.delete_opp_button = ctk.CTkButton(
            self.detail_actions,
            text="Delete Opportunity",
            fg_color=PALETTE["danger"],
            hover_color="#B94E66",
            command=self.confirm_delete_opportunity,
        )
        self.delete_opp_button.grid(row=0, column=1, padx=(0, 12))
        self.edit_stage_button = ctk.CTkButton(self.detail_actions, text="Edit Stage", command=self.open_edit_stage)
        self.edit_stage_button.grid(row=0, column=2, padx=(0, 8))
        self.delete_stage_button = ctk.CTkButton(
            self.detail_actions,
            text="Delete Stage",
            fg_color=PALETTE["danger"],
            hover_color="#B94E66",
            command=self.confirm_delete_stage,
        )
        self.delete_stage_button.grid(row=0, column=3, padx=(0, 12))
        self.edit_task_button = ctk.CTkButton(self.detail_actions, text="Edit Task", command=self.open_edit_task)
        self.edit_task_button.grid(row=0, column=4, padx=(0, 8))
        self.delete_task_button = ctk.CTkButton(
            self.detail_actions,
            text="Delete Task",
            fg_color=PALETTE["danger"],
            hover_color="#B94E66",
            command=self.confirm_delete_task,
        )
        self.delete_task_button.grid(row=0, column=5)

        self.stage_summary = ctk.CTkLabel(self.detail_panel, text="", text_color=PALETTE["ink_700"], justify="left")
        self.stage_summary.grid(row=3, column=0, sticky="w", padx=18, pady=(0, 10))

        self.task_focus = ctk.CTkFrame(self.detail_panel, fg_color=PALETTE["surface_1"], border_width=1, border_color=PALETTE["border_soft"])
        self.task_focus.grid(row=4, column=0, sticky="ew", padx=18, pady=(0, 10))
        self.task_focus.grid_columnconfigure(0, weight=1)
        self.task_focus_title = ctk.CTkLabel(
            self.task_focus,
            text="Select a task",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=PALETTE["ink_900"],
        )
        self.task_focus_title.grid(row=0, column=0, sticky="w", padx=14, pady=(12, 4))
        self.task_focus_meta = ctk.CTkLabel(self.task_focus, text="", justify="left", text_color=PALETTE["ink_700"])
        self.task_focus_meta.grid(row=1, column=0, sticky="w", padx=14, pady=(0, 12))

        self.stage_sections = ctk.CTkScrollableFrame(self.detail_panel, fg_color=PALETTE["surface_1"])
        self.stage_sections.grid(row=5, column=0, sticky="nsew", padx=18, pady=(0, 18))

    def refresh(self):
        opportunities = self.app.opportunity_service.list_opportunities()
        if opportunities and self.selected_opportunity_id is None:
            self.selected_opportunity_id = opportunities[0]["id"]
        visible_ids = {opportunity["id"] for opportunity in opportunities}
        if self.selected_opportunity_id and self.selected_opportunity_id not in visible_ids:
            self.selected_opportunity_id = opportunities[0]["id"] if opportunities else None
        self.render_opportunities()
        if self.selected_opportunity_id:
            self.load_detail(self.selected_opportunity_id, reselect_stage=True)
        else:
            self.clear_detail()

    def clear_detail(self):
        self.current_opportunity = None
        self.current_stages = []
        self.current_tasks = []
        self.selected_stage_id = None
        self.selected_task_id = None
        self.summary_title.configure(text="Select an opportunity")
        self.summary_meta.configure(text="")
        self.stage_summary.configure(text="")
        self.task_focus_title.configure(text="Select a task")
        self.task_focus_meta.configure(text="No task selected.")
        for child in self.stage_sections.winfo_children():
            child.destroy()
        ctk.CTkLabel(self.stage_sections, text="No opportunity selected.", text_color=PALETTE["ink_700"]).pack(anchor="w", padx=8, pady=8)
        self._update_action_states()

    def _visible_opportunities(self) -> list[dict]:
        opportunities = self.app.opportunity_service.list_opportunities()
        search_term = self.search_var.get().strip().lower()
        if not search_term:
            return opportunities
        return [
            opportunity
            for opportunity in opportunities
            if search_term in (opportunity["title"] or "").lower()
            or search_term in (opportunity.get("department_name") or "").lower()
            or search_term in (opportunity.get("external_pic_name") or "").lower()
        ]

    def render_opportunities(self):
        for child in self.list_scroll.winfo_children():
            child.destroy()
        opportunities = self._visible_opportunities()
        if not opportunities:
            ctk.CTkLabel(self.list_scroll, text="No opportunities found.", text_color=PALETTE["ink_700"]).pack(anchor="w", padx=8, pady=8)
            return
        if self.selected_opportunity_id not in {item["id"] for item in opportunities}:
            self.selected_opportunity_id = opportunities[0]["id"]
        for opportunity in opportunities:
            selected = opportunity["id"] == self.selected_opportunity_id
            card = ctk.CTkFrame(
                self.list_scroll,
                fg_color=PALETTE["primary_500"] if selected else PALETTE["surface_0"],
                border_width=1,
                border_color=PALETTE["border_soft"],
                corner_radius=16,
            )
            card.pack(fill="x", padx=4, pady=6)
            title_color = "white" if selected else PALETTE["ink_900"]
            sub_color = "#EEF0FF" if selected else PALETTE["ink_700"]
            title_label = ctk.CTkLabel(
                card,
                text=truncate_text(opportunity["title"], 42),
                text_color=title_color,
                font=ctk.CTkFont(size=15, weight="bold"),
                justify="left",
                anchor="w",
            )
            title_label.pack(fill="x", padx=14, pady=(12, 4))
            meta_label = ctk.CTkLabel(
                card,
                text=join_meta(
                    opportunity.get("department_name") or "-",
                    opportunity.get("pipeline_status") or "-",
                    f"Open tasks: {opportunity.get('open_task_count') or 0}",
                ),
                text_color=sub_color,
                font=ctk.CTkFont(size=12),
                justify="left",
                anchor="w",
            )
            meta_label.pack(fill="x", padx=14, pady=(0, 12))
            full_text = (
                f"{opportunity['title']}\n"
                f"Department: {opportunity.get('department_name') or '-'}\n"
                f"External PIC: {opportunity.get('external_pic_name') or '-'}\n"
                f"Status: {opportunity.get('pipeline_status') or '-'}"
            )
            HoverTip(card, full_text)
            HoverTip(title_label, full_text)
            HoverTip(meta_label, full_text)
            callback = lambda _event, opportunity_id=opportunity["id"]: self.load_detail(opportunity_id)
            bind_click(card, callback)
            bind_click(title_label, callback)
            bind_click(meta_label, callback)

    def _stage_display_label(self, stage: dict) -> str:
        return f"{stage.get('stage_name') or stage.get('name') or '-'} | {stage.get('stage_status') or '-'}"

    def load_detail(self, opportunity_id: int, reselect_stage: bool = True):
        self.selected_opportunity_id = opportunity_id
        detail = self.app.opportunity_service.get_opportunity_detail(opportunity_id)
        opportunity = detail["opportunity"]
        stages = detail["stages"]
        self.current_opportunity = opportunity
        self.current_stages = stages
        self.current_tasks = detail["tasks"]
        self.summary_title.configure(text=opportunity["title"])
        self.summary_meta.configure(
            text=(
                f"Department: {opportunity.get('department_name') or '-'}\n"
                f"External PIC: {opportunity.get('external_pic_name') or '-'}\n"
                f"Opportunity status: {opportunity.get('pipeline_status') or '-'}\n"
                f"Detail: {opportunity.get('detail') or '-'}"
            )
        )
        if stages and (not reselect_stage or self.selected_stage_id not in {stage["id"] for stage in stages}):
            self.selected_stage_id = stages[0]["id"]
        elif not stages:
            self.selected_stage_id = None
        self.stage_summary.configure(text=f"{len(stages)} stage-status pair(s) | {len(self.current_tasks)} task(s)")
        self._reconcile_selected_task()
        self._render_task_focus()
        self.render_tasks()
        self.render_opportunities()
        self._update_action_states()

    def _tasks_for_stage(self, stage_id: int) -> list[dict]:
        return [task for task in self.current_tasks if task["phase_id"] == stage_id]

    def _reconcile_selected_task(self):
        visible_ids = {task["id"] for task in self.current_tasks}
        if self.selected_task_id not in visible_ids:
            preferred = self._tasks_for_stage(self.selected_stage_id) if self.selected_stage_id else []
            if self.selected_stage_id and not preferred:
                self.selected_task_id = None
                return
            pool = preferred or self.current_tasks
            self.selected_task_id = pool[0]["id"] if pool else None

    def _selected_task(self) -> dict | None:
        return next((task for task in self.current_tasks if task["id"] == self.selected_task_id), None)

    def _render_task_focus(self):
        task = self._selected_task()
        if not task:
            self.task_focus_title.configure(text="Select a task")
            self.task_focus_meta.configure(text="No task selected in the current stage.")
            return
        self.task_focus_title.configure(text=task["title"])
        self.task_focus_meta.configure(
            text=(
                f"Stage: {task.get('stage_name') or '-'} | Status: {task.get('stage_status') or '-'}\n"
                f"Owner: {task.get('owner_name') or '-'} | PIC: {task.get('pic_name') or '-'}\n"
                f"Status: {task['manual_status']} | Health: {title_case_health(task['health_status'])} | Deadline: {task.get('deadline') or '-'}\n"
                f"Next: {task.get('next_action') or '-'}\n"
                f"Latest update: {task.get('latest_update_summary') or '-'}"
            )
        )

    def render_tasks(self):
        for child in self.stage_sections.winfo_children():
            child.destroy()
        if not self.current_stages:
            ctk.CTkLabel(self.stage_sections, text="No stage-status pairs yet.", text_color=PALETTE["ink_700"]).pack(anchor="w", padx=8, pady=8)
            return
        for stage in self.current_stages:
            stage_selected = stage["id"] == self.selected_stage_id
            section = ctk.CTkFrame(
                self.stage_sections,
                fg_color=PALETTE["surface_0"],
                border_width=2 if stage_selected else 1,
                border_color=PALETTE["primary_500"] if stage_selected else PALETTE["border_soft"],
                corner_radius=18,
            )
            section.pack(fill="x", padx=4, pady=8)

            header = ctk.CTkFrame(section, fg_color=PALETTE["surface_2"] if stage_selected else "transparent", corner_radius=14)
            header.pack(fill="x", padx=10, pady=(10, 8))
            header.grid_columnconfigure(0, weight=1)
            stage_label = ctk.CTkLabel(
                header,
                text=self._stage_display_label(stage),
                font=ctk.CTkFont(size=15, weight="bold"),
                text_color=PALETTE["ink_900"],
                anchor="w",
            )
            stage_label.grid(row=0, column=0, sticky="w", padx=12, pady=(10, 2))
            count_label = ctk.CTkLabel(
                header,
                text=f"{stage.get('task_count') or 0} task(s)",
                text_color=PALETTE["ink_700"],
                anchor="w",
            )
            count_label.grid(row=1, column=0, sticky="w", padx=12, pady=(0, 10))
            add_task_button = ctk.CTkButton(
                header,
                text="Add Task",
                width=92,
                height=32,
                command=lambda stage_id=stage["id"]: self.open_new_task(stage_id=stage_id),
            )
            add_task_button.grid(row=0, column=1, rowspan=2, padx=10, pady=10)

            select_stage = lambda _event, stage_id=stage["id"]: self.select_stage(stage_id)
            bind_click(section, select_stage)
            bind_click(header, select_stage)
            bind_click(stage_label, select_stage)
            bind_click(count_label, select_stage)

            tasks = self._tasks_for_stage(stage["id"])
            if not tasks:
                ctk.CTkLabel(section, text="No tasks in this stage-status yet.", text_color=PALETTE["ink_700"]).pack(anchor="w", padx=14, pady=(0, 12))
                continue

            for task in tasks:
                selected = task["id"] == self.selected_task_id
                card = ctk.CTkFrame(
                    section,
                    fg_color=PALETTE["primary_500"] if selected else PALETTE["surface_1"],
                    border_width=1,
                    border_color=PALETTE["border_soft"],
                    corner_radius=14,
                )
                card.pack(fill="x", padx=12, pady=(0, 8))
                title_color = "white" if selected else PALETTE["ink_900"]
                meta_color = "#EEF0FF" if selected else PALETTE["ink_700"]
                title_label = ctk.CTkLabel(
                    card,
                    text=truncate_text(task["title"], 70),
                    font=ctk.CTkFont(size=14, weight="bold"),
                    text_color=title_color,
                    justify="left",
                    anchor="w",
                )
                title_label.pack(fill="x", padx=14, pady=(12, 4))
                meta_text = (
                    f"Owner: {task.get('owner_name') or '-'} | PIC: {task.get('pic_name') or '-'}\n"
                    f"Status: {task['manual_status']} | Health: {title_case_health(task['health_status'])} | Deadline: {task.get('deadline') or '-'}\n"
                    f"Next: {task.get('next_action') or '-'}"
                )
                meta_label = ctk.CTkLabel(card, text=meta_text, justify="left", text_color=meta_color, font=ctk.CTkFont(size=12), anchor="w")
                meta_label.pack(fill="x", padx=14, pady=(0, 12))
                full_text = (
                    f"{task['title']}\n"
                    f"Stage: {task.get('stage_name') or '-'} | Stage status: {task.get('stage_status') or '-'}\n"
                    f"Owner: {task.get('owner_name') or '-'} | PIC: {task.get('pic_name') or '-'}\n"
                    f"Status: {task['manual_status']} | Health: {title_case_health(task['health_status'])}\n"
                    f"Deadline: {task.get('deadline') or '-'}\n"
                    f"Next: {task.get('next_action') or '-'}\n"
                    f"Latest update: {task.get('latest_update_summary') or '-'}"
                )
                HoverTip(card, full_text)
                HoverTip(title_label, full_text)
                HoverTip(meta_label, full_text)
                callback = lambda _event, task_id=task["id"], stage_id=stage["id"]: self.select_task(task_id, stage_id)
                bind_click(card, callback)
                bind_click(title_label, callback)
                bind_click(meta_label, callback)

    def select_stage(self, stage_id: int):
        self.selected_stage_id = stage_id
        self.selected_task_id = None
        self._reconcile_selected_task()
        self._render_task_focus()
        self.render_tasks()
        self._update_action_states()

    def select_task(self, task_id: int, stage_id: int | None = None):
        if stage_id is not None:
            self.selected_stage_id = stage_id
        self.selected_task_id = task_id
        self._render_task_focus()
        self.render_tasks()
        self._update_action_states()

    def _update_action_states(self):
        task_state = "normal" if self.selected_task_id else "disabled"
        opp_state = "normal" if self.selected_opportunity_id else "disabled"
        stage_state = "normal" if self.selected_stage_id else "disabled"
        self.edit_opp_button.configure(state=opp_state)
        self.delete_opp_button.configure(state=opp_state)
        self.edit_stage_button.configure(state=stage_state)
        self.delete_stage_button.configure(state=stage_state)
        self.edit_task_button.configure(state=task_state)
        self.delete_task_button.configure(state=task_state)

    def import_excel(self):
        path = filedialog.askopenfilename(
            title="Select workbook",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            report = self.app.import_service.import_workbook(path, DEFAULT_SHEET_NAME)
            self.toast(
                (
                    f"Import completed. Opportunities: {report.opportunities_created}, "
                    f"Stages: {report.phases_created}, Tasks: {report.tasks_created}, Skipped: {report.skipped_rows}"
                ),
                "success",
            )
            self.app.refresh_views("dashboard", "opportunities", "board", "settings")
        except ValidationError as exc:
            self.toast(f"Import failed: {exc}", "error")

    def open_new_opportunity(self):
        OpportunityDialog(self.app, on_submit=self._create_opportunity)

    def open_edit_opportunity(self):
        if not self.current_opportunity:
            self.toast("Select an opportunity first.", "warning")
            return
        OpportunityDialog(self.app, on_submit=self._update_opportunity, initial_data=self.current_opportunity, dialog_title="Edit Opportunity")

    def _create_opportunity(self, payload: dict):
        try:
            opportunity_id = self.app.opportunity_service.create_opportunity(**payload)
            self.selected_opportunity_id = opportunity_id
            self.selected_stage_id = None
            self.selected_task_id = None
            self.refresh()
            self.load_detail(opportunity_id, reselect_stage=False)
            self.app.refresh_views("dashboard", "board")
            self.toast("Opportunity created successfully.", "success")
        except ValidationError as exc:
            self.toast(f"Create opportunity failed: {exc}", "error")
            raise

    def _update_opportunity(self, payload: dict):
        try:
            self.app.opportunity_service.update_opportunity(self.selected_opportunity_id, **payload)
            self.load_detail(self.selected_opportunity_id, reselect_stage=True)
            self.app.refresh_views("dashboard", "board")
            self.toast("Opportunity updated successfully.", "success")
        except ValidationError as exc:
            self.toast(f"Update opportunity failed: {exc}", "error")
            raise

    def confirm_delete_opportunity(self):
        if not self.selected_opportunity_id:
            self.toast("Select an opportunity first.", "warning")
            return
        ConfirmDialog(
            self.app,
            title="Delete Opportunity",
            message="Archive this opportunity and all its stages/tasks?",
            confirm_label="Delete Opportunity",
            on_confirm=self._delete_opportunity,
        )

    def _delete_opportunity(self):
        try:
            self.app.opportunity_service.archive_opportunity(self.selected_opportunity_id)
            self.selected_opportunity_id = None
            self.selected_stage_id = None
            self.selected_task_id = None
            self.app.refresh_views("dashboard", "opportunities", "board")
            opportunities = self._visible_opportunities()
            if opportunities:
                self.load_detail(opportunities[0]["id"], reselect_stage=False)
            else:
                self.clear_detail()
            self.toast("Opportunity deleted successfully.", "success")
        except ValidationError as exc:
            self.toast(f"Delete opportunity failed: {exc}", "error")
            raise

    def _selected_stage(self) -> dict | None:
        return next((stage for stage in self.current_stages if stage["id"] == self.selected_stage_id), None)

    def open_new_stage(self):
        if not self.selected_opportunity_id:
            self.toast("Select an opportunity before creating a stage.", "warning")
            return
        StageDialog(self.app, on_submit=self._create_stage, dialog_title="Add Stage-Status")

    def open_edit_stage(self):
        stage = self._selected_stage()
        if not stage:
            self.toast("Select a stage first.", "warning")
            return
        StageDialog(self.app, on_submit=self._update_stage, initial_data=stage, dialog_title="Edit Stage")

    def _create_stage(self, payload: dict):
        try:
            stage_id = self.app.opportunity_service.create_stage(self.selected_opportunity_id, **payload)
            self.selected_stage_id = stage_id
            self.load_detail(self.selected_opportunity_id)
            self.toast("Stage created successfully.", "success")
        except ValidationError as exc:
            self.toast(f"Create stage failed: {exc}", "error")
            raise

    def _update_stage(self, payload: dict):
        try:
            self.app.opportunity_service.update_stage(self.selected_stage_id, **payload)
            self.load_detail(self.selected_opportunity_id, reselect_stage=True)
            self.toast("Stage updated successfully.", "success")
        except ValidationError as exc:
            self.toast(f"Update stage failed: {exc}", "error")
            raise

    def confirm_delete_stage(self):
        if not self.selected_stage_id:
            self.toast("Select a stage first.", "warning")
            return
        ConfirmDialog(
            self.app,
            title="Delete Stage",
            message="Archive the selected stage and all tasks inside it?",
            confirm_label="Delete Stage",
            on_confirm=self._delete_stage,
        )

    def _delete_stage(self):
        try:
            self.app.opportunity_service.archive_stage(self.selected_stage_id)
            self.selected_stage_id = None
            self.selected_task_id = None
            self.load_detail(self.selected_opportunity_id, reselect_stage=False)
            self.app.refresh_views("dashboard", "board")
            self.toast("Stage deleted successfully.", "success")
        except ValidationError as exc:
            self.toast(f"Delete stage failed: {exc}", "error")
            raise

    def _stage_dialog_options(self) -> list[tuple[str, int]]:
        return [(self._stage_display_label(stage), stage["id"]) for stage in self.current_stages] or [("General | TT", self.selected_stage_id or 0)]

    def open_new_task(self, stage_id: int | None = None):
        if not self.selected_opportunity_id:
            self.toast("Select an opportunity before creating a task.", "warning")
            return
        if not self.current_stages:
            self.toast("Create a stage before adding a task.", "warning")
            return
        if stage_id is not None:
            self.selected_stage_id = stage_id
        if not self.selected_stage_id:
            self.selected_stage_id = self.current_stages[0]["id"]
        TaskDialog(
            self.app,
            on_submit=self._create_task,
            stage_options=self._stage_dialog_options(),
            selected_stage_id=self.selected_stage_id,
        )

    def open_edit_task(self):
        task = self._selected_task()
        if not task:
            self.toast("Select a task first.", "warning")
            return
        TaskDialog(
            self.app,
            on_submit=self._update_task,
            stage_options=self._stage_dialog_options(),
            selected_stage_id=task["phase_id"],
            initial_data=task,
            dialog_title="Edit Task",
        )

    def _create_task(self, payload: dict):
        try:
            payload["opportunity_id"] = self.selected_opportunity_id
            task_id = self.app.task_service.create_task(**payload)
            self.selected_stage_id = payload["phase_id"]
            self.load_detail(self.selected_opportunity_id)
            self.selected_task_id = task_id
            self._render_task_focus()
            self.render_tasks()
            self.app.refresh_views("dashboard", "board")
            self.toast("Task created successfully.", "success")
        except ValidationError as exc:
            self.toast(f"Create task failed: {exc}", "error")
            raise

    def _update_task(self, payload: dict):
        try:
            self.app.task_service.update_task(self.selected_task_id, **payload)
            self.selected_stage_id = payload["phase_id"]
            self.load_detail(self.selected_opportunity_id, reselect_stage=True)
            self.app.refresh_views("dashboard", "board")
            self.toast("Task updated successfully.", "success")
        except ValidationError as exc:
            self.toast(f"Update task failed: {exc}", "error")
            raise

    def confirm_delete_task(self):
        if not self.selected_task_id:
            self.toast("Select a task first.", "warning")
            return
        ConfirmDialog(
            self.app,
            title="Delete Task",
            message="Archive the selected task?",
            confirm_label="Delete Task",
            on_confirm=self._delete_task,
        )

    def _delete_task(self):
        try:
            self.app.task_service.archive_task(self.selected_task_id)
            self.selected_task_id = None
            self.load_detail(self.selected_opportunity_id, reselect_stage=True)
            self.app.refresh_views("dashboard", "board")
            self.toast("Task deleted successfully.", "success")
        except ValidationError as exc:
            self.toast(f"Delete task failed: {exc}", "error")
            raise


class BoardView(BaseView):
    def __init__(self, master, app: TaskMNGApp):
        super().__init__(master, app)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(24, 10))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="Task Board", font=ctk.CTkFont(size=28, weight="bold"), text_color=PALETTE["ink_900"]).grid(
            row=0, column=0, sticky="w"
        )

        self.status_filter_var = tk.StringVar(value="All Statuses")
        self.pic_filter_var = tk.StringVar(value="All PICs")
        self.search_var = tk.StringVar()

        filters = ctk.CTkFrame(self, fg_color=PALETTE["surface_0"], border_width=1, border_color=PALETTE["border_soft"])
        filters.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 12))
        filters.grid_columnconfigure((0, 1, 2), weight=1)
        self.status_filter = ctk.CTkOptionMenu(filters, values=["All Statuses"], variable=self.status_filter_var, command=lambda _v: self.refresh())
        self.status_filter.grid(row=0, column=0, sticky="ew", padx=12, pady=12)
        self.pic_filter = ctk.CTkOptionMenu(filters, values=["All PICs"], variable=self.pic_filter_var, command=lambda _v: self.refresh())
        self.pic_filter.grid(row=0, column=1, sticky="ew", padx=12, pady=12)
        self.search_entry = ctk.CTkEntry(filters, textvariable=self.search_var, placeholder_text="Search opportunity")
        self.search_entry.grid(row=0, column=2, sticky="ew", padx=12, pady=12)
        self.search_entry.bind("<KeyRelease>", lambda _event: self.refresh())

        self.board = ctk.CTkFrame(self, fg_color="transparent")
        self.board.grid(row=2, column=0, padx=24, pady=(0, 24), sticky="nsew")

    def _board_statuses(self, tasks: list[dict]) -> list[str]:
        active = self.app.master_data_service.task_statuses() or MANUAL_STATUSES
        used = [task["manual_status"] for task in tasks if task.get("manual_status")]
        ordered = list(active)
        for status in used:
            if status not in ordered:
                ordered.append(status)
        return ordered

    def refresh(self):
        for child in self.board.winfo_children():
            child.destroy()
        tasks = self.app.task_service.list_tasks()
        statuses = self._board_statuses(tasks)
        self.status_filter.configure(values=["All Statuses"] + statuses)
        if self.status_filter_var.get() not in ["All Statuses"] + statuses:
            self.status_filter_var.set("All Statuses")

        pic_values = sorted({task.get("pic_name") for task in tasks if task.get("pic_name")})
        self.pic_filter.configure(values=["All PICs"] + pic_values)
        if self.pic_filter_var.get() not in ["All PICs"] + pic_values:
            self.pic_filter_var.set("All PICs")

        for idx in range(max(1, len(statuses))):
            self.board.grid_columnconfigure(idx, weight=1)

        columns = {status: [] for status in statuses}
        filtered_tasks = self._apply_filters(tasks)
        for task in filtered_tasks:
            columns.setdefault(task["manual_status"], []).append(task)

        for idx, status in enumerate(statuses):
            col = ctk.CTkFrame(self.board, fg_color=PALETTE["surface_0"], border_width=1, border_color=PALETTE["border_soft"])
            col.grid(row=0, column=idx, padx=6, sticky="nsew")
            ctk.CTkLabel(col, text=status, font=ctk.CTkFont(size=15, weight="bold"), text_color=PALETTE["ink_900"]).pack(
                anchor="w", padx=12, pady=(12, 6)
            )
            ctk.CTkLabel(col, text=f"{len(columns.get(status, []))} task(s)", text_color=PALETTE["ink_700"], font=ctk.CTkFont(size=11)).pack(
                anchor="w", padx=12, pady=(0, 8)
            )
            scroll = ctk.CTkScrollableFrame(col, fg_color="transparent", height=680)
            scroll.pack(fill="both", expand=True, padx=8, pady=(0, 8))
            if not columns.get(status):
                ctk.CTkLabel(scroll, text="No tasks", text_color=PALETTE["ink_700"], font=ctk.CTkFont(size=11)).pack(anchor="w", padx=6, pady=6)
            for task in columns.get(status, []):
                card = ctk.CTkFrame(scroll, fg_color=PALETTE["surface_1"], border_width=1, border_color=PALETTE["border_soft"])
                card.pack(fill="x", padx=2, pady=6)
                title_label = ctk.CTkLabel(
                    card,
                    text=truncate_text(task["title"], 28),
                    font=ctk.CTkFont(size=12, weight="bold"),
                    text_color=PALETTE["ink_900"],
                    justify="left",
                    anchor="w",
                )
                title_label.pack(fill="x", padx=10, pady=(10, 3))
                opp_label = ctk.CTkLabel(
                    card,
                    text=truncate_text(task["opportunity_title"], 30),
                    justify="left",
                    anchor="w",
                    text_color=PALETTE["ink_900"],
                    font=ctk.CTkFont(size=11),
                )
                opp_label.pack(fill="x", padx=10)
                people_label = ctk.CTkLabel(
                    card,
                    text=truncate_text(
                        f"Stage: {task.get('stage_name') or '-'} | PIC: {task.get('pic_name') or '-'}",
                        34,
                    ),
                    justify="left",
                    anchor="w",
                    text_color=PALETTE["ink_700"],
                    font=ctk.CTkFont(size=10),
                )
                people_label.pack(fill="x", padx=10, pady=(2, 0))
                status_label = ctk.CTkLabel(
                    card,
                    text=truncate_text(f"{title_case_health(task['health_status'])} | {task.get('deadline') or '-'}", 30),
                    justify="left",
                    anchor="w",
                    text_color=PALETTE["ink_700"],
                    font=ctk.CTkFont(size=10),
                )
                status_label.pack(fill="x", padx=10, pady=(2, 8))
                full_text = (
                    f"{task['title']}\n"
                    f"Opportunity: {task['opportunity_title']}\n"
                    f"Stage: {task.get('stage_name') or '-'} | Stage status: {task.get('stage_status') or '-'}\n"
                    f"PIC: {task.get('pic_name') or '-'} | Owner: {task.get('owner_name') or '-'}\n"
                    f"Status: {task['manual_status']} | Health: {title_case_health(task['health_status'])}\n"
                    f"Deadline: {task.get('deadline') or '-'}\n"
                    f"Next: {task.get('next_action') or '-'}"
                )
                HoverTip(card, full_text)
                HoverTip(title_label, full_text)
                HoverTip(opp_label, full_text)
                HoverTip(people_label, full_text)
                HoverTip(status_label, full_text)
                status_selector = ctk.CTkOptionMenu(
                    card,
                    values=statuses,
                    height=30,
                    command=lambda value, task_id=task["id"]: self.change_status(task_id, value),
                )
                status_selector.set(task["manual_status"])
                status_selector.pack(fill="x", padx=10, pady=(0, 10))

    def _apply_filters(self, tasks: list[dict]) -> list[dict]:
        status_filter = self.status_filter_var.get()
        pic_filter = self.pic_filter_var.get()
        search_term = self.search_var.get().strip().lower()

        filtered = tasks
        if status_filter != "All Statuses":
            filtered = [task for task in filtered if task["manual_status"] == status_filter]
        if pic_filter != "All PICs":
            filtered = [task for task in filtered if (task.get("pic_name") or "") == pic_filter]
        if search_term:
            filtered = [task for task in filtered if search_term in (task.get("opportunity_title") or "").lower()]
        return filtered

    def change_status(self, task_id: int, value: str):
        try:
            self.app.task_service.update_task_status(task_id, value)
            self.app.refresh_views("board", "opportunities", "dashboard")
            self.toast(f"Task status updated to {value}.", "success")
        except ValidationError as exc:
            self.toast(f"Status update failed: {exc}", "error")


class SettingsView(BaseView):
    def __init__(self, master, app: TaskMNGApp):
        super().__init__(master, app)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self, text="Settings", font=ctk.CTkFont(size=28, weight="bold"), text_color=PALETTE["ink_900"]).grid(
            row=0, column=0, sticky="w", padx=24, pady=(24, 14)
        )
        self.card = ctk.CTkFrame(self, fg_color=PALETTE["surface_0"], border_width=1, border_color=PALETTE["border_soft"])
        self.card.grid(row=1, column=0, padx=24, pady=(0, 24), sticky="nsew")
        self.card.grid_columnconfigure(0, weight=1)
        self.card.grid_rowconfigure(1, weight=1)
        self.db_label = ctk.CTkLabel(self.card, text="", justify="left", text_color=PALETTE["ink_700"])
        self.db_label.grid(row=0, column=0, sticky="w", padx=18, pady=(18, 10))

        self.tabs = ctk.CTkTabview(self.card, fg_color=PALETTE["surface_1"])
        self.tabs.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        for label in ("PIC", "Task Status", "Pipeline Status", "Stage"):
            self.tabs.add(label)

        self.pic_frame = ctk.CTkScrollableFrame(self.tabs.tab("PIC"), fg_color="transparent")
        self.pic_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.task_status_frame = ctk.CTkScrollableFrame(self.tabs.tab("Task Status"), fg_color="transparent")
        self.task_status_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.pipeline_status_frame = ctk.CTkScrollableFrame(self.tabs.tab("Pipeline Status"), fg_color="transparent")
        self.pipeline_status_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.stage_frame = ctk.CTkScrollableFrame(self.tabs.tab("Stage"), fg_color="transparent")
        self.stage_frame.pack(fill="both", expand=True, padx=10, pady=10)

    def refresh(self):
        self.db_label.configure(text=f"Database path:\n{self.app.db.db_path}")
        self._render_users()
        self._render_master_category(self.task_status_frame, MASTER_CATEGORY_TASK_STATUS, "No task statuses yet.")
        self._render_master_category(self.pipeline_status_frame, MASTER_CATEGORY_PIPELINE_STATUS, "No pipeline statuses yet.")
        self._render_master_category(self.stage_frame, MASTER_CATEGORY_PRIORITY_STAGE, "No stages yet.")

    def _render_users(self):
        for child in self.pic_frame.winfo_children():
            child.destroy()
        ctk.CTkButton(
            self.pic_frame,
            text="Add PIC",
            height=36,
            fg_color=PALETTE["primary_500"],
            command=self._open_add_pic,
        ).pack(anchor="w", padx=6, pady=(4, 12))
        users = self.app.user_service.list_all_users()
        if not users:
            ctk.CTkLabel(self.pic_frame, text="No PIC master data yet.", text_color=PALETTE["ink_700"]).pack(anchor="w", padx=8, pady=8)
            return
        for user in users:
            row = ctk.CTkFrame(self.pic_frame, fg_color=PALETTE["surface_0"], border_width=1, border_color=PALETTE["border_soft"])
            row.pack(fill="x", padx=4, pady=6)
            ctk.CTkLabel(
                row,
                text=f"{user['display_name']} {'(inactive)' if not user['is_active'] else ''}",
                text_color=PALETTE["ink_900"],
                font=ctk.CTkFont(size=14, weight="bold"),
            ).grid(row=0, column=0, sticky="w", padx=12, pady=12)
            ctk.CTkButton(row, text="Rename", width=88, command=lambda user_id=user["id"], name=user["display_name"]: self._open_rename_pic(user_id, name)).grid(
                row=0, column=1, padx=(8, 6), pady=8
            )
            ctk.CTkButton(
                row,
                text="Deactivate",
                width=92,
                fg_color=PALETTE["danger"],
                hover_color="#B94E66",
                state="disabled" if not user["is_active"] else "normal",
                command=lambda user_id=user["id"]: self._confirm_deactivate_pic(user_id),
            ).grid(row=0, column=2, padx=(0, 10), pady=8)

    def _render_master_category(self, container, category: str, empty_message: str):
        for child in container.winfo_children():
            child.destroy()
        label_map = {
            MASTER_CATEGORY_TASK_STATUS: "Add Status",
            MASTER_CATEGORY_PIPELINE_STATUS: "Add Pipeline Status",
            MASTER_CATEGORY_PRIORITY_STAGE: "Add Stage",
        }
        ctk.CTkButton(
            container,
            text=label_map[category],
            height=36,
            fg_color=PALETTE["primary_500"],
            command=lambda current_category=category: self._open_add_master_value(current_category),
        ).pack(anchor="w", padx=6, pady=(4, 12))
        values = self.app.master_data_service.list_values(category, include_inactive=True)
        if not values:
            ctk.CTkLabel(container, text=empty_message, text_color=PALETTE["ink_700"]).pack(anchor="w", padx=8, pady=8)
            return
        for item in values:
            row = ctk.CTkFrame(container, fg_color=PALETTE["surface_0"], border_width=1, border_color=PALETTE["border_soft"])
            row.pack(fill="x", padx=4, pady=6)
            title = f"{item['value']} {'(inactive)' if not item['is_active'] else ''}"
            ctk.CTkLabel(row, text=title, text_color=PALETTE["ink_900"], font=ctk.CTkFont(size=14, weight="bold")).grid(
                row=0, column=0, sticky="w", padx=12, pady=12
            )
            ctk.CTkButton(
                row,
                text="Rename",
                width=88,
                command=lambda value_id=item["id"], value=item["value"], current_category=category: self._open_rename_master_value(
                    current_category, value_id, value
                ),
            ).grid(row=0, column=1, padx=(8, 6), pady=8)
            ctk.CTkButton(
                row,
                text="Deactivate",
                width=92,
                fg_color=PALETTE["danger"],
                hover_color="#B94E66",
                state="disabled" if not item["is_active"] else "normal",
                command=lambda value_id=item["id"], current_category=category: self._confirm_deactivate_master_value(
                    current_category, value_id
                ),
            ).grid(row=0, column=2, padx=(0, 10), pady=8)

    def _open_add_pic(self):
        TextInputDialog(self.app, title="Add PIC", field_label="PIC name", on_submit=self._add_pic)

    def _add_pic(self, value: str):
        try:
            self.app.user_service.ensure_user(value)
            self.app.refresh_views("settings", "board", "opportunities")
            self.toast("PIC added successfully.", "success")
        except ValidationError as exc:
            self.toast(f"Add PIC failed: {exc}", "error")
            raise

    def _open_rename_pic(self, user_id: int, name: str):
        TextInputDialog(self.app, title="Rename PIC", field_label="PIC name", on_submit=lambda value: self._rename_pic(user_id, value), initial_value=name)

    def _rename_pic(self, user_id: int, value: str):
        try:
            self.app.user_service.rename_user(user_id, value)
            self.app.refresh_views("settings", "board", "opportunities")
            self.toast("PIC renamed successfully.", "success")
        except ValidationError as exc:
            self.toast(f"Rename PIC failed: {exc}", "error")
            raise

    def _confirm_deactivate_pic(self, user_id: int):
        ConfirmDialog(
            self.app,
            title="Deactivate PIC",
            message="Deactivate this PIC from master data?",
            confirm_label="Deactivate",
            on_confirm=lambda: self._deactivate_pic(user_id),
        )

    def _deactivate_pic(self, user_id: int):
        try:
            self.app.user_service.deactivate_user(user_id)
            self.app.refresh_views("settings", "board", "opportunities")
            self.toast("PIC deactivated successfully.", "success")
        except ValidationError as exc:
            self.toast(f"Deactivate PIC failed: {exc}", "error")
            raise

    def _open_add_master_value(self, category: str):
        label_map = {
            MASTER_CATEGORY_TASK_STATUS: "Task status",
            MASTER_CATEGORY_PIPELINE_STATUS: "Pipeline status",
            MASTER_CATEGORY_PRIORITY_STAGE: "Stage",
        }
        TextInputDialog(
            self.app,
            title=f"Add {label_map[category]}",
            field_label=label_map[category],
            on_submit=lambda value: self._add_master_value(category, value),
        )

    def _add_master_value(self, category: str, value: str):
        try:
            self.app.master_data_service.add_value(category, value)
            self.app.refresh_views("settings", "board", "opportunities")
            self.toast("Master data added successfully.", "success")
        except ValidationError as exc:
            self.toast(f"Add master data failed: {exc}", "error")
            raise

    def _open_rename_master_value(self, category: str, value_id: int, value: str):
        TextInputDialog(
            self.app,
            title="Rename Master Data",
            field_label="Value",
            on_submit=lambda new_value: self._rename_master_value(category, value_id, new_value),
            initial_value=value,
        )

    def _rename_master_value(self, category: str, value_id: int, value: str):
        try:
            self.app.master_data_service.rename_value(category, value_id, value)
            self.app.refresh_views("settings", "board", "opportunities", "dashboard")
            self.toast("Master data updated successfully.", "success")
        except ValidationError as exc:
            self.toast(f"Update master data failed: {exc}", "error")
            raise

    def _confirm_deactivate_master_value(self, category: str, value_id: int):
        ConfirmDialog(
            self.app,
            title="Deactivate Master Data",
            message="Deactivate this master data item?",
            confirm_label="Deactivate",
            on_confirm=lambda: self._deactivate_master_value(category, value_id),
        )

    def _deactivate_master_value(self, category: str, value_id: int):
        try:
            self.app.master_data_service.deactivate_value(category, value_id)
            self.app.refresh_views("settings", "board", "opportunities")
            self.toast("Master data deactivated successfully.", "success")
        except ValidationError as exc:
            self.toast(f"Deactivate master data failed: {exc}", "error")
            raise


class ItemListPanel(ctk.CTkFrame):
    def __init__(self, master, title: str):
        super().__init__(master, fg_color=PALETTE["surface_0"], border_width=1, border_color=PALETTE["border_soft"])
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text=title, font=ctk.CTkFont(size=18, weight="bold"), text_color=PALETTE["ink_900"]).grid(
            row=0, column=0, sticky="w", padx=18, pady=(18, 12)
        )
        self.list_frame = ctk.CTkScrollableFrame(self, fg_color=PALETTE["surface_1"])
        self.list_frame.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 14))

    def render_items(self, items: list[dict], mode: str = "status"):
        for child in self.list_frame.winfo_children():
            child.destroy()
        if not items:
            ctk.CTkLabel(self.list_frame, text="No items to show right now.", text_color=PALETTE["ink_700"]).pack(anchor="w", padx=8, pady=8)
            return
        for item in items:
            frame = ctk.CTkFrame(self.list_frame, fg_color=PALETTE["surface_0"], border_width=1, border_color=PALETTE["border_soft"])
            frame.pack(fill="x", padx=4, pady=6)
            full_text = f"{item['title']}\n{item.get('opportunity_title') or ''}\n{item.get('deadline') or '-'}"
            title_label = ctk.CTkLabel(
                frame,
                text=truncate_text(item["title"], 44),
                font=ctk.CTkFont(size=15, weight="bold"),
                text_color=PALETTE["ink_900"],
                anchor="w",
            )
            title_label.pack(fill="x", padx=12, pady=(12, 4))
            badge_text = item.get("health_status") if mode == "health" else item.get("manual_status")
            sub = join_meta(item.get("opportunity_title") or "", badge_text or "", item.get("deadline") or "-")
            sub_label = ctk.CTkLabel(frame, text=truncate_text(sub, 64), text_color=PALETTE["ink_700"], anchor="w")
            sub_label.pack(fill="x", padx=12, pady=(0, 12))
            HoverTip(frame, full_text)
            HoverTip(title_label, full_text)
            HoverTip(sub_label, full_text)


class BaseModalDialog(ctk.CTkToplevel):
    def __init__(self, app: TaskMNGApp, title: str, geometry: str, min_size: tuple[int, int]):
        super().__init__(app)
        app.apply_window_icon(self)
        self.title(title)
        self.geometry(geometry)
        self.minsize(*min_size)
        self.configure(fg_color=PALETTE["surface_0"])
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grab_set()
        self.transient(app)
        self.lift()
        self.focus_force()

        self.body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.body.grid(row=0, column=0, sticky="nsew", padx=20, pady=(20, 10))
        self.footer = ctk.CTkFrame(self, fg_color=PALETTE["surface_0"], corner_radius=0)
        self.footer.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 20))


class OpportunityDialog(BaseModalDialog):
    def __init__(self, app: TaskMNGApp, on_submit, initial_data: dict | None = None, dialog_title: str = "New Opportunity"):
        super().__init__(app, title=dialog_title, geometry="560x720", min_size=(520, 620))
        self.on_submit = on_submit
        self.initial_data = initial_data or {}
        self.inputs: dict[str, object] = {}

        pipeline_values = app.master_data_service.pipeline_statuses() or PIPELINE_STATUSES
        current_pipeline = self.initial_data.get("pipeline_status")
        if current_pipeline and current_pipeline not in pipeline_values:
            pipeline_values = pipeline_values + [current_pipeline]
        stage_values = app.master_data_service.priority_stages() or PRIORITY_STAGES
        current_stage = self.initial_data.get("priority_stage")
        if current_stage and current_stage not in stage_values:
            stage_values = stage_values + [current_stage]

        self._add_entry("title", "Title", self.initial_data.get("title"))
        self._add_entry("department_name", "Department", self.initial_data.get("department_name"))
        self._add_entry("external_pic_name", "External PIC", self.initial_data.get("external_pic_name"))
        self._add_option("pipeline_status", "Pipeline Status", pipeline_values, current_pipeline or pipeline_values[0])
        self._add_option("priority_stage", "Initial Stage", stage_values, current_stage or stage_values[0])
        self._add_textbox("detail", "Detail", height=160, initial_value=self.initial_data.get("detail"))

        ctk.CTkButton(
            self.footer,
            text="Save Opportunity",
            height=42,
            fg_color=PALETTE["primary_500"],
            hover_color=PALETTE["primary_700"],
            command=self.submit,
        ).pack(fill="x", padx=4, pady=4)

    def _add_entry(self, key: str, label: str, initial_value: str | None = None):
        ctk.CTkLabel(self.body, text=label, text_color=PALETTE["ink_700"]).pack(anchor="w", padx=6, pady=(18, 6))
        entry = ctk.CTkEntry(self.body, height=38)
        entry.pack(fill="x", padx=6)
        if initial_value:
            entry.insert(0, initial_value)
        self.inputs[key] = entry

    def _add_option(self, key: str, label: str, values: list[str], current_value: str):
        ctk.CTkLabel(self.body, text=label, text_color=PALETTE["ink_700"]).pack(anchor="w", padx=6, pady=(18, 6))
        option = ctk.CTkOptionMenu(self.body, values=list(values))
        option.pack(fill="x", padx=6)
        option.set(current_value)
        self.inputs[key] = option

    def _add_textbox(self, key: str, label: str, height: int, initial_value: str | None = None):
        ctk.CTkLabel(self.body, text=label, text_color=PALETTE["ink_700"]).pack(anchor="w", padx=6, pady=(18, 6))
        text = ctk.CTkTextbox(self.body, height=height)
        text.pack(fill="both", padx=6, pady=(0, 8))
        if initial_value:
            text.insert("1.0", initial_value)
        self.inputs[key] = text

    def submit(self):
        payload = {
            "title": self.inputs["title"].get(),
            "department_name": self.inputs["department_name"].get(),
            "external_pic_name": self.inputs["external_pic_name"].get(),
            "pipeline_status": self.inputs["pipeline_status"].get(),
            "priority_stage": self.inputs["priority_stage"].get(),
            "detail": self.inputs["detail"].get("1.0", tk.END).strip(),
        }
        try:
            self.on_submit(payload)
            self.destroy()
        except ValidationError:
            pass


class TextInputDialog(ctk.CTkToplevel):
    def __init__(self, app: TaskMNGApp, title: str, field_label: str, on_submit, initial_value: str = ""):
        super().__init__(app)
        app.apply_window_icon(self)
        self.on_submit = on_submit
        self.title(title)
        self.geometry("420x190")
        self.configure(fg_color=PALETTE["surface_0"])
        self.grab_set()
        self.transient(app)
        self.lift()
        ctk.CTkLabel(self, text=field_label, text_color=PALETTE["ink_700"]).pack(anchor="w", padx=24, pady=(24, 8))
        self.entry = ctk.CTkEntry(self, height=38)
        self.entry.pack(fill="x", padx=24)
        if initial_value:
            self.entry.insert(0, initial_value)
        ctk.CTkButton(
            self,
            text="Save",
            height=42,
            fg_color=PALETTE["primary_500"],
            hover_color=PALETTE["primary_700"],
            command=self.submit,
        ).pack(fill="x", padx=24, pady=24)

    def submit(self):
        try:
            self.on_submit(self.entry.get())
            self.destroy()
        except ValidationError:
            pass


class ConfirmDialog(ctk.CTkToplevel):
    def __init__(self, app: TaskMNGApp, title: str, message: str, confirm_label: str, on_confirm):
        super().__init__(app)
        app.apply_window_icon(self)
        self.on_confirm = on_confirm
        self.title(title)
        self.geometry("440x210")
        self.configure(fg_color=PALETTE["surface_0"])
        self.grab_set()
        self.transient(app)
        self.lift()
        ctk.CTkLabel(self, text=title, font=ctk.CTkFont(size=18, weight="bold"), text_color=PALETTE["ink_900"]).pack(anchor="w", padx=24, pady=(24, 10))
        ctk.CTkLabel(self, text=message, justify="left", text_color=PALETTE["ink_700"], wraplength=360).pack(anchor="w", padx=24)
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=24, pady=24)
        ctk.CTkButton(actions, text="Cancel", fg_color=PALETTE["surface_2"], text_color=PALETTE["ink_900"], command=self.destroy).pack(
            side="left", expand=True, fill="x", padx=(0, 8)
        )
        ctk.CTkButton(actions, text=confirm_label, fg_color=PALETTE["danger"], hover_color="#B94E66", command=self.submit).pack(
            side="left", expand=True, fill="x", padx=(8, 0)
        )

    def submit(self):
        try:
            self.on_confirm()
            self.destroy()
        except ValidationError:
            pass


class StageDialog(BaseModalDialog):
    def __init__(self, app: TaskMNGApp, on_submit, initial_data: dict | None = None, dialog_title: str = "Add Stage-Status"):
        super().__init__(app, title=dialog_title, geometry="520x420", min_size=(480, 360))
        self.on_submit = on_submit
        self.initial_data = initial_data or {}
        self.inputs: dict[str, object] = {}

        stage_values = app.master_data_service.priority_stages(include_inactive=True) or PRIORITY_STAGES
        current_stage = self.initial_data.get("stage_name") or self.initial_data.get("name")
        if current_stage and current_stage not in stage_values:
            stage_values = stage_values + [current_stage]
        status_values = app.master_data_service.pipeline_statuses(include_inactive=True) or PIPELINE_STATUSES
        current_status = self.initial_data.get("stage_status") or self.initial_data.get("phase_status")
        if current_status and current_status not in status_values:
            status_values = status_values + [current_status]

        self._add_combo("stage_name", "Stage", stage_values, current_stage or stage_values[0])
        self._add_option("stage_status", "Stage Status", status_values, current_status or status_values[0])
        self._add_textbox("description", "Description", height=120, initial_value=self.initial_data.get("description"))

        ctk.CTkButton(
            self.footer,
            text="Save Stage-Status",
            height=42,
            fg_color=PALETTE["primary_500"],
            hover_color=PALETTE["primary_700"],
            command=self.submit,
        ).pack(fill="x", padx=4, pady=4)

    def _add_combo(self, key: str, label: str, values: list[str], initial_value: str):
        ctk.CTkLabel(self.body, text=label, text_color=PALETTE["ink_700"]).pack(anchor="w", padx=6, pady=(16, 6))
        combo = ctk.CTkComboBox(self.body, values=values or [""])
        combo.pack(fill="x", padx=6)
        combo.set(initial_value)
        self.inputs[key] = combo

    def _add_option(self, key: str, label: str, values: list[str], current_value: str):
        ctk.CTkLabel(self.body, text=label, text_color=PALETTE["ink_700"]).pack(anchor="w", padx=6, pady=(16, 6))
        option = ctk.CTkOptionMenu(self.body, values=list(values))
        option.pack(fill="x", padx=6)
        option.set(current_value)
        self.inputs[key] = option

    def _add_textbox(self, key: str, label: str, height: int, initial_value: str | None = None):
        ctk.CTkLabel(self.body, text=label, text_color=PALETTE["ink_700"]).pack(anchor="w", padx=6, pady=(16, 6))
        text = ctk.CTkTextbox(self.body, height=height)
        text.pack(fill="both", padx=6, pady=(0, 8))
        if initial_value:
            text.insert("1.0", initial_value)
        self.inputs[key] = text

    def submit(self):
        payload = {
            "stage_name": self.inputs["stage_name"].get(),
            "stage_status": self.inputs["stage_status"].get(),
            "description": self.inputs["description"].get("1.0", tk.END).strip(),
        }
        try:
            self.on_submit(payload)
            self.destroy()
        except ValidationError:
            pass


class TaskDialog(BaseModalDialog):
    def __init__(
        self,
        app: TaskMNGApp,
        on_submit,
        stage_options: list[tuple[str, int]],
        selected_stage_id: int,
        initial_data: dict | None = None,
        dialog_title: str = "Add Task",
    ):
        super().__init__(app, title=dialog_title, geometry="560x780", min_size=(520, 680))
        self.on_submit = on_submit
        self.initial_data = initial_data or {}
        self.stage_options = stage_options
        self.stage_name_to_id = {name: stage_id for name, stage_id in stage_options}
        self.inputs: dict[str, object] = {}

        user_values = [user["display_name"] for user in app.user_service.list_users()]
        status_values = app.master_data_service.task_statuses() or MANUAL_STATUSES
        current_status = self.initial_data.get("manual_status")
        if current_status and current_status not in status_values:
            status_values = status_values + [current_status]
        current_owner = self.initial_data.get("owner_name")
        if current_owner and current_owner not in user_values:
            user_values = user_values + [current_owner]
        current_pic = self.initial_data.get("pic_name")
        if current_pic and current_pic not in user_values:
            user_values = user_values + [current_pic]

        selected_stage_name = next((name for name, stage_id in stage_options if stage_id == selected_stage_id), stage_options[0][0])

        self._add_option("stage_name", "Stage", [name for name, _stage_id in stage_options], self.initial_data.get("stage_label") or selected_stage_name)
        self._add_entry("title", "Task title", self.initial_data.get("title"))
        self._add_combo("owner_name", "Owner", user_values, self.initial_data.get("owner_name"))
        self._add_combo("pic_name", "PIC", user_values, self.initial_data.get("pic_name"))
        self._add_option("manual_status", "Manual status", status_values, current_status or status_values[0])
        self._add_entry("deadline", "Deadline (YYYY-MM-DD)", self.initial_data.get("deadline"))
        self._add_entry("next_action", "Next action", self.initial_data.get("next_action"))
        self._add_textbox("latest_update_summary", "Latest update summary", height=180, initial_value=self.initial_data.get("latest_update_summary"))

        ctk.CTkButton(
            self.footer,
            text="Save Task",
            height=42,
            fg_color=PALETTE["primary_500"],
            hover_color=PALETTE["primary_700"],
            command=self.submit,
        ).pack(fill="x", padx=4, pady=4)

    def _add_entry(self, key: str, label: str, initial_value: str | None = None):
        ctk.CTkLabel(self.body, text=label, text_color=PALETTE["ink_700"]).pack(anchor="w", padx=6, pady=(16, 6))
        entry = ctk.CTkEntry(self.body, height=38)
        entry.pack(fill="x", padx=6)
        if initial_value:
            entry.insert(0, initial_value)
        self.inputs[key] = entry

    def _add_combo(self, key: str, label: str, values: list[str], initial_value: str | None = None):
        ctk.CTkLabel(self.body, text=label, text_color=PALETTE["ink_700"]).pack(anchor="w", padx=6, pady=(16, 6))
        combo = ctk.CTkComboBox(self.body, values=values or [""])
        combo.pack(fill="x", padx=6)
        combo.set(initial_value or "")
        self.inputs[key] = combo

    def _add_option(self, key: str, label: str, values: list[str], current_value: str):
        ctk.CTkLabel(self.body, text=label, text_color=PALETTE["ink_700"]).pack(anchor="w", padx=6, pady=(16, 6))
        option = ctk.CTkOptionMenu(self.body, values=list(values))
        option.pack(fill="x", padx=6)
        option.set(current_value)
        self.inputs[key] = option

    def _add_textbox(self, key: str, label: str, height: int, initial_value: str | None = None):
        ctk.CTkLabel(self.body, text=label, text_color=PALETTE["ink_700"]).pack(anchor="w", padx=6, pady=(16, 6))
        text = ctk.CTkTextbox(self.body, height=height)
        text.pack(fill="both", padx=6, pady=(0, 8))
        if initial_value:
            text.insert("1.0", initial_value)
        self.inputs[key] = text

    def submit(self):
        stage_name = self.inputs["stage_name"].get()
        payload = {
            "phase_id": self.stage_name_to_id[stage_name],
            "title": self.inputs["title"].get(),
            "owner_name": self.inputs["owner_name"].get(),
            "pic_name": self.inputs["pic_name"].get(),
            "manual_status": self.inputs["manual_status"].get(),
            "deadline": self.inputs["deadline"].get() or None,
            "next_action": self.inputs["next_action"].get(),
            "priority": self.initial_data.get("priority", TASK_PRIORITIES[1]),
            "latest_update_summary": self.inputs["latest_update_summary"].get("1.0", tk.END).strip(),
        }
        try:
            self.on_submit(payload)
            self.destroy()
        except ValidationError:
            pass
