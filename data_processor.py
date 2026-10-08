import math
import re
from datetime import datetime, timezone
from io import BytesIO

import pandas as pd



def commits_to_dataframe(commits):
    rows = []

    for commit in commits:

        commit_data = commit.get(
            "commit",
            {}
        )

        author_data = (
            commit_data.get("author")
            or {}
        )

        rows.append(
            {
                "sha": commit.get("sha"),
                "author": author_data.get(
                    "name",
                    "Unknown"
                ),
                "date": author_data.get("date"),
                "message": commit_data.get(
                    "message",
                    ""
                ).split("\n")[0],
            }
        )

    df = pd.DataFrame(rows)

    if not df.empty:

        df["date"] = pd.to_datetime(
            df["date"]
        )

        df["day"] = df["date"].dt.date

    return df



def issues_to_dataframe(issues):
    rows = []

    for issue in issues:

        if "pull_request" in issue:
            continue

        user_data = (
            issue.get("user")
            or {}
        )

        rows.append(
            {
                "number": issue.get("number"),
                "title": issue.get("title"),
                "state": issue.get("state"),
                "author": user_data.get(
                    "login",
                    "Unknown"
                ),
                "created_at": issue.get(
                    "created_at"
                ),
                "closed_at": issue.get(
                    "closed_at"
                ),
                "comments": issue.get(
                    "comments",
                    0
                ),
            }
        )

    df = pd.DataFrame(rows)

    if not df.empty:

        df["created_at"] = pd.to_datetime(
            df["created_at"]
        )

        df["closed_at"] = pd.to_datetime(
            df["closed_at"]
        )

    return df



def pull_requests_to_dataframe(
    pull_requests
):
    rows = []

    for pull_request in pull_requests:

        user_data = (
            pull_request.get("user")
            or {}
        )

        rows.append(
            {
                "number": pull_request.get(
                    "number"
                ),
                "title": pull_request.get(
                    "title"
                ),
                "state": pull_request.get(
                    "state"
                ),
                "author": user_data.get(
                    "login",
                    "Unknown"
                ),
                "created_at": pull_request.get(
                    "created_at"
                ),
                "closed_at": pull_request.get(
                    "closed_at"
                ),
                "merged_at": pull_request.get(
                    "merged_at"
                ),
                "comments": pull_request.get(
                    "comments",
                    0
                ),
            }
        )

    df = pd.DataFrame(rows)

    if not df.empty:

        df["created_at"] = pd.to_datetime(
            df["created_at"]
        )

        df["closed_at"] = pd.to_datetime(
            df["closed_at"]
        )

        df["merged_at"] = pd.to_datetime(
            df["merged_at"]
        )

    return df



def languages_to_dataframe(languages):
    rows = []

    for language, bytes_count in languages.items():

        rows.append(
            {
                "language": language,
                "bytes": bytes_count
            }
        )

    df = pd.DataFrame(rows)

    if not df.empty:

        total_bytes = df["bytes"].sum()

        if total_bytes > 0:

            df["percentage"] = (
                df["bytes"]
                / total_bytes
            ) * 100

        else:

            df["percentage"] = 0.0

        df = df.sort_values(
            "bytes",
            ascending=False
        ).reset_index(
            drop=True
        )

    return df



def releases_to_dataframe(releases):
    rows = []

    for release in releases:

        author_data = (
            release.get("author")
            or {}
        )

        rows.append(
            {
                "tag": release.get(
                    "tag_name",
                    "Unknown"
                ),
                "name": (
                    release.get("name")
                    or release.get(
                        "tag_name",
                        "No name"
                    )
                ),
                "author": author_data.get(
                    "login",
                    "Unknown"
                ),
                "created_at": release.get(
                    "created_at"
                ),
                "published_at": release.get(
                    "published_at"
                ),
                "draft": release.get(
                    "draft",
                    False
                ),
                "prerelease": release.get(
                    "prerelease",
                    False
                ),
            }
        )

    df = pd.DataFrame(rows)

    if not df.empty:

        df["created_at"] = pd.to_datetime(
            df["created_at"]
        )

        df["published_at"] = pd.to_datetime(
            df["published_at"]
        )

    return df



def contributors_to_dataframe(
    contributors
):
    rows = []

    for contributor in contributors:

        rows.append(
            {
                "username": contributor.get(
                    "login",
                    "Unknown"
                ),
                "contributions": contributor.get(
                    "contributions",
                    0
                ),
            }
        )

    df = pd.DataFrame(rows)

    if not df.empty:

        total_contributions = (
            df["contributions"].sum()
        )

        if total_contributions > 0:

            df["contribution_percentage"] = (
                df["contributions"]
                / total_contributions
            ) * 100

        else:

            df["contribution_percentage"] = 0.0

        df = df.sort_values(
            "contributions",
            ascending=False
        ).reset_index(
            drop=True
        )

    return df



def calculate_commit_metrics(df):

    metrics = {
        "total_commits": 0,
        "unique_contributors": 0,
        "average_commits_per_day": 0.0
    }

    if df.empty:
        return metrics

    metrics["total_commits"] = int(
        len(df)
    )

    metrics["unique_contributors"] = int(
        df["author"].nunique()
    )

    date_range = (
        df["date"].max()
        - df["date"].min()
    ).days + 1

    if date_range > 0:

        metrics["average_commits_per_day"] = float(
            len(df) / date_range
        )

    return metrics



def calculate_commit_activity_trend(df):

    metrics = {
        "first_commit_date": "N/A",
        "latest_commit_date": "N/A",
        "active_days": 0,
        "most_active_day": "N/A",
        "most_active_day_commits": 0
    }

    if df.empty:
        return metrics

    metrics["first_commit_date"] = (
        df["date"]
        .min()
        .strftime("%Y-%m-%d")
    )

    metrics["latest_commit_date"] = (
        df["date"]
        .max()
        .strftime("%Y-%m-%d")
    )

    metrics["active_days"] = int(
        df["day"].nunique()
    )

    daily_activity = (
        df.groupby("day")
        .size()
        .sort_values(
            ascending=False
        )
    )

    if not daily_activity.empty:

        metrics["most_active_day"] = str(
            daily_activity.index[0]
        )

        metrics["most_active_day_commits"] = int(
            daily_activity.iloc[0]
        )

    return metrics



def calculate_monthly_commit_activity(df):

    metrics = {
        "active_months": 0,
        "most_active_month": "N/A",
        "most_active_month_commits": 0,
        "average_commits_per_active_month": 0.0
    }

    if df.empty:
        return metrics, pd.DataFrame()

    monthly_activity = (
        df.assign(
            month=df["date"].dt.tz_localize(None).dt.to_period("M")
        )
        .groupby("month")
        .agg(
            commits=("sha", "count"),
            active_days=("day", "nunique"),
            contributors=("author", "nunique")
        )
        .reset_index()
    )

    if monthly_activity.empty:
        return metrics, pd.DataFrame()

    monthly_activity["month"] = (
        monthly_activity["month"]
        .astype(str)
    )

    monthly_activity = monthly_activity.sort_values(
        "month"
    ).reset_index(
        drop=True
    )

    metrics["active_months"] = int(
        len(monthly_activity)
    )

    most_active_index = (
        monthly_activity["commits"]
        .idxmax()
    )

    metrics["most_active_month"] = str(
        monthly_activity.loc[
            most_active_index,
            "month"
        ]
    )

    metrics["most_active_month_commits"] = int(
        monthly_activity.loc[
            most_active_index,
            "commits"
        ]
    )

    metrics["average_commits_per_active_month"] = float(
        monthly_activity["commits"].mean()
    )

    return metrics, monthly_activity



def calculate_issue_metrics(df):

    metrics = {
        "total_issues": 0,
        "open_issues": 0,
        "closed_issues": 0,
        "closure_rate": 0.0
    }

    if df.empty:
        return metrics

    metrics["total_issues"] = int(
        len(df)
    )

    metrics["open_issues"] = int(
        df["state"]
        .eq("open")
        .sum()
    )

    metrics["closed_issues"] = int(
        df["state"]
        .eq("closed")
        .sum()
    )

    if metrics["total_issues"] > 0:

        metrics["closure_rate"] = float(
            (
                metrics["closed_issues"]
                / metrics["total_issues"]
            ) * 100
        )

    return metrics



def calculate_pull_request_metrics(df):

    metrics = {
        "total_pull_requests": 0,
        "open_pull_requests": 0,
        "closed_pull_requests": 0,
        "merged_pull_requests": 0,
        "merge_rate": 0.0
    }

    if df.empty:
        return metrics

    metrics["total_pull_requests"] = int(
        len(df)
    )

    metrics["open_pull_requests"] = int(
        df["state"]
        .eq("open")
        .sum()
    )

    metrics["closed_pull_requests"] = int(
        df["state"]
        .eq("closed")
        .sum()
    )

    metrics["merged_pull_requests"] = int(
        df["merged_at"]
        .notna()
        .sum()
    )

    if metrics["total_pull_requests"] > 0:

        metrics["merge_rate"] = float(
            (
                metrics["merged_pull_requests"]
                / metrics["total_pull_requests"]
            ) * 100
        )

    return metrics



def calculate_contributor_metrics(df):

    metrics = {
        "total_contributors": 0,
        "top_contributor": "N/A",
        "top_contributor_percentage": 0.0,
        "top_3_contributor_percentage": 0.0
    }

    if df.empty:
        return metrics

    metrics["total_contributors"] = int(
        len(df)
    )

    metrics["top_contributor"] = str(
        df.iloc[0]["username"]
    )

    metrics["top_contributor_percentage"] = float(
        df.iloc[0][
            "contribution_percentage"
        ]
    )

    metrics["top_3_contributor_percentage"] = float(
        df.head(3)[
            "contribution_percentage"
        ].sum()
    )

    return metrics



def calculate_contributor_concentration(df):

    metrics = {
        "top_contributor_concentration": 0.0,
        "top_3_contributor_concentration": 0.0,
        "top_5_contributor_concentration": 0.0
    }

    if df.empty:
        return metrics

    if (
        "contribution_percentage"
        not in df.columns
    ):
        return metrics

    metrics["top_contributor_concentration"] = float(
        df.iloc[0][
            "contribution_percentage"
        ]
    )

    metrics["top_3_contributor_concentration"] = float(
        df.head(3)[
            "contribution_percentage"
        ].sum()
    )

    metrics["top_5_contributor_concentration"] = float(
        df.head(5)[
            "contribution_percentage"
        ].sum()
    )

    return metrics



def calculate_release_metrics(df):

    metrics = {
        "total_releases": 0,
        "latest_release": "N/A",
        "average_days_between_releases": 0.0,
        "releases_per_month": 0.0
    }

    if df.empty:
        return metrics

    metrics["total_releases"] = int(
        len(df)
    )

    published_releases = (
        df[
            df["published_at"].notna()
        ]
        .sort_values(
            "published_at",
            ascending=True
        )
    )

    if published_releases.empty:
        return metrics

    metrics["latest_release"] = str(
        published_releases.iloc[-1]["tag"]
    )

    if len(published_releases) > 1:

        release_dates = (
            published_releases["published_at"]
            .dropna()
            .sort_values()
        )

        intervals = (
            release_dates.diff()
            .dropna()
            .dt.total_seconds()
            / 86400
        )

        if not intervals.empty:

            metrics["average_days_between_releases"] = float(
                intervals.mean()
            )

    date_span_days = (
        published_releases["published_at"].max()
        - published_releases["published_at"].min()
    ).total_seconds() / 86400

    if date_span_days > 0:

        months = date_span_days / 30.44

        metrics["releases_per_month"] = float(
            len(published_releases) / months
        )

    return metrics


