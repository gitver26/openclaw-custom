#!/usr/bin/env python3
"""
Gmail API Operations

Handles email operations: list, search, get, send, modify, delete.

Usage:
    python3 gmail.py list --max-results 10
    python3 gmail.py search --query "from:example@gmail.com"
    python3 gmail.py get --message-id "18d8f123456"
    python3 gmail.py send --to "user@example.com" --subject "Test" --body "Hello"
    python3 gmail.py modify --message-id "18d8f123456" --add-labels "IMPORTANT"
"""

import argparse
import base64
import json
import mimetypes
import os
import sys
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print(json.dumps({
        "success": False,
        "error": "Google API libraries not installed",
        "action": "Run: pip3 install google-auth google-auth-oauthlib google-api-python-client"
    }))
    sys.exit(1)

# Import shared auth module
sys.path.insert(0, str(Path(__file__).parent))
from google_auth import get_token_file, get_scopes


def get_gmail_service():
    """Get authenticated Gmail service."""
    token_file = get_token_file()
    
    if not token_file.exists():
        return None, {
            "success": False,
            "error": "Not authenticated",
            "action": "Run: python3 scripts/google_auth.py --auth"
        }
    
    try:
        scopes = get_scopes()
        creds = Credentials.from_authorized_user_file(str(token_file), scopes)
        
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                return None, {
                    "success": False,
                    "error": "Token invalid",
                    "action": "Re-authenticate: python3 scripts/google_auth.py --auth"
                }
        
        service = build('gmail', 'v1', credentials=creds)
        return service, None
    except Exception as e:
        return None, {
            "success": False,
            "error": str(e),
            "error_type": "AuthError"
        }


def list_messages(max_results=10, label_ids=None, query=None):
    """List messages in mailbox."""
    service, error = get_gmail_service()
    if error:
        return error
    
    try:
        params = {'userId': 'me', 'maxResults': max_results}
        if label_ids:
            params['labelIds'] = label_ids
        if query:
            params['q'] = query
        
        results = service.users().messages().list(**params).execute()
        messages = results.get('messages', [])
        
        # Get basic info for each message
        message_list = []
        for msg in messages:
            try:
                full_msg = service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='metadata',
                    metadataHeaders=['From', 'Subject', 'Date']
                ).execute()
                
                headers = {}
                for header in full_msg.get('payload', {}).get('headers', []):
                    headers[header['name']] = header['value']
                
                message_list.append({
                    'id': msg['id'],
                    'threadId': full_msg.get('threadId'),
                    'from': headers.get('From'),
                    'subject': headers.get('Subject'),
                    'date': headers.get('Date'),
                    'snippet': full_msg.get('snippet'),
                    'labels': full_msg.get('labelIds', [])
                })
            except Exception as e:
                print(f"Warning: Could not fetch message {msg['id']}: {e}", file=sys.stderr)
        
        return {
            "success": True,
            "messages": message_list,
            "count": len(message_list),
            "resultSizeEstimate": results.get('resultSizeEstimate', 0)
        }
    
    except HttpError as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": "ApiError"
        }


def get_message(message_id, format='full'):
    """Get full message details."""
    service, error = get_gmail_service()
    if error:
        return error
    
    try:
        message = service.users().messages().get(
            userId='me',
            id=message_id,
            format=format
        ).execute()
        
        # Parse headers
        headers = {}
        for header in message.get('payload', {}).get('headers', []):
            headers[header['name']] = header['value']
        
        # Extract body
        body = ""
        if format == 'full':
            payload = message.get('payload', {})
            if 'body' in payload and payload['body'].get('data'):
                body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
            elif 'parts' in payload:
                for part in payload['parts']:
                    if part.get('mimeType') == 'text/plain':
                        if part.get('body', {}).get('data'):
                            body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                            break
                    elif part.get('mimeType') == 'text/html' and not body:
                        if part.get('body', {}).get('data'):
                            body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
        
        return {
            "success": True,
            "message": {
                'id': message['id'],
                'threadId': message.get('threadId'),
                'from': headers.get('From'),
                'to': headers.get('To'),
                'subject': headers.get('Subject'),
                'date': headers.get('Date'),
                'body': body,
                'snippet': message.get('snippet'),
                'labels': message.get('labelIds', []),
                'headers': headers
            }
        }
    
    except HttpError as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": "ApiError"
        }


