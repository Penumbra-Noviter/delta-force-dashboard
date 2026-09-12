"""
自定义主题对话框（多主题 05）：收集 base + 6 锚点覆盖，不直接应用主题。

只负责「打开 → 选 base + 改 6 锚点 → 预览/软提示 → 取回 (base, overrides)」，
不持有全局主题状态、不调用 set_theme（应用到整窗由 06 接上）。预览采用
resolve_palette 的合并范式（``{**THEMES[base], **overrides}``）渲染示例控件，
对比度软提示复用 theme.contrast_hints（3 组文字对 <4.5:1 非阻断提示、不硬拒）。
"""

from __future__ import annotations

__all__ = ["ThemeDialog"]

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.theme import ANCHOR_KEYS, THEMES, contrast_hints

# 预设主题名（base 下拉顺序）
_PRESET_NAMES = ("light", "dark", "nord")

# 锚点显示标签（中文，供表单与 QColorDialog 标题共用）
_ANCHOR_LABELS = {
    "BTN_BG": "按钮背景",
    "BTN_BG_HOVER": "按钮悬停",
    "FG_TODAY": "今日高亮",
    "BG": "窗口背景",
    "FG_POS": "涨色",
    "FG_NEG": "跌色",
}


class ThemeDialog(QDialog):
    """自定义主题对话框：base 下拉 + 6 锚点取色 + 实时预览 + 软提示。"""

    def __init__(
        self,
        base: str,
        overrides: dict[str, str] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("自定义主题")
        self._base = base if base in THEMES else "light"
        src = overrides if isinstance(overrides, dict) else {}
        self._overrides: dict[str, str] = {
            key: src.get(key, THEMES[self._base][key]) for key in ANCHOR_KEYS
        }

        self._build_ui()
        self._refresh_preview()

    # ── UI 构建 ──────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        form = QFormLayout()

        self._base_combo = QComboBox()
        for name in _PRESET_NAMES:
            self._base_combo.addItem(name, name)
        # 构造期设置当前 base 不触发 _on_base_changed（保留预填 overrides）
        self._base_combo.blockSignals(True)
        self._base_combo.setCurrentIndex(_PRESET_NAMES.index(self._base))
        self._base_combo.blockSignals(False)
        self._base_combo.currentIndexChanged.connect(self._on_base_changed)
        form.addRow("基础主题", self._base_combo)

        self._color_buttons: dict[str, QPushButton] = {}
        for key in ANCHOR_KEYS:
            btn = QPushButton()
            btn.clicked.connect(lambda checked=False, k=key: self._pick_color(k))
            form.addRow(_ANCHOR_LABELS[key], btn)
            self._color_buttons[key] = btn
        layout.addLayout(form)

        # 预览示例框（BG 底 + 今日高亮 / 按钮 / 涨 / 跌示例控件）
        self._preview = QFrame()
        self._preview.setObjectName("themePreview")
        preview_layout = QVBoxLayout(self._preview)
        self._preview_today = QLabel("今日数据")
        self._preview_btn = QPushButton("保存")
        self._preview_pos = QLabel("+123.45")
        self._preview_neg = QLabel("-45.67")
        for w in (
            self._preview_today,
            self._preview_btn,
            self._preview_pos,
            self._preview_neg,
        ):
            preview_layout.addWidget(w)
        layout.addWidget(self._preview)

        self._hints_label = QLabel()
        self._hints_label.setObjectName("contrastHints")
        self._hints_label.setWordWrap(True)
        layout.addWidget(self._hints_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ── 交互 ────────────────────────────────────────────

    def _on_base_changed(self) -> None:
        """base 下拉变更：6 锚点重置为新 base 默认值并刷新预览。"""
        self._base = self._base_combo.currentData()
        for key in ANCHOR_KEYS:
            self._overrides[key] = THEMES[self._base][key]
        self._refresh_preview()

    def _pick_color(self, key: str) -> None:
        """经 QColorDialog 取色；有效则更新锚点并刷新预览（取消无副作用）。"""
        initial = QColor(self._overrides[key])
        color = QColorDialog.getColor(initial, self, _ANCHOR_LABELS[key])
        if color.isValid():
            self._overrides[key] = color.name(QColor.NameFormat.HexRgb).upper()
            self._refresh_preview()

    def _preview_palette(self) -> dict[str, str]:
        """合并预览色板（与 resolve_palette 对自定义槽位的合并语义一致）。

        不注册全局 CUSTOM 槽位、不调 set_theme——对话框只预览，不持有主题状态。
        """
        return {**THEMES[self._base], **self._overrides}

    def _refresh_preview(self) -> None:
        """按合并色板更新锚点色块、预览示例与对比度软提示。"""
        p = self._preview_palette()

        for key, btn in self._color_buttons.items():
            value = self._overrides[key]
            btn.setText(value)
            btn.setStyleSheet(f"background-color: {value};")

        self._preview.setStyleSheet(f"background-color: {p['BG']};")
        self._preview_today.setStyleSheet(f"color: {p['FG_TODAY']};")
        self._preview_btn.setStyleSheet(
            f"background-color: {p['BTN_BG']}; color: {p['BTN_FG']};"
        )
        self._preview_pos.setStyleSheet(f"color: {p['FG_POS']};")
        self._preview_neg.setStyleSheet(f"color: {p['FG_NEG']};")

        hints = contrast_hints(p)
        self._hints_label.setText("\n".join(hints))

    # ── 结果契约 ────────────────────────────────────────

    def result(self) -> tuple[str, dict[str, str]]:
        """返回 (base, overrides)：overrides 仅含与 base 默认值不同的 6 锚点。"""
        overrides = {
            key: value
            for key, value in self._overrides.items()
            if value != THEMES[self._base][key]
        }
        return self._base, overrides
