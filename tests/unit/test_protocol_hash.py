from kompiler.protocol.canonical import sha256_hex


def test_hash_ignores_object_key_order():
    assert sha256_hex({"a":1,"b":2})==sha256_hex({"b":2,"a":1})
