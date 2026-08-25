"""Deterministic in-memory catalog used until real provider adapters arrive."""

from __future__ import annotations

from terralab3d.domain.refinement.installations import RefinementProduct


class StaticRefinementProductCatalog:
    def __init__(self, products: tuple[RefinementProduct, ...] = ()) -> None:
        self._products = products
        self._by_id = {product.product_id: product for product in products}
        if len(self._by_id) != len(products):
            raise ValueError("Refinement product ids must be unique")

    def list_products(self, category_key: str) -> tuple[RefinementProduct, ...]:
        return tuple(
            product
            for product in self._products
            if any(
                node == category_key or node.startswith(f"{category_key}.")
                for node in product.tlst_nodes
            )
        )

    def list_all_products(self) -> tuple[RefinementProduct, ...]:
        return self._products

    def get_product(self, product_id: str) -> RefinementProduct | None:
        return self._by_id.get(product_id)
