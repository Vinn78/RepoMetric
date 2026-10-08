import contextvars
import copy
import os
import threading
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import pandas as pd
import requests
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv

from data_processor import (
    commits_to_dataframe,
    issues_to_dataframe,
    pull_requests_to_dataframe,
    languages_to_dataframe,
    releases_to_dataframe,
    contributors_to_dataframe,
    calculate_commit_metrics,
    calculate_commit_activity_trend,
    calculate_monthly_commit_activity,
    calculate_issue_metrics,
    calculate_pull_request_metrics,
    calculate_contributor_metrics,
    calculate_contributor_concentration,
    calculate_release_metrics,
    calculate_health_score,
    calculate_commit_velocity,
    calculate_issue_resolution,
    calculate_pull_request_health,
    calculate_release_cadence,
)

                                                              
                           
                                                              

load_dotenv()

GITHUB_API_URL = "https://api.github.com"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

PER_PAGE = 100

                                   
                                                             
                                                
INTERNAL_MAX_RECORDS = None


                                                              
                
                                                              

PERIOD_OPTIONS = [
    "Last 30 Days",
    "Last 3 Months",
    "Last 6 Months",
    "Last 1 Year",
    "Last 2 Years",
    "All Time",
]


def get_period_dates(period):
    """Return timezone-aware UTC start/end dates for a period."""

    now = datetime.now(timezone.utc)

    if period == "Last 30 Days":
        since = now - relativedelta(days=30)
    elif period == "Last 3 Months":
        since = now - relativedelta(months=3)
    elif period == "Last 6 Months":
        since = now - relativedelta(months=6)
    elif period == "Last 1 Year":
        since = now - relativedelta(years=1)
    elif period == "Last 2 Years":
        since = now - relativedelta(years=2)
    elif period == "All Time":
        return None, None
    else:
        raise ValueError(
            f"Invalid period '{period}'. "
            f"Choose one of: {', '.join(PERIOD_OPTIONS)}"
        )

    return since, now


def datetime_to_github_string(value):
    """Convert a datetime to the ISO format accepted by GitHub."""

    if value is None:
        return None

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


ANALYSIS_CACHE_TTL_SECONDS = 900
ANALYSIS_CACHE_MAX_ENTRIES = 32
RATE_LIMIT_LOW_SHARE = 0.10

STAGE_LABELS = {
    "repository": "Repository details",
    "commits": "Commits",
    "prior_commits": "Previous period commits",
    "contributors": "Contributors",
    "issues": "Issues",
    "pull_requests": "Pull requests",
    "languages": "Languages",
    "releases": "Releases",
    "metrics": "Calculating metrics",
}

RATE_LIMIT_METHODS = [
    {
        "name": "Where the numbers come from",
        "summary": "Every figure is read from the X-RateLimit headers GitHub returns with each response. No extra requests are made to measure it.",
        "rules": [
            ("Limit and remaining", "The most recent values reported by GitHub for each bucket. When several requests run at once, the one with the lowest remaining count for the same reset window is kept."),
            ("Buckets", "REST requests count against the core bucket and GraphQL requests against the graphql bucket. They are separate allowances."),
            ("Reset", "The time, in UTC, at which GitHub restores the full allowance for that bucket."),
            ("Requests this run", "A count of the HTTP requests this analysis sent, including retries. A result served from the cache sends none."),
        ],
    },
    {
        "name": "Warning level",
        "summary": f"The indicator turns into a warning when less than {RATE_LIMIT_LOW_SHARE * 100:.0f}% of a bucket's allowance remains.",
        "rules": [
            ("Authentication", "Without a GITHUB_TOKEN GitHub applies a much lower limit per IP address. Add a token to raise it."),
            ("Missing headers", "If GitHub did not report a value, the card says so instead of estimating it."),
        ],
    },
]

RATE_LIMIT_FOOT = (
    "Rate-limit values describe the state of GitHub's allowance when the last request finished. "
    "Other tools using the same token or IP address also consume it."
)


class GitHubError(Exception):

    def __init__(self, message, status=None, reset_epoch=None, retry_after=None):
        super().__init__(message)
        self.status = status
        self.reset_epoch = reset_epoch
        self.retry_after = retry_after


class RateLimitError(GitHubError):

    def __init__(self, message, secondary=False, **kwargs):
        super().__init__(message, **kwargs)
        self.secondary = secondary


class NotFoundError(GitHubError):
    pass


class AccessDeniedError(GitHubError):
    pass


class AuthError(GitHubError):
    pass


class NetworkError(GitHubError):
    pass


class ServerError(GitHubError):
    pass


class GraphQLError(GitHubError):
    pass


_RUN = contextvars.ContextVar("repometric_run", default=None)
_STAGE = contextvars.ContextVar("repometric_stage", default=None)


def _to_int(value):

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


