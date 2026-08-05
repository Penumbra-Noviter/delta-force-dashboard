"""kkrb_client 单元测试。"""

from __future__ import annotations

import pytest

from kkrb_client import (
    CraftingProduct,
    KkrbClient,
    KkrbError,
    _int_or_zero,
)


class TestDataModels:
    def test_crafting_product_frozen(self) -> None:
        p = CraftingProduct("技术中心", "复合弓", 24669, 39077, "晚上8点")
        assert p.station == "技术中心"
        assert p.profit == 24669


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
        products = KkrbClient._parse_ov_response(data)
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
        assert KkrbClient._parse_ov_response({"code": 1, "data": {"spData": {}}}) == []

    def test_parse_missing_data_key(self) -> None:
        assert KkrbClient._parse_ov_response({}) == []

    def test_parse_malformed(self) -> None:
        with pytest.raises(KkrbError):
            KkrbClient._parse_ov_response("not a dict")