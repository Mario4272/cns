from datetime import datetime
from dateutil.tz import UTC

from cns_py.demo.query import tls_supported_as_of


def test_tls_supersession_asof_split():
    pre = datetime(2024, 12, 31, 12, 0, 0, tzinfo=UTC)
    post = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

    pre_label = tls_supported_as_of("FrameworkX", pre)
    post_label = tls_supported_as_of("FrameworkX", post)

    assert pre_label == "TLS1.2"
    assert post_label == "TLS1.3"
