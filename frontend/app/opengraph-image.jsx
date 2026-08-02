import { ImageResponse } from "next/og";

export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

// Root-level file-convention image: Next.js wires this into `og:image`/
// `twitter:image` for every route that doesn't define its own, so the
// landing page and the rest of the public surface share one branded card
// instead of a generic link preview with no image at all.
export default function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: "#04120c",
          backgroundImage: "radial-gradient(circle at 50% 25%, rgba(52,211,153,0.35), transparent 60%)",
        }}
      >
        <div style={{ fontSize: 96, fontWeight: 700, color: "#ffffff", letterSpacing: -1 }}>GlavBox</div>
        <div style={{ marginTop: 20, fontSize: 32, color: "rgba(209,250,229,0.85)" }}>
          The glovebox for your car&apos;s paperwork
        </div>
      </div>
    ),
    { ...size }
  );
}
