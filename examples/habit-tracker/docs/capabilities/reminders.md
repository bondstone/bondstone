---
id: CAP-reminders
title: Habit reminders
status: active
owner: dawid
code: REM
depends_on: [CAP-habits]
constrained_by: [ADR-002, ADR-003]
---
## Purpose

Remind users to log a habit around the time they usually complete it.

## Requirements

### REQ-REM-001: Remind at the usual time

The app SHALL schedule a reminder 15 minutes after the median completion time of the last 14 days.

#### Scenario: Habit usually done at 7:30

- Given completions at about 07:30 on the last 14 days
- When reminders are rescheduled
- Then a reminder is scheduled for 07:45

### REQ-REM-002: Skip reminders for completed habits

The app MUST NOT send a reminder for a habit already logged today.

#### Scenario: Already logged

- Given "Read 10 pages" was logged at 07:10
- When 07:45 arrives
- Then no reminder is shown
