"""
卡战备推荐页面：输入目标战备值，显示最优的多个市场直购方案。

数据来源于 kkrb.net API（KkrbClient.fetch_cpv_data），手动查询。
"""

from __future__ import annotations

__all__ = ["GearPage"]

import logging
from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from kkrb_client import GearScheme, KkrbClient, KkrbError
from formatting import format_money, parse_money_input

logger = logging.getLogger(__name__)


class GearPage(QWidget):
    """卡战备推荐页面（QStackedWidget Page 2）。"""

    _TABLE_HEADERS = ["装备名", "磨损度", "花费", "战备值", "来源"]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._client = KkrbClient()
        self._all_tiers: dict[int, list[GearScheme]] = {}
        self._loading = False
        self._error: str | None = None

        self._build_ui()

    # ── UI 构建 ─────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 16)
        layout.setSpacing(16)

        # 标题
        title = QLabel("卡战备推荐")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        # 输入区
        input_row = QHBoxLayout()
        input_row.setSpacing(8)

        self._target_input = QLineEdit()
        self._target_input.setObjectName("gearTargetInput")
        self._target_input.setPlaceholderText("输入目标战备值，如 150000 或 150K")
        self._target_input.returnPressed.connect(self._on_query)
        input_row.addWidget(self._target_input, 1)

        self._query_btn = QPushButton("🔍 查询")
        self._query_btn.setObjectName("queryBtn")
        self._query_btn.clicked.connect(self._on_query)
        input_row.addWidget(self._query_btn)

        layout.addLayout(input_row)

        # 状态提示
        self._status_label = QLabel("")
        self._status_label.setObjectName("statusLabel")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setVisible(False)
        layout.addWidget(self._status_label)

        # 结果区
        self._result_area = QVBoxLayout()
        self._result_area.setSpacing(12)
        layout.addLayout(self._result_area)

        # 初始提示
        self._hint_label = QLabel("输入目标战备值后点击查询，将匹配最接近的档位方案")
        self._hint_label.setObjectName("hintLabel")
        self._hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._result_area.addWidget(self._hint_label)

        layout.addStretch()

    def _build_scheme_card(self, scheme: GearScheme) -> QFrame:
        card = QFrame()
        card.setObjectName("gearSchemeCard")
        card.setFrameShape(QFrame.Shape.StyledPanel)

        cl = QVBoxLayout(card)
        cl.setContentsMargins(16, 14, 16, 14)
        cl.setSpacing(8)

        # 方案标题 + 总花费 + 最终战备
        summary = QLabel(
            f"<b>{scheme.title}</b>  "
            f"总花费：{format_money(scheme.total_cost)}  "
            f"最终战备：{format_money(scheme.final_bv)}"
        )
        summary.setObjectName("schemeSummary")
        cl.addWidget(summary)

        # 装备清单表格
        table = QTableWidget(len(scheme.items), 5)
        table.setObjectName("schemeItemsTable")
        table.setHorizontalHeaderLabels(self._TABLE_HEADERS)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)

        for row, item in enumerate(scheme.items):
            table.setItem(row, 0, QTableWidgetItem(item.name))
            table.setItem(row, 1, QTableWidgetItem(item.wear))
            table.setItem(row, 2, QTableWidgetItem(format_money(item.cost)))
            table.setItem(row, 3, QTableWidgetItem(format_money(item.battle_value)))
            table.setItem(row, 4, QTableWidgetItem(item.source))

        cl.addWidget(table)

        return card

    # ── 查询 ────────────────────────────────────────────

    def _on_query(self) -> None:
        raw = self._target_input.text().strip()
        if not raw:
            self._status_label.setText("请输入目标战备值")
            self._status_label.setVisible(True)
            return

        try:
            target = parse_money_input(raw)
        except ValueError:
            self._status_label.setText("无法识别输入的金额格式")
            self._status_label.setVisible(True)
            return

        if target <= 0:
            self._status_label.setText("请输入大于 0 的战备值")
            self._status_label.setVisible(True)
            return

        self._do_query(target)

    def _do_query(self, target: int) -> None:
        self._loading = True
        self._error = None
        self._status_label.setText("🔄 查询中…")
        self._status_label.setVisible(True)
        self._query_btn.setEnabled(False)
        self._clear_results()

        QTimer.singleShot(0, lambda: self._fetch_and_show(target))

    def _fetch_and_show(self, target: int) -> None:
        try:
            self._all_tiers = self._client.fetch_cpv_data()
            self._error = None
            self._status_label.setVisible(False)
        except KkrbError as e:
            logger.warning("战备数据获取失败: %s", e)
            self._error = str(e)
            self._status_label.setText("⚠️ 数据获取失败，请重试")
            self._status_label.setVisible(True)
            self._loading = False
            self._query_btn.setEnabled(True)
            return
        except Exception as e:
            logger.error("战备数据获取异常: %s", e)
            self._error = str(e)
            self._status_label.setText("⚠️ 网络异常，请检查连接后重试")
            self._status_label.setVisible(True)
            self._loading = False
            self._query_btn.setEnabled(True)
            return

        self._loading = False
        self._query_btn.setEnabled(True)

        if not self._all_tiers:
            self._status_label.setText("未获取到战备数据，请重试")
            self._status_label.setVisible(True)
            return

        # 匹配最接近的档位
        matched_tier = self._find_closest_tier(target, list(self._all_tiers.keys()))
        if matched_tier is None:
            self._status_label.setText("未找到匹配的战备方案")
            self._status_label.setVisible(True)
            return

        schemes = self._all_tiers.get(matched_tier, [])
        if not schemes:
            self._status_label.setText(f"档位 {format_money(matched_tier)} 暂无方案数据")
            self._status_label.setVisible(True)
            return

        self._show_results(matched_tier, schemes)

    @staticmethod
    def _find_closest_tier(target: int, tiers: list[int]) -> int | None:
        if not tiers:
            return None
        return min(tiers, key=lambda t: abs(t - target))

    def _show_results(self, tier: int, schemes: list[GearScheme]) -> None:
        self._clear_results()

        # 档位标题
        tier_label = QLabel(f"匹配档位：{format_money(tier)} 战备（{len(schemes)} 个方案）")
        tier_label.setObjectName("tierLabel")
        self._result_area.addWidget(tier_label)

        for scheme in schemes:
            card = self._build_scheme_card(scheme)
            self._result_area.addWidget(card)

        self._result_area.addStretch()

    def _clear_results(self) -> None:
        while self._result_area.count():
            item = self._result_area.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def refresh(self) -> None:
        """公开刷新方法（供外部调用，清空输入和结果）。"""
        self._target_input.clear()
        self._clear_results()
        self._status_label.setVisible(False)
        hint = QLabel("输入目标战备值后点击查询，将匹配最接近的档位方案")
        hint.setObjectName("hintLabel")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint_label = hint
        self._result_area.addWidget(self._hint_label)