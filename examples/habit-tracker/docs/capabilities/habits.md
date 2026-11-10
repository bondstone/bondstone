---
id: CAP-habits
type: capability:Capability
title: Habit tracking
status: active
owner: dawid
code: HAB
constrained_by: [ADR-002]
---
## Purpose

Users create habits and log when they complete them.

## Requirements

### REQ-HAB-001: Create a habit

The app SHALL let a user create a habit with a name and a target number of days per week.

#### Scenario: Create a daily habit

- Given the habit list is empty
- When the user creates "Read 10 pages" with target 7
- Then the habit appears in the list with a 0-day streak

### REQ-HAB-002: Log a completion

The app SHALL record at most one completion per habit per day, offline.

#### Scenario: Log twice on the same day

- Given "Read 10 pages" was logged today
- When the user taps it again
- Then no second completion is recorded
