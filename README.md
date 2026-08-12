# Visual-Receipt-OCR-Daily-Bookkeeping-Automation
An automated, serverless pipeline hosted on Google Cloud Run that converts physical receipt images into structured JSON data using the Gemini API and updates daily accounting entries on Google Sheets.

---

## Features

* **Multimodal OCR Extraction**: Uses Google's Vertex AI API (model: Gemini-Flash) to extract structured fields (items, date, tax, vendor, and total amount) directly from receipt images via POST requests.
* **Automated Google Sheets Sync**: Uses a Google Cloud Service Account to seamlessly write extracted receipt data to a designated Google Drive Spreadsheet.
* **Daily Subtotal Management**: Groups transactions by date (`DD-MM-YYYY`), inserts new entries, and dynamically recalculates running daily subtotals.
* **Serverless Architecture**: Built with Python and containerized for Google Cloud Run for scalable execution.

---

## Workflow Architecture
```text
[Client App / Webhook / Apple Shortcuts]
                   │
                   │ (HTTP POST Image)
                   ▼
     [Google Cloud Run (Python)]
                   │
                   ├──► [Vertex AI API] (Parses image ──► Returns JSON)
                   ├──► [Google Drive API] (Authenticates via Service Account)
                   │
                   └──► [Google Sheets API] (Authenticates via Service Account)
                                 │
                                 ▼
                          [Google Sheet]
                                 ├── Locates / creates date sheet (DD-MM-YYYY)
                                 ├── Appends line items
                                 └── Recalculates daily subtotal
```
---

## Prerequisites

* **Google Cloud Project** with Cloud Run and Secret Manager enabled.
* **Google Cloud Service Account** with write access to the target Google Spreadsheet.

---

## Environment Variables

Configure the following environment variables in your Cloud Run deployment:

| Variable | Description |
| :--- | :--- |
| `X-API-KEY` | API key created by yourself. |
| `SPREADSHEET_ID` | The ID of the target Google Sheet located in Google Drive. |

---

## API Usage

### Endpoint

`POST /process-receipt`

### Sample Request

```bash
curl -X POST https://<your-cloud-run-service-url>/process-receipt \
  -H "X-API-KEY:YOUR_AUTH_KEY" \
  -F "file=@/path/to/receipt.jpg"
```

Copyright (c) 2026 [Mark1688288]

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
