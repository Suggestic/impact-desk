"""Unit tests for the median-first metric engine.

The "9 zeros + 1 viral" case (§3/§7 of the brief) is the product's reason to
exist and is tested explicitly first.
"""

from app.metrics import (
    ComputedMetrics,
    EngagementFormula,
    OutlierConfig,
    PostMetricsInput,
    compute_metrics,
)


def posts(**by_field) -> list[PostMetricsInput]:
    """Build parallel-list posts, e.g. posts(views=[1,2], likes=[3,4])."""
    length = max(len(v) for v in by_field.values())
    return [
        PostMetricsInput(**{k: by_field[k][i] for k in by_field})
        for i in range(length)
    ]


# --------------------------------------------------------------------------- #
# The headline case: averages lie, medians tell the truth.
# --------------------------------------------------------------------------- #
def test_nine_zeros_and_one_viral_post():
    p = posts(views=[0] * 9 + [1_000_000])
    m = compute_metrics(p)

    # The mean makes this account look like a major player...
    assert m.mean_views == 100_000
    # ...but the median correctly reports it as essentially zero reach.
    assert m.median_views == 0
    assert m.post_count == 10

    # And the flags surface *why*: one viral post carrying a dead account.
    assert m.viral_post_count == 1
    assert m.is_outlier_driven is True


def test_consistent_influencer_is_not_flagged():
    # A "real" influencer: steady views, median ~ mean.
    p = posts(views=[9_000, 11_000, 10_000, 10_500, 9_500])
    m = compute_metrics(p)

    assert m.median_views == 10_000
    assert m.mean_views == 10_000
    assert m.viral_post_count == 0
    assert m.is_outlier_driven is False
    assert m.views_mean_to_median_ratio == 1.0


def test_median_beats_mean_for_ranking_two_accounts():
    # Real account with lower mean but higher, honest median should outrank
    # a spiky account whose mean is inflated by one viral hit.
    real = compute_metrics(posts(views=[8_000, 9_000, 10_000, 11_000, 12_000]))
    spiky = compute_metrics(posts(views=[0, 0, 0, 0, 500_000]))

    assert spiky.mean_views > real.mean_views  # mean would rank spiky first
    assert real.median_views > spiky.median_views  # median ranks real first
    assert spiky.is_outlier_driven is True
    assert real.is_outlier_driven is False


# --------------------------------------------------------------------------- #
# Engagement + engagement rate
# --------------------------------------------------------------------------- #
def test_engagement_default_formula_sums_signals():
    p = posts(likes=[10], comments=[5], shares=[2])
    m = compute_metrics(p)
    assert m.median_engagement == 17  # 10 + 5 + 2
    assert m.mean_engagement == 17


def test_engagement_formula_is_configurable():
    p = posts(likes=[10], comments=[5], shares=[2])
    formula = EngagementFormula(likes_weight=1, comments_weight=2, shares_weight=3)
    m = compute_metrics(p, engagement_formula=formula)
    assert m.median_engagement == 10 + 2 * 5 + 3 * 2  # 26


def test_engagement_rate_is_median_of_per_post_ratios():
    # rates: 100/1000=0.1, 300/1000=0.3, 200/1000=0.2 -> median 0.2
    p = posts(views=[1000, 1000, 1000], likes=[100, 300, 200])
    m = compute_metrics(p, engagement_formula=EngagementFormula(1, 0, 0))
    assert m.median_engagement_rate == 0.2


def test_engagement_rate_guards_divide_by_zero():
    # Zero-view and missing-view posts must not blow up or skew the rate.
    p = [
        PostMetricsInput(views=0, likes=50),
        PostMetricsInput(views=None, likes=50),
        PostMetricsInput(views=1000, likes=100),  # only this yields a rate: 0.1
    ]
    m = compute_metrics(p, engagement_formula=EngagementFormula(1, 0, 0))
    assert m.median_engagement_rate == 0.1


# --------------------------------------------------------------------------- #
# Edge cases from §4: <20 posts, missing metrics, empties
# --------------------------------------------------------------------------- #
def test_no_posts_returns_empty_metrics():
    m = compute_metrics([])
    assert m == ComputedMetrics(post_count=0)
    assert m.median_views is None
    assert m.is_outlier_driven is False


def test_fewer_than_twenty_posts_uses_what_is_available():
    p = posts(views=[100, 200, 300])
    m = compute_metrics(p)
    assert m.post_count == 3
    assert m.median_views == 200


def test_caps_at_last_twenty_posts():
    # 25 posts newest-first; the 5 oldest (all zero) must be ignored.
    recent = [500] * 20
    older = [0] * 5
    p = posts(views=recent + older)
    m = compute_metrics(p, max_posts=20)
    assert m.post_count == 20
    assert m.median_views == 500


def test_missing_metric_is_excluded_not_zeroed():
    # A None view is dropped; it must not pull the median toward zero.
    p = [
        PostMetricsInput(views=1000),
        PostMetricsInput(views=None),
        PostMetricsInput(views=1000),
    ]
    m = compute_metrics(p)
    assert m.median_views == 1000  # not 1000/… skewed by a phantom 0


def test_viral_multiple_is_configurable():
    p = posts(views=[10, 10, 10, 10, 40])  # median 10; 40 == 4x
    strict = compute_metrics(p, outlier_config=OutlierConfig(viral_multiple=3.0))
    loose = compute_metrics(p, outlier_config=OutlierConfig(viral_multiple=5.0))
    assert strict.viral_post_count == 1
    assert loose.viral_post_count == 0


def test_config_snapshots_serialize():
    assert EngagementFormula().as_dict()["likes_weight"] == 1.0
    assert "viral_multiple" in OutlierConfig().as_dict()
