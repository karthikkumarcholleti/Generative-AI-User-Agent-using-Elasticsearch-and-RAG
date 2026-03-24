import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  // Removed rewrite rule - using API route handler instead for better timeout control
  // The API route at /pages/api/llm/[...path].ts handles all /api/llm/* requests
};

export default nextConfig;
