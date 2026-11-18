/** @type {import('next').NextConfig} */
const backend = process.env.BACKEND_URL || "http://localhost:8000";
module.exports = {
  output: "standalone",
  eslint: { ignoreDuringBuilds: true },
  // AI reviews make many sequential model calls and can take over a minute.
  // Next's default proxy timeout (30s) cuts the request and shows "Internal Server Error".
  experimental: { proxyTimeout: 300000 },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
  },
};