HEALTH_WEIGHTS = {
    "activity": 30,
    "collaboration": 20,
    "issues": 15,
    "pull_requests": 20,
    "releases": 15,
}

HEALTH_NAMES = {
    "activity": "Activity",
    "collaboration": "Collaboration",
    "issues": "Issues",
    "pull_requests": "PR Health",
    "releases": "Releases",
}

HEALTH_REQUIRED_ANALYSIS = {
    "activity": "Commits",
    "collaboration": "Contributors",
    "issues": "Issues",
    "pull_requests": "Pull Requests",
    "releases": "Releases",
}

AGE_BANDS = [(7, 100), (30, 85), (90, 60), (180, 35), (365, 15)]
RELEASE_BANDS = [(30, 100), (90, 80), (180, 60), (365, 35), (730, 15)]

CONSISTENCY_MAX_WEEKS = 52
STALE_ISSUE_DAYS = 180
STALE_PR_DAYS = 90


def _band_score(value, bands):

    for upper, score in bands:

        if value <= upper:
            return float(score)

    return 0.0


def _describe_bands(bands, unit):

    parts = [f"{score} if \u2264{upper} {unit}" for upper, score in bands]

    return ", ".join(parts) + ", else 0"


def _linear_score(value, best, worst):

    if best == worst:
        return 100.0 if value == best else 0.0

    fraction = (value - worst) / (best - worst)

    return float(min(100.0, max(0.0, fraction * 100.0)))


def _weighted_mean(parts):

    usable = [(score, weight) for score, weight in parts if score is not None]

    if not usable:
        return None

    total_weight = sum(weight for _, weight in usable)

    return sum(score * weight for score, weight in usable) / total_weight


def _utc_series(series):

    return pd.to_datetime(series, utc=True, errors="coerce")


LABEL_LAST_COMMIT = "Days since latest commit"
LABEL_ACTIVE_WEEKS = "Weeks with at least one commit"
LABEL_TOP_1 = "Top contributor share"
LABEL_TOP_3 = "Top 3 contributors share"
LABEL_BREADTH = "Contributors analyzed"
LABEL_CLOSURE = "Issue closure rate"
LABEL_STALE_ISSUES = f"Open issues older than {STALE_ISSUE_DAYS} days"
LABEL_MERGE = "Merged share of closed PRs"
LABEL_STALE_PRS = f"Open PRs older than {STALE_PR_DAYS} days"
LABEL_LAST_RELEASE = "Days since latest release"
LABEL_RELEASE_INTERVAL = "Average days between releases"

RULE_LAST_COMMIT = _describe_bands(AGE_BANDS, "days")
RULE_ACTIVE_WEEKS = (
    "Share of weeks with commits over the selected window "
    f"(at most the last {CONSISTENCY_MAX_WEEKS} weeks)"
)
RULE_TOP_1 = "100 at \u226425%, 0 at \u226590%, linear in between"
RULE_TOP_3 = "100 at \u226450%, 0 at \u226598%, linear in between"
RULE_BREADTH = "10 points per contributor, capped at 100"
RULE_CLOSURE = "Closed issues as a percentage of all issues in the window"
RULE_STALE_ISSUES = "100 minus the percentage of open issues that are stale (100 when none are open)"
RULE_MERGE = "Merged PRs as a percentage of closed PRs in the window"
RULE_STALE_PRS = "100 minus the percentage of open PRs that are stale (100 when none are open)"
RULE_LAST_RELEASE = _describe_bands(RELEASE_BANDS, "days")
RULE_RELEASE_INTERVAL = _describe_bands(RELEASE_BANDS, "days")

HEALTH_METHODS = {
    "activity": {
        "summary": "Average of commit recency and weekly commit consistency. No commits in the window scores 0.",
        "rules": [
            (LABEL_LAST_COMMIT, RULE_LAST_COMMIT),
            (LABEL_ACTIVE_WEEKS, RULE_ACTIVE_WEEKS),
        ],
    },
    "collaboration": {
        "summary": "Average of top-1 share, top-3 share and contributor breadth.",
        "rules": [
            (LABEL_TOP_1, RULE_TOP_1),
            (LABEL_TOP_3, RULE_TOP_3),
            (LABEL_BREADTH, RULE_BREADTH),
        ],
    },
    "issues": {
        "summary": "70% closure rate and 30% share of open issues that are not stale.",
        "rules": [
            (LABEL_CLOSURE, RULE_CLOSURE),
            (LABEL_STALE_ISSUES, RULE_STALE_ISSUES),
        ],
    },
    "pull_requests": {
        "summary": "60% merged share of closed PRs and 40% share of open PRs that are not stale.",
        "rules": [
            (LABEL_MERGE, RULE_MERGE),
            (LABEL_STALE_PRS, RULE_STALE_PRS),
        ],
    },
    "releases": {
        "summary": "Average of latest release age and average release interval. Scored only when published releases exist.",
        "rules": [
            (LABEL_LAST_RELEASE, RULE_LAST_RELEASE),
            (LABEL_RELEASE_INTERVAL, RULE_RELEASE_INTERVAL),
        ],
    },
}


def _health_input(label, value, score, rule):

    return {"label": label, "value": value, "score": score, "rule": rule}


def _health_component(key, score, inputs, reason=None):

    return {
        "key": key,
        "name": HEALTH_NAMES[key],
        "weight": HEALTH_WEIGHTS[key],
        "score": score,
        "available": score is not None,
        "reason": reason,
        "summary": HEALTH_METHODS[key]["summary"],
        "rules": HEALTH_METHODS[key]["rules"],
        "inputs": inputs,
        "effective_weight": None,
    }


