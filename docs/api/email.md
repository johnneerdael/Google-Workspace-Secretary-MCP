# Email Tools

Email and search tools for reading, searching, and managing emails.

::: tip OAUTH_MODE Affects Email Tools
The backend implementation varies based on your `oauth_mode` setting:
- **`api` mode** (default): Uses Gmail REST API for all operations
- **`imap` mode**: Uses IMAP/SMTP protocols (for third-party OAuth credentials)

Tool names and parameters remain identical—only the underlying implementation differs.
:::

## gmail_search

Search emails using Gmail query syntax (API mode) or IMAP search (IMAP mode).

**Parameters:**
- `query` (string, required): Search query
  - API mode: Full Gmail query syntax (`from:boss@company.com has:attachment`)
  - IMAP mode: Converted to IMAP SEARCH (basic keywords, from, subject, date)
- `max_results` (number, optional): Max results (default: 50)

**Returns:** Array of email objects with `id`, `thread_id`, `subject`, `from`, `date`, `snippet`

**Example:**
```json
{
  "id": "msg_12345",
  "thread_id": "thread_abc",
  "subject": "Q1 Budget Review",
  "from": "boss@company.com",
  "date": "2026-01-08T14:30:00Z",
  "snippet": "Please review the attached budget..."
}
```

::: warning IMAP Mode Limitations
In IMAP mode, complex Gmail queries like `label:important OR category:updates` are simplified. Basic `from:`, `subject:`, `after:`, `before:` work reliably.
:::

## gmail_get_thread

Retrieve entire conversation thread.

**Parameters:**
- `thread_id` (string, required): Thread ID from search results

**Returns:** 
- `thread_id`: Thread identifier
- `messages`: Array of all messages in thread (chronological)
- Each message includes: `id`, `from`, `to`, `cc`, `subject`, `date`, `body`, `attachments`

## send_email

Send an email message.

**Parameters:**
- `to` (string, required): Recipient email
- `subject` (string, required): Email subject
- `body` (string, required): Email body (plain text or HTML)
- `cc` (string, optional): CC recipients
- `bcc` (string, optional): BCC recipients
- `reply_to_message_id` (string, optional): Message ID for threading

**Backend:**
- API mode: Gmail REST API `messages.send`
- IMAP mode: SMTP with OAuth2 XOAUTH2 authentication

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

## search_emails (Legacy)

::: warning Deprecated
Use `gmail_search` instead. This tool uses IMAP search directly and may be removed in future versions.
:::

Search emails using keywords or advanced criteria.

**Parameters:**
- `keyword` (string, optional): Text to search for
- `from` (string, optional): Sender email filter
- `subject` (string, optional): Subject filter
- `since_date` (string, optional): ISO date (YYYY-MM-DD)
- `limit` (number, optional): Max results (default: 50)

## get_email_details

Get full email content including attachments metadata.

**Parameters:**
- `message_id` (string, required): Email UID

**Returns:**
- `subject`, `from`, `to`, `cc`, `bcc`, `date`
- `body`: Full email body
- `attachments`: Array of `{filename, size, content_type, attachment_id}`

## summarize_thread

Get a token-efficient summary of an email thread.

**Parameters:**
- `thread_id` (string, required): Thread ID

**Returns:** Summarized thread with truncated messages for AI context efficiency.

## More Tools

See full tool list in the [README](https://github.com/johnneerdael/Google-Workspace-Secretary-MCP#-available-tools).
