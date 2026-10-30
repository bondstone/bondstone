---
type: capability
id: HABIT
title: Habits
description: Creating habits, checking in and streaks.
status: stable
retired: []
---

# Habits

### HABIT-1 Check in
Release: V-1.0

The app shall record one check-in per habit per day.

- HABIT-1.1: GIVEN a habit with no check-in today WHEN the person taps it THEN today is marked kept.
- HABIT-1.2: GIVEN a habit kept today WHEN the person taps it again THEN today is unmarked.

### HABIT-2 Streak
Release: V-1.0

The app shall show the number of consecutive days with a check-in, ending today or yesterday.

- HABIT-2.1: GIVEN check-ins on the last three days WHEN the list opens THEN the streak shows 3.

### HABIT-3 Reminder time
Release: V-1.1

The app shall remind the person at a time they pick.

- HABIT-3: WHEN the reminder time comes and today is not kept THEN a notification appears.
