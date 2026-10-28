# 0001. Record decisions as ADRs

- Status: Accepted
- Date: 2026-10-28
- Spec sections: —

## Context

The spec is the source of truth, but it leaves implementation choices open and
has a few internal ambiguities (see `docs/plan.md` → Open questions). Those
choices need a durable record that later PRs can point to.

## Decision

Keep lightweight ADRs in `docs/decisions/`, numbered, one per significant choice,
using `0000-template.md`. Answers to spec ambiguities that change behaviour are
recorded as ADRs too.

## Consequences

Reviewers can see why the code looks the way it does; reversing a decision means
writing a new ADR that supersedes the old one.
