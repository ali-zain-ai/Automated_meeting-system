import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MindFuelByAli — Free AI & ML Consultations",
  description:
    "Book a free consultation or project discussion with Ali. Expert guidance on AI, Machine Learning, Deep Learning, Data Science, and tech. Powered by MindFuelByAli.",
  keywords: [
    "AI consultation",
    "ML consultation",
    "deep learning",
    "data science",
    "free meeting",
    "MindFuelByAli",
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