class RunTracker:

    def __init__(self):
        self._lock = threading.Lock()
        self._stages = {}
        self._order = []
        self._requests = 0
        self._buckets = {}
        self._started = time.monotonic()
        self._finished = None

    def plan(self, names):

        with self._lock:
            for name in names:
                if name not in self._stages:
                    self._stages[name] = {
                        "name": name,
                        "label": STAGE_LABELS.get(name, name),
                        "status": "pending",
                        "pages": 0,
                        "records": 0,
                        "started": None,
                        "finished": None,
                    }
                    self._order.append(name)

    def stage_start(self, name):

        with self._lock:
            stage = self._stages.get(name)
            if stage is None:
                return
            stage["status"] = "running"
            stage["started"] = time.monotonic()

    def stage_page(self, name, records):

        with self._lock:
            stage = self._stages.get(name)
            if stage is None:
                return
            stage["pages"] += 1
            stage["records"] += int(records)

    def stage_finish(self, name, ok):

        with self._lock:
            stage = self._stages.get(name)
            if stage is None:
                return
            stage["status"] = "done" if ok else "failed"
            stage["finished"] = time.monotonic()

    def record_request(self):

        with self._lock:
            self._requests += 1

    def record_response(self, headers, default_resource):

        limit = _to_int(headers.get("X-RateLimit-Limit"))
        remaining = _to_int(headers.get("X-RateLimit-Remaining"))
        reset = _to_int(headers.get("X-RateLimit-Reset"))

        if limit is None and remaining is None and reset is None:
            return

        resource = headers.get("X-RateLimit-Resource") or default_resource

        with self._lock:
            current = self._buckets.get(resource)

            if current is not None and current["reset"] is not None and reset is not None:
                if reset < current["reset"]:
                    return
                if (
                    reset == current["reset"]
                    and remaining is not None
                    and current["remaining"] is not None
                    and remaining > current["remaining"]
                ):
                    return

            self._buckets[resource] = {
                "limit": limit,
                "remaining": remaining,
                "reset": reset,
            }

    def finish(self):

        with self._lock:
            if self._finished is None:
                self._finished = time.monotonic()

    def snapshot(self):

        with self._lock:
            now = time.monotonic()
            stages = []

            for name in self._order:
                stage = dict(self._stages[name])
                started = stage["started"]
                finished = stage["finished"]
                if started is None:
                    stage["elapsed"] = None
                else:
                    stage["elapsed"] = (finished if finished is not None else now) - started
                stages.append(stage)

            return {
                "stages": stages,
                "requests": self._requests,
                "elapsed": (self._finished if self._finished is not None else now) - self._started,
                "done": sum(1 for stage in stages if stage["status"] in ("done", "failed")),
                "total": len(stages),
            }

    def rate_limit(self):

        with self._lock:
            return {
                "authenticated": bool(GITHUB_TOKEN),
                "requests": self._requests,
                "buckets": {name: dict(values) for name, values in self._buckets.items()},
                "low_share": RATE_LIMIT_LOW_SHARE,
                "from_cache": False,
            }


def _stage_start(name):

    run = _RUN.get()

    if run is not None:
        run.stage_start(name)


def _stage_finish(name, ok):

    run = _RUN.get()

    if run is not None:
        run.stage_finish(name, ok)


def _stage_page(records):

    run = _RUN.get()
    stage = _STAGE.get()

    if run is not None and stage is not None:
        run.stage_page(stage, records)


_CACHE_LOCK = threading.Lock()
_TTL_CACHE = {}
_RESULT_CACHE = OrderedDict()
_MISSING = object()


def _ttl_load(key, loader):

    with _CACHE_LOCK:
        entry = _TTL_CACHE.get(key)

        if entry is not None and time.monotonic() - entry[0] < ANALYSIS_CACHE_TTL_SECONDS:
            return entry[1]

    value = loader()

    with _CACHE_LOCK:
        _TTL_CACHE[key] = (time.monotonic(), value)

    return value


def _ttl_forget(owner, repo):

    owner_key = str(owner).lower()
    repo_key = str(repo).lower()

    with _CACHE_LOCK:
        for key in [k for k in _TTL_CACHE if k[1:3] == (owner_key, repo_key)]:
            _TTL_CACHE.pop(key, None)


def _clone_result(result):

    cloned = {}

    for name, value in result.items():
        if isinstance(value, pd.DataFrame):
            cloned[name] = value.copy(deep=False)
        else:
            cloned[name] = copy.deepcopy(value)

    return cloned


def _result_cache_get(key):

    with _CACHE_LOCK:
        entry = _RESULT_CACHE.get(key)

        if entry is None:
            return None

        stored_at, result = entry

        if time.monotonic() - stored_at >= ANALYSIS_CACHE_TTL_SECONDS:
            _RESULT_CACHE.pop(key, None)
            return None

        _RESULT_CACHE.move_to_end(key)

    cloned = _clone_result(result)
    cloned["from_cache"] = True
    cloned["cache_age_seconds"] = time.monotonic() - stored_at
    cloned["rate_limit"] = dict(cloned["rate_limit"], requests=0, from_cache=True)

    return cloned


