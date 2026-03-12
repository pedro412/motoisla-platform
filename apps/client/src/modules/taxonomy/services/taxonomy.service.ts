import { httpClient } from "@/lib/api/http-client";
import type { BrandListResponse, ProductTypeListResponse } from "@/lib/types/taxonomy";

export const taxonomyService = {
  searchBrands(query: string) {
    return httpClient.get<BrandListResponse>("/brands/", { q: query || undefined });
  },

  createBrand(name: string) {
    return httpClient.post<{ name: string }, { id: string; name: string }>("/brands/", { name });
  },

  searchProductTypes(query: string) {
    return httpClient.get<ProductTypeListResponse>("/product-types/", { q: query || undefined });
  },

  createProductType(name: string) {
    return httpClient.post<{ name: string }, { id: string; name: string }>("/product-types/", { name });
  },
};
