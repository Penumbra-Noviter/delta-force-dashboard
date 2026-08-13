"""kkrb_parsing 纯函数解析测试（架构深化候选 1）。

解析从 kkrb_client 拆出后可直接脱离网络单测——畸形输入矩阵
（非 dict / 缺字段 / 字段类型异常 / 结构畸形条目跳过 / 排序 / 回退 key）
是拆解析的最大收益：kkrb 响应格式多变，这些用例此前只能打桩实例覆盖。
"""

from __future__ import annotations

import pytest

from kkrb_models import KkrbError
from kkrb_parsing import (
    _int_or_zero,
    parse_ammo_package_response,
    parse_bonus_door_response,
    parse_ov_response,
)


class TestIntOrZero:
    def test_int(self) -> None:
        assert _int_or_zero(42) == 42

    def test_str_int(self) -> None:
        assert _int_or_zero("42") == 42

    def test_none(self) -> None:
        assert _int_or_zero(None) == 0

    def test_invalid(self) -> None:
        assert _int_or_zero("abc") == 0

    def test_float(self) -> None:
        assert _int_or_zero(2762.59) == 2762

    def test_bool(self) -> None:
        """bool 是 int 子类，int(True)=1（保持既有行为）。"""
        assert _int_or_zero(True) == 1


class TestParseOVResponse:
    """解析 getOVData 响应测试（实际 API 格式）。"""

    def test_parse_valid(self) -> None:
        data = {
            "code": 1,
            "data": {
                "spData": {
                    "tech": {
                        "placeName": "技术中心",
                        "itemName": "灵眼3/7测距狙击瞄准镜",
                        "profit": 24669,
                        "singlePrice": 39077,
                        "yesterdayHighestTime": "晚上8点",
                    },
                    "workbench": {
                        "placeName": "工作台",
                        "itemName": "4.6x30mm AP SX",
                        "profit": 272408,
                        "singlePrice": 3942,
                        "yesterdayHighestTime": "上午6点",
                    },
                }
            },
        }
        products = parse_ov_response(data)
        assert len(products) == 2
        # 按利润降序排列：工作台 272408 > 技术中心 24669
        assert products[0].station == "工作台"
        assert products[0].profit == 272408
        assert products[0].ideal_price == 3942
        assert products[0].sell_time == "上午6点"
        assert products[1].station == "技术中心"
        assert products[1].profit == 24669
        assert products[1].ideal_price == 39077
        assert products[1].sell_time == "晚上8点"

    def test_parse_empty_sp_data(self) -> None:
        assert parse_ov_response({"code": 1, "data": {"spData": {}}}) == []

    def test_parse_missing_data_key(self) -> None:
        assert parse_ov_response({}) == []

    def test_parse_malformed(self) -> None:
        with pytest.raises(KkrbError):
            parse_ov_response("not a dict")

    # ── 畸形矩阵扩展 ────────────────────────────────────

    def test_parse_data_not_dict(self) -> None:
        """data 字段不是 dict → 空列表（不回退、不抛）。"""
        assert parse_ov_response({"code": 1, "data": []}) == []

    def test_parse_sp_data_not_dict(self) -> None:
        assert parse_ov_response({"code": 1, "data": {"spData": "oops"}}) == []

    def test_parse_station_entry_not_dict(self) -> None:
        """畸形台位条目跳过，合法条目保留。"""
        data = {
            "data": {
                "spData": {
                    "tech": "not a dict",
                    "workbench": {
                        "placeName": "工作台",
                        "itemName": "4.6x30mm AP SX",
                        "profit": 272408,
                        "singlePrice": 3942,
                        "yesterdayHighestTime": "上午6点",
                    },
                }
            }
        }
        products = parse_ov_response(data)
        assert len(products) == 1
        assert products[0].station == "工作台"

    def test_parse_missing_fields_default(self) -> None:
        """缺字段用默认值兜底，不抛。"""
        products = parse_ov_response(
            {"data": {"spData": {"tech": {"profit": "12345"}}}}
        )
        assert len(products) == 1
        p = products[0]
        assert p.station == "tech"      # placeName 缺失 → 回退 key
        assert p.product == ""          # itemName 缺失 → 空串
        assert p.profit == 12345        # profit 字符串 → 安全转 int
        assert p.ideal_price == 0
        assert p.sell_time == ""

    def test_parse_profit_not_numeric(self) -> None:
        """profit 非数字 → 0（_int_or_zero 兜底），不抛。"""
        products = parse_ov_response(
            {"data": {"spData": {"tech": {"profit": "abc"}}}}
        )
        assert products[0].profit == 0

    def test_parse_none_profit(self) -> None:
        products = parse_ov_response(
            {"data": {"spData": {"tech": {"profit": None}}}}
        )
        assert products[0].profit == 0


