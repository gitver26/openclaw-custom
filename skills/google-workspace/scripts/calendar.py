#!/usr/bin/env python3
"""
Google Calendar API Operations

Usage:
    python3 calendar.py list --max-results 10
    python3 calendar.py create --summary "Meeting" --start "2026-03-10T14:00:00Z" --end "2026-03-10T15:00:00Z"
    python3 calendar.py update --event-id "abc123" --summary "Updated Title"
    python3 calendar.py delete --event-id "abc123"
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print(json.dumps({"success": False, "error": "Google API libraries not installed"}))
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).parent))
from google_auth import get_token_file, get_scopes


def get_calendar_service():
    """Get authenticated Calendar service."""
    token_file = get_token_file()
    if not token_file.exists():
        return None, {"success": False, "error": "Not authenticated"}
    
    try:
        creds = Credentials.from_authorized_user_file(str(token_file), get_scopes())
        if not creds.valid and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        service = build('calendar', 'v3', credentials=creds)
        return service, None
    except Exception as e:
        return None, {"success": False, "error": str(e)}


def list_events(max_results=10, start_time=None, end_time=None):
    """List calendar events."""
    service, error = get_calendar_service()
    if error:
        return error
    
    try:
        if not start_time:
            start_time = datetime.utcnow().isoformat() + 'Z'
        
        params = {
            'calendarId': 'primary',
            'timeMin': start_time,
            'maxResults': max_results,
            'singleEvents': True,
            'orderBy': 'startTime'
        }
        if end_time:
            params['timeMax'] = end_time
        
        events_result = service.events().list(**params).execute()
        events = events_result.get('items', [])
        
        return {
            "success": True,
            "events": [{
                'id': e['id'],
                'summary': e.get('summary'),
                'start': e['start'].get('dateTime', e['start'].get('date')),
                'end': e['end'].get('dateTime', e['end'].get('date')),
                'location': e.get('location'),
                'description': e.get('description'),
                'attendees': [a['email'] for a in e.get('attendees', [])]
            } for e in events],
            "count": len(events)
        }
    except HttpError as e:
        return {"success": False, "error": str(e)}


def create_event(summary, start, end, description=None, location=None, attendees=None):
    """Create calendar event."""
    service, error = get_calendar_service()
    if error:
        return error
    
    try:
        event = {
            'summary': summary,
            'start': {'dateTime': start, 'timeZone': 'UTC'},
            'end': {'dateTime': end, 'timeZone': 'UTC'},
        }
        if description:
            event['description'] = description
        if location:
            event['location'] = location
        if attendees:
            event['attendees'] = [{'email': e} for e in attendees]
        
        created = service.events().insert(calendarId='primary', body=event).execute()
        return {
            "success": True,
            "event_id": created['id'],
            "link": created.get('htmlLink')
        }
    except HttpError as e:
        return {"success": False, "error": str(e)}


def update_event(event_id, **updates):
    """Update calendar event."""
    service, error = get_calendar_service()
    if error:
        return error
    
    try:
        event = service.events().get(calendarId='primary', eventId=event_id).execute()
        if 'summary' in updates:
            event['summary'] = updates['summary']
        if 'description' in updates:
            event['description'] = updates['description']
        if 'location' in updates:
            event['location'] = updates['location']
        
        updated = service.events().update(calendarId='primary', eventId=event_id, body=event).execute()
        return {"success": True, "event_id": updated['id']}
    except HttpError as e:
        return {"success": False, "error": str(e)}


def delete_event(event_id):
    """Delete calendar event."""
    service, error = get_calendar_service()
    if error:
        return error
    
    try:
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        return {"success": True, "message": f"Event {event_id} deleted"}
    except HttpError as e:
        return {"success": False, "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Google Calendar Operations")
    subparsers = parser.add_subparsers(dest='command')
    
    list_p = subparsers.add_parser('list')
    list_p.add_argument('--max-results', type=int, default=10)
    list_p.add_argument('--start')
    list_p.add_argument('--end')
    
    create_p = subparsers.add_parser('create')
    create_p.add_argument('--summary', required=True)
    create_p.add_argument('--start', required=True)
    create_p.add_argument('--end', required=True)
    create_p.add_argument('--description')
    create_p.add_argument('--location')
    create_p.add_argument('--attendees', nargs='+')
    
    update_p = subparsers.add_parser('update')
    update_p.add_argument('--event-id', required=True)
    update_p.add_argument('--summary')
    update_p.add_argument('--description')
    update_p.add_argument('--location')
    
    delete_p = subparsers.add_parser('delete')
    delete_p.add_argument('--event-id', required=True)
    
    args = parser.parse_args()
    
    if args.command == 'list':
        result = list_events(args.max_results, args.start, args.end)
    elif args.command == 'create':
        result = create_event(args.summary, args.start, args.end, args.description, args.location, args.attendees)
    elif args.command == 'update':
        updates = {}
        if args.summary:
            updates['summary'] = args.summary
        if args.description:
            updates['description'] = args.description
        if args.location:
            updates['location'] = args.location
        result = update_event(args.event_id, **updates)
    elif args.command == 'delete':
        result = delete_event(args.event_id)
    else:
        parser.print_help()
        sys.exit(1)
    
    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get('success') else 1)


if __name__ == '__main__':
    main()
