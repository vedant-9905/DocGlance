import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "DocGlance — Document-Grounded Conversational Intelligence",
  description:
    "Explore, summarize, and analyze any document with Google Gemini style conversational intelligence. Strictly grounded in your document.",
  keywords: ["DocGlance", "Gemini Doc", "Google Gemini", "Document AI", "Conversational NLP", "Offline LLM"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="antialiased bg-[#131314] text-[#e3e3e3]">{children}</body>
    </html>
  );
}