def _result_cache_put(key, result):

    with _CACHE_LOCK:
        _RESULT_CACHE[key] = (time.monotonic(), _clone_result(result))
        _RESULT_CACHE.move_to_end(key)

        while len(_RESULT_CACHE) > ANALYSIS_CACHE_MAX_ENTRIES:
            _RESULT_CACHE.popitem(last=False)


def clear_analysis_cache():

    with _CACHE_LOCK:
        _TTL_CACHE.clear()
        _RESULT_CACHE.clear()


                                                              
                    
                                                              

HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

if GITHUB_TOKEN:
    HEADERS["Authorization"] = f"Bearer {GITHUB_TOKEN}"


                                                              
                             
                                                              

def _error_text(response):

    try:
        return response.text
    except Exception:
        return ""


def _raise_for_rest_status(response, label):

    status = response.status_code
    headers = response.headers
    remaining = headers.get("X-RateLimit-Remaining")
    reset_epoch = _to_int(headers.get("X-RateLimit-Reset"))
    retry_after = _to_int(headers.get("Retry-After"))
    text = _error_text(response)
    lowered = text.lower()

    if status in (403, 429):

        if remaining == "0":
            raise RateLimitError(
                "GitHub API rate limit reached. "
                f"Rate limit reset timestamp: {reset_epoch}. "
                "Please try again after the limit resets.",
                status=status,
                reset_epoch=reset_epoch,
                retry_after=retry_after,
            )

        if (
            status == 429
            or retry_after is not None
            or "secondary rate limit" in lowered
            or "abuse" in lowered
            or "rate limit" in lowered
        ):
            raise RateLimitError(
                "GitHub API secondary rate limit reached. "
                "Too many requests were sent in a short time. "
                + (
                    f"Retry after {retry_after} seconds."
                    if retry_after is not None
                    else "Please wait a minute and try again."
                ),
                status=status,
                reset_epoch=reset_epoch,
                retry_after=retry_after,
                secondary=True,
            )

    if status == 401:
        raise AuthError(
            f"{label}: {status} - {text}",
            status=status,
        )

    if status == 403:
        raise AccessDeniedError(
            f"{label}: {status} - {text}",
            status=status,
        )

    if status == 404:
        raise NotFoundError(
            f"{label}: {status} - {text}",
            status=status,
        )

    if status >= 500:
        raise ServerError(
            f"{label}: {status} - {text}",
            status=status,
        )

    raise GitHubError(
        f"{label}: {status} - {text}",
        status=status,
    )


def _graphql_error_for(errors, response):

    reset_epoch = _to_int(response.headers.get("X-RateLimit-Reset"))
    retry_after = _to_int(response.headers.get("Retry-After"))
    types = {
        str(item.get("type") or "").upper()
        for item in errors
        if isinstance(item, dict)
    }
    message = "GitHub GraphQL API error: " + str(errors)

    if "RATE_LIMITED" in types:
        return RateLimitError(
            "GitHub API rate limit reached. "
            f"Rate limit reset timestamp: {reset_epoch}. "
            "Please try again after the limit resets.",
            status=200,
            reset_epoch=reset_epoch,
            retry_after=retry_after,
        )

    if "NOT_FOUND" in types:
        return NotFoundError(message, status=200)

    return GraphQLError(message, status=200)


def github_get(url, params=None):
    """Perform one authenticated GitHub REST API request with retry handling."""

    last_error = None
    run = _RUN.get()

    for attempt in range(3):
        if run is not None:
            run.record_request()
        try:
            response = requests.get(
                url,
                params=params,
                headers=HEADERS,
                timeout=30,
            )
            break
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as exc:
            last_error = exc
            if attempt == 2:
                raise NetworkError(
                    "GitHub API connection failed after 3 attempts: "
                    f"{exc}"
                ) from exc

    if last_error is not None and "response" not in locals():
        raise NetworkError(
            "GitHub API connection failed: "
            f"{last_error}"
        ) from last_error

    if run is not None:
        run.record_response(response.headers, "core")

    if response.status_code != 200:
        _raise_for_rest_status(response, "GitHub API error")

    return response.json()


                                                              
                                 
                                                              

def github_graphql(query, variables=None):
    """Perform an authenticated GitHub GraphQL API request with retry handling."""

    last_error = None
    run = _RUN.get()

    for attempt in range(3):
        if run is not None:
            run.record_request()
        try:
            response = requests.post(
                "https://api.github.com/graphql",
                json={
                    "query": query,
                    "variables": variables or {},
                },
                headers=HEADERS,
                timeout=30,
            )
            break
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as exc:
            last_error = exc
            if attempt == 2:
                raise NetworkError(
                    "GitHub GraphQL connection failed after 3 attempts: "
                    f"{exc}"
                ) from exc

    if last_error is not None and "response" not in locals():
        raise NetworkError(
            "GitHub GraphQL connection failed: "
            f"{last_error}"
        ) from last_error

    if run is not None:
        run.record_response(response.headers, "graphql")

    if response.status_code != 200:
        _raise_for_rest_status(response, "GitHub GraphQL API error")

    payload = response.json()

    if payload.get("errors"):
        raise _graphql_error_for(payload["errors"], response)

    return payload.get("data", {})


                                                              
                  
                                                              

