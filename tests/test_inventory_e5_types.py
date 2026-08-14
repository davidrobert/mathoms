from dev.inventory_e5_types import _blocos_opacos


def test_gap_inventory_walks_nested_objects_and_arrays() -> None:
    schema = {
        "type": "object",
        "properties": {
            "nested": {
                "type": "object",
                "properties": {
                    "missing_items": {"type": "array"},
                    "missing_shape": {"type": "object"},
                },
            }
        },
    }

    objects, arrays = _blocos_opacos(schema)

    assert objects == {"nested.missing_shape"}
    assert arrays == {"nested.missing_items"}
