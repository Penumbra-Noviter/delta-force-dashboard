"""kkrb_client 单元测试。"""

from __future__ import annotations

import pytest

from kkrb_client import (
    AmmoPackageItem,
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


class TestAmmoPackageItem:
    """AmmoPackageItem 数据模型测试。"""

    def test_ammo_package_item_frozen(self) -> None:
        item = AmmoPackageItem(
            package_name="3级子弹自选包",
            item_name="5.7x28mm L191",
            item_grade=3,
            item_count=200,
            single_price=555,
            total_price=111000,
            profit=98790,
        )
        assert item.package_name == "3级子弹自选包"
        assert item.item_name == "5.7x28mm L191"
        assert item.item_grade == 3
        assert item.item_count == 200
        assert item.single_price == 555
        assert item.total_price == 111000
        assert item.profit == 98790


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
        items = KkrbClient._parse_ammo_package_response(data)
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
        items = KkrbClient._parse_ammo_package_response(data)
        assert len(items) == 2
        # 按利润降序：3级 98790 > 2级 22917
        assert items[0].item_grade == 3
        assert items[1].item_grade == 2

    def test_parse_empty_data(self) -> None:
        assert KkrbClient._parse_ammo_package_response(
            {"code": 1, "data": {"cn": [], "en": []}}
        ) == []

    def test_parse_missing_data_key(self) -> None:
        assert KkrbClient._parse_ammo_package_response({}) == []

    def test_parse_malformed(self) -> None:
        with pytest.raises(KkrbError):
            KkrbClient._parse_ammo_package_response("not a dict")

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
        items = KkrbClient._parse_ammo_package_response(data)
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
        items = KkrbClient._parse_ammo_package_response(data)
        assert len(items) == 4
        names = {i.package_name for i in items}
        assert "通行证基础子弹自选包" in names
        assert "通行证高级子弹自选包" in names
        assert "进阶物流子弹自选包" in names
        assert "特级物流子弹自选包" in names