import type { SaleResponse } from "@/lib/types/sales";
import type { LayawayDetailResponse } from "@/lib/types/layaway";

// ─── ESC/POS commands ──────────────────────────────────────────────────────────
const ESC = 0x1b;
const GS = 0x1d;
const LF = 0x0a;

const CMD_INIT = [ESC, 0x40];
const CMD_ALIGN_LEFT = [ESC, 0x61, 0x00];
const CMD_ALIGN_CENTER = [ESC, 0x61, 0x01];
const CMD_BOLD_ON = [ESC, 0x45, 0x01];
const CMD_BOLD_OFF = [ESC, 0x45, 0x00];
const CMD_DOUBLE_HEIGHT = [ESC, 0x21, 0x10];
const CMD_NORMAL_SIZE = [ESC, 0x21, 0x00];
const CMD_CUT = [GS, 0x56, 0x42, 0x00]; // partial cut + feed

// ─── Config & helpers ──────────────────────────────────────────────────────────
export interface TicketConfig {
  charWidth: number;
  storeAddress?: string;
  storePhone?: string;
  // Layaway abono context
  abonoAmount?: number;
  abonoMethod?: string;
}

function encode(str: string): number[] {
  const out: number[] = [];
  for (const ch of str) {
    out.push(ch.charCodeAt(0) & 0xff);
  }
  return out;
}

function money(value: string | number): string {
  return `$${Number(value).toFixed(2)}`;
}

function padLeft(str: string, len: number): string {
  return str.length >= len ? str : " ".repeat(len - str.length) + str;
}

function col2(left: string, right: string, width: number): string {
  const gap = width - left.length - right.length;
  if (gap <= 0) return left.slice(0, width - right.length - 1) + " " + right;
  return left + " ".repeat(gap) + right;
}

function separator(width: number): string {
  return "-".repeat(width);
}

