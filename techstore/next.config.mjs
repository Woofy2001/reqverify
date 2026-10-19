/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Enable server components external packages for native Node modules if needed
  serverExternalPackages: ["node:sqlite"]
};

export default nextConfig;
