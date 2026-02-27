import type { MatchStatus } from "@/lib/types/purchases";

const IVA_RATE = 0.16;
const PUBLIC_MARKUP = 1.3;

export interface ParsedPreviewLine {
  sku: string;
  name: string;
  qty: string | null;
  unit_cost: string | null;
  unit_price: string | null;
  public_price: string | null;
  is_selected: boolean;
  notes: string;
  raw_line: string;
  match_status: MatchStatus;
}

interface PendingLine {
  sku: string;
  qty: number | null;
  name: string;
  rawLine: string;
}

const ITEM_HEADER_REGEX = /^\*+\s+([A-Z0-9-]+)\s+(\d+(?:\.\d+)?)\s+\S+\s+(.+)$/i;
const AMOUNTS_REGEX = /^\s*([\d,]+(?:\.\d{1,2})?)\s+([\d,]+(?:\.\d{1,2})?)\s*$/;

const IGNORE_LINE_PATTERNS = [/^NO\.COM\s+/i, /CFDI/i, /CLAVE\s+PRODUCTO/i, /CLAVE\s+PEDIMENTO/i];

function shouldIgnoreLine(line: string) {
  return IGNORE_LINE_PATTERNS.some((pattern) => pattern.test(line));
}

function parseNumeric(input: string): number {
  const parsed = Number(input.replace(/,/g, ""));
  return Number.isFinite(parsed) ? parsed : 0;
}

function toMoney(value: number): string {
  return value.toFixed(2);
}

function buildInvalidLine(pending: PendingLine): ParsedPreviewLine {
  return {
    sku: pending.sku,
    name: pending.name,
    qty: pending.qty !== null ? pending.qty.toFixed(2) : null,
    unit_cost: null,
    unit_price: null,
    public_price: null,
    is_selected: false,
    notes: "Linea sin importes detectados. Revisar captura.",
    raw_line: pending.rawLine,
    match_status: "INVALID",
  };
}

export function parseMyesaInvoice(rawText: string): ParsedPreviewLine[] {
  const lines = rawText.split(/\r?\n/);
  const parsed: ParsedPreviewLine[] = [];
  let pending: PendingLine | null = null;

  for (const source of lines) {
    const line = source.trim();
    if (!line || shouldIgnoreLine(line)) {
      continue;
    }

    const header = line.match(ITEM_HEADER_REGEX);
    if (header) {
      if (pending) {
        parsed.push(buildInvalidLine(pending));
      }

      pending = {
        sku: header[1].toUpperCase(),
        qty: parseNumeric(header[2]),
        name: header[3].trim(),
        rawLine: line,
      };
      continue;
    }

    const amounts = line.match(AMOUNTS_REGEX);
    if (amounts && pending) {
      const unitCost = parseNumeric(amounts[1]);
      const unitPrice = unitCost * (1 + IVA_RATE);
      const publicPrice = unitPrice * PUBLIC_MARKUP;

      parsed.push({
        sku: pending.sku,
        name: pending.name,
        qty: pending.qty !== null ? pending.qty.toFixed(2) : null,
        unit_cost: toMoney(unitCost),
        unit_price: toMoney(unitPrice),
        public_price: toMoney(publicPrice),
        is_selected: true,
        notes: "",
        raw_line: `${pending.rawLine} | ${line}`,
        match_status: pending.sku ? "NEW_PRODUCT" : "INVALID",
      });
      pending = null;
    }
  }

  if (pending) {
    parsed.push(buildInvalidLine(pending));
  }

  return parsed;
}
