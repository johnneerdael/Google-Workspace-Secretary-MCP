# Email Tools

Email and search tools for reading, searching, and managing emails.

## get_unread_messages

Fetch recent unread emails with basic metadata.

**Parameters:**
- `limit` (number, optional): Max emails to return (default: 20)

**Returns:**
Array of email objects with:
- `uid`: Unique message ID
- `subject`: Email subject
- `from`: Sender email
- `date`: Date string
- `snippet`: First 700 chars of body

**Example:**
```json
{
  "uid": "12345",
  "subject": "Meeting tomorrow",
  "from": "boss@company.com",
  "date": "2026-01-08T14:30:00Z",
  "snippet": "Hi, can we meet tomorrow at 2 PM to..."
}
```

## search_emails

Search emails using keywords or advanced criteria.

**Parameters:**
- `keyword` (string, optional): Text to search for
- `from` (string, optional): Sender email filter
- `subject` (string, optional): Subject filter
- `since_date` (string, optional): ISO date (YYYY-MM-DD)
- `limit` (number, optional): Max results (default: 50)

**Returns:** Array of matching emails (same format as `get_unread_messages`)

## get_email_details

Get full email content including attachments metadata.

**Parameters:**
- `message_id` (string, required): Email UID

**Returns:**
- `subject`, `from`, `to`, `cc`, `bcc`, `date`
- `body`: Full email body
- `attachments`: Array of `{filename, size, content_type, attachment_id}`

## get_thread

Retrieve entire conversation thread.

**Parameters:**
- `thread_id` (string, required): Gmail thread ID

**Returns:** Array of all messages in thread (chronological order)

## More Tools

See full tool list in the [README](https://github.com/johnneerdael/Google-Workspace-Secretary-MCP#-available-tools).
