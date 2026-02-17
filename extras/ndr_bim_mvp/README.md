# NDR BIM MVP App

A lightweight MVP web app for **Revit/BIM request-on-demand** workflows.

## Roles supported

- **Client**
  - Stores client profile (company name, user name, user email, description).
  - Places a request ticket.
  - Updates ticket request details.
  - Closes ticket.
- **BIM Manager**
  - Stores BIM manager profile (user name, user email, tech info/description).
  - Tracks incoming tickets.
  - Answers tickets.
  - Updates ticket status.

## Ticket fields

- Company info
- Client email
- Project number
- Revit/BIM request type
- Project phase
- Request description
- Reference document upload
- Due date
- Status + manager response

## Run

```bash
python extras/ndr_bim_mvp/app.py
```

Then open: <http://localhost:8787>

Data is persisted in:

- `extras/ndr_bim_mvp/data/ndr_bim_mvp.sqlite3`
- `extras/ndr_bim_mvp/data/uploads/`
