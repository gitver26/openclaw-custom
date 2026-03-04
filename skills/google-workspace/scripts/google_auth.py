#!/usr/bin/env python3
"""
Google OAuth2 Authentication Handler

This script manages OAuth2 authentication for Google Workspace APIs.
It handles initial authentication, token refresh, and credential validation.

Usage:
    python3 google_auth.py --auth              # Initial authentication (opens browser)
    python3 google_auth.py --check             # Check token status
    python3 google_auth.py --revoke            # Revoke current token
    python3 google_auth.py --scopes            # List current scopes
"""

import argparse
import json
import os
import sys
from pathlib import Path

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print(json.dumps({
        "success": False,
        "error": "Google API libraries not installed",
        "error_type": "DependencyError",
        "action": "Run: pip3 install google-auth google-auth-oauthlib google-api-python-client"
    }))
    sys.exit(1)

# Default scopes (can be customized)
DEFAULT_SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/spreadsheets',
]

# Read-only scopes alternative
READONLY_SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/documents.readonly',
    'https://www.googleapis.com/auth/spreadsheets.readonly',
]


def get_credentials_dir():
    """Get credentials directory path."""
    cred_dir = os.environ.get('GOOGLE_WORKSPACE_CREDS_DIR')
    if cred_dir:
        return Path(cred_dir)
    
    # Default to ~/.openclaw/google-workspace
    return Path.home() / '.openclaw' / 'google-workspace'


def get_credentials_file():
    """Get path to credentials.json file."""
    cred_dir = get_credentials_dir()
    
    # Check environment variable
    env_creds = os.environ.get('GOOGLE_OAUTH_CREDENTIALS_FILE')
    if env_creds:
        return Path(env_creds)
    
    # Check default location
    creds_file = cred_dir / 'credentials.json'
    if creds_file.exists():
        return creds_file
    
    return None


def get_token_file():
    """Get path to token.json file."""
    cred_dir = get_credentials_dir()
    return cred_dir / 'token.json'


def get_scopes(readonly=False):
    """Get OAuth scopes from environment or defaults."""
    env_scopes = os.environ.get('GOOGLE_OAUTH_SCOPES')
    if env_scopes:
        return [s.strip() for s in env_scopes.split(',') if s.strip()]
    
    return READONLY_SCOPES if readonly else DEFAULT_SCOPES


def authenticate(scopes=None, readonly=False):
    """
    Perform OAuth2 authentication flow.
    
    Returns:
        Credentials object or None if failed
    """
    if scopes is None:
        scopes = get_scopes(readonly=readonly)
    
    credentials_file = get_credentials_file()
    if not credentials_file:
        return {
            "success": False,
            "error": "credentials.json not found",
            "error_type": "ConfigError",
            "action": "Download OAuth credentials from Google Cloud Console and save to ~/.openclaw/google-workspace/credentials.json"
        }
    
    token_file = get_token_file()
    creds = None
    
    # Check if token exists and is valid
    if token_file.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_file), scopes)
        except Exception as e:
            print(f"Warning: Could not load existing token: {e}", file=sys.stderr)
    
    # If no valid credentials, run OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Token refresh failed: {e}", file=sys.stderr)
                creds = None
        
        if not creds:
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(credentials_file), scopes
                )
                creds = flow.run_local_server(port=0)
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "error_type": "AuthError",
                    "action": "Check credentials.json is valid and run authentication flow"
                }
        
        # Save token
        token_file.parent.mkdir(parents=True, exist_ok=True)
        with open(token_file, 'w') as f:
            f.write(creds.to_json())
        
        # Secure permissions
        os.chmod(token_file, 0o600)
    
    return {
        "success": True,
        "token_file": str(token_file),
        "scopes": creds.scopes if hasattr(creds, 'scopes') else scopes,
        "expiry": creds.expiry.isoformat() if creds.expiry else None
    }


def check_token_status():
    """Check if token exists and is valid."""
    token_file = get_token_file()
    
    if not token_file.exists():
        return {
            "success": False,
            "error": "No token found",
            "token_exists": False,
            "action": "Run authentication: python3 scripts/google_auth.py --auth"
        }
    
    try:
        scopes = get_scopes()
        creds = Credentials.from_authorized_user_file(str(token_file), scopes)
        
        return {
            "success": True,
            "token_exists": True,
            "token_valid": creds.valid,
            "token_expired": creds.expired if hasattr(creds, 'expired') else False,
            "has_refresh_token": bool(creds.refresh_token),
            "scopes": creds.scopes if hasattr(creds, 'scopes') else None,
            "expiry": creds.expiry.isoformat() if creds.expiry else None,
            "token_file": str(token_file)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": "TokenError",
            "token_exists": True,
            "token_valid": False,
            "action": "Re-authenticate: python3 scripts/google_auth.py --auth"
        }


def revoke_token():
    """Revoke current token."""
    token_file = get_token_file()
    
    if not token_file.exists():
        return {
            "success": False,
            "error": "No token to revoke",
            "action": "Token file does not exist"
        }
    
    try:
        # Delete token file
        token_file.unlink()
        return {
            "success": True,
            "message": "Token revoked successfully",
            "action": "Token file deleted. Re-authenticate to regain access."
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": "FileError"
        }


def list_scopes():
    """List available and current scopes."""
    token_file = get_token_file()
    
    current_scopes = None
    if token_file.exists():
        try:
            scopes = get_scopes()
            creds = Credentials.from_authorized_user_file(str(token_file), scopes)
            current_scopes = creds.scopes if hasattr(creds, 'scopes') else None
        except Exception:
            pass
    
    return {
        "success": True,
        "default_scopes": DEFAULT_SCOPES,
        "readonly_scopes": READONLY_SCOPES,
        "current_scopes": current_scopes,
        "env_override": os.environ.get('GOOGLE_OAUTH_SCOPES'),
        "note": "Set GOOGLE_OAUTH_SCOPES environment variable to customize"
    }


def main():
    parser = argparse.ArgumentParser(
        description="Google OAuth2 Authentication Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--auth',
        action='store_true',
        help='Run OAuth2 authentication flow (opens browser)'
    )
    
    parser.add_argument(
        '--check',
        action='store_true',
        help='Check token status'
    )
    
    parser.add_argument(
        '--revoke',
        action='store_true',
        help='Revoke current token'
    )
    
    parser.add_argument(
        '--scopes',
        action='store_true',
        help='List available and current OAuth scopes'
    )
    
    parser.add_argument(
        '--readonly',
        action='store_true',
        help='Use read-only scopes for authentication'
    )
    
    args = parser.parse_args()
    
    if args.auth:
        result = authenticate(readonly=args.readonly)
    elif args.check:
        result = check_token_status()
    elif args.revoke:
        result = revoke_token()
    elif args.scopes:
        result = list_scopes()
    else:
        parser.print_help()
        sys.exit(1)
    
    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get('success', False) else 1)


if __name__ == '__main__':
    main()
