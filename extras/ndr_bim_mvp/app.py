#!/usr/bin/env python3
"""NDR BIM MVP app: request-on-demand ticket workflow for Clients and BIM Managers."""

from __future__ import annotations

import cgi
import html
import os
import sqlite3
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "ndr_bim_mvp.sqlite3"


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT NOT NULL,
                user_name TEXT NOT NULL,
                user_email TEXT NOT NULL,
                description TEXT
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS bim_managers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_name TEXT NOT NULL,
                user_email TEXT NOT NULL,
                tech_info TEXT
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_info TEXT NOT NULL,
                client_email TEXT NOT NULL,
                project_number TEXT NOT NULL,
                request_type TEXT NOT NULL,
                project_phase TEXT NOT NULL,
                description TEXT NOT NULL,
                ref_doc_path TEXT,
                due_date TEXT,
                status TEXT NOT NULL DEFAULT 'Open',
                manager_response TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )


def db_rows(query: str, params: tuple = ()):
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        cur = con.execute(query, params)
        return [dict(row) for row in cur.fetchall()]


def db_execute(query: str, params: tuple = ()) -> None:
    with sqlite3.connect(DB_PATH) as con:
        con.execute(query, params)
        con.commit()


def now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def esc(value: str | None) -> str:
    return html.escape(value or "")