def _health_activity(commits_df, period_start, now):

    if commits_df is None or commits_df.empty or "date" not in commits_df.columns:

        return _health_component(
            "activity",
            0.0,
            [],
            reason="No commits were found in the selected window, so activity is scored 0.",
        )

    dates = _utc_series(commits_df["date"]).dropna()

    if dates.empty:

        return _health_component(
            "activity",
            None,
            [],
            reason="Commit dates were not available.",
        )

    latest = dates.max()
    days_since = max(0.0, (now - latest).total_seconds() / 86400)
    recency_score = _band_score(days_since, AGE_BANDS)

    window_start = period_start if period_start is not None else dates.min()
    window_start = pd.Timestamp(window_start)

    if window_start.tzinfo is None:
        window_start = window_start.tz_localize("UTC")

    cap_start = now - pd.Timedelta(weeks=CONSISTENCY_MAX_WEEKS)
    window_start = max(window_start, cap_start)

    window_days = max(0.0, (now - window_start).total_seconds() / 86400)
    total_weeks = max(1, math.ceil(window_days / 7))

    in_window = dates[dates >= window_start]
    week_index = ((in_window - window_start).dt.total_seconds() // (7 * 86400)).astype(int)
    week_index = week_index[(week_index >= 0) & (week_index < total_weeks)]
    active_weeks = int(week_index.nunique())
    consistency_score = min(100.0, active_weeks / total_weeks * 100.0)

    inputs = [
        _health_input(
            LABEL_LAST_COMMIT,
            f"{days_since:.0f} days",
            recency_score,
            RULE_LAST_COMMIT,
        ),
        _health_input(
            LABEL_ACTIVE_WEEKS,
            f"{active_weeks} of {total_weeks} weeks",
            consistency_score,
            RULE_ACTIVE_WEEKS,
        ),
    ]

    return _health_component(
        "activity",
        (recency_score + consistency_score) / 2,
        inputs,
    )


def _health_collaboration(contributors_df):

    if (
        contributors_df is None
        or contributors_df.empty
        or "contribution_percentage" not in contributors_df.columns
    ):

        return _health_component(
            "collaboration",
            None,
            [],
            reason="No contributor data was available.",
        )

    ordered = contributors_df.sort_values(
        "contribution_percentage", ascending=False
    )

    top_1 = float(ordered["contribution_percentage"].iloc[0])
    top_3 = float(ordered["contribution_percentage"].head(3).sum())
    count = int(len(ordered))

    top_1_score = _linear_score(top_1, 25, 90)
    top_3_score = _linear_score(top_3, 50, 98)
    breadth_score = min(count, 10) / 10 * 100.0

    inputs = [
        _health_input(LABEL_TOP_1, f"{top_1:.1f}%", top_1_score, RULE_TOP_1),
        _health_input(LABEL_TOP_3, f"{top_3:.1f}%", top_3_score, RULE_TOP_3),
        _health_input(LABEL_BREADTH, f"{count}", breadth_score, RULE_BREADTH),
    ]

    return _health_component(
        "collaboration",
        (top_1_score + top_3_score + breadth_score) / 3,
        inputs,
    )


def _stale_open_count(open_df, now, stale_days):

    if open_df.empty or "created_at" not in open_df.columns:
        return 0

    created = _utc_series(open_df["created_at"])
    age_days = (now - created).dt.total_seconds() / 86400

    return int((age_days > stale_days).sum())


def _health_issues(issues_df, now):

    if (
        issues_df is None
        or issues_df.empty
        or "state" not in issues_df.columns
    ):

        return _health_component(
            "issues",
            None,
            [],
            reason="No issues were found in the selected window.",
        )

    total = int(len(issues_df))
    closed = int(issues_df["state"].eq("closed").sum())
    open_df = issues_df[issues_df["state"].eq("open")]
    open_count = int(len(open_df))

    closure_rate = closed / total * 100.0

    stale_count = _stale_open_count(open_df, now, STALE_ISSUE_DAYS)
    stale_share = (stale_count / open_count * 100.0) if open_count > 0 else 0.0
    freshness_score = 100.0 - stale_share

    inputs = [
        _health_input(
            LABEL_CLOSURE,
            f"{closure_rate:.1f}% ({closed} of {total})",
            closure_rate,
            RULE_CLOSURE,
        ),
        _health_input(
            LABEL_STALE_ISSUES,
            f"{stale_count} of {open_count} open",
            freshness_score,
            RULE_STALE_ISSUES,
        ),
    ]

    return _health_component(
        "issues",
        _weighted_mean([(closure_rate, 70), (freshness_score, 30)]),
        inputs,
    )


def _health_pull_requests(pull_requests_df, now):

    if (
        pull_requests_df is None
        or pull_requests_df.empty
        or "state" not in pull_requests_df.columns
    ):

        return _health_component(
            "pull_requests",
            None,
            [],
            reason="No pull requests were found in the selected window.",
        )

    closed_df = pull_requests_df[pull_requests_df["state"].eq("closed")]
    open_df = pull_requests_df[pull_requests_df["state"].eq("open")]

    closed_count = int(len(closed_df))
    open_count = int(len(open_df))

    merged_count = (
        int(closed_df["merged_at"].notna().sum())
        if "merged_at" in closed_df.columns
        else 0
    )

    merge_share = (
        merged_count / closed_count * 100.0 if closed_count > 0 else None
    )

    stale_count = _stale_open_count(open_df, now, STALE_PR_DAYS)
    stale_share = (stale_count / open_count * 100.0) if open_count > 0 else 0.0
    freshness_score = 100.0 - stale_share

    inputs = []

    if merge_share is not None:

        inputs.append(
            _health_input(
                LABEL_MERGE,
                f"{merge_share:.1f}% ({merged_count} of {closed_count})",
                merge_share,
                RULE_MERGE,
            )
        )

    inputs.append(
        _health_input(
            LABEL_STALE_PRS,
            f"{stale_count} of {open_count} open",
            freshness_score,
            RULE_STALE_PRS,
        )
    )

    score = _weighted_mean([(merge_share, 60), (freshness_score, 40)])

    return _health_component("pull_requests", score, inputs)


def _health_releases(releases_df, now):

    unavailable = _health_component(
        "releases",
        None,
        [],
        reason="No published releases were found in the selected window.",
    )

    if (
        releases_df is None
        or releases_df.empty
        or "published_at" not in releases_df.columns
    ):
        return unavailable

    published = _utc_series(releases_df["published_at"]).dropna().sort_values()

    if published.empty:
        return unavailable

    days_since = max(0.0, (now - published.iloc[-1]).total_seconds() / 86400)
    age_score = _band_score(days_since, RELEASE_BANDS)

    inputs = [
        _health_input(
            LABEL_LAST_RELEASE,
            f"{days_since:.0f} days",
            age_score,
            RULE_LAST_RELEASE,
        )
    ]

    scores = [age_score]

    if len(published) >= 2:

        intervals = published.diff().dropna().dt.total_seconds() / 86400
        average_interval = float(intervals.mean())
        interval_score = _band_score(average_interval, RELEASE_BANDS)
        scores.append(interval_score)

        inputs.append(
            _health_input(
                LABEL_RELEASE_INTERVAL,
                f"{average_interval:.1f} days",
                interval_score,
                RULE_RELEASE_INTERVAL,
            )
        )

    return _health_component(
        "releases",
        sum(scores) / len(scores),
        inputs,
    )


def health_label(score):

    if score is None:
        return "Unavailable"

    if score >= 75:
        return "Healthy"

    if score >= 50:
        return "Moderate"

    return "Needs attention"


def calculate_health_score(
    commits_df,
    contributors_df,
    issues_df,
    pull_requests_df,
    releases_df,
    selected_analyses,
    period_start=None,
    now=None,
):

    selected = set(selected_analyses or [])

    if now is None:
        now = datetime.now(timezone.utc)

    now = pd.Timestamp(now)

    if now.tzinfo is None:
        now = now.tz_localize("UTC")

    if period_start is not None:

        period_start = pd.Timestamp(period_start)

        if period_start.tzinfo is None:
            period_start = period_start.tz_localize("UTC")

    builders = {
        "activity": lambda: _health_activity(commits_df, period_start, now),
        "collaboration": lambda: _health_collaboration(contributors_df),
        "issues": lambda: _health_issues(issues_df, now),
        "pull_requests": lambda: _health_pull_requests(pull_requests_df, now),
        "releases": lambda: _health_releases(releases_df, now),
    }

    components = []

    for key, builder in builders.items():

        required = HEALTH_REQUIRED_ANALYSIS[key]

        if required not in selected:

            components.append(
                _health_component(
                    key,
                    None,
                    [],
                    reason=f"The {required} analysis was not selected.",
                )
            )

            continue

        components.append(builder())

    available = [item for item in components if item["available"]]
    total_weight = sum(item["weight"] for item in available)

    overall = None

    if available and total_weight > 0:

        for item in available:
            item["effective_weight"] = item["weight"] / total_weight * 100.0

        overall = sum(
            item["score"] * item["weight"] for item in available
        ) / total_weight

    rounded = None if overall is None else int(round(overall))

    return {
        "overall": rounded,
        "label": health_label(rounded),
        "components": components,
        "available_count": len(available),
        "total_count": len(components),
    }


DAYS_PER_MONTH = 365.25 / 12
VELOCITY_MIN_PRIOR_COMMITS = 5
VELOCITY_MIN_WEEK_DAYS = 7
VELOCITY_MIN_MONTH_DAYS = 30
VELOCITY_MIN_WINDOW_DAYS = 1.0

ISSUE_AGE_LIMITS = [7, 30, 90, STALE_ISSUE_DAYS]
PR_AGE_LIMITS = [7, 30, STALE_PR_DAYS]

RELEASE_CADENCE_BANDS = [
    (8, "Weekly"),
    (16, "Biweekly"),
    (45, "Monthly"),
    (100, "Quarterly"),
    (200, "Twice a year"),
    (400, "Yearly"),
]
RELEASE_CADENCE_FALLBACK = "Less often than yearly"
RELEASE_CADENCE_MIN_RELEASES = 3

VELOCITY_REASON_ALL_TIME = (
    "All Time has no previous period to compare against. Choose a fixed period to see a change."
)
VELOCITY_REASON_FETCH = (
    "The previous period could not be loaded from GitHub, so no change is shown."
)
VELOCITY_REASON_HISTORY = (
    "The repository history does not cover the whole previous period, so a change would not compare like with like."
)


def _utc_stamp(value):

    if value is None:
        return None

    stamp = pd.Timestamp(value)

    if pd.isna(stamp):
        return None

    if stamp.tzinfo is None:
        return stamp.tz_localize("UTC")

    return stamp.tz_convert("UTC")


def _utc_now(now):

    stamp = _utc_stamp(now)

    if stamp is None:
        return pd.Timestamp(datetime.now(timezone.utc))

    return stamp


def _dates_from(df, column):

    if df is None or df.empty or column not in df.columns:
        return pd.Series([], dtype="datetime64[ns, UTC]")

    return _utc_series(df[column]).dropna()


def _iso_day(stamp):

    return stamp.strftime("%Y-%m-%d")


def _week_floor(stamp):

    day = stamp.normalize()

    return day - pd.Timedelta(days=day.weekday())


def _month_floor(stamp):

    return pd.Timestamp(year=stamp.year, month=stamp.month, day=1, tz="UTC")


def _weekly_table(dates, anchor_start, window_end):

    first = _week_floor(anchor_start)
    last = _week_floor(window_end)
    starts = pd.date_range(first, last, freq="7D")

    counts = [0] * len(starts)

    if not dates.empty:

        indexes = ((dates - first).dt.days // 7).astype(int)

        for index in indexes:

            if 0 <= index < len(counts):
                counts[index] += 1

    table = pd.DataFrame(
        {
            "week_start": starts,
            "commits": counts,
        }
    )

    table["complete"] = [
        bool(start >= anchor_start and start + pd.Timedelta(days=7) <= window_end)
        for start in starts
    ]

    table["week_end"] = (table["week_start"] + pd.Timedelta(days=6)).dt.tz_localize(None)
    table["week_start"] = table["week_start"].dt.tz_localize(None)

    return table[["week_start", "week_end", "commits", "complete"]]


def _monthly_commit_table(dates, anchor_start, window_end):

    first = _month_floor(anchor_start)
    last = _month_floor(window_end)
    starts = pd.date_range(first, last, freq="MS")

    counts = [0] * len(starts)

    if not dates.empty:

        for stamp in dates:

            index = (stamp.year - first.year) * 12 + stamp.month - first.month

            if 0 <= index < len(counts):
                counts[index] += 1

    next_starts = [start + pd.offsets.MonthBegin(1) for start in starts]

    return pd.DataFrame(
        {
            "month_start": starts,
            "month_end": [stamp - pd.Timedelta(days=1) for stamp in next_starts],
            "commits": counts,
            "complete": [
                bool(start >= anchor_start and stamp <= window_end)
                for start, stamp in zip(starts, next_starts)
            ],
        }
    )


def _peak_row(table, start_column, end_column):

    if table.empty:
        return None

    candidates = table[table["complete"] & (table["commits"] > 0)]

    if candidates.empty:
        return None

    row = candidates.loc[candidates["commits"].idxmax()]

    return {
        "start": _iso_day(pd.Timestamp(row[start_column])),
        "end": _iso_day(pd.Timestamp(row[end_column])),
        "commits": int(row["commits"]),
    }


def _velocity_comparison(current_count, prior_df, prior_fetch_ok, period_start, now, repo_created_at):

    comparison = {
        "status": "unavailable",
        "change_pct": None,
        "change_abs": None,
        "current_commits": current_count,
        "prior_commits": None,
        "prior_start": None,
        "prior_end": None,
        "reason": "",
    }

    if period_start is None:

        comparison["reason"] = VELOCITY_REASON_ALL_TIME

        return comparison

    prior_start = period_start - (now - period_start)

    comparison["prior_start"] = _iso_day(prior_start)
    comparison["prior_end"] = _iso_day(period_start)

    if not prior_fetch_ok:

        comparison["reason"] = VELOCITY_REASON_FETCH

        return comparison

    prior_dates = _dates_from(prior_df, "date")
    prior_dates = prior_dates[(prior_dates >= prior_start) & (prior_dates < period_start)]

    created = _utc_stamp(repo_created_at)

    covered = created is not None and (
        created <= prior_start
        or (len(prior_dates) > 0 and prior_dates.min() < created)
    )

    if not covered:

        comparison["reason"] = VELOCITY_REASON_HISTORY

        return comparison

    prior_count = int(len(prior_dates))

    comparison["prior_commits"] = prior_count
    comparison["change_abs"] = current_count - prior_count

    if prior_count == 0:

        comparison["status"] = "limited"
        comparison["reason"] = "The previous period had no commits, so a percentage change is undefined."

        return comparison

    if prior_count < VELOCITY_MIN_PRIOR_COMMITS:

        comparison["status"] = "limited"
        comparison["reason"] = (
            f"The previous period had only {prior_count} commit(s). "
            f"At least {VELOCITY_MIN_PRIOR_COMMITS} are needed before a percentage is shown."
        )

        return comparison

    comparison["status"] = "comparable"
    comparison["change_pct"] = float((current_count - prior_count) / prior_count * 100.0)

    return comparison


def calculate_commit_velocity(
    current_df,
    prior_df,
    period_start,
    now,
    repo_created_at,
    prior_fetch_ok=True,
):

    now = _utc_now(now)
    start = _utc_stamp(period_start)

    dates = _dates_from(current_df, "date")

    if start is not None:
        dates = dates[dates >= start]

    metrics = {
        "commits": int(len(dates)),
        "window_days": None,
        "window_start": None,
        "window_end": _iso_day(now),
        "per_day": None,
        "per_week": None,
        "per_month": None,
        "comparison": _velocity_comparison(
            int(len(dates)),
            prior_df,
            prior_fetch_ok,
            start,
            now,
            repo_created_at,
        ),
        "peak_week": None,
        "peak_month": None,
        "complete_weeks": 0,
        "total_weeks": 0,
        "complete_months": 0,
        "total_months": 0,
    }

    empty_weekly = pd.DataFrame(
        {
            "week_start": pd.Series([], dtype="datetime64[ns]"),
            "week_end": pd.Series([], dtype="datetime64[ns]"),
            "commits": pd.Series([], dtype="int64"),
            "complete": pd.Series([], dtype="bool"),
        }
    )

    if start is None:

        if dates.empty:
            return metrics, empty_weekly

        window_start = dates.min()
        anchor_week = _week_floor(window_start)
        anchor_month = _month_floor(window_start)

    else:

        window_start = start
        anchor_week = start
        anchor_month = start

    window_end = max(now, dates.max()) if not dates.empty else now

    window_days = max(
        (now - window_start).total_seconds() / 86400,
        VELOCITY_MIN_WINDOW_DAYS,
    )

    metrics["window_days"] = float(window_days)
    metrics["window_start"] = _iso_day(window_start)

    per_day = len(dates) / window_days

    metrics["per_day"] = float(per_day)

    if window_days >= VELOCITY_MIN_WEEK_DAYS:
        metrics["per_week"] = float(per_day * 7)

    if window_days >= VELOCITY_MIN_MONTH_DAYS:
        metrics["per_month"] = float(per_day * DAYS_PER_MONTH)

    weekly = _weekly_table(dates, anchor_week, window_end)
    monthly = _monthly_commit_table(dates, anchor_month, window_end)

    metrics["total_weeks"] = int(len(weekly))
    metrics["complete_weeks"] = int(weekly["complete"].sum())
    metrics["total_months"] = int(len(monthly))
    metrics["complete_months"] = int(monthly["complete"].sum())

    metrics["peak_week"] = _peak_row(weekly, "week_start", "week_end")
    metrics["peak_month"] = _peak_row(monthly, "month_start", "month_end")

    return metrics, weekly.reset_index(drop=True)


def _age_distribution(ages_days, limits):

    labels = []
    previous = None

    for limit in limits:

        if previous is None:
            labels.append(f"Up to {limit} days")
        else:
            labels.append(f"{previous}-{limit} days")

        previous = limit

    labels.append(f"Over {previous} days")

    counts = [0] * len(labels)

    for age in ages_days:

        slot = len(limits)

        for position, limit in enumerate(limits):

            if age <= limit:
                slot = position
                break

        counts[slot] += 1

    total = sum(counts)

    return pd.DataFrame(
        {
            "age_band": labels,
            "count": counts,
            "share": [
                (count / total * 100.0) if total > 0 else 0.0
                for count in counts
            ],
        }
    )


def _monthly_counts_table(series_by_column):

    names = list(series_by_column.keys())
    counts = {}

    for name, dates in series_by_column.items():

        if dates.empty:
            counts[name] = pd.Series([], dtype="int64")
            continue

        periods = dates.dt.tz_convert("UTC").dt.tz_localize(None).dt.to_period("M")
        counts[name] = periods.value_counts()

    all_periods = [period for series in counts.values() for period in series.index]

    if not all_periods:
        return pd.DataFrame(columns=["month"] + names)

    full = pd.period_range(min(all_periods), max(all_periods), freq="M")

    frame = pd.DataFrame({"month": [str(period) for period in full]})

    for name in names:
        frame[name] = [int(counts[name].get(period, 0)) for period in full]

    return frame


def _oldest_open(frame, created, ages):

    if ages.empty:
        return None

    index = ages.idxmax()
    row = frame.loc[index]

    return {
        "number": int(row["number"]) if pd.notna(row.get("number")) else None,
        "title": str(row.get("title") or ""),
        "age_days": float(ages.loc[index]),
        "created_at": _iso_day(created.loc[index]),
    }


def _duration_summary(durations):

    if durations.empty:
        return None, None

    return float(durations.mean()), float(durations.median())


def calculate_issue_resolution(df, now=None):

    now = _utc_now(now)

    metrics = {
        "closed_with_duration": 0,
        "average_days_to_close": None,
        "median_days_to_close": None,
        "open_count": 0,
        "oldest_open": None,
        "stale_open_count": 0,
        "stale_open_share": None,
    }

    empty_aging = _age_distribution([], ISSUE_AGE_LIMITS)
    empty_monthly = pd.DataFrame(columns=["month", "opened", "closed"])

    if (
        df is None
        or df.empty
        or "created_at" not in df.columns
        or "state" not in df.columns
    ):
        return metrics, empty_aging, empty_monthly

    created = _utc_series(df["created_at"])
    closed_at = (
        _utc_series(df["closed_at"])
        if "closed_at" in df.columns
        else pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns, UTC]")
    )

    closed_mask = df["state"].eq("closed") & closed_at.notna() & created.notna()
    durations = (closed_at - created)[closed_mask].dt.total_seconds() / 86400
    durations = durations[durations >= 0]

    metrics["closed_with_duration"] = int(len(durations))
    metrics["average_days_to_close"], metrics["median_days_to_close"] = _duration_summary(durations)

    open_mask = df["state"].eq("open") & created.notna()
    ages = ((now - created[open_mask]).dt.total_seconds() / 86400).clip(lower=0)

    metrics["open_count"] = int(len(ages))
    metrics["oldest_open"] = _oldest_open(df, created, ages)
    metrics["stale_open_count"] = int((ages > STALE_ISSUE_DAYS).sum())

    if len(ages) > 0:
        metrics["stale_open_share"] = float(metrics["stale_open_count"] / len(ages) * 100.0)

    aging = _age_distribution(list(ages), ISSUE_AGE_LIMITS)

    monthly = _monthly_counts_table(
        {
            "opened": created.dropna(),
            "closed": closed_at[closed_mask],
        }
    )

    return metrics, aging, monthly


def calculate_pull_request_health(df, now=None):

    now = _utc_now(now)

    metrics = {
        "closed_count": 0,
        "closed_unmerged_count": 0,
        "closed_unmerged_share": None,
        "merged_with_duration": 0,
        "average_days_to_merge": None,
        "median_days_to_merge": None,
        "open_count": 0,
        "oldest_open": None,
        "stale_open_count": 0,
        "stale_open_share": None,
    }

    empty_aging = _age_distribution([], PR_AGE_LIMITS)
    empty_monthly = pd.DataFrame(columns=["month", "opened", "merged", "closed_unmerged"])

    if (
        df is None
        or df.empty
        or "created_at" not in df.columns
        or "state" not in df.columns
    ):
        return metrics, empty_aging, empty_monthly

    created = _utc_series(df["created_at"])
    blank = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns, UTC]")
    merged_at = _utc_series(df["merged_at"]) if "merged_at" in df.columns else blank
    closed_at = _utc_series(df["closed_at"]) if "closed_at" in df.columns else blank

    closed_mask = df["state"].eq("closed")
    unmerged_mask = closed_mask & merged_at.isna()
    merged_mask = merged_at.notna() & created.notna()

    metrics["closed_count"] = int(closed_mask.sum())
    metrics["closed_unmerged_count"] = int(unmerged_mask.sum())

    if metrics["closed_count"] > 0:
        metrics["closed_unmerged_share"] = float(
            metrics["closed_unmerged_count"] / metrics["closed_count"] * 100.0
        )

    durations = (merged_at - created)[merged_mask].dt.total_seconds() / 86400
    durations = durations[durations >= 0]

    metrics["merged_with_duration"] = int(len(durations))
    metrics["average_days_to_merge"], metrics["median_days_to_merge"] = _duration_summary(durations)

    open_mask = df["state"].eq("open") & created.notna()
    ages = ((now - created[open_mask]).dt.total_seconds() / 86400).clip(lower=0)

    metrics["open_count"] = int(len(ages))
    metrics["oldest_open"] = _oldest_open(df, created, ages)
    metrics["stale_open_count"] = int((ages > STALE_PR_DAYS).sum())

    if len(ages) > 0:
        metrics["stale_open_share"] = float(metrics["stale_open_count"] / len(ages) * 100.0)

    aging = _age_distribution(list(ages), PR_AGE_LIMITS)

    monthly = _monthly_counts_table(
        {
            "opened": created.dropna(),
            "merged": merged_at[merged_mask],
            "closed_unmerged": closed_at[unmerged_mask].dropna(),
        }
    )

    return metrics, aging, monthly