class TestParseAmmoPackageResponse:
    """解析 getAmmoPackageData 响应测试。"""

    def test_parse_valid_cn_only(self) -> None:
        data = {
            "code": 1,
            "data": {
                "cn": [
                    {
                        "packageName": "3级子弹自选包",
                        "itemName": "5.7x28mm L191",
                        "itemGrade": 3,
                        "itemCount": 200,
                        "singlePrice": 555,
                        "totalPrice": 111000,
                        "profit": 98790,
                    },
                    {
                        "packageName": "4级子弹自选包",
                        "itemName": "6.8x51mm FMJ",
                        "itemGrade": 4,
                        "itemCount": 150,
                        "singlePrice": 1934,
                        "totalPrice": 290100,
                        "profit": 258189,
                    },
                    {
                        "packageName": "5级子弹自选包",
                        "itemName": "5.8x42mm DVC12",
                        "itemGrade": 5,
                        "itemCount": 240,
                        "singlePrice": 4585,
                        "totalPrice": 1100400,
                        "profit": 979356,
                    },
                ],
                "en": [],
                "version": "202608061035",
            },
        }
        items = parse_ammo_package_response(data)
        # 只解析 cn 数据，3 条
        assert len(items) == 3
        # 按利润降序排列：5级 > 4级 > 3级
        assert items[0].item_grade == 5
        assert items[0].profit == 979356
        assert items[1].item_grade == 4
        assert items[1].profit == 258189
        assert items[2].item_grade == 3
        assert items[2].profit == 98790

    def test_parse_returns_all_grades(self) -> None:
        """所有等级条目均返回，不再过滤 2 级。"""
        data = {
            "code": 1,
            "data": {
                "cn": [
                    {
                        "packageName": "2级子弹自选包",
                        "itemName": "5.7x28mm SS197SR",
                        "itemGrade": 2,
                        "itemCount": 250,
                        "singlePrice": 103,
                        "totalPrice": 25750,
                        "profit": 22917,
                    },
                    {
                        "packageName": "3级子弹自选包",
                        "itemName": "5.7x28mm L191",
                        "itemGrade": 3,
                        "itemCount": 200,
                        "singlePrice": 555,
                        "totalPrice": 111000,
                        "profit": 98790,
                    },
                ],
                "en": [],
            },
        }
        items = parse_ammo_package_response(data)
        assert len(items) == 2
        # 按利润降序：3级 98790 > 2级 22917
        assert items[0].item_grade == 3
        assert items[1].item_grade == 2

    def test_parse_empty_data(self) -> None:
        assert parse_ammo_package_response(
            {"code": 1, "data": {"cn": [], "en": []}}
        ) == []

    def test_parse_missing_data_key(self) -> None:
        assert parse_ammo_package_response({}) == []

    def test_parse_malformed(self) -> None:
        with pytest.raises(KkrbError):
            parse_ammo_package_response("not a dict")

    def test_parse_multiple_same_grade(self) -> None:
        """同一等级多个条目，全部返回（由 UI 层取最高利润）。"""
        data = {
            "code": 1,
            "data": {
                "cn": [
                    {
                        "packageName": "3级子弹自选包",
                        "itemName": "5.7x28mm L191",
                        "itemGrade": 3,
                        "itemCount": 200,
                        "singlePrice": 555,
                        "totalPrice": 111000,
                        "profit": 98790,
                    },
                    {
                        "packageName": "3级子弹自选包",
                        "itemName": ".45 ACP FMJ",
                        "itemGrade": 3,
                        "itemCount": 180,
                        "singlePrice": 611,
                        "totalPrice": 109980,
                        "profit": 97882,
                    },
                ],
                "en": [],
            },
        }
        items = parse_ammo_package_response(data)
        assert len(items) == 2
        # 按利润降序
        assert items[0].item_name == "5.7x28mm L191"
        assert items[0].profit == 98790
        assert items[1].item_name == ".45 ACP FMJ"
        assert items[1].profit == 97882

    def test_parse_special_packages(self) -> None:
        """特殊包类型（通行证/物流）被正确解析。"""
        data = {
            "code": 1,
            "data": {
                "cn": [
                    {
                        "packageName": "通行证基础子弹自选包",
                        "itemName": ".45 ACP FMJ",
                        "itemGrade": 3,
                        "itemCount": 100,
                        "singlePrice": 611,
                        "totalPrice": 61100,
                        "profit": 54379,
                    },
                    {
                        "packageName": "通行证高级子弹自选包",
                        "itemName": "5.8x42mm DBP10",
                        "itemGrade": 4,
                        "itemCount": 50,
                        "singlePrice": 1813,
                        "totalPrice": 90650,
                        "profit": 80678,
                    },
                    {
                        "packageName": "进阶物流子弹自选包",
                        "itemName": ".50 AE JHP",
                        "itemGrade": 3,
                        "itemCount": 200,
                        "singlePrice": 644,
                        "totalPrice": 128800,
                        "profit": 114632,
                    },
                    {
                        "packageName": "特级物流子弹自选包",
                        "itemName": "6.8x51mm FMJ",
                        "itemGrade": 4,
                        "itemCount": 200,
                        "singlePrice": 1934,
                        "totalPrice": 386800,
                        "profit": 344252,
                    },
                ],
                "en": [],
            },
        }
        items = parse_ammo_package_response(data)
        assert len(items) == 4
        names = {i.package_name for i in items}
        assert "通行证基础子弹自选包" in names
        assert "通行证高级子弹自选包" in names
        assert "进阶物流子弹自选包" in names
        assert "特级物流子弹自选包" in names

    # ── 畸形矩阵扩展 ────────────────────────────────────

    def test_parse_data_not_dict(self) -> None:
        assert parse_ammo_package_response({"code": 1, "data": "oops"}) == []

    def test_parse_cn_not_list(self) -> None:
        """cn 不是 list → 跳过该区域（不抛）。"""
        assert parse_ammo_package_response(
            {"code": 1, "data": {"cn": "oops"}}
        ) == []

    def test_parse_entry_not_dict(self) -> None:
        """畸形条目跳过，合法条目保留。"""
        data = {
            "data": {
                "cn": [
                    "not a dict",
                    {
                        "packageName": "3级子弹自选包",
                        "itemName": "5.7x28mm L191",
                        "itemGrade": 3,
                        "itemCount": 200,
                        "singlePrice": 555,
                        "totalPrice": 111000,
                        "profit": 98790,
                    },
                ]
            }
        }
        items = parse_ammo_package_response(data)
        assert len(items) == 1
        assert items[0].item_name == "5.7x28mm L191"

    def test_parse_missing_fields_default(self) -> None:
        """缺字段用默认值兜底（str 字段空串、int 字段 0），不抛。"""
        items = parse_ammo_package_response(
            {"data": {"cn": [{"itemGrade": "4"}]}}
        )
        assert len(items) == 1
        item = items[0]
        assert item.package_name == ""
        assert item.item_name == ""
        assert item.item_grade == 4  # 字符串等级 → 安全转 int
        assert item.item_count == 0
        assert item.single_price == 0
        assert item.total_price == 0
        assert item.profit == 0

    def test_parse_profit_not_numeric(self) -> None:
        items = parse_ammo_package_response(
            {"data": {"cn": [{"profit": "abc"}]}}
        )
        assert items[0].profit == 0


