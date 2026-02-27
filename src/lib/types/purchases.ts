import type { PaginatedResponse } from "@/lib/types/api";

export interface Supplier {
  id: string;
  code: string;
  name: string;
  is_active: boolean;
}

export interface SupplierParser {
  id: string;
  supplier: string;
  parser_key: string;
  version: number;
  description: string;
  is_active: boolean;
}

export type MatchStatus = "NEW_PRODUCT" | "MATCHED_PRODUCT" | "AMBIGUOUS" | "INVALID";

export interface ImportLine {
  id: string;
  line_no: number;
  raw_line: string;
  parsed_sku: string;
  parsed_name: string;
  parsed_qty: string | null;
  parsed_unit_cost: string | null;
  parsed_unit_price: string | null;
  sku: string;
  name: string;
  qty: string | null;
  unit_cost: string | null;
  unit_price: string | null;
  public_price: string | null;
  matched_product: string | null;
  match_status: MatchStatus;
  is_selected: boolean;
  notes: string;

  // Future feature (not implemented): image upload in preview table.
  preview_image_url?: string;
  preview_image_file?: File;
}

export interface ImportBatch {
  id: string;
  supplier: string;
  parser: string;
  raw_text: string;
  status: "DRAFT" | "PARSED" | "CONFIRMED" | "CANCELLED" | "ERROR";
  invoice_number: string | null;
  invoice_date: string | null;
  subtotal: string | null;
  tax: string | null;
  total: string | null;
  lines: ImportLine[];
}

export type SupplierListResponse = PaginatedResponse<Supplier>;
export type SupplierParserListResponse = PaginatedResponse<SupplierParser>;

export interface PreviewConfirmLinePayload {
  sku: string;
  name: string;
  qty: string | null;
  unit_cost: string | null;
  unit_price: string | null;
  public_price: string | null;
  is_selected: boolean;
  notes: string;
}

export interface PreviewConfirmPayload {
  supplier: string;
  parser: string;
  invoice_number?: string;
  invoice_date?: string;
  subtotal?: string;
  tax?: string;
  total?: string;
  raw_text: string;
  lines: PreviewConfirmLinePayload[];
}
