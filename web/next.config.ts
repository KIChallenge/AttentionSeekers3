import type { NextConfig } from "next";

const API = process.env.STATAGENT_API ?? "http://127.0.0.1:8000";

const config: NextConfig = {
  devIndicators: false,
  // Compression would buffer Server-Sent Events from the backend.
  compress: false,
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API}/api/:path*` }];
  },
};

export default config;
