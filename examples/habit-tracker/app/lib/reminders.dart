// bondstone: REQ-REM-001, REQ-REM-002
Future<void> rescheduleReminder(Habit habit) async {
  if (await db.isLoggedToday(habit.id)) return cancel(habit.id);
  final at = medianCompletionTime(habit, days: 14).add(const Duration(minutes: 15));
  await notifications.schedule(habit.id, at);
}
