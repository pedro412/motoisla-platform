import type { PaginatedResponse } from "@/lib/types/api";

export interface Brand {
  id: string;
  name: string;
  normalized_name: string;
  is_active: boolean;
}

export interface ProductType {
  id: string;
  name: string;
  normalized_name: string;
  is_active: boolean;
}

export type BrandListResponse = PaginatedResponse<Brand>;
export type ProductTypeListResponse = PaginatedResponse<ProductType>;
