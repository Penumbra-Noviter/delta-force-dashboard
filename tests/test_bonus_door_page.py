"""密码门页面（BonusDoorPage）测试（BD-02）。

覆盖：
- 三态：加载中（status label 文案）/ 数据渲染（动态卡片网格）/ 错误（占位可区分）；
- 空态：显式占位「暂无数据」；错误态占位「加载失败，点击重试」（C2-05 惯例）；
- 卡片动态构建：_render_data 清空网格按数据重建（数据量小，重建成本可忽略）；
- 密码大字内联样式仅字号/字重（34px bold），颜色全走 QSS 选择器（C1 契约）；
- 双主题 QSS 选择器（#bonusDoorCard / #bonusDoorMap / #bonusDoorPassword）与
  密码色随主题（TEXT_PRIMARY 双主题异值）；
- 构造注入 stub client 断网测试（C2-02 惯例）。
"""

from __future__ import annotations

import os

# offscreen 平台必须在 QApplication 创建前设置
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import re

import pytest

from tests.conftest import make_stub_client

__all__ = []


@pytest.fixture(autouse=True)
def _drain_delete_later(qapp):
    """排水：每个用例结束后处理 deleteLater 队列（_rebuild_cards 的旧卡删除）。

    仓库既有纪律（test_ui_smoke C4-债4「排水等待」）：deleteLater 的 C++
    对象随后续事件循环才真正删除——页面测试多次 _render_data 重建卡片若不
    排水，pending-delete 对象跨用例累积（GDI/字体资源），全量套件跑至数百
    窗口后触发 pyqtgraph TextItem 原生 access violation（Windows offscreen）。
    """
    yield
    qapp.processEvents()


def _sample_items() -> list:
    """6 张图的样本条目（与 fetch_bonus_door_data 输出同构，az3r6 已剔除）。"""
    from kkrb_client import BonusDoorItem

    return [
        BonusDoorItem("db", "零号大坝", "870140", "20260813000000"),
        BonusDoorItem("cgxg", "长弓溪谷", "123456", "20260813000000"),
        BonusDoorItem("bks", "巴克什", "654321", "20260813000000"),
        BonusDoorItem("htjd", "航天基地", "135790", "20260813000000"),
        BonusDoorItem("cxjy", "潮汐监狱", "888888", "20260813000000"),
        BonusDoorItem("az3", "AZ3", "246810", "20260813000000"),
    ]


# ── 三态：加载中 / 数据渲染 / 错误 ─────────────────────────


def test_bonus_door_page_lazy_loads_and_renders(qapp) -> None:
    """showEvent 首次显示触发加载：加载中文案 → 数据渲染 6 卡 + 占位隐藏。"""
    from app.bonus_door_page import BonusDoorPage

    page = BonusDoorPage(client=make_stub_client(bonus_impl=_sample_items))

    page.show()  # 触发 showEvent → 懒加载
    assert page._load_state.is_loading is True
    assert "加载中" in page._status_label.text()
    worker = page._worker
    assert worker is not None
    assert worker.wait(5000)
    qapp.processEvents()

    assert page.is_loaded is True
    assert page._load_state.is_loading is False
    assert page._status_label.isHidden()
    assert len(page._cards) == 6
    # 卡片内容：地图名 + 密码大字（BD-02 验收：不展示更新时间）
    first = page._cards[0]
    assert first._map_label.text() == "零号大坝"
    assert first._password_label.text() == "870140"
    assert first._map_label.objectName() == "bonusDoorMap"
    assert first._password_label.objectName() == "bonusDoorPassword"
    assert not page._placeholder.isVisible(), "有数据时占位必须隐藏"
    page.hide()


def test_bonus_door_render_data_rebuilds_cards(qapp) -> None:
    """动态构建：_render_data 清空网格按数据重建（3→6→2 卡，无残留）。"""
    from app.bonus_door_page import BonusDoorPage
    from kkrb_client import BonusDoorItem

    page = BonusDoorPage(client=make_stub_client())

    page._render_data(_sample_items()[:3])
    assert len(page._cards) == 3
    assert page._card_grid.count() == 3

    page._render_data(_sample_items())
    assert len(page._cards) == 6
    assert page._card_grid.count() == 6

    page._render_data(
        [BonusDoorItem("db", "零号大坝", "870140", "20260813000000")]
    )
    assert len(page._cards) == 1
    assert page._card_grid.count() == 1
    assert page._cards[0]._map_label.text() == "零号大坝"