def github_get_all(
    url,
    params=None,
    per_page=PER_PAGE,
    max_records=None,
    stop_when_older_than=None,
    date_fields=None,
):
    """
    Fetch paginated GitHub results.

    When stop_when_older_than is supplied, the endpoint should be
    sorted newest-first. Pagination stops as soon as an item is
    older than the requested period.
    """

    if params is None:
        params = {}

    if date_fields is None:
        date_fields = []

    all_data = []
    page = 1
    page_size = min(per_page, 100)

    while max_records is None or len(all_data) < max_records:
        page_params = params.copy()
        page_params["per_page"] = page_size
        page_params["page"] = page

        data = github_get(url, page_params)

        _stage_page(len(data) if data else 0)

        if not data:
            break

        stop_pagination = False

        for item in data:
            item_date = None

            if stop_when_older_than is not None:
                for field in date_fields:
                    raw_value = item.get(field)

                    if not raw_value:
                        continue

                    parsed = pd.to_datetime(
                        raw_value,
                        utc=True,
                        errors="coerce",
                    )

                    if pd.notna(parsed):
                        item_date = parsed
                        break

                if (
                    item_date is not None
                    and item_date < pd.Timestamp(
                        stop_when_older_than
                    )
                ):
                    stop_pagination = True
                    break

            all_data.append(item)

            if max_records is not None and len(all_data) >= max_records:
                break

        if stop_pagination:
            break

        if len(data) < page_size:
            break

        page += 1

    return all_data


                                                              
                
                                                              

def get_repository(owner, repo):
    url = (
        f"{GITHUB_API_URL}/repos/"
        f"{owner}/{repo}"
    )

    return _ttl_load(
        ("repository", str(owner).lower(), str(repo).lower()),
        lambda: github_get(url),
    )


                                                              
             
                                                              

def get_commits(
    owner,
    repo,
    since=None,
    until=None,
    per_page=PER_PAGE,
    max_records=None,
):
    url = (
        f"{GITHUB_API_URL}/repos/"
        f"{owner}/{repo}/commits"
    )

    params = {}

    if since is not None:
        params["since"] = datetime_to_github_string(since)

    if until is not None:
        params["until"] = datetime_to_github_string(until)

    return github_get_all(
        url,
        params=params,
        per_page=per_page,
        max_records=max_records,
    )


                                                              
                  
                                                              

def get_contributors(
    owner,
    repo,
    per_page=PER_PAGE,
    max_records=None,
):
    url = (
        f"{GITHUB_API_URL}/repos/"
        f"{owner}/{repo}/contributors"
    )

    return github_get_all(
        url,
        per_page=per_page,
        max_records=max_records,
    )


                                                              
            
                                                              

def get_issues(
    owner,
    repo,
    state="all",
    since=None,
    per_page=PER_PAGE,
    max_records=None,
):
    """
    Fetch repository issues using GraphQL cursor pagination.

    GitHub can reject REST page-based pagination for very large issue
    datasets with HTTP 422. GraphQL cursor pagination avoids that
    limitation and also returns actual issues without pull requests.
    """

    if state == "open":
        states = ["OPEN"]
    elif state == "closed":
        states = ["CLOSED"]
    else:
        states = ["OPEN", "CLOSED"]

    query = """
    query(
        $owner: String!,
        $repo: String!,
        $first: Int!,
        $after: String,
        $states: [IssueState!]!
    ) {
        repository(owner: $owner, name: $repo) {
            issues(
                first: $first,
                after: $after,
                states: $states,
                orderBy: {field: CREATED_AT, direction: DESC}
            ) {
                nodes {
                    number
                    title
                    state
                    author {
                        login
                    }
                    createdAt
                    closedAt
                    comments {
                        totalCount
                    }
                }
                pageInfo {
                    hasNextPage
                    endCursor
                }
            }
        }
    }
    """

    results = []
    cursor = None
    page_size = min(per_page, 100)

    while max_records is None or len(results) < max_records:
        data = github_graphql(
            query,
            {
                "owner": owner,
                "repo": repo,
                "first": page_size,
                "after": cursor,
                "states": states,
            },
        )

        repository = data.get("repository")

        if repository is None:
            raise Exception(
                f"GitHub GraphQL could not find repository "
                f"'{owner}/{repo}'."
            )

        connection = repository.get("issues") or {}
        nodes = connection.get("nodes") or []

        _stage_page(len(nodes))

        stop_pagination = False

        for item in nodes:
            if not item:
                continue

            created_at = item.get("createdAt")

            if since is not None and created_at:
                parsed = pd.to_datetime(
                    created_at,
                    utc=True,
                    errors="coerce",
                )

                if (
                    pd.notna(parsed)
                    and parsed < pd.Timestamp(since)
                ):
                    stop_pagination = True
                    break

                                                                  
                                    
            results.append(
                {
                    "number": item.get("number"),
                    "title": item.get("title"),
                    "state": (item.get("state") or "").lower(),
                    "user": item.get("author"),
                    "created_at": item.get("createdAt"),
                    "closed_at": item.get("closedAt"),
                    "comments": (
                        (item.get("comments") or {})
                        .get("totalCount", 0)
                    ),
                }
            )

            if max_records is not None and len(results) >= max_records:
                break

        if stop_pagination:
            break

        page_info = connection.get("pageInfo") or {}

        if not page_info.get("hasNextPage"):
            break

        next_cursor = page_info.get("endCursor")

        if not next_cursor or next_cursor == cursor:
            break

        cursor = next_cursor

    return results


                                                              
                   
                                                              

