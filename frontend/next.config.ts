import type { NextConfig } from "next";
import { loadEnvConfig } from "@next/env";
import path from "node:path";

// Both applications read the one project-level .env. Only explicitly public
// values are copied into the browser build; DATABASE_URL remains server-only.
loadEnvConfig(path.resolve(process.cwd(), ".."), process.env.NODE_ENV !== "production", console, true);
process.env.NEXT_PUBLIC_SUPABASE_URL ||= process.env.SUPABASE_URL || "";

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  // Live routes render an authenticated client shell; opt in page by page
  // when a route has an actual instant-navigation loading state to validate.
  experimental: { instantInsights: { validationLevel: "manual-warning" } },
  images: {
    formats: ["image/avif", "image/webp"],
    unoptimized: false,
  },
};

export default nextConfig;
