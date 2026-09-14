/**
 * Client-side-only file peek for the upload preview step — counts lines
 * and reads the header row so the user can sanity-check a file before
 * committing. Deliberately does NOT parse amount-descriptions, map
 * canonical enums, or validate rows: that's the backend's job
 * (ARCHITECTURE.md §3 "no business rules duplicated in the browser").
 * See CROSS-SYSTEM-DEPENDENCIES.md's upload-preview note for the real gap
 * this stands in for — a proper dry-run endpoint that validates server-side
 * without creating a report.
 */
export interface FilePeek {
  headerColumns: string[];
  approxDataRowCount: number;
}

export async function peekSettlementFile(file: File): Promise<FilePeek> {
  const text = await file.text();
  const lines = text.split(/\r\n|\n|\r/).filter((line) => line.trim().length > 0);
  const [header, ...rest] = lines;
  const delimiter = header?.includes("\t") ? "\t" : ",";
  return {
    headerColumns: header ? header.split(delimiter).map((c) => c.trim()) : [],
    approxDataRowCount: rest.length,
  };
}
