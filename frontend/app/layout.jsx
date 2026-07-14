import "./globals.css";

export const metadata = {
  title: "My Car",
  description: "Track your cars — service history, reminders and expenses.",
};

export const viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50 text-gray-900 antialiased">
        <div className="mx-auto min-h-screen w-full max-w-lg">{children}</div>
      </body>
    </html>
  );
}
