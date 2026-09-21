from scrapy import Field, Item

from scrapy_jev import QualityGatePipeline


class Product(Item):
    name = Field()
    price = Field()
    sku = Field()
    category = Field()


class Listing(Item):
    product_urls = Field()
    next_page_url = Field()


class FixedJev:
    """Stand-in for JevClient returning one canned dict per call."""

    def __init__(self, scores):
        self.scores = scores
        self.calls = 0

    def score_item(self, item, fields):
        self.calls += 1
        return {field: self.scores.get(field) for field in fields}


def make_gate(client, fields=("name", "price"), sample_size=2,
              pass_rate_threshold=0.7, field_threshold=0.5):
    stops = []
    gate = QualityGatePipeline(
        client=client,
        fields=list(fields),
        sample_size=sample_size,
        pass_rate_threshold=pass_rate_threshold,
        field_threshold=field_threshold,
        stop_reason="quality check",
        stop=stops.append,
    )
    return gate, stops


def test_skips_items_that_do_not_declare_fields():
    client = FixedJev({})
    gate, stops = make_gate(client, sample_size=1, pass_rate_threshold=0.9)
    gate.process_item(Listing(product_urls=["https://example.com/x"]))
    assert client.calls == 0
    assert stops == []


def test_passes_when_all_fields_clear_threshold():
    client = FixedJev({"name": 0.9, "price": 0.9})
    gate, stops = make_gate(client, sample_size=2, pass_rate_threshold=0.5)
    gate.process_item(Product(name="A", price="1.00"))
    gate.process_item(Product(name="B", price="2.00"))
    assert stops == []


def test_stops_when_pass_rate_below_threshold():
    from scrapy_jev.pipeline import QualityGatePipeline as Q

    class Seq:
        def __init__(self):
            self.i = 0

        def score_item(self, item, fields):
            score = 1.0 if self.i == 0 else 0.0
            self.i += 1
            return {f: score for f in fields}

    client = Seq()
    stops = []
    gate = Q(client=client, fields=["name", "price"], sample_size=2,
             pass_rate_threshold=0.9, field_threshold=0.5,
             stop_reason="quality check", stop=stops.append)
    gate.process_item(Product(name="A", price="1.00"))
    gate.process_item(Product(name="B", price="2.00"))
    assert len(stops) == 1
    assert "1/2 items passed" in stops[0]


def test_missing_field_is_a_failure():
    client = FixedJev({"name": 0.9, "price": None})
    gate, stops = make_gate(client, sample_size=1, pass_rate_threshold=0.9)
    gate.process_item(Product(name="A"))
    assert len(stops) == 1


def test_single_bad_field_fails_item():
    client = FixedJev({"name": 0.9, "price": 0.1})
    gate, stops = make_gate(client, sample_size=1, pass_rate_threshold=0.9)
    gate.process_item(Product(name="A", price="x"))
    assert len(stops) == 1


def test_accepts_plain_dict_items():
    # A plain dict (non-scrapy Item) should be judged through itemadapter.
    client = FixedJev({"name": 0.9, "price": 0.9})
    gate, stops = make_gate(client, sample_size=1, pass_rate_threshold=0.9)
    gate.process_item({"name": "A", "price": "1.00"})
    assert client.calls == 1
    assert stops == []