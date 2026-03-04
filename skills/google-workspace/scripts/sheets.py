#!/usr/bin/env python3
"""
Google Sheets API Operations

Usage:
    python3 sheets.py create --title "Spreadsheet Title"
    python3 sheets.py read --sheet-id "1XYZ" --range "Sheet1!A1:D10"
    python3 sheets.py write --sheet-id "1XYZ" --range "Sheet1!A1" --values '[["Data"]]'
    python3 sheets.py append --sheet-id "1XYZ" --range "Sheet1!A:C" --values '[["Row"]]'
"""

import argparse
import json
import sys
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


def get_sheets_service():
    """Get authenticated Sheets service."""
    token_file = get_token_file()
    if not token_file.exists():
        return None, {"success": False, "error": "Not authenticated"}
    
    try:
        creds = Credentials.from_authorized_user_file(str(token_file), get_scopes())
        if not creds.valid and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        service = build('sheets', 'v4', credentials=creds)
        return service, None
    except Exception as e:
        return None, {"success": False, "error": str(e)}


def create_spreadsheet(title):
    """Create new spreadsheet."""
    service, error = get_sheets_service()
    if error:
        return error
    
    try:
        spreadsheet = {'properties': {'title': title}}
        result = service.spreadsheets().create(body=spreadsheet).execute()
        
        return {
            "success": True,
            "spreadsheet_id": result['spreadsheetId'],
            "title": result['properties']['title'],
            "url": result['spreadsheetUrl']
        }
    except HttpError as e:
        return {"success": False, "error": str(e)}


def read_values(spreadsheet_id, range_name):
    """Read values from spreadsheet."""
    service, error = get_sheets_service()
    if error:
        return error
    
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        return {
            "success": True,
            "range": result.get('range'),
            "values": values,
            "row_count": len(values),
            "column_count": len(values[0]) if values else 0
        }
    except HttpError as e:
        return {"success": False, "error": str(e)}


def write_values(spreadsheet_id, range_name, values):
    """Write values to spreadsheet."""
    service, error = get_sheets_service()
    if error:
        return error
    
    try:
        body = {'values': values}
        result = service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='RAW',
            body=body
        ).execute()
        
        return {
            "success": True,
            "updated_cells": result.get('updatedCells'),
            "updated_rows": result.get('updatedRows'),
            "updated_columns": result.get('updatedColumns')
        }
    except HttpError as e:
        return {"success": False, "error": str(e)}


def append_values(spreadsheet_id, range_name, values):
    """Append values to spreadsheet."""
    service, error = get_sheets_service()
    if error:
        return error
    
    try:
        body = {'values': values}
        result = service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='RAW',
            body=body
        ).execute()
        
        return {
            "success": True,
            "updated_range": result.get('updates', {}).get('updatedRange'),
            "updated_cells": result.get('updates', {}).get('updatedCells')
        }
    except HttpError as e:
        return {"success": False, "error": str(e)}


def clear_values(spreadsheet_id, range_name):
    """Clear values from spreadsheet."""
    service, error = get_sheets_service()
    if error:
        return error
    
    try:
        result = service.spreadsheets().values().clear(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        
        return {
            "success": True,
            "cleared_range": result.get('clearedRange')
        }
    except HttpError as e:
        return {"success": False, "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Google Sheets Operations")
    subparsers = parser.add_subparsers(dest='command')
    
    create_p = subparsers.add_parser('create')
    create_p.add_argument('--title', required=True)
    
    read_p = subparsers.add_parser('read')
    read_p.add_argument('--sheet-id', required=True)
    read_p.add_argument('--range', required=True)
    
    write_p = subparsers.add_parser('write')
    write_p.add_argument('--sheet-id', required=True)
    write_p.add_argument('--range', required=True)
    write_p.add_argument('--values', required=True, help='JSON array of arrays')
    
    append_p = subparsers.add_parser('append')
    append_p.add_argument('--sheet-id', required=True)
    append_p.add_argument('--range', required=True)
    append_p.add_argument('--values', required=True, help='JSON array of arrays')
    
    clear_p = subparsers.add_parser('clear')
    clear_p.add_argument('--sheet-id', required=True)
    clear_p.add_argument('--range', required=True)
    
    args = parser.parse_args()
    
    if args.command == 'create':
        result = create_spreadsheet(args.title)
    elif args.command == 'read':
        result = read_values(args.sheet_id, args.range)
    elif args.command == 'write':
        values = json.loads(args.values)
        result = write_values(args.sheet_id, args.range, values)
    elif args.command == 'append':
        values = json.loads(args.values)
        result = append_values(args.sheet_id, args.range, values)
    elif args.command == 'clear':
        result = clear_values(args.sheet_id, args.range)
    else:
        parser.print_help()
        sys.exit(1)
    
    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get('success') else 1)


if __name__ == '__main__':
    main()