def release_cadence_label(median_days):

    if median_days is None:
        return None

    for limit, label in RELEASE_CADENCE_BANDS:

        if median_days <= limit:
            return label

    return RELEASE_CADENCE_FALLBACK


def calculate_release_cadence(df, now=None):

    now = _utc_now(now)

    metrics = {
        "published_count": 0,
        "latest_tag": None,
        "latest_age_days": None,
        "median_interval_days": None,
        "shortest_interval_days": None,
        "longest_interval_days": None,
        "cadence_label": None,
        "cadence_reason": "No published releases were found in the selected window.",
    }

    empty_intervals = pd.DataFrame(columns=["tag", "published_at", "days_since_previous"])

    if (
        df is None
        or df.empty
        or "published_at" not in df.columns
        or "tag" not in df.columns
    ):
        return metrics, empty_intervals

    published = df.assign(published_at=_utc_series(df["published_at"]))
    published = published[published["published_at"].notna()]
    published = published.sort_values("published_at", kind="stable").reset_index(drop=True)

    if published.empty:
        return metrics, empty_intervals

    metrics["published_count"] = int(len(published))
    metrics["latest_tag"] = str(published.iloc[-1]["tag"])
    metrics["latest_age_days"] = float(
        max(0.0, (now - published.iloc[-1]["published_at"]).total_seconds() / 86400)
    )

    gaps = published["published_at"].diff().dt.total_seconds() / 86400

    intervals = pd.DataFrame(
        {
            "tag": published["tag"].astype(str),
            "published_at": published["published_at"],
            "days_since_previous": gaps,
        }
    ).iloc[1:].reset_index(drop=True)

    if intervals.empty:

        metrics["cadence_reason"] = (
            f"At least {RELEASE_CADENCE_MIN_RELEASES} published releases are needed to label a cadence."
        )

        return metrics, intervals

    metrics["median_interval_days"] = float(intervals["days_since_previous"].median())
    metrics["shortest_interval_days"] = float(intervals["days_since_previous"].min())
    metrics["longest_interval_days"] = float(intervals["days_since_previous"].max())

    if metrics["published_count"] >= RELEASE_CADENCE_MIN_RELEASES:

        metrics["cadence_label"] = release_cadence_label(metrics["median_interval_days"])
        metrics["cadence_reason"] = ""

    else:

        metrics["cadence_reason"] = (
            f"At least {RELEASE_CADENCE_MIN_RELEASES} published releases are needed to label a cadence."
        )

    return metrics, intervals


def _describe_cadence_bands():

    parts = []
    previous = None

    for limit, label in RELEASE_CADENCE_BANDS:

        if previous is None:
            parts.append(f"up to {limit} days: {label}")
        else:
            parts.append(f"over {previous} to {limit} days: {label}")

        previous = limit

    parts.append(f"over {previous} days: {RELEASE_CADENCE_FALLBACK}")

    return "; ".join(parts)


def _describe_age_limits(limits):

    parts = []
    previous = None

    for limit in limits:

        parts.append(f"up to {limit} days" if previous is None else f"{previous}-{limit} days")
        previous = limit

    parts.append(f"over {previous} days")

    return ", ".join(parts)


