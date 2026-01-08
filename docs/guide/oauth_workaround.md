# OAuth Workaround (Unsupported)

> **WARNING**: This configuration is **unsupported** and may break at any time. It relies on reusing public Client IDs from popular open-source applications (Thunderbird, GNOME) which are trusted by Google. We strongly recommend creating your own [GCP Project](configuration.md#step-2-google-cloud-project-setup) if possible.

If you are unable to create a Google Cloud Platform project (e.g., due to organizational restrictions or verification issues), you can attempt to use the public credentials of known open-source email clients.

## OAUTH_MODE: The Key Setting

When using third-party OAuth credentials (Thunderbird, GNOME, etc.), you **must** set `oauth_mode: imap` in your config or set the `OAUTH_MODE=imap` environment variable.

### Why This Matters

Third-party OAuth credentials typically include these scopes:
- ✅ `https://mail.google.com/` - IMAP/SMTP access
- ✅ `https://www.googleapis.com/auth/calendar` - Google Calendar API

But they **do NOT include**:
- ❌ `https://www.googleapis.com/auth/gmail.readonly` - Gmail REST API
- ❌ `https://www.googleapis.com/auth/gmail.modify` - Gmail REST API

This means **Gmail REST API calls will fail** with these credentials. The `oauth_mode: imap` setting tells the server to use IMAP/SMTP protocols instead.

### Mode Comparison

| Feature | `oauth_mode: api` | `oauth_mode: imap` |
|---------|-------------------|---------------------|
| Email search | Gmail REST API | IMAP SEARCH |
| Fetch threads | Gmail REST API | IMAP FETCH |
| Send emails | Gmail REST API | SMTP with XOAUTH2 |
| Calendar | Google Calendar API | Google Calendar API |
| Labels/folders | Gmail labels | IMAP folders |
| Required scopes | gmail.readonly, gmail.modify, calendar | mail.google.com, calendar |
| Best for | Own GCP credentials | Third-party credentials |

## Known Public Credentials

These credentials belong to widely used open-source projects. They are generally whitelisted by Google for broad use.

### Mozilla Thunderbird
- **Source**: [Thunderbird Source Code](https://hg.mozilla.org/comm-central/file/tip/mailnews/base/src/OAuth2Providers.jsm)
- **Scopes**: `mail.google.com` (IMAP/SMTP), `calendar` ✅
- Search for `googlemail.com` in the source to find the Client ID and Secret

### GNOME Online Accounts
- **Source**: [GNOME GOA Source Code](https://gitlab.gnome.org/GNOME/gnome-online-accounts/-/blob/master/src/goabackend/goagoogleprovider.c)
- **Scopes**: `mail.google.com` (IMAP/SMTP), `calendar` ✅
- Search for `CLIENT_ID` in the source file

## How to Use

1. Open your `config.yaml`.
2. **Set oauth_mode to imap** (critical!):

```yaml
oauth_mode: imap

imap:
  host: imap.gmail.com
  port: 993
  username: your-email@gmail.com
  use_ssl: true
  oauth2:
    client_id: "<client_id_from_thunderbird_or_gnome_source>"
    client_secret: "<client_secret_from_source>"

timezone: America/Los_Angeles
working_hours:
  start: "09:00"
  end: "17:00"
  workdays: [1, 2, 3, 4, 5]
vip_senders: []
```

3. Run the authentication setup:
```bash
uv run auth_setup --mode imap
```

4. When authenticating, you'll see a consent screen for "Mozilla Thunderbird" or "GNOME". This is expected.

## Limitations

1. **IMAP Search Limitations**: Gmail's IMAP search is less powerful than the Gmail REST API. Complex queries like `label:important OR from:boss@example.com` may not work exactly as expected.

2. **No Gmail Labels**: In IMAP mode, you work with IMAP folders instead of Gmail labels. The `modify_gmail_labels` tool is not available.

3. **Quota Sharing**: You share the API quota with all other users of that client ID (though usually per-user quotas apply).

4. **Future Blocking**: Google may rotate these secrets or block access at any time.

## Troubleshooting

### "Gmail API scopes not available" Error
Make sure you've set `oauth_mode: imap` in your config.yaml or `OAUTH_MODE=imap` environment variable.

### "Authentication failed" During SMTP Send
Re-run `uv run auth_setup --mode imap` to refresh your tokens.

### Calendar Still Works But Email Doesn't
This confirms you're using third-party credentials. Set `oauth_mode: imap` to fix email operations.

