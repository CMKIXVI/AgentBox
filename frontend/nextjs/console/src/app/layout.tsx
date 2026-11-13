import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AgentBox Console",
  description: "Create, operate, evaluate, and govern AI agents with AgentBox.",
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
