import { createRequire } from "module";

const pkg = createRequire(import.meta.url)("./package.json");

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  env: {
    // Bakes a version into the client bundle at build time so telemetry
    // signals can be tagged with the app version they came from, and so it
    // can be surfaced on the Settings page (see #74). The Docker build arg
    // (release tag / "dev-<sha>", set by the deploy workflow) wins when
    // present; package.json's version is just the local-dev fallback — this
    // key would otherwise unconditionally clobber the build arg, since a
    // value set here overrides whatever's already in process.env.
    NEXT_PUBLIC_APP_VERSION: process.env.NEXT_PUBLIC_APP_VERSION || pkg.version,
  },
};

export default nextConfig;