def get_pull_requests(
    owner,
    repo,
    state="all",
    since=None,
    per_page=PER_PAGE,
    max_records=None,
):
    url = (
        f"{GITHUB_API_URL}/repos/"
        f"{owner}/{repo}/pulls"
    )

    params = {
        "state": state,
        "sort": "created",
        "direction": "desc",
    }

    return github_get_all(
        url,
        params=params,
        per_page=per_page,
        max_records=max_records,
        stop_when_older_than=since,
        date_fields=["created_at"],
    )


                                                              
               
                                                              

def get_languages(owner, repo):
    url = (
        f"{GITHUB_API_URL}/repos/"
        f"{owner}/{repo}/languages"
    )

    return _ttl_load(
        ("languages", str(owner).lower(), str(repo).lower()),
        lambda: github_get(url),
    )


                                                              
              
                                                              

def get_releases(
    owner,
    repo,
    since=None,
    per_page=PER_PAGE,
    max_records=None,
):
    url = (
        f"{GITHUB_API_URL}/repos/"
        f"{owner}/{repo}/releases"
    )

    return github_get_all(
        url,
        per_page=per_page,
        max_records=max_records,
        stop_when_older_than=since,
        date_fields=["published_at", "created_at"],
    )


                                                              
                          
                                                              

def filter_dataframe_by_date(
    df,
    date_column,
    since=None,
    until=None,
):
    """Filter a DataFrame between two UTC datetime boundaries."""

    if df.empty:
        return df

    if since is None and until is None:
        return df

    if date_column not in df.columns:
        return df

    filtered_df = df.copy()

    dates = pd.to_datetime(
        filtered_df[date_column],
        utc=True,
        errors="coerce",
    )

    mask = dates.notna()

    if since is not None:
        mask &= dates >= pd.Timestamp(since)

    if until is not None:
        mask &= dates <= pd.Timestamp(until)

    return filtered_df.loc[mask].reset_index(drop=True)


def filter_issues_by_period(
    issues_df,
    since=None,
    until=None,
):
    return filter_dataframe_by_date(
        issues_df,
        "created_at",
        since,
        until,
    )


def filter_pull_requests_by_period(
    pull_requests_df,
    since=None,
    until=None,
):
    return filter_dataframe_by_date(
        pull_requests_df,
        "created_at",
        since,
        until,
    )


def filter_releases_by_period(
    releases_df,
    since=None,
    until=None,
):
    return filter_dataframe_by_date(
        releases_df,
        "published_at",
        since,
        until,
    )


                                                              
                               
                                                              

def commits_to_contributors(commits_df):
    """
    Build contributor records from commits.

    The GitHub contributors endpoint gives overall contribution
    history. For a selected period, contributors are therefore
    calculated from commits inside that period.
    """

    if commits_df.empty:
        return []

    if "author" not in commits_df.columns:
        return []

    counts = (
        commits_df["author"]
        .fillna("Unknown")
        .replace("", "Unknown")
        .value_counts()
    )

    return [
        {
            "login": str(username),
            "contributions": int(contributions),
        }
        for username, contributions in counts.items()
    ]


                                                              
                      
                                                              

def empty_dataframe():
    return pd.DataFrame()


def empty_metric_dict():
    return {}


                                                              
                        
                                                              

def _staged(name, task):

    def runner():
        _stage_start(name)
        token = _STAGE.set(name)

        try:
            value = task()
        except Exception:
            _stage_finish(name, False)
            raise
        finally:
            _STAGE.reset(token)

        _stage_finish(name, value is not None)

        return value

    return runner


