from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QAbstractItemView, QMainWindow, QMessageBox, QTableWidgetItem

from controller import Controller, ControllerError
from ui_main_window import Ui_MainWindow

ADMIN_TABS = ("manage_games_tab", "manage_members_tab", "manage_fees_tab")


def _set_row(table, row, values):
    for col, value in enumerate(values):
        table.setItem(row, col, QTableWidgetItem(str(value)))


def _selected_ids(table, id_column=0):
    rows = {index.row() for index in table.selectedIndexes()}
    return [int(table.item(row, id_column).text()) for row in sorted(rows)]


class MainWindow:
    def __init__(self, controller: Controller | None = None):
        self.controller = controller or Controller()
        self.member = None

        self.main_win = QMainWindow()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self.main_win)

        self.ui.stackedWidget.setCurrentWidget(self.ui.login_page)
        self._signals()

    def show(self):
        self.main_win.show()

    # ----- wiring ----- #
    def _signals(self):
        self.ui.login_btn.clicked.connect(self.login)
        self.ui.password_le.returnPressed.connect(self.login)
        self.ui.logout_btn.clicked.connect(self.logout)

        self.ui.search_btn.clicked.connect(self.show_catalogue)
        self.ui.borrow_btn.clicked.connect(self.borrow_selected)
        self.ui.hold_btn.clicked.connect(self.toggle_hold_selected)

        self.ui.return_btn.clicked.connect(self.return_selected)

        self.ui.add_game_btn.clicked.connect(self.add_game)
        self.ui.remove_game_btn.clicked.connect(self.remove_selected_game)

        self.ui.register_btn.clicked.connect(self.register_member)
        self.ui.toggle_active_btn.clicked.connect(self.toggle_selected_member)

        self.ui.fee_member_cb.currentIndexChanged.connect(self.show_member_fees)
        self.ui.mark_paid_btn.clicked.connect(self.mark_fee_paid)
        self.ui.run_fees_btn.clicked.connect(self.run_annual_fees)

        self.ui.tabWidget.currentChanged.connect(self.tab_changed)

    # ----- auth ----- #
    def login(self):
        email = self.ui.email_le.text().strip()
        password = self.ui.password_le.text()

        try:
            member = self.controller.login(email, password)
        except ControllerError as exc:
            self.ui.login_error_lbl.setText(str(exc))
            return

        if member is None:
            self.ui.login_error_lbl.setText("Invalid email or password.")
            return

        self.member = member
        self.ui.login_error_lbl.setText("")
        self.ui.password_le.clear()
        self.ui.welcome_lbl.setText(
            f"Welcome, {member['first_name']} {member['last_name']}"
            + (" (admin)" if member["admin"] else "")
        )

        self._apply_role_visibility()
        self.ui.stackedWidget.setCurrentWidget(self.ui.main_page)
        self.ui.tabWidget.setCurrentIndex(0)
        self.tab_changed(0)

    def logout(self):
        self.member = None
        self.ui.email_le.clear()
        self.ui.password_le.clear()
        self.ui.stackedWidget.setCurrentWidget(self.ui.login_page)

    def _apply_role_visibility(self):
        is_admin = bool(self.member and self.member["admin"])
        for tab_name in ADMIN_TABS:
            tab = getattr(self.ui, tab_name)
            index = self.ui.tabWidget.indexOf(tab)
            self.ui.tabWidget.setTabVisible(index, is_admin)

    def _show_error(self, exc: Exception):
        QMessageBox.warning(self.main_win, "Error", str(exc))

    # ----- tab lazy-loading ----- #
    def tab_changed(self, index):
        tab = self.ui.tabWidget.widget(index)
        name = tab.objectName()

        if name == "browse_tab":
            self._populate_filters()
            self.show_catalogue()
        elif name == "loans_tab":
            self.show_loans()
        elif name == "fees_tab":
            self.show_fees()
        elif name == "manage_games_tab":
            self._populate_game_form_dropdowns()
            self.show_admin_games()
        elif name == "manage_members_tab":
            self.show_members()
        elif name == "manage_fees_tab":
            self._populate_fee_member_dropdown()

    # ----- browse / search ----- #
    def _populate_filters(self):
        if self.ui.category_cb.count() > 0:
            return
        self.ui.category_cb.addItem("Any category", None)
        for cat_id, name in self.controller.get_categories():
            self.ui.category_cb.addItem(name, cat_id)

    def show_catalogue(self):
        category_id = self.ui.category_cb.currentData()
        players = self.ui.players_sb.value() or None
        age = self.ui.age_sb.value() or None

        games = self.controller.browse_catalogue(
            search_title=self.ui.search_le.text().strip(),
            category_id=category_id,
            num_players=players,
            min_age=age,
            available_only=self.ui.available_only_cb.isChecked(),
        )

        table = self.ui.catalogue_tb
        table.setRowCount(len(games))
        for row, game in enumerate(games):
            game_id, name, category, min_p, max_p, min_age, status, on_hold = game
            _set_row(
                table,
                row,
                [game_id, name, category, min_p, max_p, min_age, status, "Yes" if on_hold else "No"],
            )

    def borrow_selected(self):
        if not self.member:
            return
        game_ids = _selected_ids(self.ui.catalogue_tb)
        try:
            self.controller.borrow_games(self.member["mem_id"], game_ids)
        except ControllerError as exc:
            self._show_error(exc)
            return
        self.show_catalogue()

    def toggle_hold_selected(self):
        if not self.member:
            return
        game_ids = _selected_ids(self.ui.catalogue_tb)
        try:
            for game_id in game_ids:
                self.controller.toggle_hold(self.member["mem_id"], game_id)
        except ControllerError as exc:
            self._show_error(exc)
            return
        self.show_catalogue()

    # ----- loans ----- #
    def show_loans(self):
        if not self.member:
            return
        loans = self.controller.get_member_loans(self.member["mem_id"])
        table = self.ui.loans_tb
        table.setRowCount(len(loans))
        for row, (game_id, name) in enumerate(loans):
            _set_row(table, row, [game_id, name])

    def return_selected(self):
        game_ids = _selected_ids(self.ui.loans_tb)
        try:
            for game_id in game_ids:
                self.controller.return_game(game_id)
        except ControllerError as exc:
            self._show_error(exc)
            return
        self.show_loans()

    # ----- fees (member) ----- #
    def show_fees(self):
        if not self.member:
            return
        fees = self.controller.get_member_fees(self.member["mem_id"])
        table = self.ui.fees_tb
        table.setRowCount(len(fees))
        for row, (year, paid) in enumerate(fees):
            _set_row(table, row, [year, "Yes" if paid else "No"])

    # ----- manage games (admin) ----- #
    def _populate_game_form_dropdowns(self):
        if self.ui.add_cat_cb.count() == 0:
            for cat_id, name in self.controller.get_categories():
                self.ui.add_cat_cb.addItem(name, cat_id)

        self.ui.owner_cb.clear()
        self.ui.owner_cb.addItem("Club", None)
        for mem_id, name in self.controller.get_active_members():
            self.ui.owner_cb.addItem(name, mem_id)

    def add_game(self):
        try:
            self.controller.add_game(
                name=self.ui.name_le.text(),
                cat_id=self.ui.add_cat_cb.currentData(),
                min_players=self.ui.min_players_sb.value(),
                max_players=self.ui.max_players_sb.value(),
                min_age=self.ui.min_age_sb.value(),
                owner=self.ui.owner_cb.currentData(),
            )
        except ControllerError as exc:
            self._show_error(exc)
            return

        self.ui.name_le.clear()
        self.show_admin_games()

    def show_admin_games(self):
        games = self.controller.browse_catalogue()
        table = self.ui.admin_games_tb
        table.setRowCount(len(games))
        for row, game in enumerate(games):
            game_id, name, category, _min_p, _max_p, _min_age, status, _hold = game
            _set_row(table, row, [game_id, name, category, status])

    def remove_selected_game(self):
        game_ids = _selected_ids(self.ui.admin_games_tb)
        confirm = self.ui.remove_confirm_cb.isChecked()
        try:
            for game_id in game_ids:
                self.controller.remove_game(game_id, confirm_on_loan=confirm)
        except ControllerError as exc:
            self._show_error(exc)
            return
        self.show_admin_games()

    # ----- manage members (admin) ----- #
    def register_member(self):
        try:
            self.controller.register_member(
                first_name=self.ui.reg_first_le.text(),
                last_name=self.ui.reg_last_le.text(),
                email=self.ui.reg_email_le.text(),
                password=self.ui.reg_password_le.text(),
                phone=self.ui.reg_phone_le.text(),
                admin=1 if self.ui.reg_admin_cb.isChecked() else 0,
            )
        except ControllerError as exc:
            self._show_error(exc)
            return

        for field in (
            self.ui.reg_first_le,
            self.ui.reg_last_le,
            self.ui.reg_email_le,
            self.ui.reg_password_le,
            self.ui.reg_phone_le,
        ):
            field.clear()
        self.ui.reg_admin_cb.setChecked(False)
        self.show_members()

    def show_members(self):
        members = self.controller.get_all_members()
        table = self.ui.members_tb
        table.setRowCount(len(members))
        for row, (mem_id, name, active, admin) in enumerate(members):
            _set_row(
                table,
                row,
                [mem_id, name, "Yes" if active else "No", "Yes" if admin else "No"],
            )

    def toggle_selected_member(self):
        for mem_id in _selected_ids(self.ui.members_tb):
            self.controller.toggle_member_active(mem_id)
        self.show_members()

    # ----- manage fees (admin) ----- #
    def _populate_fee_member_dropdown(self):
        if self.ui.fee_member_cb.count() > 0:
            return
        for mem_id, name in self.controller.get_active_members():
            self.ui.fee_member_cb.addItem(name, mem_id)
        if self.ui.fee_member_cb.count() > 0:
            self.show_member_fees()

    def show_member_fees(self):
        mem_id = self.ui.fee_member_cb.currentData()
        if mem_id is None:
            return
        fees = self.controller.get_member_fees(mem_id)
        table = self.ui.member_fees_tb
        table.setRowCount(len(fees))
        for row, (year, paid) in enumerate(fees):
            _set_row(table, row, [year, "Yes" if paid else "No"])

    def mark_fee_paid(self):
        mem_id = self.ui.fee_member_cb.currentData()
        if mem_id is None:
            return
        try:
            self.controller.record_fee_payment(self.ui.fee_year_sb.value(), mem_id)
        except ControllerError as exc:
            self._show_error(exc)
            return
        self.show_member_fees()

    def run_annual_fees(self):
        try:
            self.controller.run_annual_fees(
                self.ui.run_year_sb.value(), self.ui.run_amt_sb.value()
            )
        except ControllerError as exc:
            self._show_error(exc)
            return
        self.show_member_fees()