VELOCITY_METHODS = [
    {
        "name": "Commit rates",
        "summary": "Commits per day, week and month over the analysis window.",
        "rules": [
            ("Per day", "Commits in the window divided by the window length in days. Windows shorter than 1 day count as 1 day. For All Time the window runs from the first commit to now."),
            ("Per week", f"Per-day rate multiplied by 7. Shown only when the window is at least {VELOCITY_MIN_WEEK_DAYS} days."),
            ("Per month", f"Per-day rate multiplied by {DAYS_PER_MONTH:.2f} days. Shown only when the window is at least {VELOCITY_MIN_MONTH_DAYS} days."),
            ("Difference from Avg Commits / Day", "The Commit Analysis card divides by the span between the first and last commit. Velocity divides by the whole window, so quiet recent stretches lower the rate."),
        ],
    },
    {
        "name": "Change vs previous period",
        "summary": "Compares the window with an equally long window that ends where it begins.",
        "rules": [
            ("Previous period", "Same length as the selected window, ending at the moment the selected window starts. A commit exactly at that moment counts only in the selected window."),
            ("Percentage", f"(current - previous) / previous x 100. Shown only when the previous period has at least {VELOCITY_MIN_PRIOR_COMMITS} commits."),
            ("Repository history", "Shown only when the repository existed for the whole previous period. Otherwise the card explains why it is not shown."),
            ("All Time", "Has no previous period, so no change is shown."),
        ],
    },
    {
        "name": "Peak week and peak month",
        "summary": "The busiest complete week and month in the window.",
        "rules": [
            ("Weeks", "Monday to Sunday in UTC, based on the commit author date. Weeks with no commits count as 0."),
            ("Months", "Calendar months in UTC. Months with no commits count as 0."),
            ("Complete only", "A week or month is complete when it lies fully inside the window. Partial ones are drawn lighter in the chart and never chosen as the peak. For All Time the first week and month count as complete because no history precedes them."),
            ("Ties", "The earliest period wins."),
        ],
    },
]

VELOCITY_FOOT = (
    "Commit velocity describes how much commit activity was recorded. It does not measure code quality or effort, "
    "and a higher number is not automatically better."
)

ISSUE_RESOLUTION_METHODS = [
    {
        "name": "Time to close",
        "summary": "How long closed issues stayed open.",
        "rules": [
            ("Included issues", "Issues created in the selected window that are now closed and have a closing date. Issues still open are not included, so the figures can understate how long issues really take."),
            ("Average and median", "Mean and median of closing date minus creation date. The median is less affected by a few very long-lived issues."),
        ],
    },
    {
        "name": "Oldest open and aging",
        "summary": "How long open issues have been waiting.",
        "rules": [
            ("Age", "Now minus creation date for issues that are currently open."),
            ("Age bands", f"An issue falls in the first band whose upper limit its age does not exceed: {_describe_age_limits(ISSUE_AGE_LIMITS)}."),
            ("Stale", f"Open issues older than {STALE_ISSUE_DAYS} days, the same threshold used by the health score."),
        ],
    },
    {
        "name": "Issues by month",
        "summary": "Issues opened and closed per calendar month.",
        "rules": [
            ("Opened", "Issues created in that month (UTC)."),
            ("Closed", "Issues from the selected window that were closed in that month. Issues created before the window are not counted."),
        ],
    },
]

PR_HEALTH_METHODS = [
    {
        "name": "Closed without merge",
        "summary": "Pull requests that were closed but never merged.",
        "rules": [
            ("Count", "Closed pull requests with no merge date."),
            ("Share", "Closed without merge divided by all closed pull requests in the window."),
        ],
    },
    {
        "name": "Time to merge",
        "summary": "How long merged pull requests took to merge.",
        "rules": [
            ("Included pull requests", "Pull requests created in the selected window that have been merged. Open ones are not included, so the figures can understate real waiting times."),
            ("Average and median", "Mean and median of merge date minus creation date."),
        ],
    },
    {
        "name": "Open pull request aging",
        "summary": "How long open pull requests have been waiting.",
        "rules": [
            ("Age bands", f"Now minus creation date, placed in the first band whose upper limit it does not exceed: {_describe_age_limits(PR_AGE_LIMITS)}."),
            ("Stale", f"Open pull requests older than {STALE_PR_DAYS} days, the same threshold used by the health score."),
        ],
    },
    {
        "name": "Pull requests per month",
        "summary": "Pull requests opened, merged and closed without merge per calendar month.",
        "rules": [
            ("Opened", "Pull requests created in that month (UTC)."),
            ("Merged and closed without merge", "Pull requests from the selected window merged or closed in that month. Those created before the window are not counted."),
        ],
    },
]

RELEASE_CADENCE_METHODS = [
    {
        "name": "Release interval",
        "summary": "Days between consecutive published releases.",
        "rules": [
            ("Included releases", "Published releases (including pre-releases, excluding drafts) inside the selected window. Releases before the window are not used."),
            ("Median", "Median of the gaps between consecutive release dates. It is not pulled up by one long pause."),
            ("Shortest and longest", "Smallest and largest of those gaps."),
        ],
    },
    {
        "name": "Cadence label",
        "summary": "A plain-language label for the median interval.",
        "rules": [
            ("Bands", _describe_cadence_bands()),
            ("Minimum data", f"At least {RELEASE_CADENCE_MIN_RELEASES} published releases in the window. With fewer, no label is given."),
        ],
    },
    {
        "name": "Latest release age",
        "summary": "Days from the latest published release in the window to now.",
        "rules": [
            ("Window", "If no release was published in the window, the age is not shown even when older releases exist."),
        ],
    },
]

ISSUE_RESOLUTION_FOOT = (
    "Issues are selected by creation date, so closing times describe issues created in the window that have since been closed. "
    "Nothing here judges whether a resolution time is good or bad."
)

PR_HEALTH_FOOT = (
    "Pull requests are selected by creation date, so merge times describe pull requests created in the window that have since been merged. "
    "Nothing here judges whether a merge time is good or bad."
)

RELEASE_CADENCE_FOOT = (
    "Cadence describes how regularly releases were published inside the window. "
    "It does not measure release quality, and repositories that do not use GitHub releases will show little or nothing here."
)



EXPORT_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
EXPORT_ILLEGAL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
EXCEL_MAX_DATA_ROWS = 1048575
TABLE_SEARCH_MIN_ROWS = 10
TABLE_FILTER_MAX_OPTIONS = 200
EXCEL_SHEET_NAME_LIMIT = 31
EXCEL_SHEET_NAME_FORBIDDEN = re.compile(r"[\\/*?:\[\]]")

TABLE_TOOLS_METHODS = [
    {
        "name": "Search and filters",
        "summary": "Narrow a table to the rows you care about before reading or exporting it.",
        "rules": [
            ("Where it appears", f"Search and filters are offered on tables with at least {TABLE_SEARCH_MIN_ROWS} rows. Every table can be exported."),
            ("Search", "Case-insensitive plain-text match, not a pattern. A row is kept when any text column, or the number column of issues and pull requests, contains the text."),
            ("Filters", "Choosing values in a filter keeps only rows with one of those values. Leaving a filter empty applies no filter. Search and filters combine."),
            ("Author and status", "Issues and pull requests can be filtered by author and state, and pull requests also by whether they were merged, closed without merging, or are still open. The author list shows the most active authors."),
            ("Date range", "Commits are filtered by commit date, issues by the date they were opened and pull requests by the date they were opened. Both ends of the range are included. A range only applies once both dates are chosen."),
            ("Labels", "Issue labels are not fetched from GitHub, so there is no label filter."),
            ("Scope", "Filtering only changes what is shown and exported. The charts, KPIs and scores above are always calculated from the full data."),
        ],
    },
    {
        "name": "Exports",
        "summary": "CSV and Excel files contain exactly the rows currently shown in that table.",
        "rules": [
            ("Workbook", "The workbook holds a Summary metrics sheet with every calculated headline figure, followed by every table from the analysis, unfiltered, one sheet per table."),
            ("Dates", "Dates are written in UTC without a time zone label, because Excel cannot store time zones."),
            ("Text safety", "GitHub titles and messages are untrusted. Text starting with =, +, - or @ gets a leading apostrophe so spreadsheet programs do not run it as a formula, and control characters are removed."),
            ("Size limit", f"An Excel sheet holds at most {EXCEL_MAX_DATA_ROWS:,} data rows. Larger tables are cut at that limit and the workbook says which ones."),
        ],
    },
]

TABLE_TOOLS_FOOT = (
    "Exports reflect the data as it was fetched from GitHub at the time shown above. "
    "Refresh the data to export newer information."
)


def _is_text_column(series):

    return (
        pd.api.types.is_string_dtype(series.dtype)
        or pd.api.types.is_object_dtype(series.dtype)
    )


def filter_table(df, query="", column_values=None, date_column=None, date_range=None):

    if df is None or df.empty:
        return df

    result = df

    if date_column and date_range and date_column in result.columns:

        stamps = pd.to_datetime(result[date_column], utc=True, errors="coerce")
        first = pd.Timestamp(date_range[0], tz="UTC")
        last = pd.Timestamp(date_range[1], tz="UTC") + pd.Timedelta(days=1)
        result = result[(stamps >= first) & (stamps < last)]

    for column, wanted in (column_values or {}).items():

        if column in result.columns and wanted:
            result = result[result[column].isin(list(wanted))]

    text = str(query or "").strip().casefold()

    if not text or result.empty:
        return result

    mask = pd.Series(False, index=result.index)

    for column in result.columns:

        series = result[column]

        if not (_is_text_column(series) or column == "number"):
            continue

        mask |= (
            series.astype("string")
            .str.casefold()
            .str.contains(text, regex=False, na=False)
        )

    return result[mask]


def _export_cell(value):

    if isinstance(value, str):

        value = EXPORT_ILLEGAL_CHARACTERS.sub("", value)

        if value.startswith(EXPORT_FORMULA_PREFIXES):
            return "'" + value

    return value


def prepare_export_frame(df):

    frame = df.copy()

    for column in frame.columns:

        series = frame[column]

        if isinstance(series.dtype, pd.DatetimeTZDtype):
            frame[column] = series.dt.tz_convert("UTC").dt.tz_localize(None)

        elif _is_text_column(series):
            frame[column] = series.map(_export_cell)

    return frame


def dataframe_to_csv_bytes(df):

    return prepare_export_frame(df).to_csv(index=False).encode("utf-8-sig")


def _excel_sheet_name(name, used):

    cleaned = EXCEL_SHEET_NAME_FORBIDDEN.sub(" ", str(name)).strip().strip("'").strip()
    base = (cleaned or "Sheet")[:EXCEL_SHEET_NAME_LIMIT]
    candidate = base
    counter = 2

    while candidate.lower() in used:
        suffix = f" {counter}"
        candidate = base[: EXCEL_SHEET_NAME_LIMIT - len(suffix)] + suffix
        counter += 1

    used.add(candidate.lower())

    return candidate


