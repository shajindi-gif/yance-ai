"""Pagination discovery tests.

These exist because a wrong page-URL template is invisible: the site answers
``200`` for ``index_2.html`` on a column that serves ``index_1.htm``, the list
parser finds zero candidates, and backfill used to smooth that over as "the
archive ended". Every assertion here pins down one way a real government column
expresses its pagination.
"""

from __future__ import annotations

import pytest

from app.services.policy_collection.extract import (
    detect_page_count,
    discover_page_urls,
    paginate_urls,
    pagination_urls,
)

MOF_STYLE = """
<div class="page">
  <script>createPageHTML(23, 0, "index", "htm")</script>
</div>
"""

HREF_STYLE = """
<ul class="pagination">
  <li><a href="index.html">1</a></li>
  <li><a href="index_1.html">2</a></li>
  <li><a href="index_2.html">3</a></li>
  <li><a href="index_3.html">4</a></li>
  <li><a href="https://other.gov.cn/index_9.html">next site</a></li>
</ul>
"""


def test_create_page_html_template_numbers_files_from_screen_minus_one():
    """``createPageHTML(23, 0, "index", "htm")`` -> index_1.htm is screen 2."""
    urls = pagination_urls(
        MOF_STYLE, "https://www.mof.gov.cn/gkml/bulinggonggao/tongzhitonggao/", cap=3
    )
    base = "https://www.mof.gov.cn/gkml/bulinggonggao/tongzhitonggao/"
    assert urls == [f"{base}index_1.htm", f"{base}index_2.htm", f"{base}index_3.htm"]


def test_create_page_html_respects_declared_page_count():
    urls = pagination_urls(MOF_STYLE, "https://a.gov.cn/col/", cap=50)
    assert len(urls) == 22, "23 screens means 22 additional page files"


def test_published_hrefs_win_over_constructed_template():
    urls = pagination_urls(HREF_STYLE, "https://a.gov.cn/col/index.html", cap=3)
    assert urls == [
        "https://a.gov.cn/col/index_1.html",
        "https://a.gov.cn/col/index_2.html",
        "https://a.gov.cn/col/index_3.html",
    ], "cross-domain links must be dropped"


def test_foreign_domain_pagination_links_are_ignored():
    urls = discover_page_urls(HREF_STYLE, "https://a.gov.cn/col/index.html", cap=10)
    assert all("other.gov.cn" not in url for url in urls)


def test_unknown_layout_falls_back_to_html_guess():
    urls = pagination_urls("<html><body>no pager</body></html>", "https://a.gov.cn/col/", cap=2)
    assert urls == ["https://a.gov.cn/col/index_2.html", "https://a.gov.cn/col/index_3.html"]


def test_page_parameter_style_still_supported():
    urls = pagination_urls("<html/>", "https://a.gov.cn/list", cap=2, page_parameter="page")
    assert urls == ["https://a.gov.cn/list?page=2", "https://a.gov.cn/list?page=3"]


def test_detect_page_count_reads_create_page_html():
    assert detect_page_count(MOF_STYLE, cap=100) == 23
    assert detect_page_count(MOF_STYLE, cap=5) == 5, "cap must clamp runaway declarations"


def test_paginate_urls_accepts_suffix_and_first_number():
    urls = paginate_urls("https://a.gov.cn/col/", 4, suffix="htm", first_page_number=2)
    assert urls == [
        "https://a.gov.cn/col/index_2.htm",
        "https://a.gov.cn/col/index_3.htm",
        "https://a.gov.cn/col/index_4.htm",
    ]


@pytest.mark.parametrize("cap", [0, 1])
def test_cap_bounds_number_of_returned_pages(cap):
    assert len(pagination_urls(MOF_STYLE, "https://a.gov.cn/col/", cap=cap)) <= cap
