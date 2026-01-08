# Calendar Tools

Calendar management and scheduling tools.

## check_calendar

Check calendar availability in a time range.

**Parameters:**
- `time_min` (string, required): ISO 8601 timestamp
- `time_max` (string, required): ISO 8601 timestamp

**Returns:** Array of events in range with:
- `summary`: Event title
- `start`: Start time
- `end`: End time
- `attendees`: Array of attendee emails

## suggest_reschedule

Find alternative meeting times within working hours.

**Parameters:**
- `thread_id` (string, required): Email thread with original invite
- `suggested_date` (string, required): ISO date (YYYY-MM-DD)

**Returns:** Array of 3 available time slots within configured `working_hours` and `timezone`.

## list_calendar_events

List calendar events in date range.

**Parameters:**
- `start_date` (string, required): ISO date
- `end_date` (string, required): ISO date

**Returns:** Array of events

## More Tools

See full tool list in the [README](https://github.com/johnneerdael/Google-Workspace-Secretary-MCP#-available-tools).