def tables_to_excel_bytes(tables):

    buffer = BytesIO()
    notes = []
    used = set()
    wrote = False

    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:

        for name, df in tables:

            if df is None:
                continue

            frame = prepare_export_frame(df)

            if len(frame) > EXCEL_MAX_DATA_ROWS:
                notes.append(
                    f"{name}: only the first {EXCEL_MAX_DATA_ROWS:,} of {len(frame):,} rows fit in an Excel sheet."
                )
                frame = frame.iloc[:EXCEL_MAX_DATA_ROWS]

            frame.to_excel(
                writer,
                sheet_name=_excel_sheet_name(name, used),
                index=False,
            )
            wrote = True

        if notes:
            pd.DataFrame({"note": notes}).to_excel(
                writer,
                sheet_name=_excel_sheet_name("Notes", used),
                index=False,
            )
            wrote = True

        if not wrote:
            pd.DataFrame({"note": ["No tables were available to export."]}).to_excel(
                writer,
                sheet_name="Empty",
                index=False,
            )

    return buffer.getvalue(), notes

HEATMAP_DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
HEATMAP_DAY_NAMES = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]
HEATMAP_BLOCK_HOURS = 4
HEATMAP_BLOCK_LABELS = [
    f"{start:02d}:00-{start + HEATMAP_BLOCK_HOURS:02d}:00"
    for start in range(0, 24, HEATMAP_BLOCK_HOURS)
]
HEATMAP_MIN_COMMITS = 20
HEATMAP_WEEKEND_DAYS = 2


def empty_heatmap_matrix():
    return pd.DataFrame(columns=["block"] + HEATMAP_DAY_LABELS)