def test_bonus_door_empty_data_shows_placeholder(qapp) -> None:
    """空数据 → 显式占位「暂无数据」、零卡片（与错误态文案可区分）。"""
    from app.bonus_door_page import BonusDoorPage

    page = BonusDoorPage(client=make_stub_client())
    page.show()
    worker = page._worker
    assert worker is not None
    assert worker.wait(5000)
    qapp.processEvents()

    assert page.is_loaded is True
    assert page._cards == []
    assert page._placeholder.isVisible()
    assert page._placeholder.text() == "暂无数据"
    page.hide()


def test_bonus_door_render_data_none_fields_defensive(qapp) -> None:
    """BD-债3：None 字段的 BonusDoorItem（仅 stub 手造可达）渲染不崩，显示空串。

    契约守卫（C4-债6 先例）：实测 PySide6 6.11.1 下 QLabel(None) 不崩、
    退化为空文本——无行为级反证，改动属防御性/一致性加固（QLabel 构造
    入参契约是 str），测试锁定「None 字段 → 空串显示」行为。
    """
    from app.bonus_door_page import BonusDoorPage
    from kkrb_client import BonusDoorItem

    page = BonusDoorPage(client=make_stub_client())
    page._render_data(
        [
            BonusDoorItem(key="db", name=None, password=None, updated=None),  # type: ignore[arg-type]
            BonusDoorItem(key="cgxg", name=None, password=None, updated=None),  # type: ignore[arg-type]
        ]
    )
    assert len(page._cards) == 2
    for card in page._cards:
        assert card._map_label.text() == ""
        assert card._password_label.text() == ""


def test_bonus_door_render_data_none_item_skipped(qapp) -> None:
    """Falsify（BD-债批次评审②）：list 内 None 条目跳过不崩（仅 stub 手造可达）。

    BD-债3 相邻边界：`_build_card(None)` 的 `item.name` 会 AttributeError；
    真实路径 parse 恒产 BonusDoorItem，纯防御。
    """
    from app.bonus_door_page import BonusDoorPage
    from kkrb_client import BonusDoorItem

    page = BonusDoorPage(client=make_stub_client())
    page._render_data(
        [
            None,  # type: ignore[list-item]
            BonusDoorItem(key="db", name="零号大坝", password="0003", updated=""),
        ]
    )
    assert len(page._cards) == 1
    assert page._cards[0]._password_label.text() == "0003"


def test_bonus_door_render_data_none_falls_back_to_empty(qapp) -> None:
    """Falsify：_render_data(None) 与空数据等价（data or [] 兜底，不抛）。"""
    from app.bonus_door_page import BonusDoorPage

    page = BonusDoorPage(client=make_stub_client())
    page._render_data(None)  # type: ignore[arg-type]
    assert page._cards == []
    assert page._placeholder.text() == "暂无数据"
    assert not page._placeholder.isHidden()


def test_bonus_door_error_renders_distinct_from_empty(qapp) -> None:
    """错误态：占位「加载失败，点击重试」≠ 空态「暂无数据」（C2-05），卡片清空。"""
    from app.bonus_door_page import BonusDoorPage
    from kkrb_client import KkrbError

    page = BonusDoorPage(
        client=make_stub_client(
            bonus_impl=lambda: (_ for _ in ()).throw(KkrbError("boom"))
        )
    )
    page.show()
    worker = page._worker
    assert worker is not None
    assert worker.wait(5000)
    qapp.processEvents()

    assert page._status_label.text() == "⚠ 数据获取失败，点击重试"
    assert page._placeholder.isVisible()
    assert page._placeholder.text() == "加载失败，点击重试"
    assert page._placeholder.text() != "暂无数据"  # 与空态可区分
    assert page._cards == []
    page.hide()


def test_bonus_door_generic_error_shows_network_message(qapp) -> None:
    """非 KkrbError 异常走 generic 分支：网络文案 + 错误占位（Falsify）。"""
    from app.bonus_door_page import BonusDoorPage

    page = BonusDoorPage(
        client=make_stub_client(
            bonus_impl=lambda: (_ for _ in ()).throw(RuntimeError("timeout"))
        )
    )
    page.show()
    worker = page._worker
    assert worker is not None
    assert worker.wait(5000)
    qapp.processEvents()

    assert page._status_label.text() == "⚠ 网络异常，请检查连接后重试"
    assert page._placeholder.text() == "加载失败，点击重试"
    page.hide()


