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
        p = CraftingProduct("技术中心", "复合弓", 3904, 132000, "晚上9点")
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


class TestParseOVResponse:
    def test_parse_valid(self) -> None:
        data = {
            "data": {
                "stations": [
                    {
                        "stationName": "技术中心",
                        "productName": "复合弓",
                        "profit": 3904,
                        "idealPrice": 132000,
                        "sellTime": "晚上9点",
                    },
                    {
                        "stationName": "工作台",
                        "productName": "5.45x39mm BS",
                        "profit": 35319,
                        "idealPrice": 4963,
                        "sellTime": "凌晨1点",
                    },
                ]
            }
        }
        products = KkrbClient._parse_ov_response(data)
        assert len(products) == 2
        assert products[0].profit >= products[1].profit

    def test_parse_empty(self) -> None:
        assert KkrbClient._parse_ov_response({}) == []
        assert KkrbClient._parse_ov_response({"data": {"stations": []}}) == []

    def test_parse_malformed(self) -> None:
        with pytest.raises(KkrbError):
            KkrbClient._parse_ov_response("not a dict")


class TestParseCPVResponse:
    def test_parse_valid(self) -> None:
        data = {
            "data": {
                "tiers": [
                    {
                        "tierValue": 112500,
                        "schemes": [
                            {
                                "title": "方案 #1",
                                "totalCost": 101965,
                                "finalBv": 112637,
                                "items": [
                                    {
                                        "name": "QSZ92G",
                                        "cost": 4800,
                                        "battleValue": 4694,
                                        "source": "市场",
                                        "wear": "全新",
                                    }
                                ],
                            }
                        ],
                    }
                ]
            }
        }
        result = KkrbClient._parse_cpv_response(data)
        assert 112500 in result
        assert len(result[112500]) == 1
        scheme = result[112500][0]
        assert scheme.title == "方案 #1"
        assert len(scheme.items) == 1
        assert scheme.items[0].name == "QSZ92G"
        assert scheme.items[0].wear == "全新"

    def test_parse_wear_fallback_durability(self) -> None:
        """wear 字段缺失时尝试 durability 字段。"""
        data = {
            "data": {
                "tiers": [
                    {
                        "tierValue": 112500,
                        "schemes": [
                            {
                                "title": "方案 #1",
                                "totalCost": 101965,
                                "finalBv": 112637,
                                "items": [
                                    {
                                        "name": "AKM",
                                        "cost": 5000,
                                        "battleValue": 4800,
                                        "source": "市场",
                                        "durability": "破损",
                                    }
                                ],
                            }
                        ],
                    }
                ]
            }
        }
        result = KkrbClient._parse_cpv_response(data)
        assert result[112500][0].items[0].wear == "破损"

    def test_parse_filter_tier(self) -> None:
        data = {
            "data": {
                "tiers": [
                    {"tierValue": 112500, "schemes": []},
                    {"tierValue": 187500, "schemes": []},
                ]
            }
        }
        result = KkrbClient._parse_cpv_response(data, filter_tier=187500)
        assert 112500 not in result
        assert 187500 in result

    def test_parse_empty(self) -> None:
        assert KkrbClient._parse_cpv_response({"data": {"tiers": []}}) == {}

    def test_parse_malformed(self) -> None:
        with pytest.raises(KkrbError):
            KkrbClient._parse_cpv_response("not a dict")