function formatDateTime(iso: string | null): string {
  if (!iso) return "-";
  return new Intl.DateTimeFormat("es-MX", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

function formatDate(iso: string): string {
  return new Intl.DateTimeFormat("es-MX", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(new Date(iso));
}

function paymentLabel(method: string, cardLabel?: string): string {
  if (method === "CASH") return "Efectivo";
  if (method === "CUSTOMER_CREDIT") return "Saldo a favor";
  return cardLabel || "Tarjeta";
}

// ─── Builder ───────────────────────────────────────────────────────────────────
class Builder {
  private bytes: number[] = [];

  cmd(...codes: number[]): this {
    this.bytes.push(...codes);
    return this;
  }

  text(str: string): this {
    this.bytes.push(...encode(str));
    return this;
  }

  line(str = ""): this {
    return this.text(str).cmd(LF);
  }

  feed(n = 1): this {
    return this.cmd(ESC, 0x64, n);
  }

  build(): Uint8Array {
    return new Uint8Array(this.bytes);
  }
}

// ─── Shared header & footer ────────────────────────────────────────────────────
function buildHeader(b: Builder, storeName: string, subtitle: string, width: number): void {
  b.cmd(...CMD_ALIGN_CENTER)
    .cmd(...CMD_DOUBLE_HEIGHT)
    .cmd(...CMD_BOLD_ON)
    .line(storeName.slice(0, width))
    .cmd(...CMD_BOLD_OFF)
    .cmd(...CMD_NORMAL_SIZE)
    .line(subtitle)
    .line(separator(width));
}

export function buildFooter(b: Builder, config: TicketConfig): void {
  const { charWidth, storeAddress, storePhone } = config;
  b.cmd(...CMD_ALIGN_CENTER).feed(1).line("Gracias por su compra!");
  if (storeAddress) b.line(storeAddress.slice(0, charWidth));
  if (storePhone) b.line(`Tel: ${storePhone}`);
  b.feed(4).cmd(...CMD_CUT);
}

// ─── Sale ticket ───────────────────────────────────────────────────────────────
export function buildSaleTicketBytes(sale: SaleResponse, config: TicketConfig): Uint8Array {
  const { charWidth } = config;
  const b = new Builder();

  b.cmd(...CMD_INIT);

  buildHeader(b, "MOTO ISLA", "Ticket de venta", charWidth);

  b.cmd(...CMD_ALIGN_LEFT);
  b.line(`Fecha:   ${formatDateTime(sale.confirmed_at ?? sale.created_at)}`);
  b.line(`Cajero:  ${sale.cashier_username}`);
  if (sale.customer_summary) {
    b.line(`Cliente: ${sale.customer_summary.name.slice(0, charWidth - 9)}`);
    b.line(`Tel:     ${sale.customer_summary.phone}`);
  } else {
    b.line("Cliente: Mostrador");
  }
  b.line(separator(charWidth));

  // Products
  b.cmd(...CMD_BOLD_ON).line("PRODUCTOS:").cmd(...CMD_BOLD_OFF);
  for (const line of sale.lines) {
    const name = (line.product_name ?? line.product_sku ?? "Producto").slice(0, charWidth);
    const qty = Number(line.qty);
    const price = Number(line.unit_price);
    const disc = Number(line.discount_pct);
    const lineTotal = qty * price * (1 - disc / 100);
    b.line(name);
    const qtyStr = `  ${qty} x ${money(price)}`;
    b.line(col2(qtyStr, money(lineTotal), charWidth));
  }

  b.line(separator(charWidth));

  // Totals
  b.line(col2("SUBTOTAL:", padLeft(money(sale.subtotal), 10), charWidth));
  if (Number(sale.discount_amount) > 0) {
    b.line(col2("DESCUENTO:", padLeft(money(sale.discount_amount), 10), charWidth));
  }
  b.cmd(...CMD_BOLD_ON)
    .line(col2("TOTAL:", padLeft(money(sale.total), 10), charWidth))
    .cmd(...CMD_BOLD_OFF);
  b.line(separator(charWidth));

  // Payments
  for (const payment of sale.payments) {
    const label = paymentLabel(payment.method, payment.card_plan_label);
    b.line(col2(label, padLeft(money(payment.amount), 10), charWidth));
    if (payment.method === "CARD" && payment.installments_months && payment.installments_months > 1) {
      b.line(`  ${payment.installments_months} meses`);
    }
  }

  buildFooter(b, config);
  return b.build();
}

// ─── Layaway ticket ────────────────────────────────────────────────────────────
export type LayawayTicketType = "created" | "abono" | "liquidated";

export function buildLayawayTicketBytes(
  layaway: LayawayDetailResponse,
  type: LayawayTicketType,
  config: TicketConfig,
): Uint8Array {
  const { charWidth, abonoAmount, abonoMethod } = config;
  const b = new Builder();

  b.cmd(...CMD_INIT);

  const subtitleMap: Record<LayawayTicketType, string> = {
    created: "Apartado creado",
    abono: "Abono registrado",
    liquidated: "Apartado liquidado",
  };
  buildHeader(b, "MOTO ISLA", subtitleMap[type], charWidth);

  b.cmd(...CMD_ALIGN_LEFT);
  b.line(`Fecha:   ${formatDateTime(layaway.created_at)}`);
  b.line(`Cliente: ${(layaway.customer_name ?? "").slice(0, charWidth - 9)}`);
  b.line(`Tel:     ${layaway.customer_phone}`);
  if (type !== "liquidated") {
    b.line(`Vence:   ${formatDate(layaway.expires_at)}`);
  }
  b.line(separator(charWidth));

  // Products
  b.cmd(...CMD_BOLD_ON).line("PRODUCTOS:").cmd(...CMD_BOLD_OFF);
  for (const line of layaway.lines) {
    const name = (line.product_name ?? line.product_sku ?? "Producto").slice(0, charWidth);
    b.line(name);
    const qty = Number(line.qty);
    const price = Number(line.unit_price);
    const lineTotal = qty * price;
    b.line(col2(`  ${qty} x ${money(price)}`, money(lineTotal), charWidth));
  }

  b.line(separator(charWidth));
  b.line(col2("TOTAL APARTADO:", padLeft(money(layaway.total_price ?? layaway.total), 10), charWidth));

  if (type === "created") {
    b.line(col2("ABONO INICIAL:", padLeft(money(layaway.deposit_amount), 10), charWidth));
    b.line(col2("SALDO PENDIENTE:", padLeft(money(layaway.balance_due), 10), charWidth));
  } else if (type === "abono" && abonoAmount !== undefined) {
    b.line(separator(charWidth));
    b.cmd(...CMD_BOLD_ON)
      .line(col2("ABONO:", padLeft(money(abonoAmount), 10), charWidth))
      .cmd(...CMD_BOLD_OFF);
    if (abonoMethod) {
      b.line(`Método: ${paymentLabel(abonoMethod)}`);
    }
    b.line(col2("TOTAL PAGADO:", padLeft(money(layaway.amount_paid), 10), charWidth));
    b.line(col2("SALDO PENDIENTE:", padLeft(money(layaway.balance_due), 10), charWidth));
  } else if (type === "liquidated") {
    b.cmd(...CMD_BOLD_ON).line("** APARTADO LIQUIDADO **").cmd(...CMD_BOLD_OFF);
  }

  buildFooter(b, config);
  return b.build();
}

// ─── Test ticket ───────────────────────────────────────────────────────────────
export function buildTestTicketBytes(config: TicketConfig): Uint8Array {
  const { charWidth } = config;
  const b = new Builder();

  b.cmd(...CMD_INIT);
  buildHeader(b, "MOTO ISLA", "Ticket de prueba", charWidth);

  b.cmd(...CMD_ALIGN_LEFT)
    .line(`Ancho: ${charWidth} caracteres`)
    .line(`Fecha: ${formatDateTime(new Date().toISOString())}`)
    .line(separator(charWidth));

  b.cmd(...CMD_BOLD_ON).line("123456789012345678901234567890123456789012345678").cmd(...CMD_BOLD_OFF);
  b.line("|" + "-".repeat(charWidth - 2) + "|");
  b.line(col2("Columna izquierda", "Derecha", charWidth));
  b.line(separator(charWidth));

  buildFooter(b, config);
  return b.build();
}
