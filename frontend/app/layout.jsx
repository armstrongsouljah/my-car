import "./globals.css";
import { ThemeProvider } from "@/components/ThemeProvider";
import { THEME_KEY } from "@/lib/theme";

export const metadata = {
  title: "My Car",
  description: "Track your cars — service history, reminders and expenses.",
};

export const viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
};

const NO_FLASH_SCRIPT = `(function(){try{var t=localStorage.getItem(${JSON.stringify(THEME_KEY)})||"system";var d=t==="dark"||(t==="system"&&window.matchMedia("(prefers-color-scheme: dark)").matches);document.documentElement.classList.toggle("dark",d);}catch(e){}})();`;

export default function RootLayout({ children }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: NO_FLASH_SCRIPT }} />
      </head>
      <body className="min-h-screen bg-gray-50 text-gray-900 antialiased dark:bg-gray-950 dark:text-gray-100">
        <ThemeProvider>
          <div className="mx-auto min-h-screen w-full max-w-lg">{children}</div>
        </ThemeProvider>
      </body>
    </html>
  );
}
