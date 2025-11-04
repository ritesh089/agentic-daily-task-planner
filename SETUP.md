# Setup Instructions

## Prerequisites

1. **Ollama with llama3.2**
   ```bash
   ollama pull llama3.2
   ```

2. **Python 3.13+** with virtual environment

## Credential Setup

### 1. Google Gmail API Credentials

Create `credentials.json` from Google Cloud Console:
- Go to [Google Cloud Console](https://console.cloud.google.com/)
- Create a project and enable Gmail API
- Create OAuth 2.0 credentials
- Download as `credentials.json` and place in project root

### 2. Slack API Credentials

Create `slack_credentials.json` in the project root:

```json
{
  "user_token": "xoxp-your-slack-user-token-here",
  "channels": [
    "C01234567",
    "C98765432"
  ],
  "time_range_hours": 24
}
```

**How to get your Slack User Token:**
1. Go to [Slack API](https://api.slack.com/apps)
2. Create a new app or use existing one
3. Navigate to **OAuth & Permissions**
4. Add the following **User Token Scopes**:
   - `channels:history` - View messages in public channels
   - `channels:read` - View basic channel info
   - `im:history` - View messages in DMs
   - `im:read` - View basic DM info
   - `mpim:history` - View messages in group DMs
   - `mpim:read` - View basic group DM info
   - `users:read` - View users in workspace
5. Install app to your workspace
6. Copy the **User OAuth Token** (starts with `xoxp-`)

**Finding Channel IDs:**
- Right-click on a channel → View channel details → Copy channel ID (at the bottom)
- Or use Slack API: `https://slack.com/api/conversations.list`

**Configuration:**
- `user_token`: Your Slack OAuth user token
- `channels`: List of channel IDs to monitor (optional, leave empty `[]` for DMs and mentions only)
- `time_range_hours`: How many hours back to fetch messages (default: 24)

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
./run_email_summarizer.sh
```

## Security Notes

⚠️ **Never commit credential files to Git!**

The following files are automatically ignored:
- `credentials.json`
- `slack_credentials.json`
- `token.json`

Keep these files secure and local only.

