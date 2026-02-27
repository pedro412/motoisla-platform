import { ApiError } from "@/lib/api/errors";

type HttpMethod = "GET" | "POST" | "PUT" | "DELETE";

type RequestOptions = Omit<RequestInit, "body" | "method">;

const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:3001";

class HttpClient {
  private async request<TResponse>(
    method: HttpMethod,
    path: string,
    body?: unknown,
    options: RequestOptions = {},
  ): Promise<TResponse> {
    const response = await fetch(`${baseUrl}${path}`, {
      method,
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
      ...options,
      body: body ? JSON.stringify(body) : undefined,
    });

    if (!response.ok) {
      let errorPayload: unknown;

      try {
        errorPayload = await response.json();
      } catch {
        errorPayload = undefined;
      }

      const errorMessage =
        typeof errorPayload === "object" &&
        errorPayload !== null &&
        "message" in errorPayload &&
        typeof errorPayload.message === "string"
          ? errorPayload.message
          : "Request failed";

      const errorCode =
        typeof errorPayload === "object" &&
        errorPayload !== null &&
        "code" in errorPayload &&
        typeof errorPayload.code === "string"
          ? errorPayload.code
          : "REQUEST_FAILED";

      throw new ApiError(errorMessage, response.status, errorCode, errorPayload);
    }

    if (response.status === 204) {
      return undefined as TResponse;
    }

    return (await response.json()) as TResponse;
  }

  get<TResponse>(path: string, options?: RequestOptions) {
    return this.request<TResponse>("GET", path, undefined, options);
  }

  post<TRequest, TResponse>(path: string, body: TRequest, options?: RequestOptions) {
    return this.request<TResponse>("POST", path, body, options);
  }

  put<TRequest, TResponse>(path: string, body: TRequest, options?: RequestOptions) {
    return this.request<TResponse>("PUT", path, body, options);
  }

  delete<TResponse>(path: string, options?: RequestOptions) {
    return this.request<TResponse>("DELETE", path, undefined, options);
  }
}

export const httpClient = new HttpClient();
