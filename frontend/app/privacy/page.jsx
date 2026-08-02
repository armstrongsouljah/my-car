import PrivacyContent from "@/components/PrivacyContent";

export const metadata = {
  title: "Privacy & Security",
  description: "How GlavBox handles your data: what we collect, why, and how you stay in control of it.",
  robots: { index: true, follow: true },
  alternates: { canonical: "/privacy" },
  openGraph: { url: "/privacy" },
};

export default function Page() {
  return <PrivacyContent />;
}
