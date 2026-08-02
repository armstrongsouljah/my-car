import { APP_URL } from "@/lib/site";

export default function sitemap() {
  const lastModified = new Date();
  return [
    { url: APP_URL, lastModified, changeFrequency: "monthly", priority: 1 },
    { url: `${APP_URL}/contact`, lastModified, changeFrequency: "yearly", priority: 0.5 },
    { url: `${APP_URL}/privacy`, lastModified, changeFrequency: "yearly", priority: 0.3 },
  ];
}
