import { createRequire } from "module";

const pkg = createRequire(import.meta.url)("./package.json");

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  env: {
    // Bakes package.json's version into the client bundle at build time so
    // telemetry signals can be tagged with the app version they came from.
    NEXT_PUBLIC_APP_VERSION: pkg.version,
  },
};

export default nextConfig;
