import ContactForm from "@/components/ContactForm";

export const metadata = {
  title: "Contact support",
  description: "Get in touch with GlavBox support — account help, app questions, or feature suggestions.",
  robots: { index: true, follow: true },
  alternates: { canonical: "/contact" },
  openGraph: { url: "/contact" },
};

export default function Page() {
  return <ContactForm />;
}