def fetch_selected_datasets(
    owner,
    repo,
    commits_required=False,
    contributors_required=False,
    issues_required=False,
    pull_requests_required=False,
    languages_required=False,
    releases_required=False,
    since=None,
    until=None,
    prior_commits_required=False,
    prior_since=None,
):
    """
    Fetch independent GitHub datasets concurrently.

    All-time analysis can require many paginated API requests. Running
    the independent resources concurrently prevents one large dataset
    from making the whole dashboard appear frozen while another resource
    is being fetched.
    """

    tasks = {}

    if commits_required:
        tasks["commits"] = lambda: get_commits(
            owner, repo, since=since, until=until
        )

    if prior_commits_required:

        def fetch_prior_commits():
            try:
                return get_commits(
                    owner, repo, since=prior_since, until=since
                )
            except Exception:
                return None

        tasks["prior_commits"] = fetch_prior_commits

    if contributors_required:
        tasks["contributors"] = lambda: get_contributors(
            owner, repo
        )

    if issues_required:
        tasks["issues"] = lambda: get_issues(
            owner, repo, since=since
        )

    if pull_requests_required:
        tasks["pull_requests"] = lambda: get_pull_requests(
            owner, repo, since=since
        )

    if languages_required:
        tasks["languages"] = lambda: get_languages(owner, repo)

    if releases_required:
        tasks["releases"] = lambda: get_releases(
            owner, repo, since=since
        )

    results = {
        "commits": [],
        "prior_commits": [],
        "contributors": [],
        "issues": [],
        "pull_requests": [],
        "languages": {},
        "releases": [],
    }

    if not tasks:
        return results

                                                               
                                                                   
                                                      
    with ThreadPoolExecutor(max_workers=min(6, len(tasks))) as executor:
        future_map = {
            executor.submit(
                contextvars.copy_context().run,
                _staged(name, task),
            ): name
            for name, task in tasks.items()
        }

        try:
            for future in as_completed(future_map):
                name = future_map[future]
                results[name] = future.result()
        except Exception:
                                                                     
                                                                   
            for future in future_map:
                future.cancel()
            raise

    return results


                                                              
                              
                                                              

