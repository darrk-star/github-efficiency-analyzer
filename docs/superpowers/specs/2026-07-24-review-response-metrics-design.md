# Review Response Metrics Design

## Goal

Measure how quickly a pull request receives its first external human review, using historical GitHub review events rather than the current `requested_reviewers` snapshot.

## Review Event Collection

For every pull request included in the analysis window, the GitHub client requests the paginated REST endpoint:

```text
GET /repos/{owner}/{repo}/pulls/{pull_number}/reviews
```

Review events are translated into a compact immutable record containing the reviewer login, submitted timestamp, and review state. The existing bounded retry and API error behavior applies to review requests. Review events are not persisted in snapshots or raw report JSON.

## First Response Definition

The first review response is the earliest review event that satisfies all of these rules:

- The reviewer is not the pull request author.
- The review state is one of `APPROVED`, `CHANGES_REQUESTED`, or `COMMENTED`.
- The review has a `submitted_at` timestamp.
- The submitted timestamp is on or after the PR creation timestamp.

`PENDING` and `DISMISSED` reviews do not count. A PR with no qualifying event has no first-review response time and is counted separately as unreplied rather than being treated as a zero-hour response.

## Metrics and Outputs

`PullRequestRecord` stores an optional `first_review_at` timestamp and optional `first_reviewer` login. The pull request summary adds:

- Average first review response time in hours across PRs with a qualifying review.
- Median first review response time in hours across PRs with a qualifying review.
- Count of PRs without a qualifying external review.
- Top reviewers by count of first review responses, sorted by count descending and login ascending.

The PR CSV gains first-review timestamp, reviewer, and calculated response-hours columns. Markdown and HTML reports show the three aggregate values and the top first reviewers. Missing data renders as `N/A` or an explicit empty-state message.

## Request Cost and Scope

Review events add one paginated API family per selected PR. The current `--limit` remains the explicit upper bound for this work, and the README will describe that trade-off. This iteration does not fetch review comments, request history, team membership, or reviewer ownership.

## Demo and Compatibility

The offline fixture gains deterministic first-review values through its PR data model, so the demo remains network-free. Existing requested-reviewer exports remain as current-request context and are not relabeled as historical participation.

## Tests

Tests cover review-event pagination, author filtering, excluded states, missing timestamps, timestamps before PR creation, no-review PRs, summary calculation, stable reviewer ranking, CSV fields, report rendering, and fixture compatibility. All HTTP tests continue to use fake sessions and deterministic payloads.
