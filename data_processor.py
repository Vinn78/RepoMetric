import math
from datetime import datetime, timezone

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
        "top_3_contributor_concentration": 0.0
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