def _analyze_uncached(
    owner,
    repo,
    selected_analyses=None,
    period="All Time",
):
    """
    Fetch and analyze only the datasets selected by the user.

    Repository information is always fetched.

    Period handling:
    - Commits: GitHub API since/until filtering.
    - Contributors: period contributors derived from commits.
    - Issues: newest-first pagination + period filtering.
    - Pull Requests: newest-first pagination + early stopping.
    - Releases: newest-first pagination + early stopping.
    - Languages: repository-level distribution.
    """

    if selected_analyses is None:
        selected_analyses = [
            "Commits",
            "Contributors",
            "Issues",
            "Pull Requests",
            "Languages",
            "Releases",
        ]

    selected_analyses = list(
        dict.fromkeys(selected_analyses)
    )

    valid_analyses = {
        "Commits",
        "Contributors",
        "Issues",
        "Pull Requests",
        "Languages",
        "Releases",
    }

    invalid = [
        item
        for item in selected_analyses
        if item not in valid_analyses
    ]

    if invalid:
        raise ValueError(
            "Invalid analysis selection: "
            + ", ".join(invalid)
        )

    if period not in PERIOD_OPTIONS:
        raise ValueError(
            f"Invalid period '{period}'. "
            f"Choose one of: {', '.join(PERIOD_OPTIONS)}"
        )

    since, until = get_period_dates(period)

                                             
    run = _RUN.get()

    if run is not None:
        run.plan(["repository"])

    _stage_start("repository")

    try:
        repository = get_repository(owner, repo)
    except Exception:
        _stage_finish("repository", False)
        raise

    _stage_finish("repository", True)

                                                              
                                          
                                                              

    commits_required = (
        "Commits" in selected_analyses
        or (
            "Contributors" in selected_analyses
            and period != "All Time"
        )
    )

    contributors_required = (
        "Contributors" in selected_analyses
        and period == "All Time"
    )

    issues_required = "Issues" in selected_analyses

    pull_requests_required = (
        "Pull Requests" in selected_analyses
    )

    languages_required = (
        "Languages" in selected_analyses
    )

    releases_required = "Releases" in selected_analyses

    prior_commits_required = (
        "Commits" in selected_analyses
        and since is not None
    )

    prior_since = (
        since - (until - since)
        if prior_commits_required
        else None
    )

                                                              
                                           
                                                              

    if run is not None:
        planned = []

        for flag, name in (
            (commits_required, "commits"),
            (prior_commits_required, "prior_commits"),
            (contributors_required, "contributors"),
            (issues_required, "issues"),
            (pull_requests_required, "pull_requests"),
            (languages_required, "languages"),
            (releases_required, "releases"),
        ):
            if flag:
                planned.append(name)

        planned.append("metrics")
        run.plan(planned)

    datasets = fetch_selected_datasets(
        owner,
        repo,
        commits_required=commits_required,
        contributors_required=contributors_required,
        issues_required=issues_required,
        pull_requests_required=pull_requests_required,
        languages_required=languages_required,
        releases_required=releases_required,
        since=since,
        until=until,
        prior_commits_required=prior_commits_required,
        prior_since=prior_since,
    )

    _stage_start("metrics")

    commits = datasets["commits"]
    prior_commits = datasets["prior_commits"]
    contributors = datasets["contributors"]
    issues = datasets["issues"]
    pull_requests = datasets["pull_requests"]
    languages = datasets["languages"]
    releases = datasets["releases"]

                                                              
                                            
                                                              

    commits_df = (
        commits_to_dataframe(commits)
        if commits_required
        else empty_dataframe()
    )

    if (
        "Contributors" in selected_analyses
        and period != "All Time"
    ):
        contributors_df = contributors_to_dataframe(
            commits_to_contributors(commits_df)
        )

    elif contributors_required:
        contributors_df = contributors_to_dataframe(
            contributors
        )

    else:
        contributors_df = empty_dataframe()

    issues_df = (
        issues_to_dataframe(issues)
        if issues_required
        else empty_dataframe()
    )

    pull_requests_df = (
        pull_requests_to_dataframe(pull_requests)
        if pull_requests_required
        else empty_dataframe()
    )

    languages_df = (
        languages_to_dataframe(languages)
        if languages_required
        else empty_dataframe()
    )

    releases_df = (
        releases_to_dataframe(releases)
        if releases_required
        else empty_dataframe()
    )

                                                              
                                            
                                                              

    if "Commits" in selected_analyses:
        commits_df = filter_dataframe_by_date(
            commits_df,
            "date",
            since,
            until,
        )

    if issues_required:
        issues_df = filter_issues_by_period(
            issues_df,
            since,
            until,
        )

    if pull_requests_required:
        pull_requests_df = filter_pull_requests_by_period(
            pull_requests_df,
            since,
            until,
        )

    if releases_required:
        releases_df = filter_releases_by_period(
            releases_df,
            since,
            until,
        )

                                                              
                                                  
                                                              

    if "Commits" in selected_analyses:
        commit_metrics = calculate_commit_metrics(
            commits_df
        )
        commit_activity_trend = (
            calculate_commit_activity_trend(
                commits_df
            )
        )
        commit_monthly_metrics, commit_monthly_trend = (
            calculate_monthly_commit_activity(
                commits_df
            )
        )
    else:
        commit_metrics = empty_metric_dict()
        commit_activity_trend = empty_metric_dict()
        commit_monthly_metrics = empty_metric_dict()
        commit_monthly_trend = empty_dataframe()

    if "Contributors" in selected_analyses:
        contributor_metrics = (
            calculate_contributor_metrics(
                contributors_df
            )
        )
        contributor_concentration = (
            calculate_contributor_concentration(
                contributors_df
            )
        )
    else:
        contributor_metrics = empty_metric_dict()
        contributor_concentration = empty_metric_dict()

    if "Issues" in selected_analyses:
        issue_metrics = calculate_issue_metrics(
            issues_df
        )
    else:
        issue_metrics = empty_metric_dict()

    if "Pull Requests" in selected_analyses:
        pull_request_metrics = (
            calculate_pull_request_metrics(
                pull_requests_df
            )
        )
    else:
        pull_request_metrics = empty_metric_dict()

    if "Releases" in selected_analyses:
        release_metrics = calculate_release_metrics(
            releases_df
        )
    else:
        release_metrics = empty_metric_dict()

    if "Commits" in selected_analyses:
        commit_velocity, commit_velocity_weekly = (
            calculate_commit_velocity(
                commits_df,
                (
                    commits_to_dataframe(prior_commits)
                    if prior_commits
                    else empty_dataframe()
                ),
                since,
                until,
                repository.get("created_at"),
                prior_fetch_ok=prior_commits is not None,
            )
        )
    else:
        commit_velocity = empty_metric_dict()
        commit_velocity_weekly = empty_dataframe()

    if "Issues" in selected_analyses:
        issue_resolution, issue_aging, issue_monthly = (
            calculate_issue_resolution(
                issues_df,
                until,
            )
        )
    else:
        issue_resolution = empty_metric_dict()
        issue_aging = empty_dataframe()
        issue_monthly = empty_dataframe()

    if "Pull Requests" in selected_analyses:
        pull_request_health, pull_request_aging, pull_request_monthly = (
            calculate_pull_request_health(
                pull_requests_df,
                until,
            )
        )
    else:
        pull_request_health = empty_metric_dict()
        pull_request_aging = empty_dataframe()
        pull_request_monthly = empty_dataframe()

    if "Releases" in selected_analyses:
        release_cadence, release_intervals = (
            calculate_release_cadence(
                releases_df,
                until,
            )
        )
    else:
        release_cadence = empty_metric_dict()
        release_intervals = empty_dataframe()

    health_score = calculate_health_score(
        commits_df,
        contributors_df,
        issues_df,
        pull_requests_df,
        releases_df,
        selected_analyses,
        period_start=since,
        now=until,
    )

    _stage_finish("metrics", True)

    return {
        "repository": repository,

        "period": period,
        "period_start": since,
        "period_end": until,

        "commits": commits_df,
        "contributors": contributors_df,
        "issues": issues_df,
        "pull_requests": pull_requests_df,
        "languages": languages_df,
        "releases": releases_df,

        "commit_metrics": commit_metrics,
        "commit_activity_trend": commit_activity_trend,
        "commit_monthly_metrics": commit_monthly_metrics,
        "commit_monthly_trend": commit_monthly_trend,

        "contributor_metrics": contributor_metrics,
        "contributor_concentration": contributor_concentration,

        "issue_metrics": issue_metrics,

        "pull_request_metrics": pull_request_metrics,

        "release_metrics": release_metrics,

        "commit_velocity": commit_velocity,
        "commit_velocity_weekly": commit_velocity_weekly,

        "issue_resolution": issue_resolution,
        "issue_aging": issue_aging,
        "issue_monthly": issue_monthly,

        "pull_request_health": pull_request_health,
        "pull_request_aging": pull_request_aging,
        "pull_request_monthly": pull_request_monthly,

        "release_cadence": release_cadence,
        "release_intervals": release_intervals,

        "health_score": health_score,
    }


