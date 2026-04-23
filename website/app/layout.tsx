import type { Metadata } from "next";
import { Outfit } from "next/font/google";
import "./globals.css";

const outfit = Outfit({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "prism — RL Environment Dashboard",
  description: "OpenEnv-native RL environment · Multi-Agent Reliability Training · Meta Hackathon 2026",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${outfit.className} bg-[#050508] text-[#e2e8f0] antialiased`}>
        {children}
      </body>
    </html>
  );
}
