export interface Venta {
  id: string;
  fecha: string;
  total: number;
  estado: "pagada" | "pendiente";
}

export async function getVentas(): Promise<Venta[]> {
  return [
    { id: "v1", fecha: "2026-02-26", total: 219.5, estado: "pagada" },
    { id: "v2", fecha: "2026-02-25", total: 79.99, estado: "pendiente" },
  ];
}
