"use client";
import Config from "../config/config";

class Api {
  private static baseUrl: string = Config.NEXT_PUBLIC_API_BASE_URL;

  private static getHeaders() {
    const token = localStorage.getItem("token");
    return {
      "Content-Type": "application/json",
      Accept: "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };
  }

  private static async formatResponse(
    response: Response,
  ): Promise<Record<string, any>> {
    let res = {};
    try {
      res = await response.json();
    } catch (e) {
      res = {};
    }
    return { status: response.status, ok: response.ok, ...res };
  }

  static async get(url: string) {
    const response = await fetch(`${this.baseUrl}${url}`, {
      headers: this.getHeaders(),
    });
    return this.formatResponse(response);
  }

  static async post(url: string, data: any) {
    const response = await fetch(`${this.baseUrl}${url}`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify(data),
    });
    return this.formatResponse(response);
  }
}

export default Api;
