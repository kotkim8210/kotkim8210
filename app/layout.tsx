import "./globals.css";
import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Coupang Partners Dashboard (MVP)",
  description: "매출 추이 및 A/B 테스트 비교 — 모의 데이터 기반 MVP",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
