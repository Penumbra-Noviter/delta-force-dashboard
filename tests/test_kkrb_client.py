"""kkrb_client 单元测试。"""

from __future__ import annotations

import pytest

from kkrb_client import (
    CraftingProduct,
    GearItem,
    GearScheme,
    KkrbClient,
    KkrbError,
    _int_or_zero,
)


class TestDataModels:
    def test_crafting_product_frozen(self) -> None:
        p = CraftingProduct("技术中心", "复合弓", 3904, 132000, "6小时")
        assert p.station == "技术中心"
        assert p.profit == 3904

    def test_gear_item_frozen(self) -> None:
        item = GearItem("QSZ92G", 4800, 4694, "市场", "全新")
        assert item.name == "QSZ92G"
        assert item.cost == 4800
        assert item.wear == "全新"

    def test_gear_scheme(self) -> None:
        items = [GearItem("A", 100, 200, "市场")]
        s = GearScheme("方案 #1", 1000, 1200, items)
        assert s.title == "方案 #1"
        assert s.total_cost == 1000
        assert len(s.items) == 1
        # wear defaults to ""
        assert s.items[0].wear == ""


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
                        "productionTime": 6,
                        "itemForge": [
                            {"requiredLevel": 1, "productionTime": 9, "hourlyProfit": 2762},
                            {"requiredLevel": 2, "productionTime": 6, "hourlyProfit": 4143},
                        ],
                        "totalMaterialLists": [
                            {"itemName": "枪械零件", "totalPrice": 18309},
                            {"itemName": "高精数显卡尺", "totalPrice": 31536},
                        ],
                    },
                    "workbench": {
                        "placeName": "工作台",
                        "itemName": "4.6x30mm AP SX",
                        "productionTime": 8,
                        "itemForge": [
                            {"requiredLevel": 3, "productionTime": 8, "hourlyProfit": 36804},
                        ],
                        "totalMaterialLists": [
                            {"itemName": "高级燃料", "totalPrice": 200114},
                        ],
                    },
                }
            },
        }
        products = KkrbClient._parse_ov_response(data)
        assert len(products) == 2
        # 按利润降序排列：工作台 36804 > 技术中心 4143
        assert products[0].station == "工作台"
        assert products[0].profit == 36804
        assert products[0].ideal_price == 200114
        assert products[0].sell_time == "8小时"
        assert products[1].station == "技术中心"
        assert products[1].profit == 4143
        assert products[1].ideal_price == 49845  # 18309 + 31536

    def test_parse_empty_sp_data(self) -> None:
        assert KkrbClient._parse_ov_response({"code": 1, "data": {"spData": {}}}) == []

    def test_parse_missing_data_key(self) -> None:
        assert KkrbClient._parse_ov_response({}) == []

    def test_parse_malformed(self) -> None:
        with pytest.raises(KkrbError):
            KkrbClient._parse_ov_response("not a dict")


class TestParseCPVResponse:
    """解析 getCPVData 响应测试（实际 API 格式）。"""

    def test_parse_valid(self) -> None:
        data = {
            "code": 1,
            "data": [
                {
                    "targetValue": 112500,
                    "totalHafCost": 104854,
                    "currentValue": 112564,
                    "schemeType": "market",
                    "schemeItems": [
                        {
                            "objectName": "M870霰弹枪",
                            "costHafCoin": 5000,
                            "currentValue": 4733,
                            "from": "市场",
                        },
                    ],
                },
                {
                    "targetValue": 112500,
                    "totalHafCost": 105060,
                    "currentValue": 112796,
                    "schemeType": "market",
                    "schemeItems": [
                        {
                            "objectName": "M1911",
                            "costHafCoin": 17030,
                            "currentValue": 16915,
                            "from": "市场",
                        },
                    ],
                },
            ],
        }
        result = KkrbClient._parse_cpv_response(data)
        assert 112500 in result
        assert len(result[112500]) == 2

        # 方案按出现顺序编号
        scheme0 = result[112500][0]
        assert scheme0.title == "方案 #1"
        assert scheme0.total_cost == 104854
        assert scheme0.final_bv == 112564
        assert len(scheme0.items) == 1
        assert scheme0.items[0].name == "M870霰弹枪"
        assert scheme0.items[0].cost == 5000
        assert scheme0.items[0].battle_value == 4733
        assert scheme0.items[0].source == "市场"
        assert scheme0.items[0].wear == ""  # API 不提供磨损度

        scheme1 = result[112500][1]
        assert scheme1.title == "方案 #2"
        assert scheme1.total_cost == 105060
        assert scheme1.final_bv == 112796

    def test_parse_filter_tier(self) -> None:
        data = {
            "code": 1,
            "data": [
                {"targetValue": 112500, "totalHafCost": 0, "currentValue": 0, "schemeItems": []},
                {"targetValue": 187500, "totalHafCost": 0, "currentValue": 0, "schemeItems": []},
            ],
        }
        result = KkrbClient._parse_cpv_response(data, filter_tier=187500)
        assert 112500 not in result
        assert 187500 in result

    def test_parse_empty(self) -> None:
        assert KkrbClient._parse_cpv_response({"code": 1, "data": []}) == {}

    def test_parse_malformed(self) -> None:
        with pytest.raises(KkrbError):
            KkrbClient._parse_cpv_response("not a dict")