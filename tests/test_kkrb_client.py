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
        p = CraftingProduct("技术中心", "复合弓", 3904, 132000, "6小时")
        assert p.station == "技术中心"
        assert p.profit == 3904


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