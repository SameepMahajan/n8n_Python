"""
outlook_reader.py
-----------------
Handles connecting to Outlook via win32com and fetching
emails that match a subject keyword.
"""

import win32com.client


def connect_to_outlook():
    """Return the Outlook MAPI namespace."""
    outlook = win32com.client.Dispatch("Outlook.Application")
    return outlook.GetNamespace("MAPI")


def get_inbox(namespace, folder_name: str = "Inbox"):
    """Return the Inbox folder from the MAPI namespace."""
    # 6 = olFolderInbox
    return namespace.GetDefaultFolder(6)


def fetch_itinerary_emails(keyword: str = "Itinerary", sort_descending: bool = True) -> list:
    """
    Connect to Outlook and return all MailItems whose subject
    contains `keyword` (case-insensitive).
    """
    namespace = connect_to_outlook()
    inbox = get_inbox(namespace)

    messages = inbox.Items
    messages.Sort("[ReceivedTime]", sort_descending)

    matched = []
    for message in messages:
        try:
            if keyword.lower() in message.Subject.lower():
                matched.append(message)
        except AttributeError:
            continue  # skip non-mail items (meetings, notes, etc.)

    print(f"[OutlookReader] Found {len(matched)} email(s) matching keyword: '{keyword}'")
    return matched


def get_email_metadata(message) -> dict:
    """Extract basic metadata from an Outlook MailItem."""
    return {
        "subject": message.Subject,
        "received": str(message.ReceivedTime),
        "sender": message.SenderEmailAddress,
    }


def get_html_body(message) -> str:
    """Return HTML body of a mail item, fallback to plain text."""
    try:
        return message.HTMLBody or message.Body or ""
    except Exception:
        return message.Body or ""
