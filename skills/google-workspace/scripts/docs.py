#!/usr/bin/env python3
"""
Google Docs API Operations

Usage:
    python3 docs.py create --title "Document Title" --content "Content here"
    python3 docs.py read --doc-id "1ABC-def_GHI"
    python3 docs.py append --doc-id "1ABC-def_GHI" --content "More content"
    python3 docs.py export --doc-id "1ABC-def_GHI" --format pdf --output file.pdf
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


def get_docs_service():
    """Get authenticated Docs service."""
    token_file = get_token_file()
    if not token_file.exists():
        return None, None, {"success": False, "error": "Not authenticated"}
    
    try:
        creds = Credentials.from_authorized_user_file(str(token_file), get_scopes())
        if not creds.valid and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        docs_service = build('docs', 'v1', credentials=creds)
        drive_service = build('drive', 'v3', credentials=creds)
        return docs_service, drive_service, None
    except Exception as e:
        return None, None, {"success": False, "error": str(e)}


def create_document(title, content=None):
    """Create new document."""
    docs_service, _, error = get_docs_service()
    if error:
        return error
    
    try:
        doc = docs_service.documents().create(body={'title': title}).execute()
        doc_id = doc['documentId']
        
        if content:
            requests = [{'insertText': {'location': {'index': 1}, 'text': content}}]
            docs_service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
        
        return {
            "success": True,
            "doc_id": doc_id,
            "title": doc['title'],
            "url": f"https://docs.google.com/document/d/{doc_id}"
        }
    except HttpError as e:
        return {"success": False, "error": str(e)}


def read_document(doc_id):
    """Read document content."""
    docs_service, _, error = get_docs_service()
    if error:
        return error
    
    try:
        doc = docs_service.documents().get(documentId=doc_id).execute()
        content = doc.get('body', {}).get('content', [])
        
        text = ""
        for element in content:
            if 'paragraph' in element:
                for text_run in element['paragraph'].get('elements', []):
                    if 'textRun' in text_run:
                        text += text_run['textRun'].get('content', '')
        
        return {
            "success": True,
            "doc_id": doc_id,
            "title": doc['title'],
            "content": text
        }
    except HttpError as e:
        return {"success": False, "error": str(e)}


def append_to_document(doc_id, content):
    """Append content to document."""
    docs_service, _, error = get_docs_service()
    if error:
        return error
    
    try:
        doc = docs_service.documents().get(documentId=doc_id).execute()
        end_index = doc['body']['content'][-1]['endIndex'] - 1
        
        requests = [{'insertText': {'location': {'index': end_index}, 'text': content}}]
        docs_service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
        
        return {"success": True, "doc_id": doc_id}
    except HttpError as e:
        return {"success": False, "error": str(e)}


def export_document(doc_id, format='pdf', output=None):
    """Export document in specified format."""
    _, drive_service, error = get_docs_service()
    if error:
        return error
    
    try:
        mime_types = {
            'pdf': 'application/pdf',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'txt': 'text/plain',
            'html': 'text/html'
        }
        
        mime_type = mime_types.get(format, 'application/pdf')
        request = drive_service.files().export_media(fileId=doc_id, mimeType=mime_type)
        
        if output:
            with open(output, 'wb') as f:
                f.write(request.execute())
            return {"success": True, "output_file": output}
        else:
            return {"success": True, "content": request.execute().decode('utf-8') if format == 'txt' else "[binary content]"}
    except HttpError as e:
        return {"success": False, "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Google Docs Operations")
    subparsers = parser.add_subparsers(dest='command')
    
    create_p = subparsers.add_parser('create')
    create_p.add_argument('--title', required=True)
    create_p.add_argument('--content')
    
    read_p = subparsers.add_parser('read')
    read_p.add_argument('--doc-id', required=True)
    
    append_p = subparsers.add_parser('append')
    append_p.add_argument('--doc-id', required=True)
    append_p.add_argument('--content', required=True)
    
    export_p = subparsers.add_parser('export')
    export_p.add_argument('--doc-id', required=True)
    export_p.add_argument('--format', choices=['pdf', 'docx', 'txt', 'html'], default='pdf')
    export_p.add_argument('--output')
    
    args = parser.parse_args()
    
    if args.command == 'create':
        result = create_document(args.title, args.content)
    elif args.command == 'read':
        result = read_document(args.doc_id)
    elif args.command == 'append':
        result = append_to_document(args.doc_id, args.content)
    elif args.command == 'export':
        result = export_document(args.doc_id, args.format, args.output)
    else:
        parser.print_help()
        sys.exit(1)
    
    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get('success') else 1)


if __name__ == '__main__':
    main()