class TestParseBonusDoorResponse:
    """解析 getBonusDoorData 响应测试（BD-01，密码门数据层）。

    响应格式（§5.1 实测）：{code:1, data:{<key>:{password, updated, overridden}}}。
    输出按 BONUS_DOOR_NAMES 定义顺序（稳定顺序）；映射外键跳过——
    kkrb 新增地图需扩展 BONUS_DOOR_NAMES 映射（docstring 契约）。
    """

    def test_parse_valid_all_maps(self) -> None:
        """7 张图全量：按映射定义顺序输出，地图名/密码/更新时间完整。"""
        from kkrb_models import BONUS_DOOR_NAMES

        data = {
            "code": 1,
            "data": {
                # 故意乱序传入：输出必须按 BONUS_DOOR_NAMES 定义顺序
                "cxjy": {"password": "888888", "updated": "20260813000000"},
                "db": {"password": "870140", "updated": "20260813000000"},
                "az3r6": {"password": "000000", "updated": "20260813000000"},
                "bks": {"password": "654321", "updated": "20260813000000"},
                "htjd": {"password": "135790", "updated": "20260813000000"},
                "cgxg": {"password": "123456", "updated": "20260813000000"},
                "az3": {"password": "246810", "updated": "20260813000000"},
            },
        }
        items = parse_bonus_door_response(data)
        assert len(items) == 7
        # 稳定顺序 = BONUS_DOOR_NAMES 定义顺序
        assert [i.key for i in items] == list(BONUS_DOOR_NAMES)
        # 地图名来自映射单源
        for item in items:
            assert item.name == BONUS_DOOR_NAMES[item.key]
        assert items[0].name == "零号大坝"
        assert items[0].password == "870140"
        assert items[0].updated == "20260813000000"

    def test_parse_missing_data_key(self) -> None:
        assert parse_bonus_door_response({}) == []

    def test_parse_data_not_dict(self) -> None:
        """data 字段不是 dict → 空列表（不回退、不抛）。"""
        assert parse_bonus_door_response({"code": 1, "data": "oops"}) == []

    # ── BD-债1：业务错误码检查 ──────────────────────────────

    def test_parse_business_error_code_raises_with_msg(self) -> None:
        """code 存在且 != 1 → KkrbError，消息携带响应 msg（业务失败不吞为「暂无数据」）。"""
        with pytest.raises(KkrbError) as exc_info:
            parse_bonus_door_response({"code": 0, "msg": "服务器维护"})
        assert "密码门业务失败" in str(exc_info.value)
        assert "服务器维护" in str(exc_info.value)

    def test_parse_business_error_code_without_msg(self) -> None:
        """code != 1 且无 msg → KkrbError 消息不悬挂空冒号。"""
        with pytest.raises(KkrbError) as exc_info:
            parse_bonus_door_response({"code": 0})
        assert str(exc_info.value) == "密码门业务失败"

    def test_parse_code_one_is_normal(self) -> None:
        """code == 1 → 正常解析（与响应契约一致）。"""
        items = parse_bonus_door_response(
            {
                "code": 1,
                "data": {"db": {"password": "870140", "updated": "20260813000000"}},
            }
        )
        assert [i.key for i in items] == ["db"]
        assert items[0].password == "870140"

    def test_parse_missing_code_with_data_is_normal(self) -> None:
        """code 缺失但有 data → 正常解析（容错，不破坏既有无 code 用例）。"""
        items = parse_bonus_door_response(
            {"data": {"db": {"password": "870140", "updated": ""}}}
        )
        assert [i.key for i in items] == ["db"]

    def test_parse_malformed_top_level(self) -> None:
        with pytest.raises(KkrbError):
            parse_bonus_door_response("not a dict")

    def test_parse_entry_not_dict(self) -> None:
        """畸形条目跳过，合法条目保留。"""
        data = {
            "data": {
                "db": "not a dict",
                "cgxg": {"password": "123456", "updated": "20260813000000"},
            }
        }
        items = parse_bonus_door_response(data)
        assert len(items) == 1
        assert items[0].key == "cgxg"

    def test_parse_unknown_key_skipped(self) -> None:
        """映射外键跳过（kkrb 新增图需扩展 BONUS_DOOR_NAMES）。"""
        data = {
            "data": {
                "db": {"password": "870140", "updated": "20260813000000"},
                "new_map": {"password": "111111", "updated": "20260813000000"},
            }
        }
        items = parse_bonus_door_response(data)
        assert [i.key for i in items] == ["db"]

    def test_parse_unknown_key_logs_warning(self, caplog) -> None:
        """BD-债2：映射外键 logger.warning 列出键名（可观测性），解析结果不含它。"""
        import logging

        data = {
            "data": {
                "db": {"password": "870140", "updated": "20260813000000"},
                "new_map": {"password": "111111", "updated": "20260813000000"},
            }
        }
        with caplog.at_level(logging.WARNING):
            items = parse_bonus_door_response(data)

        assert [i.key for i in items] == ["db"]
        warnings = [r.message for r in caplog.records if r.name == "kkrb_parsing"]
        assert warnings, "映射外键必须留下 warning 日志"
        assert any("new_map" in w for w in warnings)
        assert any("BONUS_DOOR_NAMES" in w for w in warnings)

    def test_parse_unknown_key_non_str_logs_warning(self, caplog) -> None:
        """Falsify：畸形非 str 键（仅手造可达）不崩，warning 仍列出键名。"""
        import logging

        data = {
            "data": {
                "db": {"password": "870140", "updated": "20260813000000"},
                1: {"password": "111111", "updated": "20260813000000"},
            }
        }
        with caplog.at_level(logging.WARNING):
            items = parse_bonus_door_response(data)

        assert [i.key for i in items] == ["db"]
        assert any("1" in r.message for r in caplog.records if r.name == "kkrb_parsing")

    def test_parse_missing_fields_default(self) -> None:
        """password/updated 缺省 → 空串兜底，不抛。"""
        items = parse_bonus_door_response({"data": {"db": {}}})
        assert len(items) == 1
        assert items[0].password == ""
        assert items[0].updated == ""

    def test_parse_none_fields_default(self) -> None:
        """password/updated 为 None → 空串兜底（str() 不产生 'None'）。"""
        items = parse_bonus_door_response(
            {"data": {"db": {"password": None, "updated": None}}}
        )
        assert items[0].password == ""
        assert items[0].updated == ""

    def test_parse_az3r6_included_by_parsing(self) -> None:
        """解析层不剔除 az3r6——排除是 client 层单点过滤（fetch_bonus_door_data）。"""
        items = parse_bonus_door_response(
            {"data": {"az3r6": {"password": "000000", "updated": ""}}}
        )
        assert [i.key for i in items] == ["az3r6"]
