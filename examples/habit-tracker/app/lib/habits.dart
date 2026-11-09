// bondstone: REQ-HAB-001
Future<Habit> createHabit(String name, int targetDaysPerWeek) async {
  return db.insertHabit(Habit(name: name, target: targetDaysPerWeek));
}

// bondstone: REQ-HAB-002
Future<void> logCompletion(Habit habit, DateTime day) async {
  await db.insertCompletionIfAbsent(habit.id, DateUtils.dateOnly(day));
}
