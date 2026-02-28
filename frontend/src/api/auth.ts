import { api } from "./client";

export interface UserResponse {
  id: string;
  username: string;
  email: string;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export function register(
  username: string,
  email: string,
  password: string
): Promise<UserResponse> {
  return api.post("/auth/register", { username, email, password });
}

export function login(
  username: string,
  password: string
): Promise<TokenResponse> {
  const form = new URLSearchParams({ username, password });
  return api.postForm("/auth/token", form);
}