def create_message(to, subject, body, attachments=None):
    """Create email message with optional attachments."""
    message = MIMEMultipart() if attachments else MIMEText(body)
    
    if not attachments:
        message = MIMEText(body)
    else:
        message = MIMEMultipart()
        message.attach(MIMEText(body, 'plain'))
    
    message['to'] = to
    message['subject'] = subject
    
    # Add attachments
    if attachments:
        for filepath in attachments:
            path = Path(filepath)
            if not path.exists():
                continue
            
            content_type, encoding = mimetypes.guess_type(filepath)
            if content_type is None or encoding is not None:
                content_type = 'application/octet-stream'
            
            main_type, sub_type = content_type.split('/', 1)
            
            with open(filepath, 'rb') as f:
                if main_type == 'text':
                    msg = MIMEText(f.read().decode('utf-8'), _subtype=sub_type)
                elif main_type == 'image':
                    msg = MIMEImage(f.read(), _subtype=sub_type)
                elif main_type == 'audio':
                    msg = MIMEAudio(f.read(), _subtype=sub_type)
                else:
                    msg = MIMEBase(main_type, sub_type)
                    msg.set_payload(f.read())
                
                msg.add_header('Content-Disposition', 'attachment', filename=path.name)
                message.attach(msg)
    
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
    return {'raw': raw}


def send_message(to, subject, body, attachments=None):
    """Send email message."""
    service, error = get_gmail_service()
    if error:
        return error
    
    try:
        message = create_message(to, subject, body, attachments)
        sent_message = service.users().messages().send(
            userId='me',
            body=message
        ).execute()
        
        return {
            "success": True,
            "message_id": sent_message['id'],
            "thread_id": sent_message.get('threadId')
        }
    
    except HttpError as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": "ApiError"
        }


def modify_message(message_id, add_labels=None, remove_labels=None):
    """Modify message labels."""
    service, error = get_gmail_service()
    if error:
        return error
    
    try:
        body = {}
        if add_labels:
            body['addLabelIds'] = add_labels if isinstance(add_labels, list) else [add_labels]
        if remove_labels:
            body['removeLabelIds'] = remove_labels if isinstance(remove_labels, list) else [remove_labels]
        
        message = service.users().messages().modify(
            userId='me',
            id=message_id,
            body=body
        ).execute()
        
        return {
            "success": True,
            "message_id": message['id'],
            "labels": message.get('labelIds', [])
        }
    
    except HttpError as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": "ApiError"
        }


def delete_message(message_id):
    """Delete message."""
    service, error = get_gmail_service()
    if error:
        return error
    
    try:
        service.users().messages().delete(userId='me', id=message_id).execute()
        
        return {
            "success": True,
            "message": f"Message {message_id} deleted"
        }
    
    except HttpError as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": "ApiError"
        }


def main():
    parser = argparse.ArgumentParser(description="Gmail API Operations")
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List messages')
    list_parser.add_argument('--max-results', type=int, default=10)
    list_parser.add_argument('--label-ids', nargs='+')
    list_parser.add_argument('--query', type=str)
    
    # Search command (alias for list with query)
    search_parser = subparsers.add_parser('search', help='Search messages')
    search_parser.add_argument('--query', type=str, required=True)
    search_parser.add_argument('--max-results', type=int, default=10)
    
    # Get command
    get_parser = subparsers.add_parser('get', help='Get message details')
    get_parser.add_argument('--message-id', required=True)
    get_parser.add_argument('--format', choices=['minimal', 'full', 'raw', 'metadata'], default='full')
    
    # Send command
    send_parser = subparsers.add_parser('send', help='Send email')
    send_parser.add_argument('--to', required=True)
    send_parser.add_argument('--subject', required=True)
    send_parser.add_argument('--body', required=True)
    send_parser.add_argument('--attachments', nargs='+')
    
    # Modify command
    modify_parser = subparsers.add_parser('modify', help='Modify message labels')
    modify_parser.add_argument('--message-id', required=True)
    modify_parser.add_argument('--add-labels', nargs='+')
    modify_parser.add_argument('--remove-labels', nargs='+')
    
    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete message')
    delete_parser.add_argument('--message-id', required=True)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == 'list':
        result = list_messages(
            max_results=args.max_results,
            label_ids=args.label_ids,
            query=args.query
        )
    elif args.command == 'search':
        result = list_messages(
            max_results=args.max_results,
            query=args.query
        )
    elif args.command == 'get':
        result = get_message(args.message_id, args.format)
    elif args.command == 'send':
        result = send_message(args.to, args.subject, args.body, args.attachments)
    elif args.command == 'modify':
        result = modify_message(args.message_id, args.add_labels, args.remove_labels)
    elif args.command == 'delete':
        result = delete_message(args.message_id)
    else:
        result = {"success": False, "error": f"Unknown command: {args.command}"}
    
    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get('success', False) else 1)


if __name__ == '__main__':
    main()
