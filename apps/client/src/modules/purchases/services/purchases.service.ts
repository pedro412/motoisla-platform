import { httpClient } from "@/lib/api/http-client";
import type {
  ImportBatch,
  ImportLine,
  PreviewConfirmPayload,
  PurchaseReceipt,
  PurchaseReceiptListResponse,
  SupplierListResponse,
  SupplierParserListResponse,
} from "@/lib/types/purchases";

interface CreateImportBatchPayload {
  supplier: string;
  parser: string;
  raw_text: string;
  invoice_number?: string;
  invoice_date?: string;
  subtotal?: string;
  tax?: string;
  total?: string;
}

interface UpdateImportBatchPayload {
  invoice_number?: string;
  invoice_date?: string;
  subtotal?: string;
  tax?: string;
  total?: string;
}

interface UpdateImportLinePayload {
  sku?: string;
  name?: string;
  qty?: string;
  unit_cost?: string;
  unit_price?: string;
  public_price?: string;
  is_selected?: boolean;
  notes?: string;
}

export const purchasesService = {
  getSuppliers() {
    return httpClient.get<SupplierListResponse>("/suppliers/");
  },

  getParsersBySupplier(supplierId: string) {
    return httpClient.get<SupplierParserListResponse>("/supplier-parsers/", {
      supplier: supplierId,
    });
  },

  createImportBatch(payload: CreateImportBatchPayload) {
    return httpClient.post<CreateImportBatchPayload, ImportBatch>("/import-batches/", payload);
  },

  parseImportBatch(batchId: string) {
    return httpClient.post<Record<string, never>, ImportBatch>(`/import-batches/${batchId}/parse/`, {});
  },

  updateImportLine(lineId: string, payload: UpdateImportLinePayload) {
    return httpClient.patch<UpdateImportLinePayload, ImportLine>(`/import-lines/${lineId}/`, payload);
  },

  updateImportBatch(batchId: string, payload: UpdateImportBatchPayload) {
    return httpClient.patch<UpdateImportBatchPayload, ImportBatch>(`/import-batches/${batchId}/`, payload);
  },

  confirmImportBatch(batchId: string) {
    return httpClient.post<Record<string, never>, { batch_id: string; purchase_receipt_id: string }>(
      `/import-batches/${batchId}/confirm/`,
      {},
    );
  },

  previewConfirm(payload: PreviewConfirmPayload) {
    return httpClient.post<PreviewConfirmPayload, { batch_id: string; purchase_receipt_id: string }>(
      "/import-batches/preview-confirm/",
      payload,
    );
  },

  getPurchaseReceipts() {
    return httpClient.get<PurchaseReceiptListResponse>("/purchase-receipts/");
  },

  getPurchaseReceipt(receiptId: string) {
    return httpClient.get<PurchaseReceipt>(`/purchase-receipts/${receiptId}/`);
  },

  deletePurchaseReceipt(receiptId: string) {
    return httpClient.delete<void>(`/purchase-receipts/${receiptId}/`);
  },
};
