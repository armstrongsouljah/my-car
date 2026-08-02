import LandingContent from "@/components/LandingContent";

export const metadata = {
  // .absolute bypasses the root layout's `template: "%s · GlavBox"` — this
  // title already carries the brand name, so the template would double it up
  // ("... paperwork · GlavBox") and blow past what search results display.
  title: { absolute: "GlavBox — The glovebox for your car's paperwork" },
  description:
    "Track every car you own: service history, expenses, and reminders that catch what's due before you have to think about it. Plus a built-in assistant that knows your car.",
  robots: { index: true, follow: true },
  alternates: { canonical: "/" },
  openGraph: { url: "/" },
};

const JSON_LD = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: "GlavBox",
  applicationCategory: "LifestyleApplication",
  operatingSystem: "Web",
  description:
    "Track every car you own: service history, expenses, and reminders that catch what's due before you have to think about it.",
  offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
  sameAs: ["https://x.com/GlavboxApp"],
};

export default function Page() {
  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(JSON_LD) }} />
      <LandingContent />
    </>
  );
}