def test_bonus_door_error_after_data_clears_cards(qapp) -> None:
    """数据渲染后再出错：卡片清空、占位切换为错误文案（动态重建无残留）。"""
    from app.bonus_door_page import BonusDoorPage

    page = BonusDoorPage(client=make_stub_client())
    page._render_data(_sample_items())
    assert len(page._cards) == 6

    page._render_error()
    assert page._cards == []
    assert page._card_grid.count() == 0
    assert page._placeholder.text() == "加载失败，点击重试"
    assert not page._placeholder.isHidden()


# ── 主题契约 ──────────────────────────────────────────────


def test_bonus_door_apply_theme_is_noop(qapp) -> None:
    """C1-07：apply_theme() 空操作——不改变标签文本/样式（颜色全 QSS 驱动）。"""
    from app.bonus_door_page import BonusDoorPage

    page = BonusDoorPage(client=make_stub_client())
    page._render_data(_sample_items())
    before = [
        (c._map_label.text(), c._map_label.styleSheet(), c._password_label.styleSheet())
        for c in page._cards
    ]

    page.apply_theme()

    after = [
        (c._map_label.text(), c._map_label.styleSheet(), c._password_label.styleSheet())
        for c in page._cards
    ]
    assert before == after, "apply_theme 不得改变任何标签文本/样式"


def test_bonus_door_password_inline_style_has_no_color_literal(qapp) -> None:
    """C1-09：密码大字内联样式仅字号/字重（34px bold），无颜色字面量。

    颜色必须全部 QSS 选择器驱动（#bonusDoorPassword → TEXT_PRIMARY），
    出现 #hex / rgba( / color: 即红（构建期冻结色随主题失效）。
    """
    from app.bonus_door_page import BonusDoorPage

    page = BonusDoorPage(client=make_stub_client())
    page._render_data(_sample_items())
    color_literal = re.compile(r"#[0-9A-Fa-f]{3,8}\b|rgba?\(")
    for card in page._cards:
        style = card._password_label.styleSheet()
        assert "font-size: 34px" in style
        assert "bold" in style
        assert not color_literal.search(style), f"内联样式含颜色字面量：{style!r}"
        assert "color:" not in style, f"内联样式含 color 属性：{style!r}"


def test_bonus_door_qss_selectors_present_in_both_themes() -> None:
    """双主题 QSS 均含三选择器（新页面漏配某主题即隐形，经验回归）。"""
    from app.theme import THEMES, generate_qss

    for name in THEMES:
        qss = generate_qss(name)
        assert "QFrame#bonusDoorCard" in qss, f"{name} 缺 bonusDoorCard 选择器"
        assert "QLabel#bonusDoorMap" in qss, f"{name} 缺 bonusDoorMap 选择器"
        assert "QLabel#bonusDoorPassword" in qss, f"{name} 缺 bonusDoorPassword 选择器"


def test_bonus_door_password_color_follows_theme() -> None:
    """密码色随主题：TEXT_PRIMARY 双主题异值且各自落入 QSS 选择器块。"""
    from app.theme import THEMES, generate_qss

    def password_block(qss: str) -> str:
        return qss.split("QLabel#bonusDoorPassword")[1].split("}")[0]

    light_block = password_block(generate_qss("light"))
    dark_block = password_block(generate_qss("dark"))
    assert THEMES["light"]["TEXT_PRIMARY"] in light_block
    assert THEMES["dark"]["TEXT_PRIMARY"] in dark_block
    assert light_block != dark_block, "密码色必须随主题变化"


# ── 构造注入 stub client（C2-02 断网）──────────────────────


def test_bonus_door_page_injected_client_used_by_fetch(qapp) -> None:
    """构造注入：BonusDoorPage(client=fake) 后 _fetch 落在 fake 实例。"""
    from types import SimpleNamespace

    from app.bonus_door_page import BonusDoorPage

    calls: list[str] = []
    fake = SimpleNamespace(
        fetch_bonus_door_data=lambda: (calls.append("bonus"), [])[1]
    )
    page = BonusDoorPage(client=fake)
    assert page._fetch() == []
    assert calls == ["bonus"]


def test_bonus_door_page_without_client_builds_own_kkrb_client(qapp) -> None:
    """client=None 现状兼容：自建 KkrbClient（既有直构用例语义不变）。"""
    from app.bonus_door_page import BonusDoorPage
    from kkrb_client import KkrbClient

    assert isinstance(BonusDoorPage()._client, KkrbClient)
