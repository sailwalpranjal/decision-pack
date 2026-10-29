import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "decision-pack",
  description: "Upload a spec and a CSV, see where a metric gap comes from.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
