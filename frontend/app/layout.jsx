import "./globals.css";
import { ThemeProvider } from "@/components/ThemeProvider";
import { TelemetryProvider } from "@/components/TelemetryProvider";
import ServiceWorkerRegistration from "@/components/ServiceWorkerRegistration";
import { THEME_KEY } from "@/lib/theme";

const APP_URL = process.env.NEXT_PUBLIC_APP_URL || "https://app.glavbox.com";

export const metadata = {
  metadataBase: new URL(APP_URL),
  title: { default: "GlavBox", template: "%s · GlavBox" },
  description: "Track your cars — service history, reminders and expenses.",
  applicationName: "GlavBox",
  icons: {
    icon: [
      { url: "/icons/favicon-16.png", sizes: "16x16", type: "image/png" },
      { url: "/icons/favicon-32.png", sizes: "32x32", type: "image/png" },
      { url: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
    ],
    apple: [{ url: "/icons/apple-touch-icon.png", sizes: "180x180", type: "image/png" }],
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "GlavBox",
  },
  // The authenticated app (dashboard, cars, expenses, etc.) has nothing worth
  // indexing and shouldn't show up in search — public pages opt back in
  // individually (see app/page.jsx, app/contact, app/privacy).
  robots: { index: false, follow: false },
  // title/description deliberately omitted below — Next fills both in from
  // the resolved page metadata (the `title`/`description` above, or a page's
  // own override) whenever a page doesn't set its own openGraph/twitter.
  openGraph: { type: "website", siteName: "GlavBox" },
  twitter: { card: "summary_large_image", site: "@GlavboxApp" },
};

export const viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f9fafb" },
    { media: "(prefers-color-scheme: dark)", color: "#04120c" },
  ],
};

const NO_FLASH_SCRIPT = `(function(){try{var t=localStorage.getItem(${JSON.stringify(THEME_KEY)})||"system";var d=t==="dark"||(t==="system"&&window.matchMedia("(prefers-color-scheme: dark)").matches);document.documentElement.classList.toggle("dark",d);}catch(e){}})();`;

export default function RootLayout({ children }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: NO_FLASH_SCRIPT }} />
      </head>
      <body className="min-h-screen bg-gray-50 text-gray-900 antialiased dark:bg-gray-950 dark:text-gray-100">
        <ServiceWorkerRegistration />
        <ThemeProvider>
          <TelemetryProvider>
            <div className="mx-auto min-h-screen w-full max-w-lg">{children}</div>
          </TelemetryProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
