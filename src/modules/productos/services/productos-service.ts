export interface Producto {
  id: string;
  nombre: string;
  precio: number;
  stock: number;
}

export async function getProductos(): Promise<Producto[]> {
  return [
    { id: "p1", nombre: "Casco Integral", precio: 129.99, stock: 17 },
    { id: "p2", nombre: "Guantes Touring", precio: 39.99, stock: 42 },
  ];
}
