import { google } from "googleapis";

const SHEET_NAME = "Sheet1";
const HEADER_RANGE = `${SHEET_NAME}!A1:L1`;
const DATA_RANGE = `${SHEET_NAME}!A2:L1000`;

const HEADERS = [
  "topic_id",       // A
  "category",       // B
  "card_type",      // C
  "topic_title",    // D — user input
  "json_data",      // E
  "cover_img_url",  // F
  "body_img_url",   // G
  "cta_img_url",    // H
  "caption",        // I
  "status",         // J — pending|processing|images_done|uploaded|error_*
  "error_message",  // K
  "processed_at",   // L
];

const COLS = {
  topic_id: "A", category: "B", card_type: "C", topic_title: "D",
  json_data: "E", cover_img_url: "F", body_img_url: "G", cta_img_url: "H",
  caption: "I", status: "J", error_message: "K", processed_at: "L",
};

function rowToObject(row, rowIndex) {
  return {
    rowIndex,
    topic_id: row[0] ?? "",
    category: row[1] ?? "",
    card_type: row[2] ?? "",
    topic_title: row[3] ?? "",
    json_data: row[4] ?? "",
    cover_img_url: row[5] ?? "",
    body_img_url: row[6] ?? "",
    cta_img_url: row[7] ?? "",
    caption: row[8] ?? "",
    status: row[9] ?? "",
    error_message: row[10] ?? "",
    processed_at: row[11] ?? "",
  };
}

export class SheetsClient {
  constructor({ spreadsheetId, keyFile }) {
    if (!spreadsheetId) throw new Error("GOOGLE_SHEETS_ID 환경변수 필요");
    if (!keyFile) throw new Error("GOOGLE_SERVICE_ACCOUNT_JSON 환경변수 필요 (service account JSON 파일 경로)");
    this.spreadsheetId = spreadsheetId;
    this.auth = new google.auth.GoogleAuth({
      keyFile,
      scopes: ["https://www.googleapis.com/auth/spreadsheets"],
    });
    this.sheets = google.sheets({ version: "v4", auth: this.auth });
  }

  async ensureHeaders() {
    const res = await this.sheets.spreadsheets.values.get({
      spreadsheetId: this.spreadsheetId,
      range: HEADER_RANGE,
    });
    const existing = res.data.values?.[0] ?? [];
    const same = existing.length === HEADERS.length &&
      existing.every((v, i) => v === HEADERS[i]);
    if (!same) {
      await this.sheets.spreadsheets.values.update({
        spreadsheetId: this.spreadsheetId,
        range: HEADER_RANGE,
        valueInputOption: "RAW",
        requestBody: { values: [HEADERS] },
      });
      return { created: existing.length === 0 };
    }
    return { created: false };
  }

  async readAll() {
    const res = await this.sheets.spreadsheets.values.get({
      spreadsheetId: this.spreadsheetId,
      range: DATA_RANGE,
    });
    const rows = res.data.values ?? [];
    return rows.map((row, i) => rowToObject(row, i + 2)); // sheet rows are 1-indexed; header at row 1
  }

  /** Update specific cells in a row. `updates` is an object keyed by column name. */
  async updateCells(rowIndex, updates) {
    const data = [];
    for (const [key, value] of Object.entries(updates)) {
      const col = COLS[key];
      if (!col) throw new Error(`Unknown column: ${key}`);
      data.push({
        range: `${SHEET_NAME}!${col}${rowIndex}`,
        values: [[String(value ?? "")]],
      });
    }
    if (data.length === 0) return;
    await this.sheets.spreadsheets.values.batchUpdate({
      spreadsheetId: this.spreadsheetId,
      requestBody: { valueInputOption: "RAW", data },
    });
  }

  /** Reset any rows currently in 'processing' state back to 'pending' (crash recovery). */
  async resetStaleProcessing() {
    const all = await this.readAll();
    const stale = all.filter((r) => r.status?.toLowerCase() === "processing");
    if (stale.length === 0) return 0;
    const data = stale.map((r) => ({
      range: `${SHEET_NAME}!${COLS.status}${r.rowIndex}`,
      values: [["pending"]],
    }));
    await this.sheets.spreadsheets.values.batchUpdate({
      spreadsheetId: this.spreadsheetId,
      requestBody: { valueInputOption: "RAW", data },
    });
    return stale.length;
  }
}
