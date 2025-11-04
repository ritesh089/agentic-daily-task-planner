# Slack Integration Setup Guide

## Overview

This guide will help you set up Slack OAuth credentials to enable the multi-agent summarizer to fetch your Slack messages, DMs, and mentions.

## Credential Storage

Your Slack credentials are stored in `slack_credentials.json`, which is:
- ✅ **Git-ignored** (listed in `.gitignore`)
- ✅ **Local only** (never committed to GitHub)
- ✅ **Similar to Gmail setup** (follows same pattern as `credentials.json`)

## Setup Steps

### 1. Create Your Credentials File

Copy the example file:

```bash
cp slack_credentials.json.example slack_credentials.json
```

### 2. Get Your Slack User Token

You need a Slack **User Token** (starts with `xoxp-`):

#### Option A: Create a Slack App (Recommended)

1. **Go to Slack API**: https://api.slack.com/apps
2. **Click "Create New App"** → Choose "From scratch"
3. **Name your app**: e.g., "Personal Message Summarizer"
4. **Select your workspace**

5. **Add OAuth Scopes** (under "OAuth & Permissions"):
   - `channels:history` - Read public channel messages
   - `channels:read` - View basic channel info
   - `groups:history` - Read private channel messages
   - `groups:read` - View private channels
   - `im:history` - Read DM messages
   - `im:read` - View DMs
   - `mpim:history` - Read group DM messages
   - `mpim:read` - View group DMs
   - `search:read` - Search messages (for mentions)
   - `users:read` - View user info

6. **Install to Workspace**:
   - Click "Install to Workspace"
   - Authorize the permissions
   - Copy the **User OAuth Token** (starts with `xoxp-`)

7. **Add token to `slack_credentials.json`**:
   ```json
   {
     "user_token": "xoxp-your-actual-token-here",
     "channels": [
       "C01234567",
       "C98765432"
     ],
     "time_range_hours": 24
   }
   ```

#### Option B: Use Existing Token

If you already have a Slack user token from another app or integration, you can use it directly.

### 3. Get Channel IDs (Optional)

To monitor specific channels, you need their IDs:

#### Method 1: From Slack Client
1. Right-click on a channel
2. Select "View channel details"
3. Scroll to bottom - the Channel ID is shown (starts with `C`)

#### Method 2: Using Slack API
```bash
curl -H "Authorization: Bearer xoxp-your-token" \
  https://slack.com/api/conversations.list
```

Add channel IDs to your `slack_credentials.json`:
```json
{
  "user_token": "xoxp-...",
  "channels": [
    "C01234567",  // #general
    "C98765432"   // #team-updates
  ],
  "time_range_hours": 24
}
```

### 4. Configure Time Range

The `time_range_hours` setting controls how far back to fetch messages:

```json
{
  "time_range_hours": 24   // Last 24 hours (default)
  // OR
  "time_range_hours": 48   // Last 2 days
  // OR
  "time_range_hours": 168  // Last week
}
```

## What Gets Collected

The multi-agent system collects:

1. **📩 Direct Messages (DMs)**: All DMs sent to you
2. **💬 Channel Messages**: Messages from specified channels
3. **@️ Mentions**: All messages where you were @mentioned

## Security Best Practices

✅ **DO:**
- Keep `slack_credentials.json` local only
- Use tokens with minimum required scopes
- Rotate tokens periodically
- Review Slack app permissions regularly

❌ **DON'T:**
- Commit `slack_credentials.json` to git
- Share your user token
- Use tokens with admin scopes unnecessarily
- Leave unused tokens active

## Testing Your Setup

Run the multi-agent summarizer:

```bash
./run_multi_agent.sh
```

If configured correctly, you'll see:
```
✓ Slack credentials found
💬 Slack Collector: Fetching messages from last 24 hours...
✓ Collected X Slack messages
```

## Troubleshooting

### Token Not Working
```
Error: invalid_auth
```
**Solution**: Verify your token starts with `xoxp-` and has the required scopes.

### No Messages Found
```
✓ Collected 0 Slack messages
```
**Possible causes**:
- No messages in the time range
- Missing OAuth scopes
- Channel IDs are incorrect
- Token doesn't have access to specified channels

### Missing Mentions
```
Error: Mentions fetch error: missing_scope
```
**Solution**: Add the `search:read` scope to your Slack app.

## File Structure

```
wasmcloud-slack-agent/
├── slack_credentials.json.example  ← Template
├── slack_credentials.json          ← Your actual credentials (git-ignored)
├── credentials.json                ← Gmail credentials (git-ignored)
└── .gitignore                      ← Protects your credentials
```

## Support

For more help:
- [Slack API Documentation](https://api.slack.com/docs)
- [OAuth Scopes Reference](https://api.slack.com/scopes)

