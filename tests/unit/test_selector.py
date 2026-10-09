from kompiler.planner.selector import select


def test_selector_fields_and_wildcards():
    data={"records":[{"referent":"a"},{"referent":"b"}]}
    assert select(data,"$.records[*].referent")==["a","b"]
    assert select(data,"$.records[0].referent")==["a"]
