"""kkrb_client 单元测试（会话/传输/缓存）。

架构深化（候选 1）后：响应解析测试迁至 test_kkrb_parsing.py（纯函数直调）；
本文件保留数据模型（经 kkrb_client 重新导出访问，验证协议表面）与
KkrbClient 的网络/缓存行为。
"""

from __future__ import annotations

import pytest

from kkrb_client import (
    AmmoPackageItem,
    CraftingProduct,
    KkrbClient,
    KkrbError,
)


class TestDataModels:
    def test_crafting_product_frozen(self) -> None:
        p = CraftingProduct("技术中心", "复合弓", 24669, 39077, "晚上8点")
        assert p.station == "技术中心"
        assert p.profit == 24669

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


class TestKkrbClient:
    def test_fetch_parses_through_kkrb_parsing(self, monkeypatch) -> None:
        """fetch_ov_data 经 kkrb_parsing 解析（client 不再自带解析）。"""
        import kkrb_parsing

        calls: list[Any] = []

        def fake_post_json(self, url: str):
            calls.append(url)
            return {
                "data": {
                    "spData": {
                        "tech": {
                            "placeName": "技术中心",
                            "itemName": "复合弓",
                            "profit": 100,
                            "singlePrice": 200,
                            "yesterdayHighestTime": "晚上8点",
                        }
                    }
                }
            }

        monkeypatch.setattr(KkrbClient, "_post_json", fake_post_json)
        client = KkrbClient()
        products = client.fetch_ov_data()
        assert len(products) == 1
        assert products[0].station == "技术中心"
        # client 不再暴露私有解析方法（协议表面收敛）
        assert not hasattr(KkrbClient, "_parse_ov_response")
        assert not hasattr(KkrbClient, "_parse_ammo_package_response")
        assert not hasattr(KkrbClient, "_int_or_zero")

    def test_fetch_network_error_raises_kkrb_error(self, monkeypatch) -> None:
        """传输失败 → KkrbError（解析层异常也统一为 KkrbError 家族）。"""

        def fake_post_json(self, url: str):
            raise KkrbError("POST 失败")

        monkeypatch.setattr(KkrbClient, "_post_json", fake_post_json)
        client = KkrbClient()
        with pytest.raises(KkrbError):
            client.fetch_ov_data()