class AppHandler(BaseHTTPRequestHandler):
    def _send_html(self, content: str, status: int = 200):
        body = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _redirect(self, location: str):
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", location)
        self.end_headers()

    def _layout(self, title: str, body: str):
        return f"""
<!doctype html>
<html>
<head>
  <meta charset='utf-8'>
  <title>{esc(title)}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; background: #f6f8fa; color: #212529; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
    .card {{ background: #fff; border: 1px solid #dce0e6; border-radius: 8px; padding: 16px; }}
    h1, h2 {{ margin-top: 0; }}
    input, select, textarea {{ width: 100%; margin-bottom: 10px; padding: 8px; box-sizing: border-box; }}
    button {{ background: #0d6efd; color: white; border: 0; border-radius: 6px; padding: 8px 12px; cursor: pointer; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; }}
    th, td {{ border: 1px solid #dce0e6; padding: 8px; vertical-align: top; }}
    tr:nth-child(even) {{ background: #fafafa; }}
    .muted {{ color: #6c757d; font-size: 12px; }}
    .status-Open {{ color: #0d6efd; }}
    .status-In\ Progress {{ color: #fd7e14; }}
    .status-Closed {{ color: #198754; }}
  </style>
</head>
<body>
  <h1>NDR BIM - Request on Demand (MVP)</h1>
  <p class='muted'>Roles: Client and BIM Manager</p>
  {body}
</body>
</html>
"""

    def _parse_form(self):
        ctype, pdict = cgi.parse_header(self.headers.get("Content-Type", ""))
        if ctype == "multipart/form-data":
            pdict["boundary"] = bytes(pdict["boundary"], "utf-8")
            form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ={"REQUEST_METHOD": "POST"})
            return form

        length = int(self.headers.get("Content-Length", 0))
        data = self.rfile.read(length).decode("utf-8")
        parsed = parse_qs(data)
        return {k: v[0] for k, v in parsed.items()}

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send_html(self._layout("Dashboard", self._dashboard()))
            return
        self._send_html(self._layout("Not found", "<p>Not found</p>"), status=404)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/clients":
            self._create_client()
        elif parsed.path == "/bim-managers":
            self._create_bim_manager()
        elif parsed.path == "/tickets":
            self._create_ticket()
        elif parsed.path.startswith("/tickets/") and parsed.path.endswith("/client-update"):
            ticket_id = int(parsed.path.split("/")[2])
            self._client_update(ticket_id)
        elif parsed.path.startswith("/tickets/") and parsed.path.endswith("/close"):
            ticket_id = int(parsed.path.split("/")[2])
            self._close_ticket(ticket_id)
        elif parsed.path.startswith("/tickets/") and parsed.path.endswith("/manager-update"):
            ticket_id = int(parsed.path.split("/")[2])
            self._manager_update(ticket_id)
        else:
            self._send_html(self._layout("Not found", "<p>Not found</p>"), status=404)

    def _create_client(self):
        form = self._parse_form()
        db_execute(
            "INSERT INTO clients(company_name,user_name,user_email,description) VALUES(?,?,?,?)",
            (form.get("company_name", ""), form.get("user_name", ""), form.get("user_email", ""), form.get("description", "")),
        )
        self._redirect("/")

    def _create_bim_manager(self):
        form = self._parse_form()
        db_execute(
            "INSERT INTO bim_managers(user_name,user_email,tech_info) VALUES(?,?,?)",
            (form.get("user_name", ""), form.get("user_email", ""), form.get("tech_info", "")),
        )
        self._redirect("/")

    def _create_ticket(self):
        form = self._parse_form()
        ref_doc_path = ""
        if isinstance(form, cgi.FieldStorage) and "ref_doc" in form and getattr(form["ref_doc"], "filename", ""):
            file_item = form["ref_doc"]
            safe_name = os.path.basename(file_item.filename)
            dest = UPLOADS_DIR / f"{datetime.utcnow().timestamp():.0f}_{safe_name}"
            with open(dest, "wb") as out:
                out.write(file_item.file.read())
            ref_doc_path = str(dest.relative_to(BASE_DIR))
        db_execute(
            """
            INSERT INTO tickets(company_info,client_email,project_number,request_type,project_phase,description,ref_doc_path,due_date,status,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                form.getfirst("company_info", "") if isinstance(form, cgi.FieldStorage) else form.get("company_info", ""),
                form.getfirst("client_email", "") if isinstance(form, cgi.FieldStorage) else form.get("client_email", ""),
                form.getfirst("project_number", "") if isinstance(form, cgi.FieldStorage) else form.get("project_number", ""),
                form.getfirst("request_type", "") if isinstance(form, cgi.FieldStorage) else form.get("request_type", ""),
                form.getfirst("project_phase", "") if isinstance(form, cgi.FieldStorage) else form.get("project_phase", ""),
                form.getfirst("description", "") if isinstance(form, cgi.FieldStorage) else form.get("description", ""),
                ref_doc_path,
                form.getfirst("due_date", "") if isinstance(form, cgi.FieldStorage) else form.get("due_date", ""),
                "Open",
                now(),
                now(),
            ),
        )
        self._redirect("/")

    def _client_update(self, ticket_id: int):
        form = self._parse_form()
        db_execute(
            "UPDATE tickets SET description=?, due_date=?, updated_at=? WHERE id=?",
            (form.get("description", ""), form.get("due_date", ""), now(), ticket_id),
        )
        self._redirect("/")

    def _close_ticket(self, ticket_id: int):
        db_execute("UPDATE tickets SET status='Closed', updated_at=? WHERE id=?", (now(), ticket_id))
        self._redirect("/")

    def _manager_update(self, ticket_id: int):
        form = self._parse_form()
        db_execute(
            "UPDATE tickets SET manager_response=?, status=?, updated_at=? WHERE id=?",
            (form.get("manager_response", ""), form.get("status", "Open"), now(), ticket_id),
        )
        self._redirect("/")

    def _dashboard(self):
        clients = db_rows("SELECT * FROM clients ORDER BY id DESC")
        managers = db_rows("SELECT * FROM bim_managers ORDER BY id DESC")
        tickets = db_rows("SELECT * FROM tickets ORDER BY id DESC")

        ticket_rows = "".join(
            f"""
<tr>
  <td>#{t['id']}<br><span class='muted'>{esc(t['created_at'])}</span></td>
  <td>{esc(t['company_info'])}<br>{esc(t['client_email'])}</td>
  <td>{esc(t['project_number'])}<br>{esc(t['request_type'])}<br>{esc(t['project_phase'])}</td>
  <td>{esc(t['description'])}<br><span class='muted'>Due: {esc(t['due_date'])}</span><br><span class='muted'>Ref: {esc(t['ref_doc_path'])}</span></td>
  <td class='status-{esc(t['status'])}'>{esc(t['status'])}<br><span class='muted'>{esc(t['manager_response'])}</span></td>
  <td>
    <form method='post' action='/tickets/{t['id']}/client-update'>
      <textarea name='description' placeholder='Client update'>{esc(t['description'])}</textarea>
      <input name='due_date' type='date' value='{esc(t['due_date'])}'>
      <button type='submit'>Client update</button>
    </form>
    <form method='post' action='/tickets/{t['id']}/manager-update'>
      <textarea name='manager_response' placeholder='BIM manager response'>{esc(t['manager_response'])}</textarea>
      <select name='status'>
        <option {'selected' if t['status']=='Open' else ''}>Open</option>
        <option {'selected' if t['status']=='In Progress' else ''}>In Progress</option>
        <option {'selected' if t['status']=='Closed' else ''}>Closed</option>
      </select>
      <button type='submit'>Manager update</button>
    </form>
    <form method='post' action='/tickets/{t['id']}/close'>
      <button type='submit'>Close ticket</button>
    </form>
  </td>
</tr>
"""
            for t in tickets
        )

        return f"""
<div class='grid'>
  <div class='card'>
    <h2>Register Client</h2>
    <form method='post' action='/clients'>
      <input name='company_name' placeholder='Company name' required>
      <input name='user_name' placeholder='User name' required>
      <input name='user_email' type='email' placeholder='User email' required>
      <textarea name='description' placeholder='Client info/description'></textarea>
      <button type='submit'>Save client</button>
    </form>
    <p class='muted'>Current clients: {len(clients)}</p>
  </div>
  <div class='card'>
    <h2>Register BIM Manager</h2>
    <form method='post' action='/bim-managers'>
      <input name='user_name' placeholder='User name' required>
      <input name='user_email' type='email' placeholder='User email' required>
      <textarea name='tech_info' placeholder='BIM tech info/description'></textarea>
      <button type='submit'>Save BIM manager</button>
    </form>
    <p class='muted'>Current BIM managers: {len(managers)}</p>
  </div>
</div>

<div class='card' style='margin-top:16px;'>
  <h2>Create Ticket (Client)</h2>
  <form method='post' action='/tickets' enctype='multipart/form-data'>
    <input name='company_info' placeholder='Company info' required>
    <input name='client_email' type='email' placeholder='Client email' required>
    <input name='project_number' placeholder='Project number' required>
    <input name='request_type' placeholder='Revit/BIM request type' required>
    <input name='project_phase' placeholder='Project phase' required>
    <textarea name='description' placeholder='Request description' required></textarea>
    <label>Request reference doc upload <input name='ref_doc' type='file'></label>
    <input name='due_date' type='date'>
    <button type='submit'>Place request ticket</button>
  </form>
</div>

<h2>Ticket Board (Client + BIM Manager)</h2>
<table>
  <thead><tr><th>ID</th><th>Company / Client</th><th>Project</th><th>Request</th><th>Status</th><th>Actions</th></tr></thead>
  <tbody>{ticket_rows or "<tr><td colspan='6'>No tickets yet.</td></tr>"}</tbody>
</table>
"""


def run(port: int = 8787):
    init_db()
    server = HTTPServer(("0.0.0.0", port), AppHandler)
    print(f"NDR BIM MVP running on http://0.0.0.0:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