def analyze_repository(
    owner,
    repo,
    selected_analyses=None,
    period="All Time",
    force_refresh=False,
    progress=None,
):
    if selected_analyses is None:
        selected = [
            "Commits",
            "Contributors",
            "Issues",
            "Pull Requests",
            "Languages",
            "Releases",
        ]
    else:
        selected = list(dict.fromkeys(selected_analyses))

    key = (
        str(owner).lower(),
        str(repo).lower(),
        tuple(sorted(str(item) for item in selected)),
        period,
        bool(GITHUB_TOKEN),
    )

    if force_refresh:
        with _CACHE_LOCK:
            _RESULT_CACHE.pop(key, None)
        _ttl_forget(owner, repo)
    else:
        cached = _result_cache_get(key)

        if cached is not None:
            return cached

    run = progress if progress is not None else RunTracker()
    token = _RUN.set(run)

    try:
        result = _analyze_uncached(
            owner,
            repo,
            selected_analyses=selected,
            period=period,
        )
    finally:
        _RUN.reset(token)
        run.finish()

    result["rate_limit"] = run.rate_limit()
    result["fetched_at"] = datetime.now(timezone.utc)
    result["from_cache"] = False
    result["cache_age_seconds"] = 0.0

    _result_cache_put(key, result)

    return _clone_result(result)


                                                              
             
                                                              

if __name__ == "__main__":

    owner = "pandas-dev"
    repo = "pandas"

                                       
    test_period = "Last 30 Days"

    print("=" * 60)
    print("RepoMetric - Repository Analysis Test")
    print("=" * 60)

    if GITHUB_TOKEN:
        print("\nGitHub authentication: ENABLED")
    else:
        print("\nGitHub authentication: NOT CONFIGURED")

    print(f"\nTest period: {test_period}")
    print("\nFetching repository data...")

    analysis = analyze_repository(
        owner,
        repo,
        selected_analyses=[
            "Commits",
            "Contributors",
            "Issues",
            "Pull Requests",
            "Languages",
            "Releases",
        ],
        period=test_period,
    )

    repository = analysis["repository"]

    print("\nRepository:")
    print(f"Name: {repository['full_name']}")
    print(f"Stars: {repository['stargazers_count']}")
    print(f"Forks: {repository['forks_count']}")
    print(f"Open Issues: {repository['open_issues_count']}")
    print(f"Language: {repository['language']}")

    print("\nPeriod:")
    print(f"Selected: {analysis['period']}")
    print(f"Start: {analysis['period_start']}")
    print(f"End: {analysis['period_end']}")

    print("\nRecord Counts:")
    print(f"Commits: {len(analysis['commits'])}")
    print(f"Contributors: {len(analysis['contributors'])}")
    print(f"Issues: {len(analysis['issues'])}")
    print(f"Pull Requests: {len(analysis['pull_requests'])}")
    print(f"Releases: {len(analysis['releases'])}")

    print("\nCommit Metrics:")
    print(analysis["commit_metrics"])

    print("\nCommit Activity Trend:")
    print(analysis["commit_activity_trend"])

    print("\nContributor Metrics:")
    print(analysis["contributor_metrics"])

    print("\nContributor Concentration:")
    print(analysis["contributor_concentration"])

    print("\nIssue Metrics:")
    print(analysis["issue_metrics"])

    print("\nPull Request Metrics:")
    print(analysis["pull_request_metrics"])

    print("\nRelease Metrics:")
    print(analysis["release_metrics"])

    print("\nLanguages:")
    print(analysis["languages"].head())

    print("\nReleases:")
    print(analysis["releases"].head())

    print("\n" + "=" * 60)
    print("Analysis completed successfully.")
    print("=" * 60)