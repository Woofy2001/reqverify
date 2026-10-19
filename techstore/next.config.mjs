/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Enable server components external packages for native Node modules if needed
  serverExternalPackages: ["node:sqlite"],
  env: {
    NEXT_PUBLIC_MUTANT: process.env.MUTANT || "",
  },
};

export default nextConfig;