def calculate_commit_heatmap(commits_df):
    dates = _dates_from(commits_df, "date")

    if dates.empty:
        return {}, empty_heatmap_matrix()

    day_positions = dates.dt.weekday.to_numpy()
    block_positions = (dates.dt.hour // HEATMAP_BLOCK_HOURS).to_numpy()

    counts = [
        [0] * len(HEATMAP_DAY_LABELS)
        for _ in HEATMAP_BLOCK_LABELS
    ]

    for block, day in zip(block_positions, day_positions):
        counts[int(block)][int(day)] += 1

    matrix = pd.DataFrame(counts, columns=HEATMAP_DAY_LABELS)
    matrix.insert(0, "block", HEATMAP_BLOCK_LABELS)

    total = int(len(dates))

    day_totals = [
        sum(row[day] for row in counts)
        for day in range(len(HEATMAP_DAY_LABELS))
    ]
    block_totals = [sum(row) for row in counts]

    busiest_day = day_totals.index(max(day_totals))
    busiest_block = block_totals.index(max(block_totals))

    peak_value = max(max(row) for row in counts)
    peak_block = next(
        index for index, row in enumerate(counts) if max(row) == peak_value
    )
    peak_day = counts[peak_block].index(peak_value)

    weekend_count = len(HEATMAP_DAY_LABELS) - 5
    weekday_commits = int(sum(day_totals[:5]))
    weekend_commits = int(sum(day_totals[5:]))

    weekday_per_day = weekday_commits / 5
    weekend_per_day = weekend_commits / weekend_count

    weekend_ratio = (
        weekend_per_day / weekday_per_day
        if weekday_per_day > 0
        else None
    )

    insights = {
        "total_commits": total,
        "sufficient": total >= HEATMAP_MIN_COMMITS,
        "most_active_day": HEATMAP_DAY_NAMES[busiest_day],
        "most_active_day_commits": int(day_totals[busiest_day]),
        "most_active_day_share": day_totals[busiest_day] / total * 100.0,
        "most_active_block": HEATMAP_BLOCK_LABELS[busiest_block],
        "most_active_block_commits": int(block_totals[busiest_block]),
        "most_active_block_share": block_totals[busiest_block] / total * 100.0,
        "peak_day": HEATMAP_DAY_NAMES[peak_day],
        "peak_block": HEATMAP_BLOCK_LABELS[peak_block],
        "peak_commits": int(peak_value),
        "peak_share": peak_value / total * 100.0,
        "weekday_commits": weekday_commits,
        "weekend_commits": weekend_commits,
        "weekday_share": weekday_commits / total * 100.0,
        "weekend_share": weekend_commits / total * 100.0,
        "weekday_per_day": weekday_per_day,
        "weekend_per_day": weekend_per_day,
        "weekend_ratio": weekend_ratio,
        "max_cell": int(peak_value),
    }

    return insights, matrix


HEATMAP_METHODS = [
    {
        "name": "Heatmap cells",
        "summary": "Each cell counts the commits made on one day of the week within one time block.",
        "rules": [
            ("Time basis", "Commit author dates converted to UTC. Local working hours of contributors in other time zones are therefore not reflected, and commits from different zones are mixed into the same blocks."),
            ("Time blocks", f"The day is split into {24 // HEATMAP_BLOCK_HOURS} blocks of {HEATMAP_BLOCK_HOURS} hours each, starting at 00:00 UTC."),
            ("Days", "Monday to Sunday, taken from the UTC date of each commit."),
            ("Included commits", "Every commit in the selected analysis window. Commits without a valid date are skipped."),
        ],
    },
    {
        "name": "Most active day and time block",
        "summary": "The weekday and the time block with the most commits overall.",
        "rules": [
            ("Most active day", "The weekday with the highest total across all time blocks."),
            ("Most active time block", "The time block with the highest total across all weekdays."),
            ("Peak activity period", "The single weekday and time block combination with the most commits."),
            ("Ties", "The earliest weekday or time block wins."),
        ],
    },
    {
        "name": "Weekday versus weekend",
        "summary": "How commit activity splits between Monday to Friday and Saturday and Sunday.",
        "rules": [
            ("Share", "Commits on that part of the week divided by all commits in the window."),
            ("Per day average", "Weekday commits divided by 5 and weekend commits divided by 2, so the two can be compared fairly. Weekend days make up 2 of 7 days, so a weekend share near 28.6% means activity is spread evenly across the week."),
            ("Weekend vs weekday rate", "Average commits per weekend day divided by average commits per weekday."),
        ],
    },
    {
        "name": "Small samples",
        "summary": "Patterns from few commits are easily the result of chance.",
        "rules": [
            ("Minimum", f"With fewer than {HEATMAP_MIN_COMMITS} commits the heatmap is still drawn but is flagged as a small sample."),
        ],
    },
]

HEATMAP_FOOT = (
    "The heatmap describes when commits were recorded, not when people worked or how much effort was spent. "
    "It uses the time a commit was authored, which a developer can set or rewrite."
)


COMPARISON_DEFAULT_PERIOD = "Last 6 Months"


def _compare_get(source, *path):
    value = source

    for key in path:
        if not isinstance(value, dict):
            return None

        value = value.get(key)

    return value


def _compare_license(repository):
    license_info = repository.get("license")

    if not isinstance(license_info, dict):
        return None

    spdx = license_info.get("spdx_id")

    if spdx and spdx != "NOASSERTION":
        return spdx

    return license_info.get("name")


def _compare_day(value):
    stamp = _utc_stamp(value) if value else None

    if stamp is None:
        return None

    return _iso_day(stamp)


def _compare_top_language(languages_df):
    if (
        languages_df is None
        or languages_df.empty
        or "language" not in languages_df.columns
        or "bytes" not in languages_df.columns
    ):
        return None, None

    top = languages_df.sort_values("bytes", ascending=False).iloc[0]
    share = top["percentage"] if "percentage" in languages_df.columns else None

    return str(top["language"]), None if share is None else float(share)


def _compare_health(analysis):
    health = analysis.get("health_score") or {}
    scores = {"overall": health.get("overall")}

    for component in health.get("components") or []:
        score = component["score"]
        scores[component["key"]] = None if score is None else int(round(score))

    return scores


def _compare_rows(analysis):
    repository = analysis.get("repository") or {}
    commit_metrics = analysis.get("commit_metrics") or {}
    trend = analysis.get("commit_activity_trend") or {}
    velocity = analysis.get("commit_velocity") or {}
    contributors = analysis.get("contributor_metrics") or {}
    concentration = analysis.get("contributor_concentration") or {}
    issues = analysis.get("issue_metrics") or {}
    issue_resolution = analysis.get("issue_resolution") or {}
    pulls = analysis.get("pull_request_metrics") or {}
    pull_health = analysis.get("pull_request_health") or {}
    cadence = analysis.get("release_cadence") or {}
    languages = analysis.get("languages")
    health = _compare_health(analysis)
    top_language, top_language_share = _compare_top_language(languages)

    language_count = (
        int(len(languages))
        if isinstance(languages, pd.DataFrame) and not languages.empty
        else None
    )

    has_issues = bool(issues)
    has_pulls = bool(pulls)

    return {
        "stars": repository.get("stargazers_count"),
        "forks": repository.get("forks_count"),
        "open_issues_and_prs": repository.get("open_issues_count"),
        "primary_language": repository.get("language"),
        "license": _compare_license(repository),
        "created": _compare_day(repository.get("created_at")),
        "last_push": _compare_day(repository.get("pushed_at")),
        "archived": "Yes" if repository.get("archived") else "No",
        "commits": commit_metrics.get("total_commits"),
        "commits_per_day": velocity.get("per_day"),
        "active_days": trend.get("active_days"),
        "commit_change": _compare_get(velocity, "comparison", "change_pct"),
        "contributors": contributors.get("total_contributors"),
        "top_contributor": contributors.get("top_contributor"),
        "top_share": concentration.get("top_contributor_concentration"),
        "top_3_share": concentration.get("top_3_contributor_concentration"),
        "issues_total": issues.get("total_issues") if has_issues else None,
        "issues_closed": issues.get("closed_issues") if has_issues else None,
        "issue_closure_rate": (
            issues.get("closure_rate")
            if has_issues and issues.get("total_issues")
            else None
        ),
        "issue_median_close": issue_resolution.get("median_days_to_close"),
        "pulls_total": pulls.get("total_pull_requests") if has_pulls else None,
        "pulls_merged": pulls.get("merged_pull_requests") if has_pulls else None,
        "pull_merge_rate": (
            pulls.get("merge_rate")
            if has_pulls and pulls.get("total_pull_requests")
            else None
        ),
        "pull_median_merge": pull_health.get("median_days_to_merge"),
        "releases": cadence.get("published_count"),
        "latest_release": cadence.get("latest_tag"),
        "latest_release_age": cadence.get("latest_age_days"),
        "release_interval": cadence.get("median_interval_days"),
        "release_cadence": cadence.get("cadence_label"),
        "language_count": language_count,
        "top_language": top_language,
        "top_language_share": top_language_share,
        "health_overall": health.get("overall"),
        "health_activity": health.get("activity"),
        "health_collaboration": health.get("collaboration"),
        "health_issues": health.get("issues"),
        "health_pull_requests": health.get("pull_requests"),
        "health_releases": health.get("releases"),
    }


COMPARISON_LAYOUT = [
    ("Repository", [
        ("stars", "Stars", "int", True),
        ("forks", "Forks", "int", True),
        ("open_issues_and_prs", "Open issues and PRs (GitHub count)", "int", False),
        ("primary_language", "Primary language", "text", False),
        ("license", "License", "text", False),
        ("created", "Created", "text", False),
        ("last_push", "Last push", "text", False),
        ("archived", "Archived", "text", False),
    ]),
    ("Commit activity", [
        ("commits", "Commits", "int", True),
        ("commits_per_day", "Commits per day", "rate", True),
        ("active_days", "Active days", "int", True),
        ("commit_change", "Change vs previous period", "signed_percent", False),
    ]),
    ("Contributors", [
        ("contributors", "Contributors", "int", True),
        ("top_contributor", "Top contributor", "text", False),
        ("top_share", "Top contributor share", "percent", False),
        ("top_3_share", "Top 3 contributors share", "percent", False),
    ]),
    ("Issues", [
        ("issues_total", "Issues opened", "int", True),
        ("issues_closed", "Issues closed", "int", True),
        ("issue_closure_rate", "Issue closure rate", "percent", True),
        ("issue_median_close", "Median time to close", "days", False),
    ]),
    ("Pull requests", [
        ("pulls_total", "Pull requests opened", "int", True),
        ("pulls_merged", "Pull requests merged", "int", True),
        ("pull_merge_rate", "Merge rate", "percent", True),
        ("pull_median_merge", "Median time to merge", "days", False),
    ]),
    ("Releases", [
        ("releases", "Releases published", "int", True),
        ("latest_release", "Latest release", "text", False),
        ("latest_release_age", "Latest release age", "days", False),
        ("release_interval", "Median days between releases", "days", False),
        ("release_cadence", "Release cadence", "text", False),
    ]),
    ("Languages", [
        ("language_count", "Languages detected", "int", False),
        ("top_language", "Top language", "text", False),
        ("top_language_share", "Top language share", "percent", False),
    ]),
    ("Health score", [
        ("health_overall", "Overall health score", "score", True),
        ("health_activity", "Activity", "score", True),
        ("health_collaboration", "Collaboration", "score", True),
        ("health_issues", "Issues", "score", True),
        ("health_pull_requests", "PR Health", "score", True),
        ("health_releases", "Releases", "score", True),
    ]),
]

COMPARISON_HEALTH_KEYS = [
    ("health_activity", "Activity"),
    ("health_collaboration", "Collaboration"),
    ("health_issues", "Issues"),
    ("health_pull_requests", "PR Health"),
    ("health_releases", "Releases"),
]


def _compare_is_number(value):
    if value is None or isinstance(value, bool):
        return False

    try:
        return not math.isnan(float(value))
    except (TypeError, ValueError):
        return False


def _compare_leader(value_a, value_b):
    if not (_compare_is_number(value_a) and _compare_is_number(value_b)):
        return None

    if float(value_a) > float(value_b):
        return "a"

    if float(value_b) > float(value_a):
        return "b"

    return "tie"


def build_repository_comparison(analysis_a, analysis_b):
    values_a = _compare_rows(analysis_a)
    values_b = _compare_rows(analysis_b)

    groups = []
    wins = {"a": 0, "b": 0, "tie": 0}

    for group_name, items in COMPARISON_LAYOUT:
        rows = []

        for key, label, kind, comparable in items:
            value_a = values_a.get(key)
            value_b = values_b.get(key)
            leader = _compare_leader(value_a, value_b) if comparable else None

            if leader is not None:
                wins[leader] += 1

            rows.append(
                {
                    "key": key,
                    "metric": label,
                    "kind": kind,
                    "a": value_a,
                    "b": value_b,
                    "leader": leader,
                }
            )

        groups.append({"name": group_name, "rows": rows})

    health_chart = [
        {"name": label, "a": values_a.get(key), "b": values_b.get(key)}
        for key, label in COMPARISON_HEALTH_KEYS
    ]

    return {
        "name_a": (analysis_a.get("repository") or {}).get("full_name") or "Repository A",
        "name_b": (analysis_b.get("repository") or {}).get("full_name") or "Repository B",
        "period": analysis_a.get("period"),
        "groups": groups,
        "wins": wins,
        "compared": wins["a"] + wins["b"] + wins["tie"],
        "health_chart": health_chart,
        "values_a": values_a,
        "values_b": values_b,
    }


COMPARISON_METHODS = [
    {
        "name": "Same window for both",
        "summary": "Both repositories are analyzed with the same period and all six analyses, so figures describe the same stretch of time.",
        "rules": [
            ("Repository facts", "Stars, forks, language, license, creation date, last push and the open issue count describe the repository today and ignore the period. GitHub's open issue count includes open pull requests."),
            ("Period figures", "Commits, contributors, issues, pull requests and releases cover only the selected period. Languages are repository level."),
            ("Cached results", "A repository already analyzed with all analyses and the same period is reused from cache instead of being fetched again."),
        ],
    },
    {
        "name": "Higher value marker",
        "summary": "The higher number in a row is marked with a dot. It means higher, not better.",
        "rules": [
            ("Marked rows", "Counts, rates and health scores. Rows such as durations, shares and text are shown without a marker because higher or lower is not clearly better."),
            ("Ties and gaps", "Equal values are not marked. A row where either value is unavailable is not marked."),
            ("Higher count", "The summary counts how many marked rows each repository is higher on. Repositories of very different sizes will naturally differ on raw counts, so read the rates and health scores alongside them."),
        ],
    },
    {
        "name": "Health score",
        "summary": "The same health score used for a single repository, with the same weights and rules.",
        "rules": [
            ("Components", "Activity, Collaboration, Issues, PR Health and Releases. A component that cannot be measured is shown as N/A and left out of the overall score."),
        ],
    },
]

COMPARISON_FOOT = (
    "A comparison shows how two repositories differ on recorded activity. It does not rank their quality, "
    "and differences in size, age or workflow can explain many of the gaps."
)


TREND_STABLE_BAND = 0.15
TREND_MIN_EVENTS = 6
TREND_ARROWS = {
    "Increasing": "\u2191",
    "Stable": "\u2192",
    "Declining": "\u2193",
    "Not enough data": "\u2013",
}
TREND_SERIES = [
    ("commits", "Commits", "Commit activity", "commits", "date"),
    ("issues", "Issues", "Issue activity", "issues opened", "created_at"),
    ("pull_requests", "Pull Requests", "PR activity", "pull requests opened", "created_at"),
]
LEADERBOARD_MIN_DATA_NOTE = "Not available"


def classify_trend(earlier, later):

    earlier = int(earlier)
    later = int(later)
    total = earlier + later

    result = {
        "label": "Not enough data",
        "arrow": TREND_ARROWS["Not enough data"],
        "change": None,
        "earlier": earlier,
        "later": later,
    }

    if total < TREND_MIN_EVENTS:
        return result

    if earlier == 0:
        result["label"] = "Increasing"
        result["arrow"] = TREND_ARROWS["Increasing"]
        return result

    change = (later - earlier) / earlier
    result["change"] = change * 100.0

    if change > TREND_STABLE_BAND:
        label = "Increasing"
    elif change < -TREND_STABLE_BAND:
        label = "Declining"
    else:
        label = "Stable"

    result["label"] = label
    result["arrow"] = TREND_ARROWS[label]

    return result


def _trend_bounds(date_series, period_start, now):

    end = _utc_now(now)
    start = _utc_stamp(period_start)

    if start is None:

        starts = [series.min() for series in date_series if len(series)]

        if not starts:
            return None, end, None

        start = min(starts)

    if end <= start:
        return None, end, None

    return start, end, start + (end - start) / 2


def _half_counts(dates, start, mid, end):

    if dates is None or len(dates) == 0:
        return 0, 0

    inside = dates[(dates >= start) & (dates <= end)]

    return int((inside < mid).sum()), int((inside >= mid).sum())


def _trend_sentence(name, unit, result):

    earlier = result["earlier"]
    later = result["later"]

    if result["label"] == "Not enough data":
        return (
            f"{name}: only {earlier + later:,} {unit} in the window, "
            f"and at least {TREND_MIN_EVENTS} are needed to classify a trend."
        )

    if result["change"] is None:
        return f"{name} rose from none in the earlier half to {later:,} {unit} in the later half."

    magnitude = abs(result["change"])

    if result["label"] == "Stable":
        return (
            f"{name} was stable: {later:,} {unit} in the later half against "
            f"{earlier:,} in the earlier half ({result['change']:+.0f}%)."
        )

    verb = "increased" if result["label"] == "Increasing" else "declined"

    return (
        f"{name} {verb} {magnitude:.0f}%: {later:,} {unit} in the later half "
        f"against {earlier:,} in the earlier half."
    )


def calculate_trend_detection(
    commits_df,
    issues_df,
    pull_requests_df,
    selected_analyses,
    period_start=None,
    now=None,
):

    selected = set(selected_analyses or [])
    frames = {
        "commits": commits_df,
        "issues": issues_df,
        "pull_requests": pull_requests_df,
    }

    dates = {
        key: _dates_from(frames[key], column)
        for key, required, _, _, column in TREND_SERIES
        if required in selected
    }

    start, end, mid = _trend_bounds(list(dates.values()), period_start, now)
    rows = []

    for key, required, name, unit, _ in TREND_SERIES:

        if required not in selected:
            continue

        if start is None:
            result = classify_trend(0, 0)
        else:
            result = classify_trend(*_half_counts(dates[key], start, mid, end))

        rows.append({
            "key": key,
            "name": name,
            "unit": unit,
            "label": result["label"],
            "arrow": result["arrow"],
            "change": result["change"],
            "earlier": result["earlier"],
            "later": result["later"],
            "sentence": _trend_sentence(name, unit, result),
        })

    return {
        "rows": rows,
        "window_start": start,
        "midpoint": mid,
        "window_end": end,
    }


TREND_METHODS = [
    {
        "name": "How a trend is classified",
        "summary": "The analysis window is split into two equal halves and the same events are counted in each.",
        "rules": [
            ("Window", "The selected period, ending now. For All Time it runs from the earliest commit, issue or pull request that was fetched."),
            ("Events", "Commits are counted by commit date. Issues and pull requests are counted by the date they were opened."),
            ("Change", "Events in the later half minus events in the earlier half, divided by events in the earlier half."),
            ("Labels", f"Increasing when the change is above +{TREND_STABLE_BAND * 100:.0f}%, Declining when it is below -{TREND_STABLE_BAND * 100:.0f}%, and Stable in between."),
            ("Not enough data", f"Fewer than {TREND_MIN_EVENTS} events across both halves are not classified. If the earlier half has none, the trend is Increasing and no percentage is shown."),
        ],
    },
]

TREND_FOOT = (
    "Halves are compared on counts only, so a trend describes direction inside this window, not a forecast. "
    "A very long window can hide recent changes."
)


LEADERBOARD_METHODS = [
    {
        "name": "How the leaderboard is built",
        "summary": "Contribution counts and shares come from the contributor data. The remaining columns are measured from the fetched commits.",
        "rules": [
            ("Rank", "Position by contributions, highest first."),
            ("Share", "A contributor's contributions as a percentage of all measured contributions."),
            ("Active days", "Distinct UTC days on which the contributor has a fetched commit."),
            ("First and last", "Dates of the earliest and latest fetched commit by that contributor."),
            ("Activity trend", f"The same half-versus-half comparison used for repository trends, applied to the contributor's commits. At least {TREND_MIN_EVENTS} commits are needed."),
            ("Matching", "Commits are matched to contributors by name, ignoring case. When contributors come from GitHub's all-time list they are identified by username, so a commit author with a different display name will not match and those columns stay empty."),
        ],
    },
]

LEADERBOARD_FOOT = (
    "Commit-based columns only cover commits that were fetched for this analysis, "
    "so they can be empty when the Commits analysis was not selected."
)


def build_contributor_leaderboard(contributors_df, commits_df, period_start=None, now=None):

    if contributors_df is None or contributors_df.empty:
        return contributors_df

    board = contributors_df.copy().reset_index(drop=True)
    board.insert(0, "rank", range(1, len(board) + 1))

    commit_dates = _dates_from(commits_df, "date")
    start, end, mid = _trend_bounds([commit_dates], period_start, now)

    by_author = {}

    if (
        commits_df is not None
        and not commits_df.empty
        and "author" in commits_df.columns
        and "date" in commits_df.columns
    ):

        frame = pd.DataFrame({
            "author": commits_df["author"].fillna("Unknown").astype(str).str.casefold(),
            "date": _utc_series(commits_df["date"]),
        }).dropna(subset=["date"])

        by_author = {name: group["date"] for name, group in frame.groupby("author")}

    active_days = []
    first_dates = []
    last_dates = []
    trends = []

    for username in board["username"]:

        dates = by_author.get(str(username).casefold())

        if dates is None or dates.empty:
            active_days.append(None)
            first_dates.append(pd.NaT)
            last_dates.append(pd.NaT)
            trends.append(LEADERBOARD_MIN_DATA_NOTE)
            continue

        active_days.append(int(dates.dt.strftime("%Y-%m-%d").nunique()))
        first_dates.append(dates.min())
        last_dates.append(dates.max())

        if start is None:
            trends.append(TREND_ARROWS["Not enough data"] + " Not enough data")
            continue

        result = classify_trend(*_half_counts(dates, start, mid, end))
        trends.append(f"{result['arrow']} {result['label']}")

    board["active_days"] = pd.array(active_days, dtype="Int64")
    board["first_contribution"] = pd.to_datetime(first_dates, utc=True)
    board["last_contribution"] = pd.to_datetime(last_dates, utc=True)
    board["activity_trend"] = trends

    return board


TIMELINE_SERIES = [
    ("commits", "Commits", "Commits", "commits", "commit", "date"),
    ("issues", "Issues", "Issues", "issues opened", "issue opened", "created_at"),
    ("pull_requests", "Pull Requests", "Pull requests", "pull requests opened", "pull request opened", "created_at"),
]


def _timeline_month_counts(dates):

    if dates.empty:
        return {}

    return dates.dt.strftime("%Y-%m").value_counts().to_dict()


def _timeline_releases(releases_df):

    if releases_df is None or releases_df.empty or "published_at" not in releases_df.columns:
        return {}

    frame = releases_df.copy()
    frame["_stamp"] = _utc_series(frame["published_at"])
    frame = frame.dropna(subset=["_stamp"]).sort_values("_stamp")

    grouped = {}

    for _, item in frame.iterrows():

        prerelease = item.get("prerelease", False)
        prerelease = bool(prerelease) if pd.notna(prerelease) else False

        grouped.setdefault(item["_stamp"].strftime("%Y-%m"), []).append({
            "tag": str(item.get("tag", "Unknown")),
            "name": str(item.get("name", "")),
            "prerelease": prerelease,
            "published_at": item["_stamp"],
        })

    return grouped


def calculate_repository_timeline(
    commits_df,
    issues_df,
    pull_requests_df,
    releases_df,
    selected_analyses,
):

    selected = set(selected_analyses or [])
    frames = {
        "commits": commits_df,
        "issues": issues_df,
        "pull_requests": pull_requests_df,
    }

    series = []
    counts = {}

    for key, required, name, unit, singular, column in TIMELINE_SERIES:

        if required not in selected:
            continue

        series.append({"key": key, "name": name, "unit": unit, "singular": singular})
        counts[key] = _timeline_month_counts(_dates_from(frames[key], column))

    has_releases = "Releases" in selected
    releases = _timeline_releases(releases_df) if has_releases else {}

    months = set(releases)

    for month_counts in counts.values():
        months |= set(month_counts)

    rows = []

    for month in sorted(months):

        stamp = pd.Timestamp(f"{month}-01", tz="UTC")

        row = {
            "month": month,
            "month_start": stamp,
            "year": int(stamp.year),
            "releases": releases.get(month, []),
        }

        for item in series:
            row[item["key"]] = int(counts[item["key"]].get(month, 0))

        row["events"] = sum(row[item["key"]] for item in series)

        rows.append(row)

    table_rows = []

    for row in rows:

        entry = {"month_start": row["month_start"]}

        for item in series:
            entry[item["key"]] = row[item["key"]]

        if has_releases:
            entry["releases"] = len(row["releases"])
            entry["release_tags"] = ", ".join(release["tag"] for release in row["releases"])

        table_rows.append(entry)

    busiest = None

    if rows and series:

        top = max(rows, key=lambda row: row["events"])

        if top["events"] > 0:
            busiest = {"month_start": top["month_start"], "events": top["events"]}

    return {
        "rows": rows,
        "series": series,
        "table": pd.DataFrame(table_rows),
        "has_releases": has_releases,
        "active_months": len(rows),
        "first_month": rows[0]["month_start"] if rows else None,
        "last_month": rows[-1]["month_start"] if rows else None,
        "total_events": sum(row["events"] for row in rows),
        "release_count": sum(len(row["releases"]) for row in rows),
        "busiest": busiest,
    }


TIMELINE_METHODS = [
    {
        "name": "How the timeline is built",
        "summary": "Activity that was already fetched for the selected analyses is grouped by calendar month. No extra API requests are made.",
        "rules": [
            ("Commits", "Counted in the month of the commit date."),
            ("Issues and pull requests", "Counted in the month they were opened."),
            ("Releases", "Placed in the month they were published. Drafts without a publish date are left out, and pre-releases are marked."),
            ("Months", "Months are UTC calendar months. A month appears only when at least one selected activity happened in it."),
            ("Not selected", "An analysis that was not selected is left out of the timeline instead of being shown as zero."),
        ],
    },
]

TIMELINE_FOOT = (
    "The timeline only covers data fetched for the chosen analysis window, "
    "so months before the window or beyond fetched record limits are not shown."
)


SNAPSHOT_AREAS = [
    ("activity", "Activity", ("High", "Medium", "Low")),
    ("collaboration", "Collaboration", ("High", "Medium", "Low")),
    ("issues", "Issue Health", ("Good", "Fair", "Poor")),
    ("pull_requests", "PR Health", ("Good", "Fair", "Poor")),
    ("releases", "Maintenance", ("High", "Medium", "Low")),
]

SNAPSHOT_HIGH_SCORE = 75
SNAPSHOT_MEDIUM_SCORE = 50


def calculate_snapshot_areas(health_score):

    components = {
        item["key"]: item
        for item in ((health_score or {}).get("components") or [])
    }

    rows = []

    for key, name, words in SNAPSHOT_AREAS:

        component = components.get(key)
        score = component["score"] if component and component["available"] else None

        if score is None:
            label = "N/A"
            reason = (component or {}).get("reason") or "Not enough data to rate this area."
        else:
            reason = None
            if score >= SNAPSHOT_HIGH_SCORE:
                label = words[0]
            elif score >= SNAPSHOT_MEDIUM_SCORE:
                label = words[1]
            else:
                label = words[2]

        rows.append({
            "key": key,
            "name": name,
            "score": None if score is None else int(round(score)),
            "label": label,
            "reason": reason,
        })

    return rows


SNAPSHOT_METHODS = [
    {
        "name": "How area ratings are assigned",
        "summary": "Each rating is the score of one health-score component, turned into a word.",
        "rules": [
            ("Scores", "Activity, Collaboration, Issue Health, PR Health and Maintenance are the Activity, Collaboration, Issues, PR Health and Releases components of the repository health score. Maintenance is the Releases component."),
            ("Bands", f"A score of {SNAPSHOT_HIGH_SCORE} or more is High (Good for issues and pull requests), {SNAPSHOT_MEDIUM_SCORE} to {SNAPSHOT_HIGH_SCORE - 1} is Medium (Fair), and below {SNAPSHOT_MEDIUM_SCORE} is Low (Poor)."),
            ("Unavailable", "An area shows N/A when its analysis was not selected or the data needed to score it is missing. No value is estimated."),
        ],
    },
]

SNAPSHOT_FOOT = "The overall health score and its components are explained in the health score section."


SUMMARY_SECTIONS = [
    ("Commits", "Commits", ["commit_metrics", "commit_activity_trend", "commit_velocity", "commit_heatmap"]),
    ("Contributors", "Contributors", ["contributor_metrics", "contributor_concentration"]),
    ("Issues", "Issues", ["issue_metrics", "issue_resolution"]),
    ("Pull requests", "Pull Requests", ["pull_request_metrics", "pull_request_health"]),
    ("Releases", "Releases", ["release_metrics", "release_cadence"]),
]

SUMMARY_REPOSITORY_FIELDS = [
    ("full_name", "Repository"),
    ("stargazers_count", "Stars"),
    ("forks_count", "Forks"),
    ("open_issues_count", "Open issues and pull requests"),
    ("language", "Primary language"),
    ("created_at", "Created"),
    ("pushed_at", "Last push"),
]


def _summary_value(value):

    if isinstance(value, (list, tuple, dict, set)) or isinstance(value, pd.DataFrame):
        return None

    if isinstance(value, (pd.Timestamp, datetime)):

        stamp = _utc_stamp(value)

        return None if stamp is None else stamp.strftime("%Y-%m-%d %H:%M UTC")

    if not pd.api.types.is_scalar(value) or pd.isna(value):
        return None

    if hasattr(value, "item"):
        value = value.item()

    if isinstance(value, float):
        return round(value, 2)

    return value


def build_summary_metrics_table(analysis, selected_analyses):

    selected = set(selected_analyses or [])
    rows = []

    def add(section, metric, value):

        value = _summary_value(value)

        if value is not None:
            rows.append({"section": section, "metric": metric, "value": value})

    repository = analysis.get("repository") or {}

    for key, label in SUMMARY_REPOSITORY_FIELDS:
        add("Repository", label, repository.get(key))

    license_info = repository.get("license")
    add("Repository", "License", license_info.get("spdx_id") if isinstance(license_info, dict) else None)

    add("Analysis", "Period", analysis.get("period"))
    add("Analysis", "Window start", analysis.get("period_start"))
    add("Analysis", "Window end", analysis.get("period_end"))

    health = analysis.get("health_score") or {}
    add("Health score", "Overall score", health.get("overall"))
    add("Health score", "Overall label", health.get("label"))

    for component in health.get("components") or []:
        add("Health score", f"{component['name']} score", component.get("score"))

    for section, required, keys in SUMMARY_SECTIONS:

        if required not in selected:
            continue

        for key in keys:

            source = analysis.get(key)

            if not isinstance(source, dict):
                continue

            for name, value in source.items():
                add(section, name.replace("_", " ").strip().capitalize(), value)

    trends = analysis.get("trend_detection") or {}

    for row in trends.get("rows") or []:
        add("Trends", f"{row['name']} trend", row["label"])
        add("Trends", f"{row['name']} change in later half (%)", row["change"])

    return pd.DataFrame(rows, columns=["section", "metric", "value"])